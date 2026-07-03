#!/usr/bin/env python3
"""
发卡站指纹自动识别 → 推荐 playbook / 工具链。

示例:
  python3 faka_fingerprint.py https://zhanghao9.com
  python3 faka_fingerprint.py https://s.sggyx.com --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urlparse

import requests

from faka_common import DEFAULT_UA, json_or_text, load_proxy, log

SYSTEMS = {
    "acg": {
        "name": "异次元 ACG",
        "playbook": "/data/recon/playbooks/yiciyuan-faka-playbook.md",
        "tools": ["acg_idor", "acg_query_brute", "acg_login_brute", "order_enum", "sb_subdomain_scan"],
    },
    "rainbow": {
        "name": "彩虹发卡",
        "playbook": "/data/recon/playbooks/rainbow-faka-idor-playbook.md",
        "tools": ["rainbow_idor", "skey_chain", "probe_rainbow_faka.sh"],
    },
    "pisces": {
        "name": "Pisces/acg-faka",
        "playbook": "/data/recon/playbooks/pisces-faka-ordersearch-playbook.md",
        "tools": ["pisces_dump"],
    },
    "pyfaas": {
        "name": "赤马/pyfaas",
        "playbook": "/data/recon/playbooks/README.md",
        "tools": ["shop_token_scan", "pay_order_brute", "merchant_scan", "pyfaas_probe.sh"],
    },
}


@dataclass
class Fingerprint:
    url: str
    system: str
    confidence: int
    signals: list[str]
    playbook: str
    tools: list[str]
    samples: dict[str, Any]


def probe(url: str, path: str, method: str = "GET", json_body: dict | None = None, timeout: int = 15) -> Any:
    u = url.rstrip("/") + path
    headers = {"User-Agent": DEFAULT_UA}
    for proxy in ("", load_proxy()):
        proxies = {"http": proxy, "https": proxy} if proxy else None
        try:
            if method == "POST":
                r = requests.post(u, json=json_body, headers=headers, timeout=timeout, proxies=proxies, verify=False)
            else:
                r = requests.get(u, headers=headers, timeout=timeout, proxies=proxies, verify=False)
            return json_or_text(r), r.status_code, (r.text or "")[:2000]
        except Exception:
            continue
    return "connection failed", 0, ""


def fingerprint(base: str) -> Fingerprint:
    signals: list[str] = []
    scores = {k: 0 for k in SYSTEMS}
    samples: dict[str, Any] = {}

    # ACG
    d, code, text = probe(base, "/user/api/index/data")
    samples["acg_data"] = d
    if isinstance(d, dict) and d.get("code") == 200 and isinstance(d.get("data"), list):
        scores["acg"] += 5
        signals.append("ACG:/user/api/index/data=200")

    # Rainbow
    d, code, text = probe(base, "/ajax.php?act=getcount")
    samples["rainbow_getcount"] = d
    if isinstance(d, dict) and "orders" in str(d):
        scores["rainbow"] += 5
        signals.append("rainbow:ajax getcount")
    if "ajax.php" in text or "api.php" in text:
        scores["rainbow"] += 2
        signals.append("rainbow:ajax.php in page")

    # pyfaas shop
    d, code, text = probe(base, "/shopApi/Shop/info", "POST", {"token": "test"})
    samples["pyfaas_shop"] = d
    if isinstance(d, dict) and ("token" in str(d.get("msg", "")).lower() or d.get("code") in (0, 1)):
        scores["pyfaas"] += 4
        signals.append("pyfaas:shopApi/Shop/info")

    d, code, text = probe(base, "/merchantApi/system/config", "POST", {})
    samples["pyfaas_merchant"] = d
    if isinstance(d, dict) and d.get("code") == 1:
        scores["pyfaas"] += 3
        signals.append("pyfaas:merchantApi/system/config")

    # Pisces - fetch home and look for api/v1
    _, _, home = probe(base, "/")
    if "/api/v1/" in home or "pisces" in home.lower():
        scores["pisces"] += 3
        signals.append("pisces:api/v1 in frontend")
    m = re.search(r"/api/v1/([^/\"']+)", home)
    if m:
        api_name = m.group(1)
        d, _, _ = probe(base, f"/api/v1/{api_name}/template")
        samples["pisces_template"] = d
        if isinstance(d, dict) and d.get("code") == 1:
            scores["pisces"] += 4
            signals.append(f"pisces:/api/v1/{api_name}/template")

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        # fallback heuristics from URL/body
        if "sggyx" in base or "pyfaas" in str(samples).lower():
            best, scores["pyfaas"] = "pyfaas", 1
        elif isinstance(samples.get("acg_data"), dict):
            best, scores["acg"] = "acg", 1
    conf = scores.get(best, 0)
    meta = SYSTEMS.get(best, {"name": "未知", "playbook": "", "tools": ["faka_fingerprint"]})

    return Fingerprint(
        url=base,
        system=best,
        confidence=conf,
        signals=signals,
        playbook=meta.get("playbook", ""),
        tools=meta.get("tools", []),
        samples=samples,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="发卡站指纹识别")
    ap.add_argument("url")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    fp = fingerprint(args.url.rstrip("/"))
    if args.json:
        print(json.dumps(asdict(fp), ensure_ascii=False, indent=2))
        return
    log(f"目标: {fp.url}")
    log(f"体系: {fp.system} ({SYSTEMS.get(fp.system, {}).get('name', '未知')}) 置信={fp.confidence}")
    for s in fp.signals:
        log(f"  - {s}")
    if fp.playbook:
        log(f"playbook: {fp.playbook}")
    log(f"推荐工具: {', '.join(fp.tools)}")


if __name__ == "__main__":
    main()
