#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mine EVERY advertiser Telegram profile bio for shop websites.
Also refresh kehu/jiu224/kfcgx recent ads + dig new previewable channels.
"""
import re, urllib.request, time, json, html as htmlmod
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import Counter, defaultdict
from urllib.parse import unquote

OUT = Path("/workspace/tmp_bio_mine")
OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"

HOST_RE = re.compile(
    r"(?:https?://)?((?:[a-z0-9-]+\.)+(?:top|lol|cc|vip|com|cn|one|icu|xyz|shop|net|pw|hk|me|site|store|online|club|fun|info|io|app|co|tv|pro|live|biz|link|work))",
    re.I,
)
URL_RE = re.compile(r"https?://[^\s\"'<>\\]+", re.I)
USER_RE = re.compile(r"(?:t\.me/(?:s/)?|@)([A-Za-z][A-Za-z0-9_]{3,63})")
BAD_HOST = re.compile(
    r"(^|\.)(t\.me|telegram\.|telesco\.|github\.|google\.|baidu\.|bing\.|"
    r"microsoft\.|qq\.com$|w3\.org|cloudflare|aliyuncs|sina\.|youtube|"
    r"xiaohongshu|dnspod|iframecontel\.app|org\.telegram)",
    re.I,
)
SKIP_USER = re.compile(
    r"^(https?|http|www|com|top|lol|vip|shop|net|xyz|icu|one|cc|cn|me|fun|"
    r"site|store|online|club|html|php|index|user|admin|test|null|true|false|"
    r"telegram|premium)$|bot$",
    re.I,
)
QQISH = re.compile(
    r"(qq|企鹅|扣扣|/shop|发卡|号商|号码|卖号|出号|批发|库存|已售|ykfaka|易发卡)",
    re.I,
)


def fetch(url, timeout=12):
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def clean_host(h):
    h = unquote(h).lower().removeprefix("www.").strip(".")
    h = re.sub(r"^[^a-z0-9]+", "", h)
    if not re.match(r"^[a-z0-9][a-z0-9.-]+\.[a-z]{2,24}$", h):
        return None
    if BAD_HOST.search(h) or not (5 <= len(h) <= 58):
        return None
    # drop pure telegram junk
    if h in {"telegram.org", "telegram.me", "web.telegram.org"}:
        return None
    return h


def clean_user(u):
    u = u.strip().lstrip("@")
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]{3,63}$", u):
        return None
    if SKIP_USER.search(u):
        return None
    return u.lower()


def mine_bio(uname):
    uname = uname.lstrip("@")
    try:
        html = fetch("https://t.me/%s" % uname, 12)
    except Exception as e:
        return {"user": uname, "ok": False, "err": str(e)[:80]}

    title_m = re.search(r'og:title" content="([^"]*)"', html)
    desc_m = re.search(r'og:description" content="([^"]*)"', html)
    extra_m = re.search(r'class="tgme_page_extra"[^>]*>(.*?)</div>', html, re.S)
    title = htmlmod.unescape(title_m.group(1)) if title_m else ""
    desc = htmlmod.unescape(desc_m.group(1)) if desc_m else ""
    # also description div (sometimes richer)
    desc2_m = re.search(
        r'class="tgme_page_description"[^>]*>(.*?)</div>', html, re.S
    )
    desc2 = ""
    if desc2_m:
        desc2 = htmlmod.unescape(re.sub(r"<[^>]+>", " ", desc2_m.group(1)))
        desc2 = re.sub(r"\s+", " ", desc2).strip()
    extra = ""
    if extra_m:
        extra = re.sub(r"<[^>]+>", " ", extra_m.group(1)).strip()

    blob = " ".join([title, desc, desc2])
    hosts = []
    for h in HOST_RE.findall(blob):
        ch = clean_host(h)
        if ch and ch not in hosts:
            hosts.append(ch)
    # urls in bio
    urls = []
    for L in URL_RE.findall(blob):
        L = unquote(L.rstrip(").,;'\"}>"))
        if BAD_HOST.search(L):
            continue
        if L not in urls:
            urls.append(L)
        m = HOST_RE.search(L)
        if m:
            ch = clean_host(m.group(1))
            if ch and ch not in hosts:
                hosts.append(ch)

    users = []
    for u in USER_RE.findall(blob):
        cu = clean_user(u)
        if cu and cu != uname.lower() and cu not in users:
            users.append(cu)

    kind = "unknown"
    el = extra.lower()
    if "subscriber" in el or "订阅" in extra:
        kind = "channel"
    elif "member" in el or "成员" in extra:
        kind = "group"
    elif "Contact @" in title or (not el and "tgme_page_action" in html):
        kind = "contact"
    elif el.startswith("@"):
        kind = "contact"

    qqish = bool(QQISH.search(blob) or QQISH.search(title))
    return {
        "user": uname.lower(),
        "ok": True,
        "kind": kind,
        "title": title,
        "extra": extra,
        "desc": (desc or desc2)[:500],
        "hosts": hosts,
        "urls": urls,
        "users": users,
        "qqish": qqish,
    }


def scrape_seed_recent(uname, pages=80):
    """Refresh recent ads from public 供需 channels."""
    hosts, shops = set(), set()
    contacts = Counter()
    before = None
    for page in range(pages):
        url = "https://t.me/s/%s" % uname
        if before:
            url += "?before=%d" % before
        try:
            html = fetch(url, 14)
        except Exception:
            time.sleep(0.4)
            continue
        ids = [
            int(x)
            for x in re.findall(r'data-post="%s/(\d+)"' % re.escape(uname), html)
        ]
        if not ids:
            break
        before = min(ids)
        for t in re.findall(
            r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', html, re.S
        ):
            plain = htmlmod.unescape(re.sub(r"<[^>]+>", " ", t))
            plain = re.sub(r"\s+", " ", plain).strip()
            for L in URL_RE.findall(plain):
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
                    contacts[cu] += 1
        time.sleep(0.05)
    return {"channel": uname, "hosts": hosts, "shops": shops, "contacts": contacts}


def check_previewable(uname):
    try:
        html = fetch("https://t.me/s/%s" % uname, 10)
    except Exception:
        return False, "", "error"
    posts = len(re.findall(r"data-post=", html))
    title_m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""
    if posts > 0:
        return True, title, "channel"
    return False, title, "other"


def deep_scrape(uname, pages=120):
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
        time.sleep(0.03)
    return {
        "channel": uname,
        "title": title,
        "hosts": sorted(hosts),
        "shops": sorted(shops),
        "users": sorted(users),
    }


def load_candidates():
    cands = {}
    p = Path("/workspace/tmp_max_adv/all_advertisers_ranked.txt")
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.strip().split("\t")
            if parts:
                u = clean_user(parts[0])
                if u:
                    cands[u] = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    # leftover / expand contacts
    for fp in [
        Path("/workspace/tmp_leftover/more_contacts.txt"),
        Path("/workspace/tmp_expand2/new_contact_cands.txt"),
    ]:
        if not fp.exists():
            continue
        for line in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
            u = clean_user(line.split("\t")[0].strip())
            if u:
                cands.setdefault(u, 1)
    # seed-related
    for u in [
        "ooooy",
        "yoooo",
        "xaioqiaochuhai8",
        "xiaoqiaochuhai",
        "xiaoqiao007",
        "xiaoqiaochuhai001",
        "ajin",
        "ajindb",
        "kehu",
        "jiu224",
        "kfcgx",
    ]:
        cands.setdefault(u, 9999)
    return cands


def main():
    print("=== Phase0: seed profiles ooooy / xaioqiaochuhai8 ===", flush=True)
    seed_profiles = {}
    for u in [
        "ooooy",
        "xaioqiaochuhai8",
        "xiaoqiaochuhai",
        "xiaoqiao007",
        "xiaoqiaochuhai001",
        "yoooo",
        "ajin",
        "ajindb",
        "kehu",
    ]:
        seed_profiles[u] = mine_bio(u)
        print(
            "SEED",
            u,
            seed_profiles[u].get("kind"),
            seed_profiles[u].get("hosts"),
            seed_profiles[u].get("desc", "")[:100],
            flush=True,
        )

    print("=== Phase1: refresh 供需 recent ===", flush=True)
    refresh_hosts, refresh_shops = set(), set()
    refresh_contacts = Counter()
    for s, pages in [("kehu", 120), ("jiu224", 80), ("kfcgx", 80)]:
        r = scrape_seed_recent(s, pages=pages)
        refresh_hosts |= r["hosts"]
        refresh_shops |= r["shops"]
        refresh_contacts.update(r["contacts"])
        print(
            "refresh",
            s,
            "hosts",
            len(r["hosts"]),
            "shops",
            len(r["shops"]),
            "contacts",
            len(r["contacts"]),
            flush=True,
        )

    cands = load_candidates()
    for u in refresh_contacts:
        cands.setdefault(u, refresh_contacts[u])
    # follow users from seed bios
    for row in seed_profiles.values():
        for u in row.get("users") or []:
            cands.setdefault(u, 1)

    print("=== Phase2: BIO mine", len(cands), "profiles ===", flush=True)
    results = []
    bio_host_map = defaultdict(list)
    all_bio_hosts = Counter()
    qqish_with_hosts = []
    done = 0
    users = sorted(cands.keys(), key=lambda u: -cands[u])

    with ThreadPoolExecutor(max_workers=24) as ex:
        futs = {ex.submit(mine_bio, u): u for u in users}
        for fut in as_completed(futs):
            done += 1
            row = fut.result()
            results.append(row)
            if row.get("ok") and row.get("hosts"):
                for h in row["hosts"]:
                    bio_host_map[h].append(row["user"])
                    all_bio_hosts[h] += 1
                if row.get("qqish"):
                    qqish_with_hosts.append(row)
            if done % 200 == 0:
                print(
                    "bio_progress",
                    done,
                    "/",
                    len(users),
                    "with_hosts",
                    sum(1 for r in results if r.get("hosts")),
                    "unique_hosts",
                    len(all_bio_hosts),
                    flush=True,
                )

    (OUT / "bio_all.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "bio_hosts.txt").write_text(
        "\n".join("%s\t%d\t%s" % (h, n, ",".join(bio_host_map[h][:8])) for h, n in all_bio_hosts.most_common()),
        encoding="utf-8",
    )
    (OUT / "bio_qqish_with_hosts.json").write_text(
        json.dumps(qqish_with_hosts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "seed_profiles.json").write_text(
        json.dumps(seed_profiles, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Phase3: new previewable among contacts that look QQ-ish and weren't scraped
    already = set()
    prev_p = Path("/workspace/tmp_max_adv/previewable_channels.txt")
    if prev_p.exists():
        for line in prev_p.read_text(encoding="utf-8", errors="ignore").splitlines():
            u = clean_user(line.split("\t")[0])
            if u:
                already.add(u)

    print("=== Phase3: find NEW previewable QQ-ish channels ===", flush=True)
    new_prev = []
    check_list = []
    for r in results:
        if not r.get("ok"):
            continue
        u = r["user"]
        if u in already:
            continue
        if r.get("kind") == "channel" or r.get("qqish") or r.get("hosts"):
            check_list.append(u)
    # also top refresh contacts
    for u, _n in refresh_contacts.most_common(400):
        if u not in already:
            check_list.append(u)
    check_list = sorted(set(check_list))
    print("to_check_preview", len(check_list), flush=True)

    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = {ex.submit(check_previewable, u): u for u in check_list}
        for fut in as_completed(futs):
            u = futs[fut]
            ok, title, kind = fut.result()
            if ok:
                new_prev.append({"user": u, "title": title, "kind": kind})
                print("NEW_PREV", u, title[:80], flush=True)

    (OUT / "new_previewable.json").write_text(
        json.dumps(new_prev, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("=== Phase4: deep scrape NEW previewable ===", flush=True)
    deep_rows = []
    deep_hosts, deep_shops = set(), set()
    for row in new_prev:
        r = deep_scrape(row["user"], pages=150)
        deep_rows.append(r)
        deep_hosts.update(r["hosts"])
        deep_shops.update(r["shops"])
        print(
            "deep",
            r["channel"],
            "hosts",
            len(r["hosts"]),
            "shops",
            len(r["shops"]),
            flush=True,
        )
        # follow nested users lightly via bio
        for u in r["users"][:30]:
            br = mine_bio(u)
            if br.get("hosts"):
                for h in br["hosts"]:
                    deep_hosts.add(h)
                    bio_host_map[h].append(u)
                    all_bio_hosts[h] += 1

    (OUT / "deep_new.json").write_text(
        json.dumps(deep_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # also deep scrape xiaoqiaochuhai again + any seed-linked previewable
    for u in ["xiaoqiaochuhai", "ajindb"]:
        if u not in {x["user"] for x in new_prev}:
            r = deep_scrape(u, pages=80)
            deep_rows.append(r)
            deep_hosts.update(r["hosts"])
            deep_shops.update(r["shops"])

    all_hosts = set(all_bio_hosts) | refresh_hosts | deep_hosts
    all_shops = set(refresh_shops) | deep_shops
    # known hosts from previous dig
    old_hosts = set()
    hp = Path("/workspace/tmp_max_adv/hosts_all.txt")
    if hp.exists():
        for line in hp.read_text(encoding="utf-8", errors="ignore").splitlines():
            h = clean_host(line.split("\t")[0].strip())
            if h:
                old_hosts.add(h)
    # orders ranked
    op = Path("/workspace/qq_hunt_deliver/orders_rank/orders_ranked.json")
    if op.exists():
        try:
            data = json.loads(op.read_text(encoding="utf-8"))
            for row in data if isinstance(data, list) else data.get("shops", []):
                h = clean_host(row.get("host") or row.get("domain") or "")
                if h:
                    old_hosts.add(h)
        except Exception:
            pass

    new_hosts = sorted(h for h in all_hosts if h not in old_hosts)
    (OUT / "hosts_all_bio.txt").write_text("\n".join(sorted(all_hosts)), encoding="utf-8")
    (OUT / "hosts_NEW.txt").write_text("\n".join(new_hosts), encoding="utf-8")
    (OUT / "shops_all.txt").write_text("\n".join(sorted(all_shops)), encoding="utf-8")

    # person -> sites map (QQ-ish prioritized)
    person_map = []
    for r in results:
        if not r.get("ok"):
            continue
        if not (r.get("hosts") or r.get("qqish")):
            continue
        person_map.append(
            {
                "user": r["user"],
                "kind": r["kind"],
                "title": r["title"],
                "qqish": r["qqish"],
                "hosts": r["hosts"],
                "urls": r["urls"],
                "desc": r["desc"][:240],
                "score": cands.get(r["user"], 0),
            }
        )
    person_map.sort(key=lambda x: (-x["qqish"], -len(x["hosts"]), -x["score"]))
    (OUT / "person_sites.json").write_text(
        json.dumps(person_map, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = []
    for r in person_map:
        if not r["hosts"]:
            continue
        lines.append(
            "%s\t%s\t%s\t%s\t%s"
            % (
                r["user"],
                "QQ" if r["qqish"] else "-",
                r["kind"],
                ",".join(r["hosts"]),
                r["title"][:60],
            )
        )
    (OUT / "person_sites.txt").write_text("\n".join(lines), encoding="utf-8")

    stats = {
        "candidates_bio_mined": len(results),
        "bios_with_hosts": sum(1 for r in results if r.get("hosts")),
        "unique_bio_hosts": len(all_bio_hosts),
        "qqish_with_hosts": len(qqish_with_hosts),
        "refresh_hosts": len(refresh_hosts),
        "refresh_shops": len(refresh_shops),
        "new_previewable": len(new_prev),
        "deep_hosts": len(deep_hosts),
        "all_hosts": len(all_hosts),
        "new_hosts_vs_old": len(new_hosts),
        "old_hosts": len(old_hosts),
        "ooooy_kind": seed_profiles.get("ooooy", {}).get("kind"),
        "xaioqiaochuhai8_kind": seed_profiles.get("xaioqiaochuhai8", {}).get("kind"),
    }
    (OUT / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("STATS", json.dumps(stats, ensure_ascii=False, indent=2), flush=True)
    print("NEW_HOSTS_SAMPLE", new_hosts[:40], flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
