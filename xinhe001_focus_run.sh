#!/bin/bash
# xinhe001 full focus — requires TWOCAPTCHA_KEY for Geetest
set -euo pipefail
export QG_TUNNEL="${QG_TUNNEL:-http://15E27ADA-A-JP-T-300-S-xhdeep:661C21F2CC15@overseas-us.tunnel.qg.net:16538}"
export XINHE_OUT="${XINHE_OUT:-/workspace/results_xinhe001/run_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$XINHE_OUT"

if [[ -z "${TWOCAPTCHA_KEY:-}" ]]; then
  echo "TWOCAPTCHA_KEY missing — running no-login hunt only"
  python3 /workspace/xinhe001_full_hunt.py
else
  python3 /workspace/xinhe001_camoufox_chain.py
  python3 /workspace/xinhe001_order_deep.py
fi
