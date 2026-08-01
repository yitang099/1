#!/usr/bin/env python3
"""Single-shot poll jinku.lol + hm0880.top; run rainbow deep if up."""
import json
import os
import subprocess
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

TARGETS = [
    ("jinku.lol", "https://jinku.lol/shop/"),
    ("hm0880.top", "https://hm0880.top/shop/"),
]
OUT_DIR = "/data/automation/results"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"


def poll():
    log = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "targets": []}
    for name, url in TARGETS:
        entry = {"name": name, "url": url}
        try:
            r = requests.get(url, timeout=15, verify=False, headers={"User-Agent": UA})
            entry["status"] = r.status_code
            entry["len"] = len(r.text)
            entry["up"] = r.status_code == 200 and len(r.text) > 3000
        except Exception as e:
            entry["error"] = str(e)[:100]
            entry["up"] = False
        log["targets"].append(entry)
        print(json.dumps(entry))
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out = f"{OUT_DIR}/watchdog_poll_{stamp}.json"
    with open(out, "w") as f:
        json.dump(log, f, indent=2)
    return log


def main():
    log = poll()
    up = [t for t in log["targets"] if t.get("up")]
    if up and os.path.exists("/tmp/jinku_watchdog.py"):
        subprocess.run(["python3", "/tmp/jinku_watchdog.py"], check=False, timeout=120)


if __name__ == "__main__":
    main()
