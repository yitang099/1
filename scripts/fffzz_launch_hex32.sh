#!/bin/bash
# Generate 32-hex sample dict + launch dedicated worker
set -euo pipefail

OUT=/data/automation/results/fffzz.lol/kami_allin_20260717
BIN=/data/automation/bin
WL=/data/wordlists/faka/fffzz-hex32-sample.txt

export QG_AUTHKEY="${QG_AUTHKEY:-C413ED6D}"
export QG_AUTHPWD="${QG_AUTHPWD:-344F550A6F8B}"

mkdir -p "$OUT" "$BIN" /data/wordlists/faka
python3 "$BIN/fffzz_hex_dict_gen.py" "$WL"
wc -l "$WL"
head -5 "$WL"; echo "..."; tail -3 "$WL"

tmux kill-session -t ff-cn-hex32 2>/dev/null || true
tmux new-session -d -s ff-cn-hex32 \
  "QG_AUTHKEY=$QG_AUTHKEY QG_AUTHPWD=$QG_AUTHPWD python3 $BIN/fffzz_api_brute_fast.py $WL 0 0 12 98 $OUT 2>&1 | tee -a $OUT/cn_hex32.log"

echo "hex32 worker ff-cn-hex32 started wl=$WL ($(wc -l < $WL) lines)"
tmux ls | grep ff-cn-hex
