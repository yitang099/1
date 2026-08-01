#!/usr/bin/env python3
"""Enumerate mima1314 null pages for Query_Km link counts."""
import re
import sys

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://mima1314.com"
MAX_PAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 50
TOKEN_RE = re.compile(
    r'name=["\']__token__["\'][^>]*value=["\']([^"\']+)["\']'
    r'|value=["\']([^"\']+)["\'][^>]*name=["\']__token__["\']'
)
KM_RE = re.compile(r"/Query_Km/([a-f0-9]{12})")

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0"})
s.verify = False

total_km = 0
all_ddids = set()
for page in range(1, MAX_PAGES + 1):
    q = s.get(BASE + "/Query.html", timeout=20)
    tok = TOKEN_RE.search(q.text)
    if not tok:
        print(f"no token at page {page}")
        break
    token = tok.group(1) or tok.group(2)
    p = s.post(
        BASE + "/Query.html",
        data={"value": "null", "page": str(page), "__token__": token},
        headers={"Referer": BASE + "/Query.html"},
        timeout=25,
    )
    kms = KM_RE.findall(p.text)
    all_ddids.update(kms)
    total_km += len(kms)
    print(f"page {page}: {len(kms)} links, cumulative unique {len(all_ddids)}")
    if not kms and page > 2:
        break

print(f"DONE pages={page} total_links={total_km} unique_ddids={len(all_ddids)}")
