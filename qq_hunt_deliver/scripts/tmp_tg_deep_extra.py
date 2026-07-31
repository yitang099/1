#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extra deep TG scrape: more pages + wider BFS + extract hosts to merge later."""
import re, urllib.request, time, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path("/data/qq_hunt/allout")
OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
HOST_RE = re.compile(
    r"(?:https?://)?([a-z0-9][-a-z0-9.]{1,55}\.(?:top|lol|cc|vip|com|cn|one|icu|xyz|shop|net|pw|hk|me|site|store|online|club|fun|info|wang|live))",
    re.I,
)
BAD = re.compile(
    r"(t\.me|telegram|github|google|baidu|bing|microsoft|qq\.com$|zhihu|csdn|youtube|facebook|twitter|wikipedia|cloudflare)",
    re.I,
)


def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def scrape(uname, pages=40):
    uname = uname.lstrip("@")
    hosts, users, texts = set(), set(), []
    before = None
    for _ in range(pages):
        url = "https://t.me/s/%s" % uname
        if before:
            url += "?before=%d" % before
        try:
            html = fetch(url, 12)
        except Exception:
            break
        ids = [int(x) for x in re.findall(r'data-post="%s/(\d+)"' % re.escape(uname), html)]
        if not ids:
            break
        before = min(ids)
        for m in HOST_RE.findall(html):
            h = m.lower().removeprefix("www.")
            if not BAD.search(h):
                hosts.add(h)
        users |= {x.lower() for x in re.findall(r"(?:t\.me/(?:s/)?|@)([A-Za-z0-9_]{4,32})", html)}
        # message text snippets with QQ signals
        for t in re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', html, re.S):
            if re.search(r"qq|国卡|美卡|靓号|发卡|号商|批发", t, re.I):
                texts.append(re.sub(r"<[^>]+>", " ", t)[:300])
                for m in HOST_RE.findall(t):
                    h = m.lower().removeprefix("www.")
                    if not BAD.search(h):
                        hosts.add(h)
        time.sleep(0.03)
    return hosts, users, texts


seeds = set()
for p in [
    Path("/data/qq_hunt/tg_crawl/QQ_TG_CHANNELS.txt"),
    Path("/data/qq_hunt/tg_chans_from_jump.txt"),
    Path("/data/qq_hunt/round3/飞机频道_卖Q.txt"),
    Path("/data/qq_hunt/allout/tg_extra_seeds.txt"),
]:
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.search(r"t\.me/([A-Za-z0-9_]+)", line)
            if m:
                seeds.add(m.group(1))
            elif line.strip().startswith("@"):
                seeds.add(line.strip()[1:])

extra = """
mima1314_QQ Mima_1314 xmqqtop xmqqq aiqq bwqq666 aagao cccc88088 shaoshuai169
yedaoqq10 xinhe080 xiaodingdang122 HNBC6866 kln166 HM08088 qq321 naimao188
laoguiQQ888 titanqqjf ttqq888 qqhao8888 qqhao98 beimoqq888 yewen887 WSPJ981
kc088 qqhgm_com QQgongzuoshi dmdqq dmddqq jiaofu1314 gaozzb shaoshuaifaka
hemaqq666 pandaqq8 xiongmaoqq youkaqq ykfakaqq qqpf888 qqhao666 maihaoqq
qqhgm qqhgmcom xinhe0010 xinghe0010 kulinnan166 laogui666 naimao666
manmanqq ttqqtop tjqqtop bwqqtop xmqqwvip mima1314com gao1314com
qq8one vipworld8 jinkuqq elmqq az886 htqq fffzz nengliang qw123
maiQQhao qqwholesale qqhao_pifa guokaqq meikaqq saomaqq
""".split()
seeds |= set(extra)
seeds = sorted(s for s in seeds if re.match(r"^[A-Za-z0-9_]{4,64}$", s) and not s.lower().endswith("bot"))
print("seeds", len(seeds), flush=True)

all_hosts, all_users = set(), set()
samples = []
with ThreadPoolExecutor(max_workers=14) as ex:
    futs = {ex.submit(scrape, u, 40): u for u in seeds}
    done = 0
    for fut in as_completed(futs):
        done += 1
        h, u, t = fut.result()
        all_hosts |= h
        all_users |= u
        samples.extend(t[:2])
        if done % 50 == 0:
            print("tg %d/%d hosts=%d users=%d" % (done, len(seeds), len(all_hosts), len(all_users)), flush=True)

# wide BFS
pat = re.compile(
    r"qq|hao|faka|mei|guo|liang|xinhe|yedao|mima|gao|xmqq|bwqq|tjqq|ttqq|dmd|hema|naimao|laogui|kln|panda|jiaofu|shaoshuai|youka|ykfa|pf|pifa|maiqq|haoqq|chuh|saoma|guoka|meika",
    re.I,
)
seen = {s.lower() for s in seeds}
bfs = [u for u in all_users if u not in seen and pat.search(u)]
bfs = sorted(set(bfs))[:400]
print("BFS", len(bfs), flush=True)
with ThreadPoolExecutor(max_workers=12) as ex:
    futs = [ex.submit(scrape, u, 25) for u in bfs]
    for i, fut in enumerate(as_completed(futs), 1):
        h, u, t = fut.result()
        all_hosts |= h
        all_users |= u
        if i % 40 == 0:
            print("bfs %d/%d hosts=%d" % (i, len(bfs), len(all_hosts)), flush=True)

# second hop tiny
seen2 = seen | set(bfs)
bfs2 = [u for u in all_users if u not in seen2 and pat.search(u)]
bfs2 = sorted(set(bfs2))[:150]
print("BFS2", len(bfs2), flush=True)
with ThreadPoolExecutor(max_workers=10) as ex:
    for fut in as_completed([ex.submit(scrape, u, 15) for u in bfs2]):
        h, u, t = fut.result()
        all_hosts |= h

hosts = sorted(h for h in all_hosts if "." in h and len(h) < 58 and not BAD.search(h))
(OUT / "tg_deep_hosts.txt").write_text("\n".join(hosts) + "\n", encoding="utf-8")
(OUT / "tg_deep_users.txt").write_text("\n".join(sorted(all_users)) + "\n", encoding="utf-8")
(OUT / "tg_deep_stats.json").write_text(
    json.dumps({"hosts": len(hosts), "users": len(all_users), "seeds": len(seeds), "bfs": len(bfs), "bfs2": len(bfs2)}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("DONE hosts=%d users=%d" % (len(hosts), len(all_users)), flush=True)
for h in hosts[:100]:
    print(h, flush=True)
