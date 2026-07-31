#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jump-side ALL-OUT: Qingguo proxy + massive search + host blast + probe."""
import json, re, time, html as htmlmod, subprocess, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict

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
    r"美国卡qq|泰国卡qq|pc扫码|注册卡位|qq小号|买qq|卖qq|qq发卡)",
    re.I,
)
DROP = re.compile(
    r"(域名出售|parked|密钥猫|机场推荐|火箭统计|颜思|传奇|私服|chatgpt账号|"
    r"kärcher|karcher|物流|回收估价|代刷)",
    re.I,
)
BAD_HOST = re.compile(
    r"(t\.me|telegram|github|google|baidu|bing|microsoft|qq\.com$|zhihu|"
    r"csdn|youtube|facebook|twitter|wikipedia|cloudflare|sogou|so\.com|"
    r"duckduckgo|proxy\.qg|qg\.net|amap\.com|taobao|jd\.com|alibaba)",
    re.I,
)
HOST_RE = re.compile(
    r"(?:https?://)?([a-z0-9][-a-z0-9.]{1,55}\.(?:top|lol|cc|vip|com|cn|one|icu|xyz|shop|net|pw|hk|me|site|store|online|club|fun|info|wang|live))",
    re.I,
)

proxy = {"url": None, "exp": 0}


def refresh_proxy():
    # get qingguo ip:port
    try:
        out = subprocess.check_output(
            [
                "curl",
                "-sS",
                "--max-time",
                "15",
                "https://share.proxy.qg.net/get?key=C413ED6D&num=1",
            ],
            text=True,
        )
        data = json.loads(out)
        # expect data.list[0].server or similar
        item = None
        if isinstance(data, dict):
            lst = data.get("data") or data.get("list") or data.get("proxy_list")
            if isinstance(lst, list) and lst:
                item = lst[0]
            elif "server" in data:
                item = data
        if isinstance(item, str):
            server = item
        elif isinstance(item, dict):
            server = item.get("server") or item.get("ip")
            if server and ":" not in str(server) and item.get("port"):
                server = "%s:%s" % (server, item["port"])
        else:
            # try parse IP:PORT from raw
            m = re.search(r"(\d+\.\d+\.\d+\.\d+:\d+)", out)
            server = m.group(1) if m else None
        if not server:
            print("proxy parse fail", out[:200], flush=True)
            return None
        px = "http://C413ED6D:344F550A6F8B@%s" % server
        proxy["url"] = px
        proxy["exp"] = time.time() + 50
        print("PROXY", server, flush=True)
        return px
    except Exception as e:
        print("proxy err", e, flush=True)
        return None


def curl_get(url, timeout=14, use_proxy=True):
    if use_proxy:
        if time.time() > proxy["exp"] or not proxy["url"]:
            refresh_proxy()
        px = proxy["url"]
        if not px:
            return ""
        cmd = [
            "curl",
            "-sS",
            "-L",
            "--max-time",
            str(timeout),
            "-x",
            px,
            "-A",
            UA,
            "-H",
            "Accept-Language: zh-CN,zh;q=0.9",
            url,
        ]
    else:
        cmd = [
            "curl",
            "-sS",
            "-L",
            "--max-time",
            str(timeout),
            "-A",
            UA,
            url,
        ]
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode(
            "utf-8", "ignore"
        )
    except Exception:
        return ""


def extract_hosts(text):
    hs = set()
    for m in HOST_RE.findall(text or ""):
        h = m.lower().split("/")[0].removeprefix("www.")
        if BAD_HOST.search(h):
            continue
        if h.count(".") >= 1 and len(h) < 58:
            hs.add(h)
    return hs


all_hosts = set()

# load previous
for p in [
    Path("/data/qq_hunt/round3/DELIVER_QQ_urls.txt"),
    Path("/data/qq_hunt/round3/FINAL_QQ_STRICT_urls.txt"),
    Path("/data/qq_hunt/round3/FINAL_QQ_urls.txt"),
    Path("/data/qq_hunt/round3/hosts_alive_merged.txt"),
    Path("/data/qq_hunt/round3/hosts_raw.txt"),
    Path("/data/qq_hunt/round3/hosts_expand_raw.txt"),
    Path("/data/qq_hunt/round3/urls_large.txt"),
    Path("/data/qq_hunt/round3/大型卖Q发卡站.txt"),
    Path("/data/qq_hunt/round3/YKFAKA易发卡.txt"),
    Path("/data/qq_hunt/round3/卖Q站点_类型链接.txt"),
]:
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            all_hosts |= extract_hosts(line)

print("seed hosts", len(all_hosts), flush=True)

