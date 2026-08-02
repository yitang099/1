#!/usr/bin/env python3
"""Qingguo domestic short-term proxy (中转池 / 通道提取) helper.

Extract via share.proxy.qg.net, connect with authkey:authpwd@server.
Requires the runner host IP to be on the product whitelist (or account auth enabled).
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests

requests.packages.urllib3.disable_warnings()

API_BASE = "https://share.proxy.qg.net"
DEFAULT_KEY = os.environ.get("QG_CN_KEY", "C413ED6D")
DEFAULT_PWD = os.environ.get("QG_CN_PWD", "344F550A6F8B")


@dataclass
class CnProxy:
    server: str
    proxy_ip: str
    area: str
    area_code: int
    isp: str
    deadline: str
    proxy_url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "server": self.server,
            "proxy_ip": self.proxy_ip,
            "area": self.area,
            "area_code": self.area_code,
            "isp": self.isp,
            "deadline": self.deadline,
        }


def _row_to_proxy(row: dict[str, Any], key: str, pwd: str) -> CnProxy:
    server = row["server"]
    return CnProxy(
        server=server,
        proxy_ip=row.get("proxy_ip", ""),
        area=row.get("area", ""),
        area_code=int(row.get("area_code", 0) or 0),
        isp=row.get("isp", ""),
        deadline=row.get("deadline", ""),
        proxy_url=f"http://{key}:{pwd}@{server}",
    )


def _api_get(path: str, key: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = {"key": key}
    if params:
        p.update(params)
    r = requests.get(f"{API_BASE}/{path}", params=p, timeout=20, verify=False)
    return r.json()


def channels(key: str = DEFAULT_KEY) -> dict[str, int]:
    j = _api_get("channels", key)
    if j.get("code") != "SUCCESS":
        return {"total": 0, "idle": 0, "error": j.get("message", j.get("code"))}
    d = j.get("data") or {}
    return {"total": int(d.get("total", 0)), "idle": int(d.get("idle", 0))}


def fetch_proxy(
    key: str = DEFAULT_KEY,
    pwd: str = DEFAULT_PWD,
    area: str | None = None,
    prefer: str = "pool",
) -> CnProxy | None:
    """Return one domestic proxy. Tries pool → get → query (reuse in-use)."""
    params: dict[str, Any] = {"num": 1}
    if area:
        params["area"] = area
    order = ["pool", "get", "query"] if prefer == "pool" else ["get", "pool", "query"]
    for path in order:
        try:
            j = _api_get(path, key, params if path != "query" else None)
        except Exception:
            continue
        if j.get("code") != "SUCCESS":
            continue
        data = j.get("data") or []
        if not data:
            continue
        return _row_to_proxy(data[0], key, pwd)
    return None


def probe_proxy(proxy_url: str, timeout: int = 18) -> dict[str, Any]:
    """Check proxy reachability and whitelist."""
    out: dict[str, Any] = {"ok": False}
    try:
        r = requests.get(
            "http://myip.ipip.net",
            proxies={"http": proxy_url, "https": proxy_url},
            timeout=timeout,
            verify=False,
            allow_redirects=False,
        )
        body = (r.text or "").strip()
        loc = r.headers.get("Location", "")
        out["status"] = r.status_code
        if loc:
            out["location"] = loc[:120]
        out["body"] = body[:200]
        if "not allowed" in body or "unavailable" in body:
            out["whitelist_block"] = True
            return out
        if r.status_code == 302 and "yunkv" in loc:
            out["risk_control"] = True
            return out
        if "当前 IP" in body or (r.status_code == 200 and len(body) < 200):
            out["ok"] = True
    except Exception as e:
        out["error"] = str(e)[:160]
    return out


def make_session(
    proxy_url: str,
    referer: str = "https://xinhe001.lol/shop/",
    ua: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
) -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.proxies = {"http": proxy_url, "https": proxy_url}
    s.headers.update(
        {
            "User-Agent": ua,
            "Referer": referer,
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    )
    return s


def rotate_until_working(
    key: str = DEFAULT_KEY,
    pwd: str = DEFAULT_PWD,
    area: str | None = None,
    attempts: int = 12,
    sleep_s: float = 0.4,
) -> tuple[CnProxy | None, dict[str, Any]]:
    log: dict[str, Any] = {"attempts": []}
    for i in range(attempts):
        px = fetch_proxy(key, pwd, area=area)
        if not px:
            log["attempts"].append({"i": i, "error": "extract_failed"})
            time.sleep(sleep_s)
            continue
        pr = probe_proxy(px.proxy_url)
        row = {"i": i, "proxy": px.as_dict(), "probe": pr}
        log["attempts"].append(row)
        if pr.get("ok"):
            return px, log
        if pr.get("whitelist_block"):
            log["whitelist_block"] = True
            return None, log
        if pr.get("risk_control"):
            time.sleep(sleep_s)
            continue
        time.sleep(sleep_s)
    return None, log


if __name__ == "__main__":
    import json

    ch = channels()
    print("channels", ch)
    px, log = rotate_until_working(attempts=8)
    print("proxy", px.as_dict() if px else None)
    print("log", json.dumps(log, ensure_ascii=False, indent=2))
