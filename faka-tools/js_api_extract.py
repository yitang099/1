#!/usr/bin/env python3
"""
从 JS 包提取 API 路径（pyfaas/vue 前台）。

示例:
  python3 js_api_extract.py https://s.sggyx.com
  python3 js_api_extract.py /data/tmp/vuln-deep/index.e74f5f7e.js -o apis.txt
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

from faka_common import DEFAULT_UA, log

PATTERNS = [
    r'["\'](/(?:merchantApi|shopApi|user/api|admin/api|api/v1)[^"\']+)["\']',
    r'["\'](https?://[^"\']+/merchantApi[^"\']+)["\']',
    r'/(merchantApi/[A-Za-z]+/[A-Za-z]+)',
    r'/(shopApi/[A-Za-z]+/[A-Za-z]+)',
]


def extract_text(source: str) -> set[str]:
    found: set[str] = set()
    for pat in PATTERNS:
        for m in re.finditer(pat, source):
            p = m.group(1) if m.lastindex else m.group(0)
            if 5 < len(p) < 200:
                found.add(p.split("?")[0])
    return found


def fetch_js_urls(base: str) -> list[str]:
    r = requests.get(base, headers={"User-Agent": DEFAULT_UA}, timeout=20, verify=False)
    html = r.text
    urls = re.findall(r'(?:src|href)=["\']([^"\']+\.js[^"\']*)["\']', html)
    out = []
    for u in urls:
        out.append(urljoin(base, u))
    return out[:30]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="JS API 提取")
    ap.add_argument("target", help="URL 或本地 js 文件")
    ap.add_argument("-o", "--out", default="/data/tools/faka/out/js_apis.txt")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    apis: set[str] = set()

    if Path(args.target).exists():
        apis |= extract_text(Path(args.target).read_text(encoding="utf-8", errors="ignore"))
    elif args.target.startswith("http"):
        base = args.target.rstrip("/") + "/"
        for js_url in fetch_js_urls(base):
            try:
                t = requests.get(js_url, headers={"User-Agent": DEFAULT_UA}, timeout=20, verify=False).text
                apis |= extract_text(t)
            except Exception:
                pass
    else:
        raise SystemExit("目标需为 URL 或本地文件")

    lines = sorted(apis)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"提取 {len(lines)} 条 -> {out}")
    for line in lines[:30]:
        log(f"  {line}")


if __name__ == "__main__":
    main()
