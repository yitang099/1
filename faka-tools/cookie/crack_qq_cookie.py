#!/usr/bin/env python3
"""从 .body/.html/JS 提取 showOrder(id,skey) 对。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SHOWORDER = re.compile(r"showOrder\s*\(\s*(\d+)\s*,\s*['\"]([^'\"]+)['\"]")
SKEY_JSON = re.compile(r'"skey"\s*:\s*"([^"]{6,})"', re.I)
ID_JSON = re.compile(r'"id"\s*:\s*"?(\d+)"?', re.I)
KMINFO = re.compile(r"kminfo|卡密", re.I)
JS_SKEY_HINT = re.compile(r"(?:skey|sign|token)\s*[:=]\s*['\"]([^'\"]{8,})['\"]", re.I)


def analyze(text: str, src: str) -> dict:
    rec: dict = {
        "source": src,
        "showOrder": [{"id": a, "skey": b} for a, b in SHOWORDER.findall(text)],
        "pairs": [],
        "js_hints": JS_SKEY_HINT.findall(text)[:10],
        "kminfo": bool(KMINFO.search(text)),
    }
    if text.strip().startswith("{"):
        try:
            data = json.loads(text)
            items = data if isinstance(data, list) else data.get("data", [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and item.get("id") and item.get("skey"):
                        rec["pairs"].append({"id": item["id"], "skey": item["skey"]})
        except json.JSONDecodeError:
            pass
    if not rec["pairs"] and '"skey"' in text:
        skeys = SKEY_JSON.findall(text)
        ids = ID_JSON.findall(text)
        for i, sk in enumerate(skeys[:20]):
            oid = ids[i] if i < len(ids) else None
            if oid:
                rec["pairs"].append({"id": oid, "skey": sk})
    return rec


def scan_path(inp: Path) -> tuple[list[dict], list[dict]]:
    files = list(inp.rglob("*")) if inp.is_dir() else [inp]
    results: list[dict] = []
    pairs: list[dict] = []
    for fp in files:
        if not fp.is_file():
            continue
        if fp.suffix not in (".body", ".html", ".js", ".json", ".txt", ".php") and "body" not in fp.name:
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rec = analyze(text, str(fp))
        if rec["showOrder"] or rec["pairs"] or rec["kminfo"] or rec["js_hints"]:
            results.append(rec)
        for p in rec["showOrder"]:
            pairs.append({"id": p["id"], "skey": p["skey"], "source": str(fp)})
        for p in rec["pairs"]:
            pairs.append({**p, "source": str(fp)})
    return results, pairs


def main() -> int:
    ap = argparse.ArgumentParser(description="从 body/JS 提取 skey 对")
    ap.add_argument("--input", required=True, help="文件或目录")
    ap.add_argument("--out", default="/data/tools/faka/out/crack_skey_report.json")
    args = ap.parse_args()
    inp = Path(args.input)
    if not inp.exists():
        print(json.dumps({"error": "not found", "path": str(inp)}), file=sys.stderr)
        return 2
    results, pairs = scan_path(inp)
    seen: set[tuple[str, str]] = set()
    uniq: list[dict] = []
    for p in pairs:
        key = (str(p.get("id")), str(p.get("skey")))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    report = {"results": results, "pairs": uniq, "pair_count": len(uniq)}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(results), "pairs": len(uniq), "out": str(out)}, ensure_ascii=False))
    return 0 if uniq else 1


if __name__ == "__main__":
    raise SystemExit(main())
