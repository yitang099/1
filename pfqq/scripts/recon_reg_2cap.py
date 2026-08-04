#!/usr/bin/env python3
"""Register via 2captcha image OCR, then login + pay + query."""
import base64
import re
import json
import time
import subprocess
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

HOST = "http://xunqq.cn"
BASE = HOST + "/admin"
UA = "Mozilla/5.0"
OUT = Path("/data/recon/pfqq.net")
KEY = open("/data/recon/cookie_tool/config/2captcha.env").read().strip().split("=", 1)[1]


def main():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def get(url, data=None, binary=False, headers=None):
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
        raw = op.open(req, timeout=30).read()
        return raw if binary else raw.decode("utf-8", "ignore")

    def setc(n, v):
        cj.set_cookie(
            http.cookiejar.Cookie(
                0, n, v, None, False, "xunqq.cn", False, False, "/", False,
                False, None, False, None, None, {},
            )
        )

    # waf
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

    # reg page + hashsalt
    reg = get(BASE + "/user/reg.php")
    hm = re.search(r"var hashsalt=(.+?);", reg)
    if not hm:
        raise SystemExit("no hashsalt")
    hashsalt = subprocess.run(
        ["node", "-e", f"console.log({hm.group(1)})"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    print("hashsalt", hashsalt)

    # captcha image
    img = get(BASE + "/user/code.php?r=" + str(time.time()), binary=True)
    (OUT / "probe" / "captcha2.png").write_bytes(img)
    b64 = base64.b64encode(img).decode()

    # 2captcha
    create = urllib.request.urlopen(
        "http://2captcha.com/in.php?"
        + urllib.parse.urlencode(
            {
                "key": KEY,
                "method": "base64",
                "body": b64,
                "json": 1,
                "numeric": 0,
                "min_len": 3,
                "max_len": 6,
            }
        ),
        timeout=30,
    ).read().decode()
    print("2cap create", create)
    cj2 = json.loads(create)
    if cj2.get("status") != 1:
        raise SystemExit("2cap create fail")
    rid = cj2["request"]
    code = None
    for i in range(24):
        time.sleep(5)
        res = urllib.request.urlopen(
            f"http://2captcha.com/res.php?key={KEY}&action=get&id={rid}&json=1",
            timeout=30,
        ).read().decode()
        print("2cap poll", i, res)
        rj = json.loads(res)
        if rj.get("status") == 1:
            code = rj["request"]
            break
        if rj.get("request") != "CAPCHA_NOT_READY":
            raise SystemExit("2cap fail " + res)
    if not code:
        raise SystemExit("2cap timeout")
    print("CODE", code)

    user = "rc" + str(int(time.time()))[-7:]
    pwd = "Test123456"
    qq = "123456789"
    body = get(
        BASE + "/user/ajax.php?act=reguser",
        data=urllib.parse.urlencode(
            {
                "user": user,
                "pwd": pwd,
                "qq": qq,
                "code": code,
                "hashsalt": hashsalt,
            }
        ).encode(),
    )
    print("REG", user, body)
    (OUT / "dump" / "REG.json").write_text(
        json.dumps(
            {"user": user, "pwd": pwd, "code": code, "body": body, "hashsalt": hashsalt},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # login
    login = get(
        BASE + "/user/ajax.php?act=login",
        data=urllib.parse.urlencode({"user": user, "pass": pwd}).encode(),
    )
    print("LOGIN", login)
    print("COOKIES", [(c.name, (c.value or "")[:50]) for c in cj])

    # pay tid 1353 cheapest-ish
    buy = get(BASE + "/?mod=buy&tid=1353")
    hm = re.search(r"var hashsalt=(.+?);", buy)
    ph = subprocess.run(
        ["node", "-e", f"console.log({hm.group(1)})"],
        capture_output=True,
        text=True,
    ).stdout.strip() if hm else ""
    print("pay hashsalt", ph)
    for payload in [
        {"tid": "1353", "inputvalue": qq, "num": "1", "hashsalt": ph},
        {"tid": "1353", "input1": qq, "num": "1", "hashsalt": ph},
        {"tid": "1109", "inputvalue": qq, "num": "1", "hashsalt": ph},
    ]:
        # refresh hashsalt per tid
        buy = get(BASE + f"/?mod=buy&tid={payload['tid']}")
        hm = re.search(r"var hashsalt=(.+?);", buy)
        if hm:
            payload["hashsalt"] = subprocess.run(
                ["node", "-e", f"console.log({hm.group(1)})"],
                capture_output=True,
                text=True,
            ).stdout.strip()
        pay = get(
            BASE + "/ajax.php?act=pay",
            data=urllib.parse.urlencode(payload).encode(),
        )
        print("PAY", payload["tid"], pay[:300])

    q = get(
        BASE + "/ajax.php?act=query&page=1",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    print("QUERY", q[:400])
    page = get(BASE + f"/?mod=query&data={qq}")
    print("QUERY PAGE kami?", "卡密" in page, re.findall(r"卡密[^<]{0,80}", page)[:5])
    print("DONE")


if __name__ == "__main__":
    main()
