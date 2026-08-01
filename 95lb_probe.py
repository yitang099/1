#!/usr/bin/env python3
"""95lb.com deep probe: routes, buy flow, order search."""
import json
import re
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://95lb.com/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
OUT = "/tmp/95lb_probe.json"

PATHS = [
    "/search",
    "/shop/cart",
    "/login",
    "/user/recharge",
    "/item?id=4690",
    "/user/order/list",
    "/user/trade/list",
    "/order/search",
    "/api/shop/order/search",
    "/user/api/order/search",
]


def main():
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": UA, "Referer": BASE})
    report = {"target": "95lb.com", "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "paths": {}}

    r = s.get(BASE, timeout=25)
    report["home_len"] = len(r.text)
    report["version"] = "5.0.34" if "5.0.34" in r.text else "?"

    for p in PATHS:
        try:
            rr = s.get(BASE.rstrip("/") + p, timeout=15)
            report["paths"][p] = {
                "status": rr.status_code,
                "len": len(rr.text),
                "snip": rr.text[:120].replace("\n", " "),
            }
        except Exception as e:
            report["paths"][p] = {"error": str(e)[:80]}

    # item buy page scripts
    item = s.get(BASE + "item?id=4690", timeout=20)
    report["item_api"] = re.findall(r'["\'](/[a-zA-Z0-9_./-]+)["\']', item.text)
    report["item_api"] = [
        x for x in report["item_api"]
        if any(k in x.lower() for k in ("api", "order", "trade", "pay", "user", "shop"))
    ][:40]

    # guest order search common patterns
    for url, data in [
        ("/search", {"keywords": "1"}),
        ("/", {"keywords": "qq"}),
    ]:
        try:
            rr = s.get(BASE.rstrip("/") + url, params=data, timeout=15)
            report[f"search_{data}"] = {"len": len(rr.text), "status": rr.status_code}
        except Exception as e:
            report[f"search_{data}"] = {"error": str(e)[:60]}

    with open(OUT, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
