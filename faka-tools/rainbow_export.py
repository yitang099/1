#!/usr/bin/env python3
"""彩虹订单卡密导出为 txt。"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def extract_km(data: dict) -> list[str]:
    lines: list[str] = []
    for key in ("kminfo", "km", "card", "cards", "data"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            lines.append(val.strip())
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    lines.append(item)
                elif isinstance(item, dict):
                    lines.append(json.dumps(item, ensure_ascii=False))
    raw = json.dumps(data, ensure_ascii=False)
    for m in re.findall(r'[\w@.:+-]{8,}', raw):
        if any(x in m.lower() for x in ("kminfo", "account", "password")):
            continue
        if len(m) > 12:
            lines.append(m)
    return list(dict.fromkeys(lines))


def main() -> None:
    ap = argparse.ArgumentParser(description="彩虹订单导出 txt")
    ap.add_argument("input", help="dump 目录或 jsonl")
    ap.add_argument("-o", "--out", default="/data/tools/faka/out/rainbow_cards.txt")
    args = ap.parse_args()
    inp = Path(args.input)
    cards: list[str] = []

    if inp.is_dir():
        for fp in sorted(inp.glob("order_*.json")):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                cards.extend(extract_km(data))
            except Exception:
                pass
    else:
        for line in inp.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                payload = row.get("data") if isinstance(row.get("data"), dict) else row
                cards.extend(extract_km(payload))
            except Exception:
                pass

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    uniq = list(dict.fromkeys(cards))
    out.write_text("\n".join(uniq) + ("\n" if uniq else ""), encoding="utf-8")
    print(f"exported {len(uniq)} lines -> {out}")


if __name__ == "__main__":
    main()
