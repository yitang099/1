#!/usr/bin/env python3
"""qq1.lol infrastructure probe — origin ports 8080/8888/3306/6379/21 + panel fingerprint"""
import json
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path

IP = "45.158.21.213"
CDN = "103.43.11.95"
HOST = "qq1.lol"
OUT = Path("/workspace/results/qq1.lol")
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "infra_probe.log"
HITS = OUT / "infra_hits.jsonl"


def log(msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def hit(kind, detail, body=""):
    rec = {"ts": datetime.now().isoformat(), "kind": kind, "detail": detail, "body": (body or "")[:5000]}
    with open(HITS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"*** HIT [{kind}] {detail}: {(body or '')[:300]}")


def curl(url, host=None, resolve=None, extra=None):
    cmd = ["curl", "-sk", f"--max-time=12", "-A", "Mozilla/5.0"]
    if host:
        cmd += ["-H", f"Host: {host}"]
    if resolve:
        cmd += ["--resolve", resolve]
    if extra:
        cmd += extra
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.stdout, r.stderr, r.returncode
    except Exception as e:
        return "", str(e), -1


def probe_http_ports():
    log("=== [1] HTTP panels on origin ===")
    ports = [80, 443, 8080, 8443, 8888, 888, 8000, 9000, 3000, 5000]
    paths = ["/", "/login", "/admin", "/phpmyadmin", "/pma", "/bt", "/safe", "/panel",
             "/manager", "/wp-admin", "/user/login", "/sup/login.php", "/install/"]
    for ip in (IP, CDN):
        for port in ports:
            scheme = "https" if port in (443, 8443, 8888) else "http"
            for path in paths[:6]:
                url = f"{scheme}://{ip}:{port}{path}"
                body, err, rc = curl(url, host=HOST, resolve=f"{HOST}:{port}:{ip}")
                if body and len(body) > 50 and "404 Not Found" not in body[:200]:
                    markers = ("login", "宝塔", "baota", "phpMyAdmin", "发卡", "admin", "panel", "dashboard", "password")
                    if any(m.lower() in body.lower() for m in markers) or len(body) > 500:
                        hit("http_panel", f"{ip}:{port}{path}", body[:1500])
            # default vhost
            body, _, _ = curl(f"{scheme}://{ip}:{port}/")
            if body and len(body) > 100:
                title = ""
                if "<title>" in body:
                    import re
                    m = re.search(r"<title>([^<]+)", body, re.I)
                    title = m.group(1) if m else ""
                if title and "404" not in title:
                    hit("http_title", f"{ip}:{port} title={title}", body[:800])


def probe_redis():
    log("=== [2] Redis 6379 ===")
    for ip in (IP, CDN):
        try:
            s = socket.create_connection((ip, 6379), timeout=5)
            s.sendall(b"PING\r\n")
            resp = s.recv(1024).decode(errors="replace")
            s.close()
            hit("redis_ping", ip, resp)
            if "PONG" in resp:
                s2 = socket.create_connection((ip, 6379), timeout=5)
                s2.sendall(b"INFO\r\n")
                info = s2.recv(4096).decode(errors="replace")
                s2.close()
                hit("redis_info", ip, info)
                s3 = socket.create_connection((ip, 6379), timeout=5)
                s3.sendall(b"KEYS *\r\n")
                keys = s3.recv(8192).decode(errors="replace")
                s3.close()
                hit("redis_keys", ip, keys)
        except Exception as e:
            log(f"  redis {ip}: {e}")


def probe_mysql_banner():
    log("=== [3] MySQL 3306 banner ===")
    for ip in (IP, CDN):
        try:
            s = socket.create_connection((ip, 3306), timeout=5)
            banner = s.recv(256)
            s.close()
            hit("mysql_banner", ip, repr(banner[:200]))
        except Exception as e:
            log(f"  mysql {ip}: {e}")


def probe_ftp():
    log("=== [4] FTP 21 ===")
    for ip in (IP,):
        try:
            s = socket.create_connection((ip, 21), timeout=5)
            banner = s.recv(512).decode(errors="replace")
            s.sendall(b"USER anonymous\r\n")
            r1 = s.recv(512).decode(errors="replace")
            s.sendall(b"PASS guest@\r\n")
            r2 = s.recv(512).decode(errors="replace")
            s.close()
            hit("ftp_banner", ip, f"banner={banner.strip()} user={r1.strip()} pass={r2.strip()}")
        except Exception as e:
            log(f"  ftp {ip}: {e}")


def main():
    log("=== INFRA PROBE START ===")
    probe_http_ports()
    probe_redis()
    probe_mysql_banner()
    probe_ftp()
    n = sum(1 for _ in open(HITS)) if HITS.exists() else 0
    log(f"=== INFRA DONE hits={n} ===")


if __name__ == "__main__":
    main()
