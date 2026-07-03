#!/bin/bash
# nuclei 发卡模板扫描
set -euo pipefail
URL="${1:?用法: $0 https://target}"
TPL="${2:-/data/nuclei-templates/custom/faka}"
OUT="/data/tools/faka/out/nuclei_$(echo "$URL" | md5sum | cut -c1-8).json"

if ! command -v nuclei >/dev/null; then
  echo "nuclei 未安装"; exit 1
fi

mkdir -p /data/tools/faka/out
echo "[*] nuclei $URL templates=$TPL"
nuclei -t "$TPL" -u "$URL" -jsonl -o "$OUT" -silent 2>/dev/null || \
nuclei -t "$TPL" -u "$URL" -jsonl -o "$OUT"
echo "[+] -> $OUT"
