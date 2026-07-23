#!/usr/bin/env python3
from pathlib import Path
import re
base = Path("/tmp/qq1_deep9")
for p in sorted(base.glob("fz_*.html")) + sorted(base.glob("panel_*.html")):
    t = p.read_text(errors="replace")
    if len(t) < 200:
        continue
    title_m = re.search(r"<title>([^<]+)", t)
    print("FILE", p.name, "len", len(t), "title", title_m.group(1) if title_m else "?")
    links = sorted(set(re.findall(r'href=["\']([^"\']+)["\']', t)))
    interesting = [x for x in links if any(k in x.lower() for k in ("user/", ".php", "ajax", "api"))]
    print("  links", interesting[:40])
    for pat in ["apikey", "API", "密钥", "余额", "rmb", "money", "zid", "提成", "域名", "对接"]:
        if re.search(pat, t, re.I):
            for m in re.finditer(r".{0,40}" + pat + r".{0,70}", t, re.I):
                s = m.group(0).replace("\n", " ")[:160]
                print("  ", s)
    acts = sorted(set(re.findall(r"act=([a-zA-Z0-9_]+)", t)))
    if acts:
        print("  acts", acts)
    print()
