#!/bin/bash
# feroxbuster 目录爆破 — 使用 faka 字典
set -euo pipefail
URL="${1:?用法: $0 https://target}"
WORDLIST="${2:-/data/wordlists/faka/faka_admin.txt}"
OUT="${3:-/data/tools/faka/out/dirscan_$(echo "$URL" | md5sum | cut -c1-8).txt}"

if ! command -v feroxbuster >/dev/null; then
  echo "feroxbuster 未安装"; exit 1
fi

echo "[*] dirscan $URL wordlist=$WORDLIST"
feroxbuster -u "$URL" -w "$WORDLIST" -o "$OUT" -q -t 30 -k --no-state 2>/dev/null || \
feroxbuster -u "$URL" -w "$WORDLIST" -o "$OUT" -t 30 -k
echo "[+] -> $OUT"
