#!/usr/bin/env python3
import re
from pathlib import Path

home = Path("/data/recon/hyqq99.com/probe/https_hyqq99.com_shop_.html").read_text(
    "utf-8", "ignore"
)
print("title", re.search(r"<title>([^<]+)", home).group(1))
tids = sorted(set(re.findall(r"[?&]tid=(\d+)", home)), key=int)
cids = sorted(set(re.findall(r"[?&]cid=(\d+)", home)), key=int)
print("tids", len(tids), tids[:50])
print("cids", cids[:40])
print("tg", sorted(set(re.findall(r"@hysc\w+|t\.me/[\w]+", home)))[:20])
print("ajax refs", len(re.findall(r"ajax\.php", home)))
print("js", sorted(set(re.findall(r"assets/[^\"]+\.js", home)))[:30])
