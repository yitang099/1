#!/usr/bin/env python3
"""Fetch auth JS; try captcha register then pay."""
import re
import json
import subprocess
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

HOST = "http://xunqq.cn"
BASE = HOST + "/admin"
UA = "Mozilla/5.0"
OUT = Path("/data/recon/pfqq.net")


def main():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def get(url, data=None, headers=None, binary=False):
        h = {
            "User-Agent": UA,
            "Referer": BASE + "/user/reg.php",
            "Accept": "*/*",
        }
        if headers:
            h.update(headers)
        if data is not None:
            h["Content-Type"] = "application/x-www-form-urlencoded"
            h["X-Requested-With"] = "XMLHttpRequest"
        req = urllib.request.Request(url, data=data, headers=h)
        raw = op.open(req, timeout=20).read()
        if binary:
            return raw
        return raw.decode("utf-8", "ignore")

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

    for js in [
        BASE + "/assets/js/login.js?ver=2061",
        BASE + "/assets/js/reguser.js?ver=2061",
    ]:
        body = get(js)
        name = "login.js" if "login" in js else "reguser.js"
        (OUT / "probe" / name).write_text(body, encoding="utf-8")
        print("====", name, len(body))
        print(body[:2500])

    # get captcha image
    reg_page = get(BASE + "/user/reg.php")
    code_src = re.search(r"code\.php\?r=([^\"']+)", reg_page)
    print("code_src", code_src.group(0) if code_src else None)
    img = get(BASE + "/user/code.php?r=1", binary=True)
    (OUT / "probe" / "captcha.png").write_bytes(img)
    print("captcha bytes", len(img), img[:20])

    # OCR attempt with tesseract if available
    code = None
    try:
        p = subprocess.run(
            ["tesseract", str(OUT / "probe" / "captcha.png"), "stdout", "-l", "eng", "--psm", "7"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        code = re.sub(r"[^a-zA-Z0-9]", "", p.stdout.strip())
        print("OCR", repr(p.stdout), "->", code)
    except Exception as e:
        print("OCR unavailable", e)

    user = "rc" + val[:6]
    pwd = "Test123456"
    qq = "123456789"
    if code:
        body = get(
            BASE + "/user/ajax.php?act=reguser",
            data=urllib.parse.urlencode(
                {"user": user, "pwd": pwd, "qq": qq, "code": code}
            ).encode(),
        )
        print("REG", user, body)
        # also try pass instead of pwd
        body2 = get(
            BASE + "/user/ajax.php?act=reguser",
            data=urllib.parse.urlencode(
                {"user": user + "2", "pass": pwd, "qq": qq, "code": code}
            ).encode(),
        )
        print("REG2", body2)

    # document pay requires login
    result = {
        "login_js": "assets/js/login.js",
        "reg_js": "assets/js/reguser.js",
        "reg_act": "reguser",
        "login_act": "login",
        "login_fields": ["user", "pass"],
        "reg_fields": ["user", "pwd", "qq", "code"],
        "pay_requires_login": True,
        "ajax_query_empty": True,
        "tools_oracle_live": True,
        "kami_found": False,
        "ocr_code": code,
    }
    (OUT / "dump" / "AUTH2.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("DONE")


if __name__ == "__main__":
    main()
