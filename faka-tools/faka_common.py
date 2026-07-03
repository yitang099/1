#!/usr/bin/env python3
"""Shared helpers for /data/tools/faka toolkit."""
from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Iterator

import requests
import urllib3

urllib3.disable_warnings()

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

XFF_HEADERS = [
    "X-Forwarded-For",
    "X-Real-IP",
    "X-Client-IP",
    "X-Originating-IP",
    "CF-Connecting-IP",
    "True-Client-IP",
]

PRIVATE_IPS = [
    "127.0.0.1",
    "10.0.0.1",
    "172.16.0.1",
    "192.168.0.1",
    "192.168.1.1",
    "0.0.0.0",
    "::1",
]


def ensure_out(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_wordlist(path: str | Path, offset: int = 0, limit: int | None = None) -> Iterator[str]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"字典不存在: {path}")
    n = 0
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i < offset:
                continue
            w = line.strip()
            if not w:
                continue
            yield w
            n += 1
            if limit is not None and n >= limit:
                break


def count_lines(path: str | Path) -> int:
    path = Path(path)
    if not path.exists():
        return 0
    try:
        import subprocess

        r = subprocess.run(["wc", "-l", str(path)], capture_output=True, text=True, check=True)
        return int(r.stdout.split()[0])
    except Exception:
        n = 0
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for _ in f:
                n += 1
        return n


def make_session(proxy: str = "", ua: str = DEFAULT_UA, verify: bool = False) -> requests.Session:
    s = requests.Session()
    s.verify = verify
    s.headers.update({"User-Agent": ua, "Accept": "application/json, text/plain, */*"})
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def random_xff_headers() -> dict[str, str]:
    ip = random.choice(PRIVATE_IPS)
    hdr = {h: ip for h in XFF_HEADERS}
    hdr["X-Forwarded-For"] = f"{ip}, 8.8.8.8"
    return hdr


def json_or_text(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return resp.text[:500]


def save_hit(out: Path, tag: str, payload: dict) -> None:
    out = ensure_out(out)
    row = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "tag": tag, **payload}
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def log(msg: str) -> None:
    print(msg, flush=True)


def add_pythonpath() -> None:
    p = "/data/pip/packages"
    if p not in sys.path and os.path.isdir(p):
        sys.path.insert(0, p)


def load_proxy(default: str = "") -> str:
    """Read first QG proxy from env files used in historical recon."""
    candidates = load_proxy_candidates()
    return candidates[0] if candidates else default


def load_proxy_candidates() -> list[str]:
    """Collect all configured proxy URLs from env files."""
    if os.environ.get("FAKA_PROXY"):
        return [os.environ["FAKA_PROXY"]]

    urls: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        url = url.strip()
        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    for envf in (
        "/data/tools/faka/data/proxy_pool.env",
        "/data/recon/.env.proxy",
        "/data/recon/cookie_tool/config/qg_proxy.env",
        "/data/recon/cookie_tool/.env.kuaidaili",
        "/data/recon/qq8one/.env",
    ):
        p = Path(envf)
        if not p.exists():
            continue
        vals: dict[str, str] = {}
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")

        for full_key in ("FAKA_PROXY", "QG_PROXY", "PROXY", "http_proxy"):
            v = vals.get(full_key, "")
            if v.startswith("http") and "${" not in v:
                add(v)

        key = vals.get("QG_AUTH_KEY") or vals.get("QG_USER") or vals.get("PROXY_USER")
        pwd = vals.get("QG_AUTH_PWD") or vals.get("QG_PASS") or vals.get("PROXY_PASS")
        host = vals.get("QG_TUNNEL_HOST") or vals.get("QG_HOST") or vals.get("PROXY_HOST")
        port = vals.get("QG_TUNNEL_PORT") or vals.get("QG_PORT") or vals.get("PROXY_PORT")
        if key and pwd and host and port:
            add(f"http://{key}:{pwd}@{host}:{port}")

    pool = Path("/data/recon/proxy_pool.txt")
    if pool.exists():
        for line in pool.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("http"):
                add(line)

    return urls


def load_cf_cookies(path: str) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    raw = p.read_text(encoding="utf-8", errors="ignore")
    try:
        items = json.loads(raw)
        if isinstance(items, list):
            return {c["name"]: c["value"] for c in items if "name" in c and "value" in c}
    except json.JSONDecodeError:
        pass
    cookies = {}
    for line in raw.splitlines():
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]
        elif "=" in line:
            k, v = line.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def apply_session(s: requests.Session, proxy: str = "", use_xff: bool = False, cf_cookies: str = "") -> requests.Session:
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    if use_xff:
        s.headers.update(random_xff_headers())
    if cf_cookies:
        for k, v in load_cf_cookies(cf_cookies).items():
            s.cookies.set(k, v)
    return s


def check_proxy(proxy: str, timeout: int = 8) -> bool:
    """Return True if HTTP proxy responds."""
    if not proxy:
        return True
    try:
        r = requests.get(
            "http://httpbin.org/ip",
            proxies={"http": proxy, "https": proxy},
            timeout=timeout,
            verify=False,
        )
        return r.status_code == 200
    except Exception:
        return False


def resolve_proxy(explicit: str = "auto", fallback_direct: bool = True) -> str:
    """Load proxy from env files, skip dead tunnels, optionally fall back to direct."""
    if explicit == "none":
        return ""
    if explicit and explicit != "auto":
        if check_proxy(explicit):
            return explicit
        if fallback_direct:
            log(f"[!] 指定代理不可用，改用直连")
            return ""
        return explicit
    loaded = load_proxy_candidates()
    for candidate in loaded:
        if check_proxy(candidate):
            return candidate
    if loaded and fallback_direct:
        log(f"[!] 全部代理不可用 ({len(loaded)} 个)，改用直连")
        return ""
    return loaded[0] if loaded else ""
