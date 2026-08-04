#!/usr/bin/env python3
"""Probe Qingguo pool against 太白 query API."""
import concurrent.futures
import time

import requests
import urllib3

urllib3.disable_warnings()

KEY = "C413ED6D"
PWD = "344F550A6F8B"
B = "https://shopping.qq11399.vip"


def main():
    q = requests.get(f"https://share.proxy.qg.net/query?key={KEY}", timeout=15).json()
    items = sorted(q.get("data") or [], key=lambda x: x.get("deadline", ""), reverse=True)
    pool = [d["server"] for d in items]
    print(
        "pool",
        len(pool),
        "newest",
        items[0].get("deadline") if items else None,
        "oldest",
        items[-1].get("deadline") if items else None,
        flush=True,
    )

    def probe(server):
        proxies = {
            "http": f"http://{KEY}:{PWD}@{server}",
            "https": f"http://{KEY}:{PWD}@{server}",
        }
        t0 = time.time()
        try:
            r = requests.post(
                B + "/user/api/index/query",
                data={"keywords": "zzznotexist999@qq.com"},
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "X-Requested-With": "XMLHttpRequest",
                    "Origin": B,
                    "Referer": B + "/",
                },
                proxies=proxies,
                verify=False,
                timeout=20,
            )
            return True, server, r.status_code, r.text[:80], round(time.time() - t0, 2)
        except Exception as e:
            return False, server, e.__class__.__name__, str(e)[:100], round(time.time() - t0, 2)

    ok = 0
    with concurrent.futures.ThreadPoolExecutor(min(20, max(1, len(pool)))) as ex:
        for res in ex.map(probe, pool):
            print(res, flush=True)
            if res[0]:
                ok += 1
    print("OK", ok, "/", len(pool), flush=True)


if __name__ == "__main__":
    main()
