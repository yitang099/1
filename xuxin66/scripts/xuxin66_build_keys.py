#!/usr/bin/env python3
keys = []
base = [
    "xuxin66", "xuxin", "xuxin66.top", "xuxin66vip", "xuxin079", "xuxinzfb",
    "datou111", "datou333", "虚心", "zfb", "faka", "epay", "rainbow", "caihong",
    "123456", "888888", "666666", "111111", "000000", "admin", "password",
    "ttwl66", "ttwl", "1003", "Ykfaka999", "mckuai", "syskey", "apikey",
    "xuxin2024", "xuxin2025", "xuxin2026", "xuxin123", "xuxin888", "xuxin666",
    "XuXin66", "XUXIN66", "xx66", "xx666", "xxin66", "xin66", "虚心zfb",
    "虚心发卡", "auto", "发卡", "自动发卡", "qq", "wx", "alipay", "usdt",
]
for b in ["xuxin66", "xuxin", "datou", "zfb", "faka"]:
    for s in ["", "123", "888", "666", "000", "2024", "2025", "2026", "!", "@", "#", "_", "key", "sys", "api"]:
        base.append(b + s)
keys.extend(base)
for p, lim in [
    ("/tmp/query_pwd_list.txt", 524),
    ("/data/automation/results/youhui1998.top/deep_20260801_010500/syskey_smart.txt", 5000),
]:
    try:
        with open(p, errors="ignore") as f:
            for i, l in enumerate(f):
                if i >= lim:
                    break
                k = l.strip()
                if 1 <= len(k) <= 64:
                    keys.append(k)
    except FileNotFoundError:
        pass
seen, out = set(), []
for k in keys:
    if k not in seen:
        seen.add(k)
        out.append(k)
open("/data/tmp/xuxin66_syskeys_prio.txt", "w").write("\n".join(out))
print(len(out))
