#!/usr/bin/env python3
"""Grep plain QQ from adb logcat (fallback when Frida misses)."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

QQ_RE = re.compile(r"\b([1-9]\d{4,10})\b")
KEY_PATTERNS = ("str_key_uin", "key_uin", "keyUin", "getKeyUin", "plain_qq")


def run_logcat(adb: str = "adb", clear_first: bool = False, seconds: int = 0) -> str | None:
    if clear_first:
        subprocess.run([adb, "logcat", "-c"], check=False, capture_output=True)
    cmd = [adb, "logcat", "-d", "-v", "brief"]
    if seconds > 0:
        # live tail mode
        proc = subprocess.Popen([adb, "logcat", "-v", "brief"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        import time

        deadline = time.time() + seconds
        lines: list[str] = []
        assert proc.stdout
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            lines.append(line)
        proc.terminate()
        text = "".join(lines)
    else:
        text = subprocess.run(cmd, capture_output=True, text=True, check=False).stdout

    candidates: list[str] = []
    for line in text.splitlines():
        if not any(k in line for k in KEY_PATTERNS):
            continue
        for m in QQ_RE.finditer(line):
            candidates.append(m.group(1))
    return candidates[-1] if candidates else None


def main() -> int:
    ap = argparse.ArgumentParser(description="从 logcat 抓取 plain QQ")
    ap.add_argument("--adb", default="adb")
    ap.add_argument("--clear", action="store_true", help="先清空 logcat")
    ap.add_argument("--watch", type=int, default=0, help="实时监听 N 秒")
    args = ap.parse_args()
    qq = run_logcat(args.adb, clear_first=args.clear, seconds=args.watch)
    if qq:
        print(qq)
        return 0
    print("未在 logcat 中找到 QQ 号", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
