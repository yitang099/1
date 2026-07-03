#!/bin/bash
# pyfaas 赤马一键探测
# 用法: pyfaas_probe.sh https://s.sggyx.com [token]
set -euo pipefail
BASE="${1%/}"
TOKEN="${2:-}"
FAKA="/data/tools/faka"
PY="${PYTHON:-python3}"

echo "============================================"
echo "[*] pyfaas probe: $BASE"
echo "[*] $(date)"
echo "============================================"

$PY "$FAKA/faka_fingerprint.py" "$BASE" || true
echo
$PY "$FAKA/cors_scan.py" -u "$BASE/shopApi/Shop/info" -X POST -d "{\"token\":\"${TOKEN:-test}\"}" || true
echo
$PY "$FAKA/merchant_scan.py" -u "$BASE" --limit 25 --xff || true
echo
$PY "$FAKA/thinkphp_scan.py" -u "$BASE" --xff || true
echo
$PY "$FAKA/js_api_extract.py" "$BASE" || true

if [ -n "$TOKEN" ]; then
  echo
  $PY "$FAKA/shop_token_scan.py" -u "$BASE" --tokens "$TOKEN" -w 5 || true
fi

echo "============================================"
echo "[*] 输出目录: $FAKA/out/"
echo "============================================"