# ========== MASSIVE SEARCH ==========
queries = [
    "首页-优卡自动发卡网",
    "首页-高部长自动发卡网",
    "首页-少帅自动发卡网",
    "首页-教父网",
    "首页-哆咪哆商城",
    "首页-慢慢 自动发卡网",
    "首页-QQ号批发",
    "YKFAKA 国卡",
    "YKFAKA QQ号",
    "YKFAKA 美卡",
    '"User_Login.html" QQ',
    '"User_Login.html" 国卡',
    '"User_Login.html" 美卡',
    '"Gd_Query.html" QQ',
    "Welcome© YKFAKA",
    "content=\"YKFAKA\"",
    "熊猫QQ 专注QQ业务",
    "河马金牌号商",
    "库里南 一手QQ号商",
    "老鬼QQ 自动发卡",
    "无忧QQ批发",
    "QQ号批发 自动发卡",
    "国卡链接处号 发卡",
    "美卡QQ 自动发卡网",
    "源头号商 QQ 网站",
    "一手QQ号商 shop",
    "qqhgm QQ号批发",
    "全网0纠纷 QQ 发卡",
    "site:.top QQ号批发 发卡",
    "site:.lol QQ号商",
    "site:.cc 优卡自动发卡",
    "site:.vip 优卡自动发卡",
    "买QQ小号 自动发卡",
    "卖QQ号 发卡站",
    "直登QQ 批发 发卡",
    "太阳号 月亮号 发卡",
    "扫码号 换绑 发卡",
    "美卡国卡港卡 QQ",
    "奶猫QQ 号商",
    "星河QQ 飞机",
    "少帅自动发卡",
    "高部长自动发卡",
    "教父网 QQ",
    "哆咪哆商城",
    "xmqqw 优卡",
    "bwqq 优卡",
    "tjqq QQ号批发",
    "ttqq 慢慢",
    "mima1314 教父",
    "dmdqq 哆咪哆",
    "gao1314 高部长",
    "wwwb2c 少帅",
    "FK发卡 QQ",
    "彩虹发卡 QQ号",
    "异次元发卡 QQ",
    "独角数卡 QQ",
    "卡易信 QQ",
    "QQ靓号 自助购买",
    "QQ号码批发商城",
    "5位QQ 6位QQ 购买",
    "处号批发 发卡",
    "回流号 QQ 发卡",
    "企业QQ 私人QQ 发卡",
    "绑卡QQ 批发",
    "美国卡QQ 泰国卡",
    "PC扫码号 发卡",
    "注册卡位 QQ",
    "号商自助下单 QQ",
    "飞机 QQ号商 网站",
    "t.me QQ批发 发卡站",
]

print("search queries", len(queries), flush=True)
refresh_proxy()
for i, q in enumerate(queries, 1):
    qq = urllib.parse.quote(q)
    urls = [
        "https://www.bing.com/search?q=%s&count=50" % qq,
        "https://www.bing.com/search?q=%s&count=50&first=51" % qq,
        "https://duckduckgo.com/html/?q=%s" % qq,
        "https://www.sogou.com/web?query=%s" % qq,
        "https://www.so.com/s?q=%s" % qq,
    ]
    for u in urls:
        html = curl_get(u, 16, use_proxy=True)
        if not html:
            # refresh and retry once
            refresh_proxy()
            html = curl_get(u, 16, use_proxy=True)
        hs = extract_hosts(html)
        all_hosts |= hs
        # also extract from bing cite / <a href>
        for m in re.findall(r'href="(https?://[^"]+)"', html):
            all_hosts |= extract_hosts(m)
    if i % 10 == 0:
        print("search %d/%d hosts=%d" % (i, len(queries), len(all_hosts)), flush=True)
    time.sleep(0.15)

# crt.sh (direct, no proxy needed usually)
print("crt.sh...", flush=True)
crt_q = [
    "YKFAKA",
    "%25.ykfaka%25",
    "User_Login.html",
    "mima1314",
    "dmdqq",
    "xmqqw",
    "优卡自动发卡",
]
for q in crt_q:
    html = curl_get(
        "https://crt.sh/?q=%s&output=json" % urllib.parse.quote(q),
        25,
        use_proxy=False,
    )
    if html.strip().startswith("["):
        try:
            arr = json.loads(html)
            for row in arr[:2000]:
                name = row.get("name_value") or ""
                for part in re.split(r"[\s,]+", name):
                    part = part.strip().lower().lstrip("*.")
                    if re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", part):
                        all_hosts.add(part)
        except Exception:
            pass
    else:
        all_hosts |= extract_hosts(html)
    time.sleep(0.3)

