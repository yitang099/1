#!/usr/bin/env python3
import re
import requests

requests.packages.urllib3.disable_warnings()
s = requests.Session()
s.verify = False
s.headers.update({"User-Agent": "Mozilla/5.0"})
base = "https://mima1314.com"
TOKEN_RE = re.compile(
    r'name=["\']__token__["\'][^>]*value=["\']([^"\']+)["\']'
    r'|value=["\']([^"\']+)["\'][^>]*name=["\']__token__["\']'
)
q = s.get(base + "/Query.html", timeout=15)
tok = TOKEN_RE.search(q.text)
token = tok.group(1) or tok.group(2)
extras = [
    {},
    {"page": "2"},
    {"p": "2"},
    {"pageNum": "2"},
    {"limit": "500"},
    {"rows": "500"},
]
for extra in extras:
    data = {"value": "null", "page": "1", "__token__": token}
    data.update(extra)
    p = s.post(
        base + "/Query.html",
        data=data,
        headers={"Referer": base + "/Query.html"},
        timeout=15,
    )
    print(extra, len(p.text), p.text.count("Query_Km"))
