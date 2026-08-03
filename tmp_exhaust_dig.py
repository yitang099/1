#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXHAUSTIVE dig — leave nothing behind.
1) Re-mine all public 供需 seeds deeply
2) Classify EVERY unknown username
3) Deep-scrape every NEW previewable channel
4) Bio-mine every contact not yet mined
5) Collect ALL hosts/shops for probing
"""
import re, urllib.request, time, json, html as htmlmod
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import Counter, defaultdict
from urllib.parse import unquote

OUT = Path("/workspace/tmp_exhaust")
OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"

HOST_RE = re.compile(
    r"(?:https?://)?((?:[a-z0-9-]+\.)+(?:top|lol|cc|vip|com|cn|one|icu|xyz|shop|net|pw|hk|me|site|store|online|club|fun|info|io|app|co|tv|pro|live|biz|link|work|cloud))",
    re.I,
)
URL_RE = re.compile(r"https?://[^\s\"'<>\\]+", re.I)
USER_RE = re.compile(r"(?:t\.me/(?:s/)?|@)([A-Za-z][A-Za-z0-9_]{3,63})")
BAD_HOST = re.compile(
    r"(^|\.)(t\.me|telegram\.|telesco\.|github\.|google\.|baidu\.|bing\.|"
    r"microsoft\.|qq\.com$|w3\.org|cloudflare|aliyuncs|sina\.|youtube|"
    r"iframecontel|org\.telegram|cdn4\.|cdn5\.|amazonaws)",
    re.I,
)
SKIP_USER = re.compile(
    r"^(https?|http|www|com|top|lol|vip|shop|net|xyz|icu|one|cc|cn|me|fun|"
    r"site|store|online|club|html|php|index|user|admin|test|null|true|false|"
    r"telegram|premium|joinchat|addstickers|share|proxy)$|bot$",
    re.I,
)
QQ_KW = re.compile(
    r"(QQ号|qq号|卖QQ|卖qq|企鹅号|扣扣|QQ批发|qq批发|出QQ|QQ成品|发卡|/shop|"
    r"号商|YKFAKA|易发卡|QQ号码|qq号码|出售QQ|批发QQ|QQ库存|月卡|三网)",
    re.I,
)

# Seeds: every public channel we know that can yield QQ shop ads
SEEDS = [
    # core QQ 供需
    ("kehu", "kehu", 1000, False),
    ("jiu224", "jiu224", 500, False),
    ("kfcgx", "kfcgx", 600, False),
    # 出海/海华 (post username may differ)
    ("chgx", "chgx", 800, True),
    ("hhgx", "hhgx", 600, True),
    ("haihuagongxu", "hhgx", 200, True),
    ("gqdh", "gqdh", 80, True),
    ("hxgx", "hxgx", 400, True),  # 汇鑫供需
    ("ajindb", "ajindb", 80, False),
    ("xiaoqiaochuhai", "xiaoqiaochuhai", 30, False),
]


def fetch(url, timeout=14):
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def clean_host(h):
    h = unquote(h).lower().removeprefix("www.").strip(".")
    h = re.sub(r"^[^a-z0-9]+", "", h)
    m = re.search(r"([a-z0-9][a-z0-9.-]+\.[a-z]{2,24})$", h)
    if m:
        h = m.group(1)
    if not re.match(r"^[a-z0-9][a-z0-9.-]+\.[a-z]{2,24}$", h):
        return None
    if BAD_HOST.search(h) or not (5 <= len(h) <= 58):
        return None
    if h.count(".") > 4:
        return None
    return h


def clean_user(u):
    u = u.strip().lstrip("@")
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]{3,63}$", u):
        return None
    if SKIP_USER.search(u):
        return None
    return u.lower()


def scrape_seed(url_name, post_name, pages=400, qq_only=False):
    hosts, shops = set(), set()
    contacts, channels = Counter(), Counter()
    qq_ads = 0
    before = None
    for page in range(pages):
        url = "https://t.me/s/%s" % url_name
        if before:
            url += "?before=%d" % before
        try:
            html = fetch(url, 14)
        except Exception as e:
            print("fail", url_name, page, e, flush=True)
            time.sleep(0.5)
            continue
        ids = [
            int(x)
            for x in re.findall(
                r'data-post="%s/(\d+)"' % re.escape(post_name), html
            )
        ]
        if not ids:
            # try url_name as post name
            ids = [
                int(x)
                for x in re.findall(
                    r'data-post="%s/(\d+)"' % re.escape(url_name), html
                )
            ]
        if not ids:
            print("END", url_name, "page", page, flush=True)
            break
        before = min(ids)
        for t in re.findall(
            r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', html, re.S
        ):
            plain = htmlmod.unescape(re.sub(r"<[^>]+>", " ", t))
            plain = re.sub(r"\s+", " ", plain).strip()
            is_qq = bool(QQ_KW.search(plain))
            if qq_only and not is_qq:
                if not re.search(r"/shop|\.(lol|top|vip|cc)/", plain, re.I):
                    continue
            if is_qq:
                qq_ads += 1

            for m in re.finditer(
                r"(?:联系人|客服|售后|飞机|TG|通知频道|上货(?:通知)?(?:频道|群)?|"
                r"群组|频道|主页|发卡网|网站|对接|老板)"
                r"\s*[:：]?\s*(?:https?://t\.me/(?:s/)?|@)?([A-Za-z][A-Za-z0-9_]{3,63})",
                plain,
                re.I,
            ):
                u = clean_user(m.group(1))
                if u:
                    if re.search(r"通知|上货|频道|群组", m.group(0), re.I):
                        channels[u] += 3
                    else:
                        contacts[u] += 2

            for u in USER_RE.findall(plain):
                cu = clean_user(u)
                if cu:
                    contacts[cu] += 1

            for L in URL_RE.findall(plain):
                L = unquote(L.rstrip(").,;'\"}>"))
                if BAD_HOST.search(L):
                    continue
                if re.search(r"/shop|发卡|\.(lol|top|vip|cc|one)/", L, re.I):
                    shops.add(L.split("#")[0])
                m = HOST_RE.search(L)
                if m:
                    h = clean_host(m.group(1))
                    if h:
                        hosts.add(h)

            for m in re.findall(
                r"((?:[a-z0-9-]+\.)+(?:top|lol|cc|vip|com|cn|one|icu|xyz|shop|net)/(?:shop)?/?)",
                plain,
                re.I,
            ):
                h = clean_host(m.split("/")[0])
                if h:
                    hosts.add(h)
                    if "/shop" in m.lower():
                        shops.add("https://" + m.lstrip("/"))

        if page % 50 == 0:
            print(
                url_name,
                "p",
                page,
                "qq",
                qq_ads,
                "c",
                len(contacts),
                "h",
                len(hosts),
                "s",
                len(shops),
                flush=True,
            )
        time.sleep(0.03)

    return {
        "url_name": url_name,
        "qq_ads": qq_ads,
        "contacts": contacts,
        "channels": channels,
        "hosts": hosts,
        "shops": shops,
    }


def classify(uname):
    try:
        html = fetch("https://t.me/s/%s" % uname, 10)
    except Exception:
        try:
            html = fetch("https://t.me/%s" % uname, 10)
            # profile only
        except Exception:
            return {
                "user": uname,
                "kind": "error",
                "previewable": False,
                "title": "",
                "hosts": [],
                "extra": "",
            }
    title_m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""
    posts = len(re.findall(r"data-post=", html))
    extra_m = re.search(r'class="tgme_page_extra"[^>]*>(.*?)</div>', html, re.S)
    extra = (
        re.sub(r"<[^>]+>", " ", extra_m.group(1)).strip() if extra_m else ""
    )
    desc_m = re.search(r'og:description" content="([^"]*)"', html)
    desc = htmlmod.unescape(desc_m.group(1)) if desc_m else ""
    hosts = []
    for h in HOST_RE.findall(desc + " " + title):
        ch = clean_host(h)
        if ch and ch not in hosts:
            hosts.append(ch)
    for L in URL_RE.findall(desc):
        m = HOST_RE.search(L)
        if m:
            ch = clean_host(m.group(1))
            if ch and ch not in hosts:
                hosts.append(ch)

    if posts > 0:
        kind = "channel"
        previewable = True
    elif "subscriber" in extra.lower() or "订阅" in extra:
        kind = "empty_channel"
        previewable = False
    elif "member" in extra.lower() or "成员" in extra:
        kind = "group"
        previewable = False
    elif extra.startswith("@") or "Contact @" in title:
        kind = "contact"
        previewable = False
    elif "If you have" in html and "subscribers" not in extra.lower():
        kind = "contact"
        previewable = False
    else:
        kind = "unknown"
        previewable = False

    return {
        "user": uname,
        "kind": kind,
        "previewable": previewable,
        "title": title[:120],
        "hosts": hosts,
        "extra": extra[:80],
        "desc": desc[:240],
        "qqish": bool(QQ_KW.search(desc + title) or re.search(r"qq|企鹅|扣扣|发卡", desc + title, re.I)),
    }


def deep_scrape(uname, pages=200):
    hosts, shops, users = set(), set(), set()
    before = None
    title = ""
    for page in range(pages):
        url = "https://t.me/s/%s" % uname
        if before:
            url += "?before=%d" % before
        try:
            html = fetch(url, 14)
        except Exception:
            break
        if page == 0:
            m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
            title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        ids = [
            int(x)
            for x in re.findall(r'data-post="%s/(\d+)"' % re.escape(uname), html)
        ]
        if not ids:
            break
        before = min(ids)
        for L in URL_RE.findall(html):
            L = unquote(L.rstrip(").,;'\"}>"))
            if BAD_HOST.search(L):
                continue
            if re.search(r"/shop|发卡", L, re.I):
                shops.add(L.split("#")[0])
            m = HOST_RE.search(L)
            if m:
                h = clean_host(m.group(1))
                if h:
                    hosts.add(h)
        for t in re.findall(
            r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', html, re.S
        ):
            plain = htmlmod.unescape(re.sub(r"<[^>]+>", " ", t))
            for m in re.findall(
                r"((?:[a-z0-9-]+\.)+(?:top|lol|cc|vip|com|cn|one|icu|xyz|shop|net)/(?:shop)?/?)",
                plain,
                re.I,
            ):
                h = clean_host(m.split("/")[0])
                if h:
                    hosts.add(h)
                    if "/shop" in m.lower():
                        shops.add("https://" + m.lstrip("/"))
            for u in USER_RE.findall(plain):
                cu = clean_user(u)
                if cu:
                    users.add(cu)
        time.sleep(0.025)
    return {
        "channel": uname,
        "title": title,
        "hosts": sorted(hosts),
        "shops": sorted(shops),
        "users": sorted(users),
    }


def load_all_known_users():
    users = Counter()
    # max adv ranked
    p = Path("/workspace/tmp_max_adv/all_advertisers_ranked.txt")
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.strip().split("\t")
            if parts:
                u = clean_user(parts[0])
                if u:
                    users[u] += int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    # bio already mined
    bio_p = Path("/workspace/tmp_bio_mine/bio_all.json")
    bioed = set()
    if bio_p.exists():
        for row in json.loads(bio_p.read_text(encoding="utf-8")):
            u = row.get("user")
            if u:
                bioed.add(u)
                users.setdefault(u, 1)
    # leftover / expand / chuhai
    for fp in [
        Path("/workspace/tmp_leftover/more_contacts.txt"),
        Path("/workspace/tmp_expand2/new_contact_cands.txt"),
        Path("/workspace/tmp_chuhai_dig/advertisers_ranked.txt"),
        Path("/workspace/tmp_max_adv/previewable_channels.txt"),
    ]:
        if not fp.exists():
            continue
        for line in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
            u = clean_user(line.split("\t")[0].strip())
            if u:
                users.setdefault(u, 1)
    # person sites
    for fp in [
        Path("/workspace/tmp_bio_mine/person_sites.txt"),
        Path("/workspace/qq_hunt_deliver/orders_rank/person_sites_qq.txt"),
    ]:
        if not fp.exists():
            continue
        for line in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
            u = clean_user(line.split("\t")[0].strip())
            if u:
                users.setdefault(u, 1)
    return users, bioed


def load_old_hosts():
    old = set()
    for p in [
        Path("/workspace/tmp_max_adv/hosts_all.txt"),
        Path("/workspace/tmp_bio_mine/hosts_all_bio.txt"),
        Path("/workspace/tmp_leftover/hosts_still_to_probe.txt"),
        Path("/workspace/tmp_leftover/hosts_gongxu_all.txt"),
    ]:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            h = clean_host(line.split("\t")[0].strip())
            if h:
                old.add(h)
    op = Path("/workspace/qq_hunt_deliver/orders_rank/orders_ranked.json")
    if op.exists():
        for row in json.loads(op.read_text(encoding="utf-8")):
            h = clean_host(row.get("host", ""))
            if h:
                old.add(h)
    return old


def load_already_previewable():
    already = set()
    for p in [
        Path("/workspace/tmp_max_adv/previewable_channels.txt"),
        Path("/workspace/tmp_bio_mine/new_previewable.json"),
        Path("/workspace/tmp_chuhai_dig/new_previewable.json"),
    ]:
        if not p.exists():
            continue
        if p.suffix == ".json":
            for row in json.loads(p.read_text(encoding="utf-8")):
                u = clean_user(row.get("user", ""))
                if u:
                    already.add(u)
        else:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                u = clean_user(line.split("\t")[0])
                if u:
                    already.add(u)
    return already


def main():
    print("=== Phase1: exhaust scrape seeds ===", flush=True)
    all_hosts, all_shops = set(), set()
    score = Counter()
    seed_stats = {}
    for url_name, post_name, pages, qq_only in SEEDS:
        print("SEED", url_name, post_name, pages, flush=True)
        r = scrape_seed(url_name, post_name, pages=pages, qq_only=qq_only)
        seed_stats[url_name] = {
            "qq_ads": r["qq_ads"],
            "contacts": len(r["contacts"]),
            "channels": len(r["channels"]),
            "hosts": len(r["hosts"]),
            "shops": len(r["shops"]),
        }
        all_hosts |= r["hosts"]
        all_shops |= r["shops"]
        score.update(r["contacts"])
        for u, n in r["channels"].items():
            score[u] += n * 2
        (OUT / ("seed_%s.json" % url_name)).write_text(
            json.dumps(
                {
                    "qq_ads": r["qq_ads"],
                    "hosts": sorted(r["hosts"]),
                    "shops": sorted(r["shops"]),
                    "top_contacts": r["contacts"].most_common(500),
                    "top_channels": r["channels"].most_common(200),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print("seed_done", seed_stats[url_name], flush=True)

    known_users, bioed = load_all_known_users()
    for u, n in score.items():
        known_users[u] += n

    already_prev = load_already_previewable()
    print(
        "known_users",
        len(known_users),
        "bioed",
        len(bioed),
        "already_prev",
        len(already_prev),
        flush=True,
    )

    # Phase2: classify users never classified / unknown heavy set
    # Prioritize: high score, not already previewable, not bioed with hosts
    to_classify = []
    for u, n in known_users.most_common():
        if u in already_prev:
            continue
        to_classify.append(u)
    # also include everyone from score even if low
    print("=== Phase2: classify", len(to_classify), "users ===", flush=True)
    # Cap at 4500 for thoroughness but keep highest priority first
    to_classify = to_classify[:4500]

    classified = []
    new_prev = []
    bio_hosts = Counter()
    person_hosts = defaultdict(list)
    done = 0
    with ThreadPoolExecutor(max_workers=28) as ex:
        futs = {ex.submit(classify, u): u for u in to_classify}
        for fut in as_completed(futs):
            done += 1
            row = fut.result()
            classified.append(row)
            for h in row.get("hosts") or []:
                bio_hosts[h] += 1
                all_hosts.add(h)
                person_hosts[row["user"]].append(h)
            if row.get("previewable"):
                new_prev.append(row)
                print("NEW_PREV", row["user"], row.get("title", "")[:70], flush=True)
            if done % 300 == 0:
                print(
                    "classify",
                    done,
                    "/",
                    len(to_classify),
                    "new_prev",
                    len(new_prev),
                    "bio_hosts",
                    len(bio_hosts),
                    flush=True,
                )

    (OUT / "classified.json").write_text(
        json.dumps(classified, ensure_ascii=False), encoding="utf-8"
    )
    kinds = Counter(r["kind"] for r in classified)
    (OUT / "classify_kinds.json").write_text(
        json.dumps({"kinds": dict(kinds), "new_previewable": len(new_prev)}, indent=2),
        encoding="utf-8",
    )
    (OUT / "new_previewable.json").write_text(
        json.dumps(new_prev, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Phase3: deep scrape ALL new previewable
    print("=== Phase3: deep scrape", len(new_prev), "new channels ===", flush=True)
    deep_rows = []
    nested_users = set()
    for row in new_prev:
        r = deep_scrape(row["user"], pages=200)
        deep_rows.append(r)
        all_hosts.update(r["hosts"])
        all_shops.update(r["shops"])
        nested_users.update(r["users"])
        print(
            "deep",
            r["channel"],
            "h",
            len(r["hosts"]),
            "s",
            len(r["shops"]),
            "u",
            len(r["users"]),
            flush=True,
        )
    (OUT / "deep_new.json").write_text(
        json.dumps(deep_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Phase4: classify + bio nested users not yet seen
    nested_new = [u for u in nested_users if u not in already_prev and u not in {r["user"] for r in classified}]
    print("=== Phase4: nested users", len(nested_new), "===", flush=True)
    hop_prev = []
    with ThreadPoolExecutor(max_workers=24) as ex:
        futs = {ex.submit(classify, u): u for u in nested_new[:2000]}
        for fut in as_completed(futs):
            row = fut.result()
            classified.append(row)
            for h in row.get("hosts") or []:
                all_hosts.add(h)
                bio_hosts[h] += 1
                person_hosts[row["user"]].append(h)
            if row.get("previewable"):
                hop_prev.append(row)
                print("HOP_PREV", row["user"], row.get("title", "")[:70], flush=True)

    for row in hop_prev:
        r = deep_scrape(row["user"], pages=150)
        deep_rows.append(r)
        all_hosts.update(r["hosts"])
        all_shops.update(r["shops"])
        print("hop_deep", r["channel"], len(r["hosts"]), flush=True)

    # Phase5: also bio-mine high-score contacts that have no hosts yet (profile page)
    # classify() already gets bio hosts from profile. Collect QQ-ish with hosts.
    person_qq = [
        r
        for r in classified
        if (r.get("hosts") or r.get("qqish"))
    ]
    (OUT / "person_sites.json").write_text(
        json.dumps(person_qq, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    old_hosts = load_old_hosts()
    ranked_hosts = set()
    op = Path("/workspace/qq_hunt_deliver/orders_rank/orders_ranked.json")
    if op.exists():
        for row in json.loads(op.read_text(encoding="utf-8")):
            ranked_hosts.add(row["host"].lower())

    # leftover probe list
    leftover = set()
    lp = Path("/workspace/tmp_leftover/hosts_still_to_probe.txt")
    if lp.exists():
        for line in lp.read_text().splitlines():
            h = clean_host(line.strip())
            if h:
                leftover.add(h)

    all_hosts |= leftover
    probe_hosts = sorted(h for h in all_hosts if h not in ranked_hosts)
    # prioritize QQ-ish looking
    def prio(h):
        score = 0
        if re.search(r"qq|faka|hao|kami|fk|card|lh|liang", h, re.I):
            score += 10
        if h.endswith((".lol", ".top", ".vip", ".cc", ".one", ".icu")):
            score += 3
        if h not in old_hosts:
            score += 2
        return -score

    probe_hosts.sort(key=prio)
    (OUT / "hosts_all.txt").write_text("\n".join(sorted(all_hosts)), encoding="utf-8")
    (OUT / "hosts_to_probe.txt").write_text("\n".join(probe_hosts), encoding="utf-8")
    (OUT / "shops_all.txt").write_text("\n".join(sorted(all_shops)), encoding="utf-8")

    # person map txt
    lines = []
    for r in sorted(person_qq, key=lambda x: (-len(x.get("hosts") or []), -(x.get("qqish") or 0))):
        if not r.get("hosts"):
            continue
        lines.append(
            "%s\t%s\t%s\t%s\t%s"
            % (
                r["user"],
                "QQ" if r.get("qqish") else "-",
                r.get("kind"),
                ",".join(r["hosts"]),
                (r.get("title") or "")[:60],
            )
        )
    (OUT / "person_sites.txt").write_text("\n".join(lines), encoding="utf-8")

    stats = {
        "seeds": seed_stats,
        "known_users": len(known_users),
        "classified": len(classified),
        "kinds": dict(kinds),
        "new_previewable": len(new_prev),
        "hop_previewable": len(hop_prev),
        "deep_channels": len(deep_rows),
        "all_hosts": len(all_hosts),
        "hosts_to_probe": len(probe_hosts),
        "shops": len(all_shops),
        "person_with_hosts": len(lines),
        "bio_hosts": len(bio_hosts),
    }
    (OUT / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("STATS", json.dumps(stats, ensure_ascii=False, indent=2), flush=True)
    print("PROBE_SAMPLE", probe_hosts[:40], flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
