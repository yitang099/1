#!/bin/bash
# qq8 风格 skey 链快捷入口
set -euo pipefail
FAKA=/data/tools/faka
HOST="${1:-qq8.one}"
CONTACT="${2:-}"
source "$FAKA/cookie/use_proxy.sh"
python3 "$FAKA/skey_exploit_queue.py" -H "$HOST" --proxy auto ${CONTACT:+--contact "$CONTACT"}
