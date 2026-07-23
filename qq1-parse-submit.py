#!/usr/bin/env python3
from pathlib import Path
import re
base = Path("/tmp/qq1_deep9")
for p in sorted(base.glob("rg_*.html")) + sorted(base.glob("*submit*")):
    if not p.is_file():
        continue
    t = p.read_text(errors="replace")
    if len(t) < 50:
        continue
    print("FILE", p.name, "len", len(t))
    print(t[:600].replace("\n", " "))
    print("urls", re.findall(r"https?://[^\s\"']+", t)[:20])
    print("loc", re.findall(r"location\.href\s*=\s*['\"]([^'\"]+)", t))
    print("---")
