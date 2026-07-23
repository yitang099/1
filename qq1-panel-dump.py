#!/usr/bin/env python3
"""Login fenzhan and dump panel pages for apikey / money / nav."""
import json
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep9")
JAR = str(OUT / "panel.jar")
KEY = "685ea1068774ca8f8e9a292a08da66d6"
QG, PW = "C413ED6D", "344F550A6F8B"
USER, PASS = "p4764923", "Test64923x"
_px = None


def log(m):
    print(m, flush=True)
    open(OUT / "panel_dump.log", "a").write(m + "\n")


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
            log(f"px err {e}")
        time.sleep(0.5)
    return _px


def curl(url, post=None, mt=20):
    global _px
    if not _px:
        fresh()
    for _ in range(5):
        cmd = ["curl", "-sk", "--max-time", str(mt), "-x", _px, "-b", JAR, "-c", JAR,
               "-A", "Mozilla/5.0", "-H", "Referer: https://qq1.lol/user/",
               "-H", "X-Requested-With: XMLHttpRequest",
               "-w", "\n__HTTP:%{http_code}"]
        if post is not None:
            body = urllib.parse.urlencode(post)
            cmd += ["-X", "POST", "--data-binary", body,
                    "-H", "Content-Type: application/x-www-form-urlencoded"]
        cmd.append(url)
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 8).stdout or ""
        if "authorization expired" in out or "__HTTP:" not in out:
            fresh()
            continue
        b, code = out.rsplit("__HTTP:", 1)
        return b.strip(), code.strip()
    return "", "000"


def solve(gt, challenge):
    task = {"type": "GeeTestTaskProxyless", "websiteURL": BASE + "/user/login.php",
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


def main():
    open(OUT / "panel_dump.log", "w").write("")
    log("=== PANEL DUMP ===")
    fresh()
    Path(JAR).unlink(missing_ok=True)
    curl(BASE + "/user/login.php")
    for attempt in range(5):
        try:
            cap_b, _ = curl(BASE + f"/ajax.php?act=captcha&t={int(time.time()*1000)}")
            cap = json.loads(cap_b)
            sol = solve(cap["gt"], cap["challenge"])
        except Exception as e:
            log(f"cap fail {e}")
            continue
        b, c = curl(BASE + "/user/ajax.php?act=login", {
            "user": USER, "pass": PASS,
            "geetest_challenge": sol.get("challenge") or cap["challenge"],
            "geetest_validate": sol.get("validate", ""),
            "geetest_seccode": sol.get("seccode") or (sol.get("validate", "") + "|jordan"),
        })
        log(f"login {c} {b[:200]}")
        if b and ("成功" in b or '"code":0' in b):
            break
    else:
        log("login failed")
        return

    pages = [
        "/user/", "/user/uset.php", "/user/recharge.php", "/user/tuiguang.php",
        "/user/tixian.php", "/user/record.php", "/user/workorder.php", "/user/message.php",
        "/user/classlist.php", "/user/shoplist.php", "/user/shopedit.php", "/user/price.php",
        "/user/kami.php", "/user/fakalist.php", "/user/faka.php", "/user/sitelist.php",
        "/user/userlist.php", "/user/order.php", "/user/orderlist.php", "/user/pay.php",
        "/user/transfer.php", "/user/qiandao.php", "/user/code.php", "/user/rank.php",
        "/user/nonce.php", "/user/head.php", "/user/foot.php",
    ]
    for p in pages:
        b, c = curl(BASE + p)
        log(f"{p}: {c} len={len(b or '')}")
        if c == "200" and b and len(b) > 80 and "404 Not Found" not in b[:80]:
            fname = "panel_" + p.strip("/").replace("/", "_") + ".html"
            (OUT / fname).write_text(b, errors="replace")
            acts = sorted(set(re.findall(r"act=([a-zA-Z0-9_]+)", b)))
            if acts:
                log(f"  acts {acts}")
            links = sorted(set(re.findall(r'href=["\']([^"\']+)["\']', b)))
            ulinks = [x for x in links if "user/" in x or x.endswith(".php")]
            if ulinks:
                log(f"  links {ulinks[:30]}")
            for pat in ("余额", "密钥", "apikey", "API对接", "rmb", "money", "zid", "提成", "域名"):
                if re.search(pat, b, re.I):
                    for m in re.finditer(r".{0,40}" + re.escape(pat) + r".{0,60}", b, re.I):
                        s = m.group(0).replace("\n", " ")[:150]
                        log(f"  snip: {s}")
        time.sleep(0.15)

    # parse uset / index for form fields
    for name in ("panel_user_uset.php.html", "panel_user.html", "panel_user_recharge.php.html",
                 "panel_user_tuiguang.php.html"):
        p = OUT / name
        if not p.exists():
            continue
        t = p.read_text(errors="replace")
        inputs = re.findall(r'<input[^>]+name=["\']([^"\']+)["\'][^>]*>', t, re.I)
        log(f"{name} inputs: {inputs}")
        # values
        for m in re.finditer(r'<input[^>]+name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', t, re.I):
            log(f"  input {m.group(1)}={m.group(2)[:80]}")
        for m in re.finditer(r'<textarea[^>]+name=["\']([^"\']+)["\'][^>]*>([^<]*)</textarea>', t, re.I):
            log(f"  textarea {m.group(1)}={m.group(2)[:80]}")

    log("=== PANEL DUMP DONE ===")


if __name__ == "__main__":
    main()
