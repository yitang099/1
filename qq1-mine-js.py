#!/usr/bin/env python3
import re
from pathlib import Path
base = Path("/tmp/qq1_deep8")
for p in sorted(base.glob("*")):
    if p.suffix not in (".js", "") and "js_" not in p.name and p.name not in (
            "reguser.js", "login.js", "faka.js", "user.js", "reg.js",
            "js_assets_js_main.js", "js_assets_faka_js_faka.js"):
        continue
    if not p.is_file():
        continue
    if p.stat().st_size > 500000 or p.stat().st_size < 50:
        continue
    if p.suffix not in (".js",) and "js" not in p.name.lower():
        continue
    t = p.read_text(errors="replace")
    acts = sorted(set(re.findall(r"act=([a-zA-Z0-9_]+)", t)))
    urls = sorted(set(re.findall(r"https?://[^\s\"'<>]+", t)))
    print("FILE", p.name, "len", len(t), "acts", acts)
    for u in urls:
        if any(x in u for x in ("pay", "epay", "alipay", "api", "t.me", "telegram", "qq.com", "geetest", "ftn")):
            print("  url", u[:140])
    # function names around ajax
    for m in re.finditer(r"function\s+(\w+)|(\w+)\s*[:=]\s*function", t):
        name = m.group(1) or m.group(2)
        if name and any(x in name.lower() for x in ("pay", "order", "gift", "share", "fill", "refund", "kami", "login")):
            print("  fn", name)