# brand blast HUGE
brands = [
    "mima1314", "mima", "gao1314", "gaobu", "shaoshuai", "wwwb2c", "b2cqq",
    "xmqqw", "xmqqq", "xmqq", "bwqq", "ttqq", "tjqq", "dmdqq", "dmdd",
    "hm0880", "hmqq", "hemaqq", "jiaofu", "youka", "ykfaka", "efaka",
    "yifaka", "faka1314", "qq1314", "hao1314", "laogui", "laoguiqq",
    "naimao", "naimaoqq", "kulinnan", "kln166", "kln", "aiqq", "pandaqq",
    "xiongmao", "yedaoqq", "yewen", "xinhe001", "xinghe", "xinghe001",
    "baichuan", "yujuqq", "xdd6689", "piguqq", "kangsfqq", "maiqq",
    "maihaoqq", "qqhao", "qqfk", "qqhgm", "qqduo", "qqpf", "pifaqq",
    "pfqq", "5yqqqq", "wuyouqq", "kas666", "qq6666", "qq8", "qq520",
    "qq132", "qq178", "qq234", "qq268", "qq899", "lianghao", "1818lianghao",
    "16lh", "taoqqhao", "yunies", "qqzhw", "qqxhao", "jinku", "qd93",
    "elmqq", "zzqq", "nengliang", "fffzz", "youhui1998", "az886", "htqq",
    "hu6621", "kk987", "zhanghaofk", "xxn7788", "xihongqq", "maoqq",
    "vipworld8", "yxpf360", "qw123", "79yj", "23568", "qqhao6", "qq728",
    "manmanqq", "mmqq", "shaoshuai169", "gaozhang", "jiaofuqq", "jfqq",
    "youkaqq", "ykqq", "fakaqq", "haoqq", "buyqq", "sellqq", "qqshop",
    "qqmall", "qqstore", "qqcard", "meikaqq", "guokaQQ", "guokaqq",
    "gangkaqq", "saomaqq", "huanbang", "chuhhao", "chuhqq", "taiyangqq",
    "yueliangqq", "huangguanqq", "huiliuqq", "zhidengqq", "qidianqq",
    "haoshang", "ysqq", "yitouqq", "jipinqq", "jpqq", "lhqq", "qqlh",
    "qqhao88", "qqhao98", "qqhao168", "qqhao666", "qqhao888", "hao888",
    "qqwang", "wangqq", "feijiqq", "tgqq", "qqtg", "autoqq", "zdqq",
    "faka8", "faka66", "faka88", "faka168", "faka666", "faka888",
    "ukqq", "ukfaka", "ykfa", "youkafa", "优卡", "mimaqq", "mimaha",
    "dmd", "duomiduo", "shaoshuaifaka", "gaofaka", "jiaofuwang",
    "beimoqq", "kc088", "hnbc", "xiaodingdang", "xddqq", "titanqq",
    "ws pj", "wspj", "qqgongzuoshi", "gongzuoshiqq", "qqstudio",
    "qqhao7", "qqhao9", "7weiqq", "8weiqq", "5weiqq", "6weiqq",
    "qq5wei", "qq6wei", "qq7wei", "qq8wei", "jingpinqq", "boutiqueqq",
    "niuniuqq", "nnlh", "yiniulh", "yiniulianghao", "niulianghao",
    "kuaifaqq", "miaofaqq", "zizhuqq", "zzgmqq", "gmqq", "pifa8",
    "qqpifa8", "qqpf8", "hao8", "hao66", "hao99", "qq99", "qq66",
    "qq88", "qq168", "qq5200", "qq1314520", "loveqq", "qqlove",
    "kaixinqq", "kxqq", "xingyunqq", "xyqq", "caifuqq", "cfqq",
    "dafaqq", "dfqq", "hengfaqq", "hfqq", "shunfaqq", "sfqq",
    "anquanqq", "aqqq", "zhengguiqq", "zgqq", "yuanchuangqq",
    "shouhao", "shouhaqq", "erhaoqq", "ehqq", "sanhao", "sihao",
]
# clean brands with spaces
brands = [b.replace(" ", "") for b in brands if b and " " not in b or True]
brands = sorted(set(b for b in brands if re.match(r"^[a-zA-Z0-9]+$", b)))
tlds = [
    ".com", ".top", ".lol", ".cc", ".vip", ".cn", ".net", ".xyz", ".one",
    ".icu", ".shop", ".hk", ".pw", ".me", ".site", ".store", ".fun", ".live",
]
nums = [
    "", "1", "2", "3", "6", "8", "88", "66", "99", "168", "666", "888",
    "1314", "001", "080", "1688", "2024", "2025", "2026", "520", "007",
    "123", "321", "518", "918", "6666", "8888", "000", "111", "222",
]
print("blast brands", len(brands), "combos", len(brands) * len(nums) * len(tlds), flush=True)
for b in brands:
    for n in nums:
        for t in tlds:
            all_hosts.add("%s%s%s" % (b.lower(), n, t))

