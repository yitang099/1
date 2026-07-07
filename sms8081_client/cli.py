"""Command-line mode for 8081 SMS test client."""
from __future__ import annotations

import time

from sms8081_client.api import Sms8081Client, clean_result_data
from sms8081_client.config import load_config


def run_cli() -> int:
    cfg = load_config()
    client = Sms8081Client(cfg["sms_base"], cfg["api_secret"], cfg.get("proxy") or None)
    print("=== 8081 CLI 测验 ===")
    print("通道余额:", client.get_balance())
    phone = input("手机号: ").strip()
    area = input("区号 [86]: ").strip() or "86"
    order_id = client.create_order(phone, area=area)
    print("订单:", order_id)
    code = input("短信验证码: ").strip()
    print(client.submit_sms_code(phone, code))
    for i in range(60):
        resp = client.query_order(order_id)
        if resp.get("code") == 0:
            print("结果:", clean_result_data(str(resp.get("data") or "")))
            return 0
        print(f"[{i+1}]", resp.get("err") or resp.get("data"))
        time.sleep(3)
    print("超时")
    return 1
