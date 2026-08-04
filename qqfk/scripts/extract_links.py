#!/usr/bin/env python3
import re
from pathlib import Path

PROBE = Path("/data/recon/qqfk.net/probe")
for p in sorted(PROBE.glob("home_*.html")) + sorted(PROBE.glob("*.html")):
    t = p.read_text("utf-8", "ignore")
    print("====", p.name, "len", len(t))
    hrefs = re.findall(r'(?:href|action|src)=["\']([^"\']+)["\']', t, re.I)
    uniq = []
    for h in hrefs:
        if h not in uniq:
            uniq.append(h)
    print("HREFS", uniq[:60], "n", len(uniq))
    urls = re.findall(r"https?://[^\s\"'<>]+", t)
    u2 = []
    for u in urls:
        if u not in u2:
            u2.append(u)
    print("URLS", u2[:40], "n", len(u2))
    for pat in [
        r"location\.href\s*=\s*[\"']([^\"']+)[\"']",
        r"window\.open\([\"']([^\"']+)[\"']",
        r"window\.location\s*=\s*[\"']([^\"']+)[\"']",
    ]:
        ms = re.findall(pat, t, re.I)
        if ms:
            print(pat, ms[:20])
    # text buttons
    for m in re.finditer(r"(立即|进入|购买|商城|下单|查询|客服|电报|飞机|YY|QQ)[^<]{0,40}", t):
        print("TXT", m.group(0)[:80])
    print()
