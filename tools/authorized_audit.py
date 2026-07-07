#!/usr/bin/env python3
"""
授权安全审计脚本 — 供运营方修复后回归验证。

用法: python3 tools/authorized_audit.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

MAIN = "http://43.154.128.116:9110"
SMS = "http://47.76.163.227:8081"
LEGACY_SECRET = "18cdfb81a4e44a3a915528e67d923dba"


def call(method: str, url: str, payload: dict | None = None) -> tuple[int, str]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def pass_(msg: str) -> None:
    print(f"[PASS] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def main() -> int:
    print("=== 授权安全审计 ===\n")
    issues = 0

    # P0: removed endpoints
    for path in ("/api/desktop/refund-balance", "/api/desktop/decrease-balance"):
        code, _ = call("POST", f"{MAIN}{path}", {"username": "x", "amount": 1})
        if code == 404:
            pass_(f"已移除 {path}")
        else:
            fail(f"{path} 仍存在 (HTTP {code})")
            issues += 1

    # P0: legacy secret
    code, body = call("POST", f"{SMS}/create/{LEGACY_SECRET}", {"area": "86", "data": "17300000111", "islink": False})
    if "无效Token" in body or '"code":0' not in body:
        pass_("旧 secret 已吊销")
    else:
        warn(f"旧 secret 仍可用于 create: {body[:80]}")
        issues += 1

    # P0: balance leak
    code, body = call("GET", f"{SMS}/balance/{LEGACY_SECRET}")
    if code == 404:
        pass_("/balance 接口已下线")
    elif code == 200 and body.replace(".", "", 1).isdigit():
        warn(f"/balance 仍泄露运营余额: {body.strip()}")
        issues += 1
    else:
        pass_(f"/balance 不可读: {body[:40]}")

    # P1: settings leak
    code, body = call("GET", f"{MAIN}/api/desktop/settings?key=api_secret")
    if code == 401 or code == 403:
        pass_("settings 已需鉴权")
    elif '"value":""' in body or not json.loads(body).get("value"):
        pass_("settings 不再返回 api_secret")
    else:
        warn(f"settings 仍泄露 api_secret: {json.loads(body).get('value','')[:20]}...")
        issues += 1

    # P1: token invalidation
    user = f"audit_{int(time.time())}"
    call("POST", f"{MAIN}/api/desktop/register", {"username": user, "password": "audit123"})
    _, b1 = call("POST", f"{MAIN}/api/desktop/login", {"username": user, "password": "audit123"})
    t1 = json.loads(b1)["token"]
    call("POST", f"{MAIN}/api/desktop/login", {"username": user, "password": "audit123"})
    _, b2 = call("GET", f"{MAIN}/api/desktop/user-info?username={user}&token={t1}")
    if '"ok":true' in b2:
        warn("旧 token 在重新登录后仍有效")
        issues += 1
    else:
        pass_("重新登录后旧 token 失效")

    # P1: error message leak when operator balance low
    code, body = call("POST", f"{SMS}/create/{LEGACY_SECRET}", {"area": "86", "data": "17300000123", "islink": False})
    if "余额" in body and "单价" in body:
        warn(f"create 错误信息泄露运营余额/单价: {body[:100]}")
        issues += 1
    else:
        pass_("create 错误信息未泄露内部计费")

    ok = 0
    for i in range(5):
        u = f"burst_{int(time.time())}_{i}"
        _, b = call("POST", f"{MAIN}/api/desktop/register", {"username": u, "password": "x"})
        if '"ok":true' in b:
            ok += 1
    if ok < 5:
        pass_(f"注册有限速 ({ok}/5)")
    else:
        warn("注册仍无限速 (5/5)")
        issues += 1

    print(f"\n=== 完成: {issues} 项待修复 ===")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
