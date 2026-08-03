#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep dig 出海供需 / 公群频道 for QQ卖号 shops + every advertiser's sites.
Seeds around xaioqiaochuhai8 ecosystem + large 出海供需.
"""
import re, urllib.request, time, json, html as htmlmod
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import Counter, defaultdict
from urllib.parse import unquote

OUT = Path("/workspace/tmp_chuhai_dig")
OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"

HOST_RE = re.compile(
    r"(?:https?://)?((?:[a-z0-9-]+\.)+(?:top|lol|cc|vip|com|cn|one|icu|xyz|shop|net|pw|hk|me|site|store|online|club|fun|info|io|app|co|tv|pro|live|biz))",
    re.I,
)
URL_RE = re.compile(r"https?://[^\s\"'<>\\]+", re.I)
USER_RE = re.compile(r"(?:t\.me/(?:s/)?|@)([A-Za-z][A-Za-z0-9_]{3,63})")
BAD_HOST = re.compile(
    r"(t\.me|telegram|telesco|github|google|baidu|bing|microsoft|qq\.com$|"
    r"w3\.org|cloudflare|aliyuncs|sina\.|youtube|iframecontel)",
    re.I,
)
SKIP_USER = re.compile(
    r"^(https?|http|www|com|top|lol|vip|shop|net|xyz|icu|one|cc|cn|me|fun|"
    r"site|store|online|club|html|php|index|telegram|premium)$|bot$",
    re.I,
)
QQ_KW = re.compile(
    r"(QQ号|qq号|卖QQ|卖qq|企鹅号|扣扣号|QQ批发|qq批发|QQ号商|qq号商|"
    r"出QQ|出qq|QQ成品|qq成品|QQ库存|发卡网|号商|YKFAKA|易发卡|"
    r"QQ号码|qq号码|出售QQ|批发QQ|/shop)",
    re.I,
)


def fetch(url, timeout=14):
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
    return h


def clean_user(u):
    u = u.strip().lstrip("@")
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]{3,63}$", u):
        return None
    if SKIP_USER.search(u):
        return None
    return u.lower()


def scrape_seed(uname, pages=400, qq_only=False):
    hosts, shops = set(), set()
    contacts, channels = Counter(), Counter()
    qq_ads = 0
    before = None
    for page in range(pages):
        url = "https://t.me/s/%s" % uname
        if before:
            url += "?before=%d" % before
        try:
            html = fetch(url, 14)
        except Exception as e:
            print("fail", uname, page, e, flush=True)
            time.sleep(0.5)
            continue
        ids = [
            int(x)
            for x in re.findall(r'data-post="%s/(\d+)"' % re.escape(uname), html)
        ]
        if not ids:
            print("END", uname, "page", page, flush=True)
            break
        before = min(ids)
        for t in re.findall(
            r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', html, re.S
        ):
            plain = htmlmod.unescape(re.sub(r"<[^>]+>", " ", t))
            plain = re.sub(r"\s+", " ", plain).strip()
            is_qq = bool(QQ_KW.search(plain))
            if qq_only and not is_qq:
                # still light-harvest hosts that look like faka
                if not re.search(r"/shop|\.(lol|top|vip|cc)/", plain, re.I):
                    continue
            if is_qq:
                qq_ads += 1

            for m in re.finditer(
                r"(?:联系人|客服|售后|飞机|TG|通知频道|上货(?:通知)?(?:频道|群)?|"
                r"群组|频道|主页|发卡网|网站|对接)"
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

        if page % 30 == 0:
            print(
                uname,
                "p",
                page,
                "qq_ads",
                qq_ads,
                "c",
                len(contacts),
                "h",
                len(hosts),
                "s",
                len(shops),
                flush=True,
            )
        time.sleep(0.04)

    return {
        "channel": uname,
        "qq_ads": qq_ads,
        "contacts": contacts,
        "channels": channels,
        "hosts": sorted(hosts),
        "shops": sorted(shops),
    }


def mine_bio(uname):
    try:
        html = fetch("https://t.me/%s" % uname, 10)
    except Exception as e:
        return {"user": uname, "ok": False}
    title_m = re.search(r'og:title" content="([^"]*)"', html)
    desc_m = re.search(r'og:description" content="([^"]*)"', html)
    title = htmlmod.unescape(title_m.group(1)) if title_m else ""
    desc = htmlmod.unescape(desc_m.group(1)) if desc_m else ""
    blob = title + " " + desc
    hosts = []
    for h in HOST_RE.findall(blob):
        ch = clean_host(h)
        if ch and ch not in hosts:
            hosts.append(ch)
    urls = []
    for L in URL_RE.findall(blob):
        L = unquote(L.rstrip(").,;'\"}>"))
        if not BAD_HOST.search(L) and L not in urls:
            urls.append(L)
    qqish = bool(QQ_KW.search(blob) or re.search(r"qq|企鹅|扣扣|发卡", blob, re.I))
    return {
        "user": uname.lower(),
        "ok": True,
        "title": title,
        "desc": desc[:400],
        "hosts": hosts,
        "urls": urls,
        "qqish": qqish,
    }


def check_previewable(uname):
    try:
        html = fetch("https://t.me/s/%s" % uname, 10)
    except Exception:
        return False, ""
    if re.findall(r"data-post=", html):
        title_m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
        title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""
        return True, title
    return False, ""


def deep_scrape(uname, pages=100):
    hosts, shops = set(), set()
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
        time.sleep(0.03)
    return {
        "channel": uname,
        "title": title,
        "hosts": sorted(hosts),
        "shops": sorted(shops),
    }


def main():
    # Discover actual preview usernames for 出海联盟
    discover = [
        "chuhaiccc",
        "CHGX",
        "chgx",
        "CHGQ",
        "chgq",
        "haihuagongxu",
        "HHCH",
        "hhch",
        "haihuach",
        "haihua",
        "gqdh",
        "CHLM",
        "chlm",
        "CHGG",
        "chgg",
        "xiaoqiaochuhai",
        "xaioqiaochuhai8",
        "xiaoqiao007",
    ]
    print("=== discover ===", flush=True)
    seeds = []
    for u in discover:
        try:
            html = fetch("https://t.me/%s" % u, 10)
        except Exception:
            continue
        title_m = re.search(r'og:title" content="([^"]*)"', html)
        extra_m = re.search(r'tgme_page_extra[^>]*>([^<]+)', html)
        title = title_m.group(1) if title_m else ""
        extra = extra_m.group(1).strip() if extra_m else ""
        ok, _ = check_previewable(u)
        print(u, "prev" if ok else "-", extra, title[:60], flush=True)
        if ok:
            seeds.append(u)

    # Prefer known previewable
    for u in ["chuhaiccc", "chgq", "haihuagongxu", "kehu", "jiu224", "kfcgx"]:
        if u not in seeds:
            ok, _ = check_previewable(u)
            if ok:
                seeds.append(u)

    print("SEEDS", seeds, flush=True)

    all_hosts, all_shops = set(), set()
    score = Counter()
    seed_results = {}
    for s in seeds:
        # for huge 出海 channels use more pages but qq filter soft
        pages = 500 if s in ("chuhaiccc", "chgq", "haihuagongxu") else 200
        qq_only = s in ("chuhaiccc", "chgq", "haihuagongxu")
        print("SCRAPE", s, "pages", pages, "qq_only", qq_only, flush=True)
        r = scrape_seed(s, pages=pages, qq_only=qq_only)
        seed_results[s] = {
            "qq_ads": r["qq_ads"],
            "contacts": len(r["contacts"]),
            "channels": len(r["channels"]),
            "hosts": len(r["hosts"]),
            "shops": len(r["shops"]),
        }
        all_hosts.update(r["hosts"])
        all_shops.update(r["shops"])
        for u, n in r["contacts"].items():
            score[u] += n
        for u, n in r["channels"].items():
            score[u] += n * 2
        # persist partial
        (OUT / ("seed_%s.json" % s)).write_text(
            json.dumps(
                {
                    "qq_ads": r["qq_ads"],
                    "hosts": r["hosts"],
                    "shops": r["shops"],
                    "top_contacts": r["contacts"].most_common(200),
                    "top_channels": r["channels"].most_common(100),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print("seed_done", seed_results[s], flush=True)

    # bio mine top contacts
    print("=== bio mine top", min(1500, len(score)), "===", flush=True)
    top = [u for u, _ in score.most_common(1500)]
    bio_rows = []
    bio_hosts = Counter()
    with ThreadPoolExecutor(max_workers=24) as ex:
        futs = {ex.submit(mine_bio, u): u for u in top}
        done = 0
        for fut in as_completed(futs):
            done += 1
            row = fut.result()
            bio_rows.append(row)
            if row.get("hosts"):
                for h in row["hosts"]:
                    bio_hosts[h] += 1
                    all_hosts.add(h)
            if done % 200 == 0:
                print("bio", done, "hosts", len(bio_hosts), flush=True)

    # new previewable among scored
    already = set()
    for p in [
        Path("/workspace/tmp_max_adv/previewable_channels.txt"),
        Path("/workspace/tmp_bio_mine/new_previewable.json"),
    ]:
        if not p.exists():
            continue
        if p.suffix == ".json":
            for row in json.loads(p.read_text(encoding="utf-8")):
                already.add(row.get("user", ""))
        else:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                already.add(line.split("\t")[0].lower())

    print("=== check new previewable ===", flush=True)
    new_prev = []
    check = [u for u, n in score.most_common(800) if u not in already]
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = {ex.submit(check_previewable, u): u for u in check}
        for fut in as_completed(futs):
            u = futs[fut]
            ok, title = fut.result()
            if ok:
                new_prev.append({"user": u, "title": title})
                print("NEW_PREV", u, title[:70], flush=True)

    deep_rows = []
    for row in new_prev:
        r = deep_scrape(row["user"], pages=120)
        deep_rows.append(r)
        all_hosts.update(r["hosts"])
        all_shops.update(r["shops"])
        print("deep", r["channel"], len(r["hosts"]), len(r["shops"]), flush=True)

    # compare old
    old = set()
    for p in [
        Path("/workspace/tmp_max_adv/hosts_all.txt"),
        Path("/workspace/tmp_bio_mine/hosts_all_bio.txt"),
        Path("/workspace/qq_hunt_deliver/orders_rank/orders_ranked.json"),
    ]:
        if not p.exists():
            continue
        if p.suffix == ".json":
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                rows = data if isinstance(data, list) else data.get("shops", [])
                for row in rows:
                    h = clean_host(str(row.get("host") or row.get("domain") or ""))
                    if h:
                        old.add(h)
            except Exception:
                pass
        else:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                h = clean_host(line.split("\t")[0].strip())
                if h:
                    old.add(h)

    new_hosts = sorted(h for h in all_hosts if h not in old)
    (OUT / "hosts_all.txt").write_text("\n".join(sorted(all_hosts)), encoding="utf-8")
    (OUT / "hosts_NEW.txt").write_text("\n".join(new_hosts), encoding="utf-8")
    (OUT / "shops_all.txt").write_text("\n".join(sorted(all_shops)), encoding="utf-8")
    (OUT / "bio_rows.json").write_text(
        json.dumps([r for r in bio_rows if r.get("hosts") or r.get("qqish")], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "new_previewable.json").write_text(
        json.dumps(new_prev, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "deep_new.json").write_text(
        json.dumps(deep_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "advertisers_ranked.txt").write_text(
        "\n".join("%s\t%d" % (u, n) for u, n in score.most_common()), encoding="utf-8"
    )
    stats = {
        "seeds": seed_results,
        "advertisers": len(score),
        "hosts": len(all_hosts),
        "shops": len(all_shops),
        "new_hosts": len(new_hosts),
        "new_previewable": len(new_prev),
        "bio_with_hosts": sum(1 for r in bio_rows if r.get("hosts")),
    }
    (OUT / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("STATS", json.dumps(stats, ensure_ascii=False, indent=2), flush=True)
    print("NEW_HOSTS", new_hosts[:50], flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
