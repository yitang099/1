#!/bin/bash
# xinhe001 — historical order extraction (no login / no payment)
set -euo pipefail
export QG_TUNNEL="${QG_TUNNEL:-http://15E27ADA-A-JP-T-300-S-xhdeep:661C21F2CC15@overseas-us.tunnel.qg.net:16538}"
OUT="${XINHE_OUT:-/workspace/results_xinhe001/history_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUT"
# Optional slow api.php IDOR (WAF sensitive): export XINHE_API_SCAN=1
export XINHE_API_SCAN="${XINHE_API_SCAN:-0}"
python3 /workspace/xinhe001_history_export.py "$OUT" "${DELAY:-0.3}" "${API_N:-120}"
