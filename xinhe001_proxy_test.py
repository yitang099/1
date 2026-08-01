#!/usr/bin/env python3
import json, subprocess, requests
requests.packages.urllib3.disable_warnings()
subprocess.run(["/data/automation/bin/qg-proxy-fetch.sh"], timeout=35)
px = None
for line in open("/data/config/proxy.env"):
    if line.startswith("PROXY_URL="):
        px = line.strip().split("=", 1)[1].strip().strip('"')
        break
proxies = {"http": px, "https": px} if px else None
print("proxy", px[:30] if px else None)
UA = "Mozilla/5.0"
for base in [
    "http://xinhe001.lol/shop/",
    "https://xinhe001.lol/shop/",
    "http://103.43.11.95/shop/",
]:
    h = {"Host": "xinhe001.lol", "User-Agent": UA} if "103." in base else {"User-Agent": UA}
    try:
        r = requests.get(
            base, proxies=proxies, timeout=25, verify=False, headers=h, allow_redirects=True
        )
        print(base, r.status_code, len(r.text))
        if len(r.text) > 5000:
            gc = requests.get(
                base + "ajax.php?act=getcount",
                proxies=proxies,
                timeout=20,
                verify=False,
                headers=h,
            )
            print("  gc", gc.text[:150])
            ar = requests.get(
                base + "api.php?act=search&id=5718",
                proxies=proxies,
                timeout=20,
                verify=False,
                headers=h,
            )
            print("  api", ar.text[:150])
    except Exception as e:
        print(base, "ERR", str(e)[:100])
