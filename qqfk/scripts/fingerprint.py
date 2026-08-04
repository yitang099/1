#!/usr/bin/env python3
"""Deep fingerprint + SUCCESS_CASES first pass for qqfk.net."""
import re
import json
import ssl
import subprocess
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path

OUT = Path("/data/recon/qqfk.net")
(OUT / "probe").mkdir(parents=True, exist_ok=True)
(OUT / "dump").mkdir(parents=True, exist_ok=True)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def opener(cookie=True):
    handlers = [urllib.request.HTTPSHandler(context=CTX)]
    if cookie:
        handlers.insert(0, urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    return urllib.request.build_opener(*handlers)


def fetch(op, url, data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "text/html,application/json,*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        r = op.open(req, timeout=20)
        body = r.read()
        return r.geturl(), getattr(r, "status", 200), body, dict(r.headers)
    except urllib.error.HTTPError as e:
        return url, e.code, e.read(), dict(e.headers)
    except Exception as e:
        return url, None, str(e).encode(), {}


def main():
    op = opener()
    results = {"hosts": {}, "paths": {}, "success_cases": {}}

    for base in ["https://qqfk.net", "https://www.qqfk.net", "http://qqfk.net", "http://www.qqfk.net"]:
        final, code, body, hdrs = fetch(op, base + "/")
        text = body.decode("utf-8", "ignore") if isinstance(body, bytes) else str(body)
        title = (re.search(r"<title>([^<]+)", text) or [None, None])[1]
        links = sorted(set(re.findall(r'href=["\']([^"\']+)["\']', text, re.I)))
        scripts = sorted(set(re.findall(r'src=["\']([^"\']+)["\']', text, re.I)))
        forms = re.findall(r"<form[\s\S]*?</form>", text, re.I)
        meta = {
            "final": final,
            "code": code,
            "len": len(body) if isinstance(body, bytes) else len(text),
            "title": title,
            "server": hdrs.get("Server") or hdrs.get("server"),
            "links_sample": links[:80],
            "scripts_sample": scripts[:40],
            "form_count": len(forms),
            "keywords": {
                k: (k.lower() in text.lower() if k.isascii() else k in text)
                for k in [
                    "YKFAKA", "Query.html", "ajax.php", "api.php", "mod=query",
                    "mod=buy", "彩虹", "卡密", "sec_defend", "geetest", "faka",
                    "hashsalt", "layer.js", "nasgo", "shop", "user/login",
                ]
            },
        }
        # extract interesting path-like strings
        paths = sorted(set(re.findall(r"(?:href|action|src)=[\"'](/[^\"'#?\s]{1,80})", text, re.I)))
        meta["local_paths"] = paths[:100]
        # phones / tg / qq
        meta["contacts"] = {
            "tg": re.findall(r"t\.me/[\w]+|@[A-Za-z][\w]{3,}", text)[:20],
            "qq": re.findall(r"(?:QQ|qq|群)[：:\s]*(\d{5,12})", text)[:20],
        }
        results["hosts"][base] = meta
        safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", base)
        (OUT / "probe" / f"home_{safe}.html").write_text(text, encoding="utf-8")
        print("HOME", base, meta["title"], meta["len"], meta["keywords"])

    # path spray on both apex and www
    common = [
        "/", "/shop/", "/shop", "/Query.html", "/query.html", "/index.php",
        "/ajax.php", "/api.php", "/%61pi.php", "/admin/", "/admin",
        "/user/", "/user/login.php", "/?mod=query", "/?mod=buy",
        "/faka/", "/goods/", "/order/", "/nasgo/", "/loading/",
        "/wp/public/", "/trr/", "/assets/faka/",
    ]
    for host in ["https://qqfk.net", "https://www.qqfk.net"]:
        for path in common:
            url = host + path if path.startswith("/") else host + "/" + path
            # querystring path already has ?
            if path.startswith("/?"):
                url = host + path
            final, code, body, _ = fetch(op, url)
            text = body.decode("utf-8", "ignore") if isinstance(body, bytes) else ""
            title = (re.search(r"<title>([^<]+)", text) or [None, None])[1]
            snip = re.sub(r"\s+", " ", text[:120])
            row = {
                "final": final, "code": code,
                "len": len(body) if isinstance(body, bytes) else 0,
                "title": title, "snip": snip,
                "markers": {
                    "ajax": "ajax.php" in text,
                    "api": "api.php" in text,
                    "mod=query": "mod=query" in text,
                    "YKFAKA": "YKFAKA" in text or "ykfaka" in text.lower(),
                    "sec_defend": "sec_defend" in text,
                    "卡密": "卡密" in text,
                },
            }
            results["paths"][url] = row
            interesting = code not in (404, None) and (
                any(row["markers"].values()) or (code and code < 400 and path not in ("/",))
            )
            if interesting or path in ("/", "/shop/", "/Query.html", "/ajax.php", "/api.php", "/admin/", "/?mod=query"):
                print("PATH", url, code, row["len"], title, row["markers"])

    (OUT / "dump" / "FINGERPRINT.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("WROTE FINGERPRINT.json")


if __name__ == "__main__":
    main()
