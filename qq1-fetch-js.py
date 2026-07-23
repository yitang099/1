#!/usr/bin/env python3
import json, subprocess, re
from pathlib import Path

QG, PW = "C413ED6D", "344F550A6F8B"
BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep8")
OUT.mkdir(exist_ok=True)

d = json.loads(subprocess.check_output(
    ["curl", "-s", f"https://share.proxy.qg.net/query?key={QG}"], text=True, timeout=12))
px = None
for x in d.get("data") or []:
    cand = f"http://{QG}:{PW}@{x['server']}"
    code = subprocess.run(
        ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/tmp/t.out",
         "-w", "%{http_code}", f"{BASE}/%61pi.php?act=siteinfo"],
        capture_output=True, text=True, timeout=14).stdout.strip()
    if code == "200" and b"sitename" in open("/tmp/t.out", "rb").read():
        px = cand
        print("px", x["server"])
        break
if not px:
    raise SystemExit("no px")

for path in [
    "/assets/js/reguser.js", "/assets/js/login.js", "/assets/js/reg.js",
    "/assets/js/user.js", "/assets/faka/js/faka.js",
]:
    out = subprocess.run(
        ["curl", "-sk", "--max-time", "15", "-x", px, "-A", "Mozilla/5.0",
         "-w", "\n__HTTP:%{http_code}", BASE + path],
        capture_output=True, text=True, timeout=20).stdout or ""
    if "__HTTP:" not in out:
        print(path, "fail")
        continue
    b, c = out.rsplit("__HTTP:", 1)
    print(f"==== {path} HTTP={c.strip()} len={len(b)} ====")
    (OUT / path.split("/")[-1]).write_text(b, errors="replace")
    for pat in [
        r"act[=:'\"]([a-zA-Z0-9_]+)",
        r"ajax\.php[^\"'\s]*",
        r"url\s*:\s*[\"'][^\"']+",
        r"\.post\(\s*[\"'][^\"']+",
    ]:
        ms = re.findall(pat, b)
        if ms:
            print(" ", pat, list(dict.fromkeys(ms))[:20])
    print(b[:2000])
    print("---")
