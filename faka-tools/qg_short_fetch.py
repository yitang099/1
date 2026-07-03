#!/usr/bin/env python3
"""青果短效代理-通道提取：API 取 IP + 写入 FAKA_PROXY。"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from faka_common import log

API = "https://share.proxy.qg.net/get"
ENV_FILE = Path("/data/tools/faka/data/proxy_pool.env")


def _load_creds() -> tuple[str, str]:
    key = os.environ.get("QG_AUTH_KEY", "")
    pwd = os.environ.get("QG_AUTH_PWD", "")
    if key and pwd:
        return key, pwd
    if ENV_FILE.exists():
        vals: dict[str, str] = {}
        for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
        key = vals.get("QG_AUTH_KEY") or vals.get("QG_SHORT_KEY", "")
        pwd = vals.get("QG_AUTH_PWD", "")
        if key and pwd:
            return key, pwd
    raise SystemExit("缺少 QG_AUTH_KEY / QG_AUTH_PWD（环境变量或 proxy_pool.env）")


def fetch_ip(key: str, pwd: str, num: int = 1, area: str = "") -> list[dict]:
    params = {"key": key, "pwd": pwd, "num": num}
    if area:
        params["area"] = area
    r = requests.get(API, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != "SUCCESS":
        raise RuntimeError(data)
    return data.get("data", [])


def to_proxy_url(key: str, pwd: str, server: str) -> str:
    host, port = server.rsplit(":", 1)
    return f"http://{quote(key, safe='')}:{quote(pwd, safe='')}@{host}:{port}"


def write_env(proxy: str, key: str, pwd: str, meta: dict) -> None:
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# 青果短效代理 wbbbdcaq（通道提取，5分钟粘性）
QG_AUTH_KEY={key}
QG_AUTH_PWD={pwd}
QG_SHORT_KEY={key}
FAKA_PROXY={proxy}
# meta: {json.dumps(meta, ensure_ascii=False)}
"""
    ENV_FILE.write_text(text, encoding="utf-8")
    ENV_FILE.chmod(0o600)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="青果短效通道提取")
    ap.add_argument("--key", default="")
    ap.add_argument("--pwd", default="")
    ap.add_argument("--num", type=int, default=1)
    ap.add_argument("--area", default="", help="地区编码，逗号分隔")
    ap.add_argument("--write-env", action="store_true", help="写入 proxy_pool.env")
    ap.add_argument("--test", action="store_true", help="测试 httpbin + 打印代理 URL")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    key, pwd = args.key, args.pwd
    if not key or not pwd:
        key, pwd = _load_creds()
    items = fetch_ip(key, pwd, args.num, args.area)
    if not items:
        raise SystemExit("无可用 IP")
    item = items[0]
    server = item["server"]
    proxy = to_proxy_url(key, pwd, server)
    log(f"area={item.get('area')} server={server} deadline={item.get('deadline')}")
    log(f"PROXY={proxy}")
    if args.write_env:
        write_env(proxy, key, pwd, item)
        log(f"written {ENV_FILE}")
    if args.test:
        r = requests.get(
            "http://httpbin.org/ip",
            proxies={"http": proxy, "https": proxy},
            timeout=20,
            verify=False,
        )
        log(f"httpbin={r.text.strip()}")
    print(proxy)


if __name__ == "__main__":
    main()
