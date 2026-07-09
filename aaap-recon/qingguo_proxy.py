#!/usr/bin/env python3
"""青果网络短效代理（通道提取）辅助模块。

环境变量:
  QG_AUTHKEY  - Authkey (默认读取下方占位，请 export 覆盖)
  QG_AUTHPWD  - Authpwd

API: https://share.proxy.qg.net/get?key=AUTHKEY
用法: curl -x http://{key}:{pwd}@{server} {url}
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request

GET_URL = "https://share.proxy.qg.net/get"
QUERY_URL = "https://share.proxy.qg.net/query"
IP_URL = "https://d.qg.net/ip"

AUTHKEY = os.environ.get("QG_AUTHKEY", "")
AUTHPWD = os.environ.get("QG_AUTHPWD", "")


def _fetch(url: str, timeout: int = 15) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def egress_ip() -> str:
    with urllib.request.urlopen(IP_URL, timeout=10) as r:
        return r.read().decode().strip()


def get_proxy(force_new: bool = False) -> dict:
    """Return proxy dict: server, proxy_ip, area, deadline, proxy_url."""
    if not AUTHKEY or not AUTHPWD:
        raise RuntimeError("Set QG_AUTHKEY and QG_AUTHPWD environment variables")
    if not force_new:
        try:
            q = _fetch(f"{QUERY_URL}?key={AUTHKEY}")
            if q.get("code") == "SUCCESS" and q.get("data"):
                row = q["data"][0]
                return _row_to_proxy(row)
        except Exception:
            pass
    r = _fetch(f"{GET_URL}?key={AUTHKEY}&num=1")
    if r.get("code") != "SUCCESS":
        raise RuntimeError(f"proxy get failed: {r}")
    return _row_to_proxy(r["data"][0])


def _row_to_proxy(row: dict) -> dict:
    server = row["server"]
    host, port = server.rsplit(":", 1)
    return {
        "server": server,
        "host": host,
        "port": port,
        "proxy_ip": row.get("proxy_ip", ""),
        "area": row.get("area", ""),
        "deadline": row.get("deadline", ""),
        "proxy_url": f"http://{AUTHKEY}:{AUTHPWD}@{server}",
    }


def curl_via_proxy(url: str, method: str = "GET", data: str | None = None,
                   headers: list[str] | None = None, timeout: int = 25) -> tuple[str, int]:
    px = get_proxy()
    cmd = [
        "curl", "-sS", "-m", str(timeout), "-w", "\n__HTTP__%{http_code}",
        "-x", px["proxy_url"],
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    ]
    for h in headers or ["Accept-Language: zh-CN,zh;q=0.9"]:
        cmd += ["-H", h]
    if method == "POST":
        cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded"]
        if data:
            cmd += ["-d", data]
    cmd.append(url)
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", "replace")
    except subprocess.CalledProcessError as e:
        out = e.output.decode("utf-8", "replace")
        if "__HTTP__" not in out:
            return out.strip(), 0
    body, _, code = out.rpartition("__HTTP__")
    return body.strip(), int(code)


if __name__ == "__main__":
    print(f"egress_ip={egress_ip()}  (add to 青果白名单 if using whitelist mode)")
    try:
        p = get_proxy()
        print(json.dumps(p, ensure_ascii=False, indent=2))
        body, code = curl_via_proxy("https://xinhe001.lol/shop/")
        print(f"xinhe test http={code} body[:200]={body[:200]!r}")
    except Exception as e:
        print(f"error: {e}")
