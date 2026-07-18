#!/bin/bash
# Generate fffzz priority dict + launch dedicated priority brute worker
set -euo pipefail

OUT=/data/automation/results/fffzz.lol/kami_allin_20260717
BIN=/data/automation/bin
WL=/data/wordlists/faka/fffzz-priority.txt

export QG_AUTHKEY="${QG_AUTHKEY:-C413ED6D}"
export QG_AUTHPWD="${QG_AUTHPWD:-344F550A6F8B}"

mkdir -p "$OUT" "$BIN" /data/wordlists/faka
python3 "$BIN/fffzz_dict_gen.py" "$WL"
wc -l "$WL"

tmux kill-session -t ff-cn-priority 2>/dev/null || true
tmux new-session -d -s ff-cn-priority \
  "QG_AUTHKEY=$QG_AUTHKEY QG_AUTHPWD=$QG_AUTHPWD python3 $BIN/fffzz_api_brute_fast.py $WL 0 0 12 99 $OUT 2>&1 | tee -a $OUT/cn_priority.log"

echo "priority worker ff-cn-priority started wl=$WL"
tmux ls | grep ff-cn-priority