hosts = sorted(
    h
    for h in all_hosts
    if h
    and "." in h
    and 4 < len(h) < 58
    and not BAD_HOST.search(h)
    and not h.startswith(".")
    and not h.endswith(".")
)
(OUT / "hosts_all_jump.txt").write_text("\n".join(hosts) + "\n", encoding="utf-8")
print("PROBE hosts", len(hosts), flush=True)


def probe(h):
    best = None
    for url in ["https://%s/" % h, "http://%s/" % h, "https://%s/shop/" % h, "http://%s/shop/" % h]:
        html = curl_get(url, 12, use_proxy=True)
        if len(html) < 400:
            continue
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = re.sub(r"\s+", " ", htmlmod.unescape(m.group(1))).strip() if m else ""
        if DROP.search(title or ""):
            continue
        blob = "%s %s" % (title, html[:25000])
        if not QQ.search(blob):
            # still keep strong YKFAKA with faka signals
            if not (YK.search(html) and re.search(r"(发卡|自动发卡|卡密|下单)", blob)):
                continue
        yk = bool(YK.search(html))
        trades = len(re.findall(r"(?:Trade|Item)/\d+\.html", html, re.I))
        goods = len(re.findall(r"(购买|下单|库存|卡密)", html))
        stocks = [
            int(x)
            for x in re.findall(r">\s*(\d{2,6})\s*<", html)
            if int(x) < 500000
        ]
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
        if score < 15 and not yk:
            continue
        row = {
            "url": url if url.endswith("/shop/") or "/shop/" in url else ("https://%s/" % h),
            "host": h,
            "title": title[:160],
            "ykfaka": yk,
            "large_score": score,
            "trades": trades,
            "type": "大型卖Q" if score >= 50 else "卖Q发卡",
            "system": "YKFAKA易发卡" if yk else "发卡站",
        }
        if yk:
            row["url"] = "https://%s/" % h
        if not best or score > best["large_score"]:
            best = row
    return best


# Prefer probing: previous alive + shorter brand hosts first to get quick wins,
# but still cover all — shard into priority then rest
prio = []
rest = []
known_stems = set()
for p in [
    Path("/data/qq_hunt/round3/hosts_alive_merged.txt"),
    Path("/data/qq_hunt/round3/DELIVER_QQ_urls.txt"),
]:
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            for h in extract_hosts(line):
                known_stems.add(h)
                known_stems.add(h.split(".")[0])

for h in hosts:
    stem = h.split(".")[0]
    if h in known_stems or stem in known_stems or len(h) <= 18:
        prio.append(h)
    else:
        rest.append(h)

# Cap ultra-huge blast rest to keep runtime sane but still huge
# Probe ALL prio + up to 25000 rest
rest = rest[:25000]
queue = prio + rest
print("queue", len(queue), "prio", len(prio), "rest", len(rest), flush=True)
(OUT / "hosts_queue.txt").write_text("\n".join(queue) + "\n", encoding="utf-8")

hits = []
refresh_proxy()
with ThreadPoolExecutor(max_workers=20) as ex:
    futs = {ex.submit(probe, h): h for h in queue}
    for i, fut in enumerate(as_completed(futs), 1):
        try:
            r = fut.result()
        except Exception:
            r = None
        if r:
            hits.append(r)
            print(
                "HIT",
                r["type"],
                "score=%d" % r["large_score"],
                "YK" if r["ykfaka"] else "--",
                r["url"],
                r["title"][:40],
                flush=True,
            )
        if i % 200 == 0:
            # refresh proxy periodically
            refresh_proxy()
            print(
                "prog %d/%d hits=%d yk=%d"
                % (i, len(queue), len(hits), sum(1 for x in hits if x["ykfaka"])),
                flush=True,
            )
            # checkpoint
            (OUT / "hits_partial.json").write_text(
                json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8"
            )

by = {}
for r in hits:
    if r["host"] not in by or r["large_score"] > by[r["host"]]["large_score"]:
        by[r["host"]] = r

stem_map = defaultdict(list)
for r in by.values():
    stem_map[r["host"].split(".")[0]].append(r)
final = []
for items in stem_map.values():
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
            "hosts_total": len(hosts),
            "hosts_probed": len(queue),
            "all_hits": len(final),
            "large": len(large),
            "ykfaka": len(yk),
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print("DONE all=%d large=%d yk=%d" % (len(final), len(large), len(yk)), flush=True)
for r in yk:
    print("YK", r["url"], r["large_score"], r["title"][:50], flush=True)
for r in large[:80]:
    print("LG", r["url"], r["large_score"], r["title"][:40], flush=True)
