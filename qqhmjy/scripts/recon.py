#!/usr/bin/env python3
"""qqhmjy.com recon — ASP cluster sibling of qqfk.net; SUCCESS_CASES first."""
import re
import json
import ssl
import hashlib
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path

OUT = Path("/data/recon/qqhmjy.com")
(OUT / "probe").mkdir(parents=True, exist_ok=True)
(OUT / "dump").mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
BASES = ["https://qqhmjy.com", "https://www.qqhmjy.com"]


def make_op():
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        urllib.request.HTTPSHandler(context=CTX),
    )


def fetch(op, url, data=None):
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": BASES[0] + "/"}
    if data is not None:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        r = op.open(req, timeout=20)
        return r.geturl(), getattr(r, "status", 200), r.read()
    except urllib.error.HTTPError as e:
        return url, e.code, e.read()
    except Exception as e:
        return url, None, str(e).encode()


def dec(body):
    if not isinstance(body, (bytes, bytearray)):
        return str(body)
    for enc in ("utf-8", "gbk"):
        try:
            return body.decode(enc)
        except Exception:
            pass
    return body.decode("utf-8", "ignore")


def main():
    op = make_op()
    results = {
        "target": "https://qqhmjy.com",
        "success_cases": {},
        "paths": {},
        "compare_qqfk": {},
        "kami_found": False,
    }

    # SUCCESS_CASES
    sc_paths = [
        ("ykfaka_query", "/Query.html"),
        ("ykfaka_null", "/index.php?m=Home&c=Order&a=query&value=null"),
        ("qd93", "/?mod=query&data=1"),
        ("rainbow_ajax", "/ajax.php?act=query&page=1"),
        ("api_search", "/api.php?act=search&id=1"),
        ("tools", "/api.php?act=tools&key=123456&limit=1"),
        ("rainbow_shop", "/shop/"),
        ("admin", "/admin/"),
    ]
    for base in BASES:
        for label, path in sc_paths:
            final, code, body = fetch(op, base + path)
            text = dec(body)
            title = (re.search(r"<title>([^<]+)", text) or [None, None])[1]
            row = {
                "url": base + path,
                "final": final,
                "code": code,
                "len": len(body or b""),
                "title": title,
                "snip": re.sub(r"\s+", " ", text[:140]),
            }
            results["success_cases"][f"{label}@{base}"] = row
            print("SC", label, base, code, row["len"], title)

    # ASP surfaces
    asp_paths = [
        "/", "/Index.asp", "/index.asp", "/login.asp", "/reg.asp", "/member.asp",
        "/buy.asp", "/buy.asp?id=171", "/buy.asp?id=1", "/kucun.asp",
        "/chongzhi.asp", "/chkuser.asp", "/channel.asp?id=2",
        "/saveprofile.asp", "/manage/", "/manage/login.asp",
        "/order.asp", "/query.asp", "/chaxun.asp",
        "/inc/", "/inc/checkcode.asp", "/inc/config.asp",
    ]
    for base in BASES:
        for path in asp_paths:
            final, code, body = fetch(op, base + path)
            text = dec(body)
            title = (re.search(r"<title>([^<]+)", text) or [None, None])[1]
            markers = {
                "kami": "卡密" in text,
                "login": "登录" in text or "login" in text.lower(),
                "buy_form": "ordertb" in text or "danjia" in text,
                "iis404": "404.0" in text or "Not Found" in (title or ""),
            }
            row = {
                "final": final, "code": code, "len": len(body or b""),
                "title": title, "markers": markers,
                "sha1": hashlib.sha1(body or b"").hexdigest()[:16],
            }
            results["paths"][base + path] = row
            if path in ("/", "/buy.asp?id=171", "/kucun.asp", "/login.asp", "/member.asp", "/Query.html") or markers["buy_form"] or markers["kami"]:
                print("PATH", code, base + path, row["len"], title, markers)

    # compare homepage hash to qqfk apex if available
    for peer in ["https://qqfk.net/", "http://qqlhmd.com/", "https://qqlhmd.com/"]:
        final, code, body = fetch(op, peer)
        text = dec(body)
        results["compare_qqfk"][peer] = {
            "code": code,
            "len": len(body or b""),
            "sha1": hashlib.sha1(body or b"").hexdigest()[:16],
            "title": (re.search(r"<title>([^<]+)", text) or [None, None])[1],
            "chkuser": "chkuser.asp" in text,
            "buy_asp": "buy.asp" in text,
        }
        print("PEER", peer, results["compare_qqfk"][peer])

    # home links / contacts
    _, _, body = fetch(op, BASES[0] + "/")
    text = dec(body)
    (OUT / "probe" / "home.html").write_text(text, encoding="utf-8")
    hrefs = sorted(set(re.findall(r'(?:href|src|action)=["\']([^"\']+)["\']', text, re.I)))
    results["home_hrefs"] = hrefs[:80]
    results["contacts"] = {
        "tg": re.findall(r"t\.me/[\w]+|@[A-Za-z][\w]{3,}", text)[:20],
        "qq": re.findall(r"(?:uin=|群[：:\s]*|QQ[：:\s]*)(\d{5,12})", text)[:20],
    }
    print("CONTACTS", results["contacts"])
    print("HREFS", hrefs[:40])

    # buy/kucun depth on primary
    _, code, body = fetch(op, BASES[0] + "/kucun.asp")
    text = dec(body)
    (OUT / "probe" / "kucun.html").write_text(text, encoding="utf-8")
    buys = sorted(set(re.findall(r"buy\.asp\?id=(\d+)", text)))
    results["kucun_buy_ids"] = buys
    print("KUCUN buys", len(buys), buys[:40])

    _, code, body = fetch(op, BASES[0] + "/buy.asp?id=171")
    text = dec(body)
    (OUT / "probe" / "buy_171.html").write_text(text, encoding="utf-8")
    results["buy_171"] = {
        "code": code,
        "len": len(body or b""),
        "asps": sorted(set(re.findall(r"[\w/]+\.asp[^\"'\s]*", text, re.I)))[:40],
        "has_order": "ordertb" in text,
        "prices": re.findall(r"([\d]+\.[\d]{2})", text)[:10],
    }
    print("BUY171", results["buy_171"])

    (OUT / "dump" / "RECON.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("DONE kami", results["kami_found"])


if __name__ == "__main__":
    main()
