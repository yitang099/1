#!/usr/bin/env python3
"""
CORS 反射 + credentials 检测。

示例:
  python3 cors_scan.py -u https://s.sggyx.com/shopApi/Shop/info -X POST -d '{"token":"test"}'
  python3 cors_scan.py -u https://zhanghao9.com/user/api/site/info
"""
from __future__ import annotations

import argparse
import json

import requests

from faka_common import DEFAULT_UA, ensure_out, json_or_text, load_proxy, log, save_hit
from pathlib import Path


def test_cors(url: str, method: str, body: str, origin: str, timeout: int, proxy: str) -> dict:
    headers = {
        "User-Agent": DEFAULT_UA,
        "Origin": origin,
        "Access-Control-Request-Method": method,
        "Content-Type": "application/json",
    }
    proxies = {"http": proxy, "https": proxy} if proxy else None
    proxies_list = [proxy] if proxy else []
    proxies_list.append("")
    result = {"url": url, "origin": origin, "method": method}

    for px in proxies_list:
        proxies = {"http": px, "https": px} if px else None
        headers = {
            "User-Agent": DEFAULT_UA,
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Content-Type": "application/json",
        }
        try:
            requests.options(url, headers=headers, timeout=timeout, proxies=proxies, verify=False)
            if method.upper() == "POST":
                r = requests.post(url, data=body, headers={**headers, "Content-Type": "application/json"}, timeout=timeout, proxies=proxies, verify=False)
            else:
                r = requests.get(url, headers=headers, timeout=timeout, proxies=proxies, verify=False)
            result["status"] = r.status_code
            result["acao_actual"] = r.headers.get("Access-Control-Allow-Origin", "")
            result["acac_actual"] = r.headers.get("Access-Control-Allow-Credentials", "")
            result["body"] = json_or_text(r)
            result["vulnerable"] = (
                result.get("acao_actual") in (origin, "*") or origin in str(result.get("acao_actual", ""))
            ) and result.get("acac_actual", "").lower() == "true"
            return result
        except Exception as e:
            result["error"] = str(e)
            continue
    return result


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="CORS 检测")
    ap.add_argument("-u", "--url", required=True)
    ap.add_argument("-X", "--method", default="GET")
    ap.add_argument("-d", "--data", default="{}")
    ap.add_argument("--origin", default="https://evil.com")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--out", default="/data/tools/faka/out/cors_scan.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = load_proxy() if args.proxy == "auto" else ("" if args.proxy == "none" else args.proxy)
    res = test_cors(args.url, args.method, args.data, args.origin, args.timeout, proxy)
    log(json.dumps(res, ensure_ascii=False, indent=2))
    if res.get("vulnerable"):
        save_hit(Path(args.out), "cors_vuln", res)
        log("[+] CORS 反射 + credentials 可能存在")


if __name__ == "__main__":
    main()
