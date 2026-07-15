#!/bin/bash
# 青果代理获取 - 优先 /get，通道满时用 /query 复用已在用IP，最后用 /pool
set -euo pipefail
ENV_FILE="${ENV_FILE:-/data/config/proxy.env}"
KEY="${QG_AUTHKEY:-02E76F93}"
PWD="${QG_AUTHPWD:-A0FFB679553D}"
API="https://share.proxy.qg.net"

fetch_json() {
  curl -sS --max-time 15 "$1"
}

pick_server() {
  python3 - "$1" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
if d.get("code") != "SUCCESS":
    sys.exit(1)
data = d.get("data")
if isinstance(data, dict):
    # channels response etc
    sys.exit(1)
if not data:
    sys.exit(1)
# prefer latest deadline
items = sorted(data, key=lambda x: x.get("deadline",""), reverse=True)
print(items[0]["server"])
PY
}

BODY=""
for url in \
  "$API/get?key=$KEY&pwd=$PWD&num=1&distinct=true" \
  "$API/query?key=$KEY&pwd=$PWD" \
  "$API/pool?key=$KEY&pwd=$PWD"; do
  BODY=$(fetch_json "$url" || true)
  if SERVER=$(pick_server "$BODY" 2>/dev/null); then
    break
  fi
done

if [ -z "${SERVER:-}" ]; then
  echo "qg-proxy-fetch: no proxy available: $BODY" >&2
  exit 1
fi

PROXY_URL="http://${KEY}:${PWD}@${SERVER}"
mkdir -p "$(dirname "$ENV_FILE")"
cat > "$ENV_FILE" <<EOF
QG_AUTHKEY="$KEY"
QG_AUTHPWD="$PWD"
PROXY_URL="$PROXY_URL"
PROXY_SERVER="$SERVER"
PROXY_FETCHED_AT="$(date -Iseconds)"
EOF
echo "PROXY_URL=$PROXY_URL"
