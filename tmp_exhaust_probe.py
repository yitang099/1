#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thorough probe of all candidate hosts via Qingguo proxy on jump."""
import os, re, json, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROXY = os.environ.get("PROXY", "")
HOSTS_FILE = Path(os.environ.get("HOSTS_FILE", "/data/qq_hunt/round3/exhaust_hosts.txt"))
OUT = Path("/data/qq_hunt/round3/exhaust_probe")
OUT.mkdir(parents=True, exist_ok=True)

QQ = re.compile(r"(QQ|qq|企鹅|扣扣|号码|号商|发卡|已售|库存|/shop|月卡|三网)", re.I)
REJECT_TITLE = re.compile(
    r"(域名已过期|DNSPod|卡盾防火墙|Facebook|Instagram|小红书|苹果id|Apple ID|"
    r"WhatsApp|飞机号|海外账号批发|博彩|威尼斯|棋牌|casino|1xbet)",
    re.I,
)


def curl(url, timeout=18):
    cmd = [
        "curl", "-sL", "-A", "Mozilla/5.0",
        "--max-time", str(timeout), "-x", PROXY, "-k", url,
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
        return p.stdout.decode("utf-8", "ignore")
    except Exception:
        return ""


def classify(body):
    if re.search(r"易发卡|ykfaka|YKFAKA", body, re.I):
        return "YKFAKA易发卡"
    if re.search(r"异次元", body):
        return "异次元发卡"
    if re.search(r"独角", body):
        return "独角数卡"
    if re.search(r'title="商品库存">\d+个', body):
        return "卡网列表模板(通用自动发卡)"
    if re.search(r"靓号", body):
        return "靓号网/选号站"
    return "未识别模板"


def probe(host):
    best = None
    for url in [
        f"https://{host}/shop/",
        f"https://{host}/",
        f"http://{host}/shop/",
        f"http://{host}/",
    ]:
        body = curl(url)
        if not body or len(body) < 300:
            continue
        title_m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
        title = re.sub(r"\s+", " ", title_m.group(1) if title_m else "").strip()
        title = re.sub(r"<[^>]+>", "", title)[:140]
        if REJECT_TITLE.search(title) and not re.search(r"QQ|企鹅", title):
            continue
        qq = bool(QQ.search(body) or QQ.search(title))
        sales = 0
        for pat in [
            r"已售[^\d]{0,8}(\d+)",
            r'title="[^"]*已售[^"]*">(\d+)',
            r"销量[^\d]{0,8}(\d+)",
        ]:
            vals = [int(x) for x in re.findall(pat, body)]
            if vals:
                sales = sum(vals)
                break
        stock = sum(int(x) for x in re.findall(r'title="商品库存">(\d+)个', body))
        if not stock:
            stock = sum(int(x) for x in re.findall(r"库存[^\d]{0,6}(\d+)", body)[:40])
        sys = classify(body)
        strong_qq = bool(
            re.search(r"QQ|企鹅|扣扣|qq号|QQ号|卖Q", body + title)
        )
        shopish = (
            "/shop" in url
            or sys.startswith(("YKFAKA", "卡网", "异次元", "独角", "靓号"))
            or re.search(r"商品|库存|购买|下单|发卡", body)
        )
        row = {
            "host": host,
            "url": url,
            "title": title,
            "qq": qq,
            "strong_qq": strong_qq,
            "sales": sales,
            "stock": stock,
            "sys": sys,
            "len": len(body),
        }
        if strong_qq and shopish:
            return row
        if qq and shopish and (stock > 0 or sales > 0 or sys.startswith("YKFAKA") or sys.startswith("卡网")):
            return row
        if best is None or (strong_qq and not best.get("strong_qq")):
            best = row
    return best or {
        "host": host,
        "url": "",
        "title": "",
        "qq": False,
        "strong_qq": False,
        "sales": 0,
        "stock": 0,
        "sys": "dead",
        "len": 0,
    }


def main():
    hosts = [h.strip() for h in HOSTS_FILE.read_text().splitlines() if h.strip()]
    # de-dupe preserve order
    seen = set()
    uniq = []
    for h in hosts:
        h = h.lower().strip()
        if h and h not in seen:
            seen.add(h)
            uniq.append(h)
    hosts = uniq
    print("probing", len(hosts), "via", PROXY, flush=True)
    rows = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(probe, h): h for h in hosts}
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            rows.append(r)
            mark = "QQ" if r.get("strong_qq") or (r.get("qq") and r.get("stock", 0) > 0) else (
                "hit" if r.get("len", 0) > 500 else "dead"
            )
            print(
                f"{i}/{len(hosts)} {mark} {r['host']} sales={r.get('sales')} stock={r.get('stock')} {r.get('sys')} {r.get('title','')[:55]}",
                flush=True,
            )
            if i % 50 == 0:
                (OUT / "probe_partial.json").write_text(
                    json.dumps(rows, ensure_ascii=False), encoding="utf-8"
                )

    rows.sort(
        key=lambda x: (
            -(x.get("strong_qq") or False),
            -(x.get("qq") or False),
            -x.get("sales", 0),
            -x.get("stock", 0),
        )
    )
    (OUT / "probe_results.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    alive = [
        r
        for r in rows
        if (r.get("strong_qq") or (r.get("qq") and (r.get("stock", 0) > 0 or r.get("sys", "").startswith(("YKFAKA", "卡网")))))
        and r.get("sys") != "dead"
        and not REJECT_TITLE.search(r.get("title") or "")
    ]
    # extra filter: must look like QQ shop
    strict = []
    for r in alive:
        t = (r.get("title") or "") + " " + r["host"]
        if r.get("strong_qq") or re.search(r"qq|faka|hao", r["host"], re.I):
            if re.search(r"Facebook|Instagram|小红书|苹果|WhatsApp|飞机号", r.get("title") or "") and not re.search(
                r"QQ|企鹅", r.get("title") or ""
            ):
                continue
            strict.append(r)
    (OUT / "qq_alive.json").write_text(
        json.dumps(strict, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("ALIVE_QQ", len(strict), "/", len(rows), flush=True)
    for r in strict:
        print(
            "+",
            r["host"],
            r["sales"],
            r["stock"],
            r["sys"],
            r["url"],
            r["title"][:60],
        )


if __name__ == "__main__":
    main()
