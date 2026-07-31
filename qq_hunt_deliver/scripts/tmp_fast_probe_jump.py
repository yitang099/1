#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fast parallel probe of host lists via Qingguo; merge-friendly output."""
import json, re, time, html as htmlmod, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict

OUT = Path("/data/qq_hunt/allout")
OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
YK = re.compile(
    r'(content=["\']YKFAKA["\']|YKFAKA|/User_Login\.html|/Gd_Query\.html|'
    r'/public/static/AmazeUI/|Welcome©\s*20\d{2}\s*YKFAKA)',
    re.I,
)
QQ = re.compile(
    r"(qq号|qq号码|批发qq|qq批发|卖qq|买qq|美卡|国卡|港卡|靓号|扫码号|换绑|卡位|"
    r"处号|太阳|月亮|皇冠|回流|直登|私人qq|企业qq|星星|单太|双太|三太|河马|老鬼|"
    r"奶猫|库里南|熊猫|教父|高部长|少帅|哆咪哆|慢慢|发号|号商|qq账号|绑卡qq|"
    r"美国卡qq|泰国卡qq|pc扫码|注册卡位|qq小号)",
    re.I,
)
DROP = re.compile(r"(域名出售|parked|密钥猫|机场|传奇|私服|chatgpt|回收估价|代刷)", re.I)
proxy = {"url": None, "exp": 0}


def refresh_proxy():
    try:
        out = subprocess.check_output(
            ["curl", "-sS", "--max-time", "15", "https://share.proxy.qg.net/get?key=C413ED6D&num=1"],
            text=True,
        )
        data = json.loads(out)
        lst = data.get("data") or data.get("list") or []
        item = lst[0] if lst else data
        server = item.get("server") if isinstance(item, dict) else None
        if not server and isinstance(item, dict) and item.get("ip"):
            server = "%s:%s" % (item["ip"], item.get("port"))
        if not server:
            return None
        proxy["url"] = "http://C413ED6D:344F550A6F8B@%s" % server
        proxy["exp"] = time.time() + 50
        print("PROXY", server, flush=True)
        return proxy["url"]
    except Exception as e:
        print("proxy err", e, flush=True)
        return None


def curl_get(url, timeout=11):
    if time.time() > proxy["exp"] or not proxy["url"]:
        refresh_proxy()
    if not proxy["url"]:
        return ""
    try:
        return subprocess.check_output(
            ["curl", "-sS", "-L", "--max-time", str(timeout), "-x", proxy["url"], "-A", UA,
             "-H", "Accept-Language: zh-CN,zh;q=0.9", url],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", "ignore")
    except Exception:
        return ""


def probe(h):
    best = None
    for url in ["https://%s/" % h, "https://%s/shop/" % h, "http://%s/" % h, "http://%s/shop/" % h]:
        html = curl_get(url, 11)
        if len(html) < 400:
            continue
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = re.sub(r"\s+", " ", htmlmod.unescape(m.group(1))).strip() if m else ""
        if DROP.search(title or ""):
            continue
        blob = "%s %s" % (title, html[:25000])
        yk = bool(YK.search(html))
        if not QQ.search(blob):
            if not (yk and re.search(r"(发卡|卡密|下单)", blob)):
                continue
        trades = len(re.findall(r"(?:Trade|Item)/\d+\.html", html, re.I))
        goods = len(re.findall(r"(购买|下单|库存|卡密)", html))
        stocks = [int(x) for x in re.findall(r">\s*(\d{2,6})\s*<", html) if int(x) < 500000]
        score = min(trades, 120) * 2 + min(goods, 100) + min(sum(stocks[:50]) // 15, 150)
        if yk:
            score += 30
        if len(html) > 25000:
            score += 25
        elif len(html) > 12000:
            score += 12
        if re.search(r"(源头|一手|机房|金牌|五年|六年|全网0纠纷|批发|专注QQ|号商)", blob):
            score += 35
        if score < 15 and not yk:
            continue
        row = {
            "url": ("https://%s/" % h) if yk else url,
            "host": h,
            "title": title[:160],
            "ykfaka": yk,
            "large_score": score,
            "type": "大型卖Q" if score >= 50 else "卖Q发卡",
            "system": "YKFAKA易发卡" if yk else "发卡站",
        }
        if not best or score > best["large_score"]:
            best = row
    return best


hosts = set()
for p in [
    OUT / "hosts_from_hk.txt",
    OUT / "tg_deep_hosts.txt",
    OUT / "hosts_queue.txt",
    Path("/data/qq_hunt/round3/hosts_alive_merged.txt"),
    Path("/data/qq_hunt/round3/DELIVER_QQ_urls.txt"),
    Path("/data/qq_hunt/round3/FINAL_QQ_STRICT_urls.txt"),
]:
    if not p.exists():
        continue
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip().lower()
        m = re.search(r"https?://([^/\s]+)", line)
        if m:
            line = m.group(1)
        line = line.removeprefix("www.")
        if re.match(r"^[a-z0-9.-]+\.[a-z]{2,24}$", line) and len(line) < 58:
            hosts.add(line)

hosts = sorted(hosts)
print("probe", len(hosts), flush=True)
refresh_proxy()
hits = []
with ThreadPoolExecutor(max_workers=22) as ex:
    futs = [ex.submit(probe, h) for h in hosts]
    for i, fut in enumerate(as_completed(futs), 1):
        r = fut.result()
        if r:
            hits.append(r)
            print("HIT", r["type"], r["large_score"], "YK" if r["ykfaka"] else "--", r["url"], r["title"][:40], flush=True)
        if i % 150 == 0:
            refresh_proxy()
            print("prog %d/%d hits=%d yk=%d" % (i, len(hosts), len(hits), sum(1 for x in hits if x["ykfaka"])), flush=True)
            (OUT / "fast_hits_partial.json").write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")

by = {}
for r in hits:
    if r["host"] not in by or r["large_score"] > by[r["host"]]["large_score"]:
        by[r["host"]] = r
stem = defaultdict(list)
for r in by.values():
    stem[r["host"].split(".")[0]].append(r)
final = []
for items in stem.values():
    items = sorted(items, key=lambda x: (-x["large_score"], 0 if x["ykfaka"] else 1, len(x["host"])))
    final.append(items[0])
final = sorted(final, key=lambda x: (-x["large_score"], x["host"]))
(OUT / "fast_all.json").write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "fast_stats.json").write_text(
    json.dumps({"probed": len(hosts), "hits": len(final), "large": sum(1 for x in final if x["large_score"] >= 50), "yk": sum(1 for x in final if x["ykfaka"])}, indent=2),
    encoding="utf-8",
)
print("DONE", len(final), "yk", sum(1 for x in final if x["ykfaka"]), flush=True)
for r in final:
    if r["ykfaka"] or r["large_score"] >= 50:
        print(r["url"], r["large_score"], r["system"], r["title"][:50], flush=True)
