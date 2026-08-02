#!/bin/bash
# xinhe001 via Qingguo domestic CN proxy (短效代理 中转池)
# Run on whitelisted jump host (国内跳板) or add runner IP to Qingguo whitelist.
set -euo pipefail

export QG_CN_KEY="${QG_CN_KEY:-C413ED6D}"
export QG_CN_PWD="${QG_CN_PWD:-344F550A6F8B}"
export QG_CN_AREA="${QG_CN_AREA:-}"          # optional e.g. 310100 上海
export CN_API_DELAY="${CN_API_DELAY:-3.0}"
export XINHE_API_SCAN="${XINHE_API_SCAN:-1}"

OUT="${XINHE_OUT:-/workspace/results_xinhe001/cn_run_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUT"

echo "=== probe CN proxy ==="
python3 /workspace/qg_cn_proxy.py | tee "$OUT/proxy_probe.log"

echo "=== api.php slow scan (domestic IP) ==="
API_N="${API_N:-300}"
python3 /workspace/xinhe001_cn_api_scan.py "$OUT/api" 0 "$API_N"

if [[ "${XINHE_QUERY_SCAN:-0}" == "1" ]]; then
  echo "=== query substring (uses rotating PROXY_URL) ==="
  PX=$(python3 -c "
from qg_cn_proxy import rotate_until_working
px,_=rotate_until_working()
print(px.proxy_url if px else '')
")
  if [[ -n "$PX" ]]; then
    export PROXY_URL="$PX"
    export QG_TUNNEL=""
    python3 /workspace/xinhe001_history_export.py "$OUT/query" "${DELAY:-0.35}" 0
  fi
fi

echo "OUT=$OUT"
