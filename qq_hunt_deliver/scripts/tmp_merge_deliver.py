#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge HK allout + round3 + new hits; scrub FPs; deliver clean lists."""
import json, re, html as htmlmod, subprocess, time
from pathlib import Path
from collections import defaultdict

OUT = Path("/data/qq_hunt/allout")
R3 = Path("/data/qq_hunt/round3")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
YK = re.compile(
    r'(content=["\']YKFAKA["\']|YKFAKA|/User_Login\.html|/Gd_Query\.html|'
    r'/public/static/AmazeUI/|Welcome©\s*20\d{2}\s*YKFAKA)',
    re.I,
)
QQ_STRONG = re.compile(
    r"(qq号|qq号码|批发qq|qq批发|卖qq|买qq|美卡|国卡|港卡|靓号|扫码号|"
    r"处号|太阳号|月亮号|皇冠号|回流号|直登qq|私人qq|企业qq|星星号|单太|双太|三太|"
    r"河马|老鬼qq|奶猫|库里南|熊猫qq|教父|高部长|少帅|哆咪哆|号商|qq账号|qq小号|"
    r"绑卡qq|美国卡|泰国卡|pc扫码|注册卡位|qq发卡|发号网)",
    re.I,
)
FP = re.compile(
    r"(在线播放|看片|中文字幕|影视大全|成人|色情|熊猫视频|彩尊|立赢|迪信通|"
    r"域名出售|parked|个性导航|密钥猫|机场|传奇|私服|chatgpt|回收估价|代刷|"
    r"日本免费|韩国精品)",
    re.I,
)


def get_proxy():
    out = subprocess.check_output(
        ["curl", "-sS", "--max-time", "12", "https://share.proxy.qg.net/get?key=C413ED6D&num=1"],
        text=True,
    )
    d = json.loads(out)
    s = (d.get("data") or [{}])[0].get("server")
    if not s:
        raise RuntimeError(out[:200])
    return "http://C413ED6D:344F550A6F8B@%s" % s


