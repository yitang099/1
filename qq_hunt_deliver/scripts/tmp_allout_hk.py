#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALL-OUT hunt on HK:
1) Scrape ALL TG channels for shop hosts
2) Massive brand/tld blast
3) Bing/DDG search harvest
4) Probe every host for YKFAKA + QQ faka (root+/shop)
"""
import re, urllib.request, urllib.parse, json, time, html as htmlmod
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path("/data/qq_hunt/allout")
OUT.mkdir(parents=True, exist_ok=True)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
YK = re.compile(
    r'(content=["\']YKFAKA["\']|YKFAKA|/User_Login\.html|/Gd_Query\.html|'
    r'/public/static/AmazeUI/|am-topbar-inverse|Welcome©\s*20\d{2}\s*YKFAKA)',
    re.I,
)
QQ = re.compile(
    r"(qq号|qq号码|批发qq|qq批发|卖qq|买qq|美卡|国卡|港卡|靓号|扫码号|换绑|卡位|"
    r"处号|太阳|月亮|皇冠|回流|直登|私人qq|企业qq|星星|单太|双太|三太|河马|老鬼|"
    r"奶猫|库里南|熊猫|教父|高部长|少帅|哆咪哆|慢慢|发号|号商|qq账号|绑卡qq|"
    r"美国卡qq|泰国卡qq|pc扫码|注册卡位)",
    re.I,
)
DROP = re.compile(
    r"(域名出售|parked|密钥猫|机场推荐|火箭统计|颜思|爱奇艺会员一个月\[测试\]|"
    r"传奇|私服|chatgpt账号)",
    re.I,
)
BAD_HOST = re.compile(
    r"(t\.me|telegram|github|google|baidu|bing|microsoft|qq\.com$|zhihu|"
    r"csdn|youtube|facebook|twitter|wikipedia|cloudflare)",
    re.I,
)


def fetch(url, timeout=13):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def scrape_tg(uname, pages=20):
    uname = uname.lstrip("@")
    hosts, users, links = set(), set(), set()
    before = None
    for _ in range(pages):
        url = "https://t.me/s/%s" % uname
        if before:
            url += "?before=%d" % before
        try:
            html = fetch(url, 12)
        except Exception:
            break
        ids = [
            int(x)
            for x in re.findall(
                r'data-post="%s/(\d+)"' % re.escape(uname), html
            )
        ]
        if not ids:
            break
        before = min(ids)
        for m in re.findall(
            r"(?:https?://)?((?:[a-z0-9-]+\.)+(?:top|lol|cc|vip|com|cn|one|icu|xyz|shop|net|pw|hk|me|site|store|online|club))",
            html,
            re.I,
        ):
            hosts.add(m.lower())
        for L in re.findall(r"https?://[^\s\"'<>]+", html):
            links.add(L.rstrip(").,;'\"}"))
        users |= set(
            re.findall(r"(?:t\.me/(?:s/)?|@)([A-Za-z0-9_]{4,32})", html)
        )
        time.sleep(0.04)
    return hosts, users, links


# ---------- seeds ----------
seeds = set()
for p in [
    Path("/data/qq_hunt/tg_crawl/QQ_TG_CHANNELS.txt"),
    Path("/data/qq_hunt/tg_chans_from_jump.txt"),
]:
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.search(r"t\.me/([A-Za-z0-9_]+)", line)
            if m:
                seeds.add(m.group(1))
            elif line.strip().startswith("@"):
                seeds.add(line.strip()[1:])

extra_seeds = [
    "mima1314_QQ", "Mima_1314", "xmqqtop", "xmqqq", "aiqq", "bwqq666",
    "aagao", "cccc88088", "shaoshuai169", "yedaoqq10", "xinhe080",
    "xiaodingdang122", "HNBC6866", "kln166", "HM08088", "qq321",
    "naimao188", "laoguiQQ888", "titanqqjf", "ttqq888", "qqhao8888",
    "qqhao98", "beimoqq888", "yewen887", "WSPJ981", "kc088",
    "qqhgm_com", "QQgongzuoshi",
]
seeds |= set(extra_seeds)
seeds = sorted(s for s in seeds if re.match(r"^[A-Za-z0-9_]{4,64}$", s) and not s.lower().endswith("bot"))
print("TG seeds", len(seeds), flush=True)

all_hosts, all_users, all_links = set(), set(), set()
with ThreadPoolExecutor(max_workers=12) as ex:
    futs = {ex.submit(scrape_tg, u): u for u in seeds}
    done = 0
    for fut in as_completed(futs):
        done += 1
        h, u, L = fut.result()
        all_hosts |= h
        all_users |= {x.lower() for x in u}
        all_links |= L
        if done % 40 == 0:
            print(
                "tg %d/%d hosts=%d links=%d"
                % (done, len(seeds), len(all_hosts), len(all_links)),
                flush=True,
            )

# BFS one more level on new users mentioning qq-ish
new_users = [
    u
    for u in all_users
    if u not in {s.lower() for s in seeds}
    and re.search(r"qq|hao|faka|mei|guo|liang|xinhe|yedao|mima|gao|xmqq|bwqq|tjqq", u, re.I)
][:200]
print("BFS users", len(new_users), flush=True)
with ThreadPoolExecutor(max_workers=10) as ex:
    for fut in as_completed([ex.submit(scrape_tg, u, 12) for u in new_users]):
        h, u, L = fut.result()
        all_hosts |= h
        all_links |= L

# search harvest
print("search...", flush=True)
queries = [
    "首页-优卡自动发卡网",
    "首页-高部长自动发卡网",
    "首页-少帅自动发卡网",
    "首页-教父网",
    "首页-哆咪哆商城",
    "YKFAKA 国卡",
    "YKFAKA QQ号批发",
    '"User_Login.html" 国卡',
    '"User_Login.html" QQ号',
    '"Welcome©" YKFAKA',
    "熊猫QQ 专注QQ业务 发卡",
    "河马金牌号商 shop",
    "无忧QQ批发",
    "QQ号批发 自动发卡",
    "国卡链接处号 发卡",
    "美卡QQ 自动发卡网",
    "源头号商 QQ 网站",
    "kas666 QQ",
    "qqhgm QQ号批发",
    "全网0纠纷 QQ 发卡",
]
for q in queries:
    for base in [
        "https://www.bing.com/search?q=%s&count=50" % urllib.parse.quote(q),
        "https://duckduckgo.com/html/?q=%s" % urllib.parse.quote(q),
    ]:
        try:
            html = fetch(base, 16)
        except Exception:
            continue
        for m in re.findall(
            r"(?:https?://)?([a-z0-9][-a-z0-9.]{2,60}\.(?:top|lol|cc|vip|com|cn|one|net|xyz|shop|hk|icu|pw|me|site))",
            html,
            re.I,
        ):
            all_hosts.add(m.lower().split("/")[0])
        time.sleep(0.2)

# brand blast
brands = [
    "mima1314", "mima", "gao1314", "gao", "shaoshuai", "wwwb2c", "b2c",
    "xmqqw", "xmqqq", "xmqq", "bwqq", "ttqq", "tjqq", "dmdqq", "hm0880",
    "hmqq", "jiaofu", "youka", "ykfaka", "efaka", "yifaka", "faka1314",
    "qq1314", "hao1314", "laogui", "naimao", "hemaqq", "kulinnan", "kln166",
    "aiqq", "pandaqq", "xiongmao", "yedaoqq", "yewen", "xinhe001", "xinghe",
    "baichuan", "yujuqq", "xdd6689", "piguqq", "kangsfqq", "maiqq", "maihaoqq",
    "qqhao", "qqfk", "qqhgm", "qqduo", "qqpf", "pifaqq", "pfqq", "5yqqqq",
    "wuyouqq", "kas666", "qq6666", "qq8", "qq520", "qq234", "qq178", "qq899",
    "lianghao", "1818lianghao", "16lh", "taoqqhao", "yunies", "qqzhw",
    "qqxhao", "jinku", "qd93", "elmqq", "zzqq", "nengliang", "fffzz",
    "youhui1998", "az886", "htqq", "hu6621", "kk987", "zhanghaofk",
    "xxn7788", "xihongqq", "naimaoqq", "maoqq", "vipworld8", "yxpf360",
]
tlds = [".com", ".top", ".lol", ".cc", ".vip", ".cn", ".net", ".xyz", ".one", ".icu", ".shop", ".hk", ".pw", ".me"]
nums = ["", "1", "2", "6", "8", "88", "666", "888", "1314", "168", "001", "080", "66", "99", "1688", "2024", "2025", "2026"]
for b in brands:
    for n in nums:
        for t in tlds:
            all_hosts.add("%s%s%s" % (b, n, t))

# from links
for L in all_links:
    try:
        m = re.search(r"https?://([^/\s]+)", L)
        if m:
            all_hosts.add(m.group(1).lower().removeprefix("www."))
    except Exception:
        pass

# previous delivers
for p in [
    Path("/data/qq_hunt/round3/DELIVER_QQ_urls.txt"),
    Path("/data/qq_hunt/ykfaka_final.txt"),
    Path("/data/qq_hunt/mega_faka_hk/hosts_from_tg.txt"),
]:
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.search(r"https?://([^/\s]+)", line)
            if m:
                all_hosts.add(m.group(1).lower().removeprefix("www."))
            elif re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", line.strip(), re.I):
                all_hosts.add(line.strip().lower())

hosts = sorted(
    h
    for h in all_hosts
    if h
    and "." in h
    and len(h) < 60
    and not BAD_HOST.search(h)
    and not h.startswith(".")
)
(OUT / "hosts_all.txt").write_text("\n".join(hosts) + "\n", encoding="utf-8")
print("PROBE hosts", len(hosts), flush=True)


def probe(h):
    best = None
    for url in ["https://%s/" % h, "https://%s/shop/" % h]:
        try:
            html = fetch(url, 12)
        except Exception:
            continue
        if len(html) < 400:
            continue
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        if DROP.search(title or ""):
            continue
        blob = "%s %s" % (title, html[:22000])
        if not QQ.search(blob):
            continue
        yk = bool(YK.search(html))
        trades = len(re.findall(r"(?:Trade|Item)/\d+\.html", html, re.I))
        goods = len(re.findall(r"(购买|下单|库存|卡密)", html))
        stocks = [int(x) for x in re.findall(r">\s*(\d{2,6})\s*<", html) if int(x) < 500000]
        stock_sum = sum(stocks[:50])
        score = min(trades, 120) * 2 + min(goods, 100) + min(stock_sum // 15, 150)
        if yk:
            score += 30
        if len(html) > 25000:
            score += 25
        elif len(html) > 12000:
            score += 12
        if re.search(r"(源头|一手|机房|金牌|五年|六年|全网0纠纷|批发|专注QQ|号商)", blob):
            score += 35
        row = {
            "url": ("https://%s/" % h) if yk else (url if "/shop" in url else "https://%s/" % h),
            "host": h,
            "title": title[:160],
            "ykfaka": yk,
            "large_score": score,
            "trades": trades,
            "type": "大型卖Q" if score >= 50 else "卖Q发卡",
            "system": "YKFAKA易发卡" if yk else "发卡站",
        }
        if not best or score > best["large_score"]:
            best = row
    return best


hits = []
with ThreadPoolExecutor(max_workers=18) as ex:
    futs = [ex.submit(probe, h) for h in hosts]
    for i, fut in enumerate(as_completed(futs), 1):
        r = fut.result()
        if r:
            hits.append(r)
            tag = "YK" if r["ykfaka"] else "--"
            print(
                "HIT",
                r["type"],
                "score=%d" % r["large_score"],
                tag,
                r["url"],
                r["title"][:40],
                flush=True,
            )
        if i % 100 == 0:
            print("prog %d/%d hits=%d yk=%d" % (i, len(hosts), len(hits), sum(1 for x in hits if x["ykfaka"])), flush=True)

by = {}
for r in hits:
    if r["host"] not in by or r["large_score"] > by[r["host"]]["large_score"]:
        by[r["host"]] = r

# stem dedupe
from collections import defaultdict

stem_map = defaultdict(list)
for r in by.values():
    stem = r["host"].split(".")[0]
    stem_map[stem].append(r)
final = []
for stem, items in stem_map.items():
    items = sorted(
        items,
        key=lambda x: (-x["large_score"], 0 if x["ykfaka"] else 1, len(x["host"])),
    )
    final.append(items[0])

final = sorted(final, key=lambda x: (-x["large_score"], x["host"]))
large = [r for r in final if r["large_score"] >= 50]
yk = [r for r in final if r["ykfaka"]]

(OUT / "all.json").write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "large.json").write_text(json.dumps(large, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "ykfaka.json").write_text(json.dumps(yk, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "大型卖Q发卡站.txt").write_text(
    "\n".join(
        "%s\t%s\tscore=%d\t%s\t%s"
        % (r["type"], r["url"], r["large_score"], r["system"], r["title"])
        for r in large
    )
    + "\n",
    encoding="utf-8",
)
(OUT / "全部卖Q发卡站.txt").write_text(
    "\n".join(
        "%s\t%s\tscore=%d\t%s\t%s"
        % (r["type"], r["url"], r["large_score"], r["system"], r["title"])
        for r in final
    )
    + "\n",
    encoding="utf-8",
)
(OUT / "YKFAKA易发卡.txt").write_text(
    "\n".join(
        "%s\tscore=%d\t%s\t%s" % (r["url"], r["large_score"], r["type"], r["title"])
        for r in yk
    )
    + "\n",
    encoding="utf-8",
)
(OUT / "urls_large.txt").write_text("\n".join(r["url"] for r in large) + "\n", encoding="utf-8")
(OUT / "stats.txt").write_text(
    json.dumps(
        {
            "tg_seeds": len(seeds),
            "hosts_probed": len(hosts),
            "all_hits": len(final),
            "large": len(large),
            "ykfaka": len(yk),
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(
    "DONE all=%d large=%d yk=%d probed=%d"
    % (len(final), len(large), len(yk), len(hosts)),
    flush=True,
)
print("---YKFAKA---", flush=True)
for r in yk:
    print(r["url"], r["large_score"], r["title"][:50], flush=True)
print("---LARGE TOP50---", flush=True)
for r in large[:50]:
    print(
        r["url"],
        r["large_score"],
        r["system"],
        r["title"][:40],
        flush=True,
    )
