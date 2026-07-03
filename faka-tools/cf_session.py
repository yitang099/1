#!/usr/bin/env python3
"""
Cloudflare 绕过：playwright 取 cookie 并输出给其它脚本。

示例:
  python3 cf_session.py https://zhanghao9.com/admin/authentication/login
  python3 cf_session.py https://TARGET -o /tmp/cf.json
  python3 acg_login_brute.py -u https://TARGET --cf-cookies /tmp/cf.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from faka_common import ensure_out, log

CF_LOGIN = Path("/data/tools/bin/cf-login")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="CF cookie 获取")
    ap.add_argument("url")
    ap.add_argument("-o", "--out", default="/data/tools/faka/out/cf_cookies.json")
    ap.add_argument("--timeout", type=int, default=90)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    if not CF_LOGIN.exists():
        log(f"[!] 缺少 {CF_LOGIN}")
        sys.exit(1)
    cmd = [sys.executable, str(CF_LOGIN), args.url, args.out]
    log(f"[*] {' '.join(cmd)}")
    r = subprocess.run(cmd, timeout=args.timeout)
    if r.returncode != 0:
        sys.exit(r.returncode)
    if Path(args.out).exists():
        data = json.loads(Path(args.out).read_text(encoding="utf-8"))
        log(f"[+] cookies={len(data)} -> {args.out}")
    else:
        log("[!] cookie 文件未生成")


if __name__ == "__main__":
    main()
