#!/usr/bin/env python3
"""
代理池轮换 — 从文件或环境读取多个代理。

文件格式每行: http://user:pass@host:port

示例:
  python3 proxy_pool.py list
  python3 proxy_pool.py next
  FAKA_PROXY=$(python3 proxy_pool.py next) python3 shop_token_scan.py ...
"""
from __future__ import annotations

import argparse
import os
import random
from pathlib import Path

from faka_common import load_proxy, log

POOL_FILES = [
    "/data/recon/.env.proxy",
    "/data/recon/proxy_pool.txt",
    "/data/tools/faka/proxy_pool.txt",
]

_state = {"idx": 0}


def load_pool() -> list[str]:
    proxies: list[str] = []
    p = load_proxy()
    if p:
        proxies.append(p)
    for fp in POOL_FILES:
        path = Path(fp)
        if not path.exists() or path.suffix == ".proxy":
            continue
        if path.name.endswith(".env.proxy"):
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("http"):
                proxies.append(line)
    # tor socks as fallback
    proxies.append("socks5h://127.0.0.1:9050")
    return list(dict.fromkeys(proxies))


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="代理池")
    ap.add_argument("action", choices=["list", "next", "random"])
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    pool = load_pool()
    if not pool:
        log("无代理")
        return
    if args.action == "list":
        for i, p in enumerate(pool):
            print(f"{i}: {p}")
        return
    if args.action == "random":
        print(random.choice(pool))
        return
    p = pool[_state["idx"] % len(pool)]
    _state["idx"] += 1
    print(p)


if __name__ == "__main__":
    main()
