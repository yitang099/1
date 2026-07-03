#!/usr/bin/env python3
"""
异次元/ACG 批量指纹扫描。

示例:
  python3 scan_acg_batch.py -f /data/recon/tools/targets_acg.txt
  python3 scan_acg_batch.py -u zhanghao9.com qq898.vip suran888.top
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests

from faka_common import DEFAULT_UA, ensure_out, json_or_text, log, resolve_proxy, save_hit

PATHS = [
    "/user/api/index/data",
    "/user/api/index/commodity",
    "/user/api/site/info",
]

DEFAULT_TARGETS = Path("/data/tools/faka/data/targets_acg.txt")


def probe_host(host: str, timeout: int, proxy: str) -> dict:
    base = host if host.startswith("http") else f"https://{host}"
    base = base.rstrip("/")
    proxies = {"http": proxy, "https": proxy} if proxy else None
    hits = []
    for path in PATHS:
        try:
            r = requests.get(base + path, headers={"User-Agent": DEFAULT_UA}, timeout=timeout, proxies=proxies, verify=False)
            data = json_or_text(r)
            if isinstance(data, dict) and data.get("code") in (200, 1):
                hits.append({"path": path, "code": data.get("code"), "sample": str(data)[:200]})
        except Exception as e:
            continue
    return {"host": host, "base": base, "acg": bool(hits), "hits": hits}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ACG 批量指纹")
    ap.add_argument("-f", "--file", default=str(DEFAULT_TARGETS))
    ap.add_argument("-u", "--urls", nargs="*", default=[])
    ap.add_argument("-w", "--workers", type=int, default=10)
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--out", default="/data/tools/faka/out/scan_acg.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = resolve_proxy(args.proxy)

    hosts: list[str] = list(args.urls)
    if not hosts and Path(args.file).exists():
        hosts = [x.strip() for x in Path(args.file).read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip() and not x.startswith("#")]

    log(f"ACG batch scan hosts={len(hosts)} workers={args.workers}")
    acg_hits = 0

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(probe_host, h, args.timeout, proxy): h for h in hosts}
        for fut in as_completed(futs):
            res = fut.result()
            if res["acg"]:
                acg_hits += 1
                save_hit(Path(args.out), "acg_hit", res)
                log(f"[+] ACG {res['host']} paths={len(res['hits'])}")
            time.sleep(args.delay)

    summary = {"time": datetime.now().isoformat(), "scanned": len(hosts), "acg_hits": acg_hits}
    Path(args.out).with_suffix(".summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"完成 acg_hits={acg_hits}/{len(hosts)}")


if __name__ == "__main__":
    main()
