#!/bin/bash
# Run xinhe001 Camoufox chain on HK with Qingguo overseas tunnel.
# Usage: export TWOCAPTCHA_KEY=... QG_TUNNEL=... && ./xinhe001_camoufox_run.sh
set -euo pipefail
export QG_TUNNEL="${QG_TUNNEL:-http://15E27ADA-A-JP-T-300-S-xhcfox:661C21F2CC15@overseas-us.tunnel.qg.net:16538}"
export TWOCAPTCHA_KEY="${TWOCAPTCHA_KEY:-}"
export XINHE_OUT="${XINHE_OUT:-/data/automation/results/xinhe001.lol/camoufox_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$XINHE_OUT"
exec /data/automation/venv-camoufox/bin/python -u /data/automation/bin/xinhe001_camoufox_chain.py 2>&1 | tee "$XINHE_OUT/nohup.out"
