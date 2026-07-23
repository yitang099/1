#!/usr/bin/env python3
"""Probe related hosts via QG; hunt cross-site keys / panels."""
import json, subprocess, time, urllib.parse, re
from pathlib import Path

QG, PW = "C413ED6D", "344F550A6F8B"
OUT = Path("/tmp/qq1_deep8")
OUT.mkdir(exist_ok=True)
LOG = OUT / "related.log"


def log(m):
    print(m, flush=True)
    open(LOG, "a").write(m + "\n")


def pick():
    d = json.loads(subprocess.check_output(
        ["curl", "-s", f"https://share.proxy.qg.net/query?key={QG}"], text=True, timeout=12))
    for s in [x["server"] for x in d.get("data") or []]:
        cand = f"http://{QG}:{PW}@{s}"
        code = subprocess.run(
            ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/dev/null",
             "-w", "%{http_code}", "https://qq1.lol/%61pi.php?act=siteinfo"],
            capture_output=True, text=True, timeout=14).stdout.strip()
        if code == "200":
            log(f"px {s}")
            return cand
    time.sleep(2)
    d = json.loads(subprocess.check_output(
        ["curl", "-s", f"https://share.proxy.qg.net/get?key={QG}&num=2&area=440000"], text=True, timeout=12))
    for x in d.get("data") or []:
        cand = f"http://{QG}:{PW}@{x['server']}"
        code = subprocess.run(
            ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/dev/null",
             "-w", "%{http_code}", "https://qq1.lol/%61pi.php?act=siteinfo"],
            capture_output=True, text=True, timeout=14).stdout.strip()
        if code == "200":
            log(f"px {x['server']}")
            return cand
    return None


px = pick()
if not px:
    raise SystemExit("no px")


def c(url, post=None, mt=12):
    cmd = ["curl", "-sk", "--max-time", str(mt), "-x", px, "-A", "Mozilla/5.0",
           "-H", "Referer: https://qq1.lol/", "-w", "\n__HTTP:%{http_code}"]
    if post is not None:
        cmd += ["-X", "POST", "--data-binary",
                urllib.parse.urlencode(post) if isinstance(post, dict) else post,
                "-H", "Content-Type: application/x-www-form-urlencoded"]
    cmd.append(url)
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 5).stdout or ""
    if "__HTTP:" not in out:
        return out, "000"
    b, code = out.rsplit("__HTTP:", 1)
    return b.strip(), code.strip()


hosts = [
    "https://ka1.one", "http://ka1.one", "https://www.ka1.one",
    "https://qqkqq.com", "http://qqkqq.com", "https://www.qqkqq.com",
    "https://fffzz.lol", "http://fffzz.lol",
    "https://hmjf.lol", "https://htqq.lol", "https://kln166.com",
    "https://buyiq.com", "http://buyiq.com",
]
paths = ["/", "/%61pi.php?act=siteinfo", "/ajax.php?act=getcount",
         "/sup/login.php", "/user/login.php", "/robots.txt", "/.git/HEAD"]

results = {}
for base in hosts:
    host = base.split("//")[1]
    results[base] = {}
    for p in paths:
        b, code = c(base + p)
        results[base][p] = {"code": code, "len": len(b or ""), "head": (b or "")[:200]}
        log(f"{base}{p} -> {code} len={len(b or '')} {(b or '')[:100].replace(chr(10),' ')}")
        if code == "200" and b and ("sitename" in b or "getcount" in b or "订单" in b or "发卡" in b):
            log(f"*** RELATED LIVE {base}{p}")
            (OUT / f"related_{host.replace('.','_')}{p.replace('/','_')[:40]}").write_text(b[:100000], errors="replace")
        time.sleep(0.25)

# IP direct for ka1 / fffzz / qqkqq
for ip, host in [
    ("172.237.129.108", "ka1.one"),
    ("103.43.11.241", "fffzz.lol"),
    ("13.223.25.84", "qqkqq.com"),
]:
    b, code = c(f"http://{ip}/", mt=10)
    # Host header via separate curl
    cmd = ["curl", "-sk", "--max-time", "12", "-x", px, "-A", "Mozilla/5.0",
           "-H", f"Host: {host}", "-w", "\n__HTTP:%{http_code}", f"https://{ip}/"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=18).stdout or ""
    if "__HTTP:" in out:
        b2, c2 = out.rsplit("__HTTP:", 1)
        log(f"IP {ip} Host:{host} -> {c2.strip()} len={len(b2.strip())} {b2.strip()[:100]}")
        results[f"ip_{ip}_{host}"] = {"code": c2.strip(), "head": b2.strip()[:300]}

(OUT / "related_report.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
log("DONE related")