def curl(url, px, timeout=13):
    try:
        return subprocess.check_output(
            ["curl", "-sS", "-L", "--max-time", str(timeout), "-x", px, "-A", UA, url],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", "ignore")
    except Exception:
        return ""


def probe(host):
    host = host.lower().removeprefix("www.")
    try:
        px = get_proxy()
    except Exception:
        return None
    best = None
    for url in ["https://%s/" % host, "https://%s/shop/" % host, "http://%s/" % host, "http://%s/shop/" % host]:
        html = curl(url, px)
        if len(html) < 400:
            continue
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = re.sub(r"\s+", " ", htmlmod.unescape(m.group(1))).strip() if m else ""
        blob = "%s %s" % (title, html[:25000])
        if FP.search(title) or FP.search(html[:3000]):
            continue
        yk = bool(YK.search(html))
        if not QQ_STRONG.search(blob):
            if not (yk and re.search(r"(发卡|卡密|下单|国卡|美卡)", blob)):
                continue
        trades = len(re.findall(r"(?:Trade|Item)/\d+\.html", html, re.I))
        goods = len(re.findall(r"(购买|下单|库存|卡密)", html))
        stocks = [int(x) for x in re.findall(r">\s*(\d{2,6})\s*<", html) if int(x) < 500000]
        score = min(trades, 120) * 2 + min(goods, 100) + min(sum(stocks[:40]) // 15, 120)
        if yk:
            score += 30
        if len(html) > 25000:
            score += 25
        elif len(html) > 12000:
            score += 12
        if re.search(r"(源头|一手|机房|金牌|五年|六年|全网0纠纷|批发|专注QQ|号商)", blob):
            score += 35
        row = {
            "url": ("https://%s/" % host) if yk else url,
            "host": host,
            "title": title[:160],
            "ykfaka": yk,
            "large_score": score,
            "type": "大型卖Q" if score >= 50 else "卖Q发卡",
            "system": "YKFAKA易发卡" if yk else "发卡站",
        }
        if not best or score > best["large_score"]:
            best = row
    return best


# collect candidate hosts from all sources
hosts = set()
for p in [
    OUT / "大型卖Q发卡站.txt",
    OUT / "全部卖Q发卡站.txt",
    OUT / "YKFAKA易发卡.txt",
    OUT / "tg_qqish_hosts.txt",
    OUT / "tg_qqish_hits.json",
    OUT / "tg_reprobe_hits.json",
    OUT / "fast_hits_partial.json",
    OUT / "all.json",
    R3 / "大型卖Q发卡站.txt",
    R3 / "YKFAKA易发卡.txt",
    R3 / "卖Q站点_类型链接.txt",
    R3 / "DELIVER_QQ_urls.txt",
    R3 / "urls_large.txt",
]:
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    if p.suffix == ".json":
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for row in data:
                    if isinstance(row, dict) and row.get("host"):
                        hosts.add(row["host"].lower().removeprefix("www."))
                    elif isinstance(row, dict) and row.get("url"):
                        m = re.search(r"https?://([^/\s]+)", row["url"])
                        if m:
                            hosts.add(m.group(1).lower().removeprefix("www."))
        except Exception:
            pass
    for m in re.findall(r"https?://([^/\s]+)", text):
        hosts.add(m.lower().removeprefix("www."))
    for line in text.splitlines():
        line = line.strip().lower()
        if re.match(r"^[a-z0-9.-]+\.[a-z]{2,24}$", line):
            hosts.add(line.removeprefix("www."))

# must-include known + newly found
extra = """
dmdqq.cc xmqqw.vip bwqq.top tjqq.top ttqq.top mima1314.com gao1314.com wwwb2c.com
16lh.com efaka.shop qq.728.hk qq178.com 1818lianghao.com m.qq268.com qqhgm.com
79yj.com qd93.com qqx2.cn vipworld8.top yunies.com qqxhao.com qqqxiaohao.com
qqzhw.com 06xp.com 132226.com qq520.cn qq857.cc qqlhw.com 66689.cn 88320.cn
baichuan.lol qqduo.com hm0880.top kln166.lol xinhe001.lol jinku.lol elmqq.top
nengliang.lol piguqq.top qq6666.top qq8.one az886.top fffzz.top htqq.lol
qw123.top maihaoqq.com 23568.cn qq234.cn qq899.com qqhao6.cn taoqqhao.com
youhui1998.top kangsfqq.top maiqq88.top maoqq.lol naimaoqq.top yedaoqq.top
xihongqq.top zhanghaofk88.top zzqq.lol qq1.lol ka1.one qq2025.vip
""".split()
hosts |= {h.lower() for h in extra}
hosts = sorted(h for h in hosts if "." in h and len(h) < 58)
print("reprobe hosts", len(hosts), flush=True)

hits = []
for i, h in enumerate(hosts, 1):
    r = probe(h)
    if r:
        hits.append(r)
        print("OK", r["type"], r["large_score"], "YK" if r["ykfaka"] else "--", r["url"], r["title"][:50], flush=True)
    else:
        print("NO", h, flush=True)
    if i % 20 == 0:
        print("prog", i, "/", len(hosts), "hits", len(hits), flush=True)

# stem dedupe prefer yk + score
stem = defaultdict(list)
for r in hits:
    stem[r["host"].split(".")[0]].append(r)
final = []
for items in stem.values():
    # also drop www duplicate of same registrable roughly
    items = sorted(items, key=lambda x: (-x["large_score"], 0 if x["ykfaka"] else 1, len(x["host"])))
    final.append(items[0])

# extra dedupe: same title SEO clones keep highest score one
by_title = defaultdict(list)
for r in final:
    key = re.sub(r"\s+", "", r["title"])[:40] if r["title"] else r["host"]
    by_title[key].append(r)
final2 = []
for items in by_title.values():
    items = sorted(items, key=lambda x: (-x["large_score"], 0 if x["ykfaka"] else 1))
    # keep all if titles generic "自动发卡"
    if items[0]["title"] in ("自动发卡", "首页 | FK发卡 - 低价自动发卡平台", ""):
        # keep by host uniqueness already
        final2.extend(items)
    else:
        final2.append(items[0])

# prefer host-level uniqueness
by_host = {}
for r in final2:
    by_host[r["host"]] = r
# merge mima www
if "www.mima1314.com" in by_host and "mima1314.com" in by_host:
    by_host.pop("www.mima1314.com", None)

final = sorted(by_host.values(), key=lambda x: (-x["large_score"], x["host"]))
large = [r for r in final if r["large_score"] >= 50]
yk = [r for r in final if r["ykfaka"]]
all_qq = final

# write deliverables to allout AND round3
for dest in [OUT, R3]:
    (dest / "大型卖Q发卡站.txt").write_text(
        "\n".join("%s\t%s\tscore=%d\t%s\t%s" % (r["type"], r["url"], r["large_score"], r["system"], r["title"]) for r in large) + "\n",
        encoding="utf-8",
    )
    (dest / "全部卖Q发卡站.txt").write_text(
        "\n".join("%s\t%s\tscore=%d\t%s\t%s" % (r["type"], r["url"], r["large_score"], r["system"], r["title"]) for r in all_qq) + "\n",
        encoding="utf-8",
    )
    (dest / "YKFAKA易发卡.txt").write_text(
        "\n".join("%s\tscore=%d\t%s\t%s" % (r["url"], r["large_score"], r["type"], r["title"]) for r in yk) + "\n",
        encoding="utf-8",
    )
    (dest / "urls_large.txt").write_text("\n".join(r["url"] for r in large) + "\n", encoding="utf-8")
    (dest / "urls_all_qq.txt").write_text("\n".join(r["url"] for r in all_qq) + "\n", encoding="utf-8")
    (dest / "merged_all.json").write_text(json.dumps(all_qq, ensure_ascii=False, indent=2), encoding="utf-8")
    (dest / "merged_stats.txt").write_text(
        json.dumps({"all": len(all_qq), "large": len(large), "ykfaka": len(yk), "probed": len(hosts)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

# note
note = """全力扩源说明
================
探测范围：
- HK：523+ TG频道深挖 + BFS + Bing/DDG + 品牌×TLD爆破 → 探测 21875 主机
- HK TG深挖：563种子 + 400 BFS → 412域名 / 数千用户
- 跳板：青果代理多引擎搜索70词 + 海量爆破队列 + TG线索复探

过滤：
- 仅保留强卖Q信号（QQ号/国卡/美卡/靓号/号商/YKFAKA等）
- 剔除影视色情、彩票导航、域名停放等误报
- 同品牌多TLD/www 去重，保留最高分

局限（实话）：
- 大量号商只挂飞机私链/短期域名，搜索引擎几乎不收录
- YKFAKA/易发卡正版店公开可扫到的卖Q站目前仍是个位数级；更多在未索引私域
- 公共网页能稳定打开的大型卖Q发卡站，本轮合并后见统计数字
"""
(R3 / "大型发卡_说明.txt").write_text(note, encoding="utf-8")
(OUT / "大型发卡_说明.txt").write_text(note, encoding="utf-8")

# tar
subprocess.call(
    "cd /data/qq_hunt/round3 && tar czf 大型卖Q发卡站.tar.gz 大型卖Q发卡站.txt 全部卖Q发卡站.txt YKFAKA易发卡.txt urls_large.txt urls_all_qq.txt merged_stats.txt 大型发卡_说明.txt 飞机频道_卖Q.txt 卖Q站点_类型链接.txt 2>/dev/null || true",
    shell=True,
)

print("FINAL all=%d large=%d yk=%d" % (len(all_qq), len(large), len(yk)), flush=True)
print("---YK---", flush=True)
for r in yk:
    print(r["url"], r["large_score"], r["title"][:50], flush=True)
print("---LARGE---", flush=True)
for r in large:
    print(r["url"], r["large_score"], r["system"], r["title"][:45], flush=True)
