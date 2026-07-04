#!/bin/bash
# zhanghao9.com 后台：订单枚举 + 后台喷洒 + Epay KEY
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${FAKA_OUT:-/data/tools/faka/out/zh9}"
if [ ! -d "$(dirname "$OUT")" ]; then
  OUT="$ROOT/out/zh9"
fi
mkdir -p "$OUT"

export PYTHONPATH="$ROOT:${PYTHONPATH:-}"
LOG="$OUT/run_zh9_bg.log"

echo "[$(date -Iseconds)] zh9 bg start" | tee -a "$LOG"

if [ -f "$ROOT/qg_short_fetch.py" ]; then
  python3 "$ROOT/qg_short_fetch.py" --write-env 2>>"$LOG" || true
fi

nohup python3 "$ROOT/out/zh9/order_enum_bg.py" >>"$OUT/order_enum_bg.log" 2>&1 &
echo $! >"$OUT/order_enum.pid"
echo "order_enum pid=$(cat "$OUT/order_enum.pid")" | tee -a "$LOG"

nohup python3 "$ROOT/out/zh9/admin_spray_bg.py" --proxy none >>"$OUT/admin_spray_bg.log" 2>&1 &
echo $! >"$OUT/admin_spray.pid"
echo "admin_spray pid=$(cat "$OUT/admin_spray.pid")" | tee -a "$LOG"

nohup python3 "$ROOT/out/zh9/epay_brute_bg.py" >>"$OUT/epay_brute_bg.log" 2>&1 &
echo $! >"$OUT/epay_brute.pid"
echo "epay_brute pid=$(cat "$OUT/epay_brute.pid")" | tee -a "$LOG"

echo "tail -f $OUT/order_enum_bg.log"
echo "tail -f $OUT/admin_spray_bg.log"
echo "tail -f $OUT/epay_brute_bg.log"
