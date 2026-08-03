#!/bin/bash
set -u
KEY=C413ED6D; PWD=344F550A6F8B
RESP=$(curl -s --max-time 10 "https://share.proxy.qg.net/get?key=$KEY&num=1")
SERVER=$(python3 -c "import json,sys
try:
 d=json.loads(sys.argv[1]); print(d['data'][0]['server'] if d.get('code')=='SUCCESS' and d.get('data') else '')
except Exception:
 print('')" "$RESP")
PROXY_URL="http://$KEY:$PWD@$SERVER"
echo PROXY=$PROXY_URL
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://xxn7788.top/shop
CK=/tmp/xxn_pay.ck
OUT=/tmp/xxn_pay_out
rm -rf "$OUT"; mkdir -p "$OUT"; rm -f "$CK"
c(){ curl -sk --connect-timeout 5 --max-time 25 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -e "$BASE/" "$@"; }

c "$BASE/" -o /dev/null -w "HOME=%{http_code}\n"
# cheapest looking tid 500 = 40yuan, or find 10 yuan
TID=$(python3 -c "
import json
d=json.load(open('/tmp/xxn_d3_out/goodslist.json'))['data']
# prefer low price >0 and <100
cands=sorted([(float(x.get('price') or 9999), x.get('tid'), x.get('name')) for x in d if 0 < float(x.get('price') or 0) < 1000])
print(cands[0][1], cands[0][0], cands[0][2][:40])
open('/tmp/xxn_pay_tid.txt','w').write(str(cands[0][1]))
")
echo TID_LINE=$TID
TID=$(cat /tmp/xxn_pay_tid.txt)
c "$BASE/?mod=buy&tid=$TID" -o "$OUT/buy.html" -w "BUY=%{http_code}:%{size_download}\n"

python3 - <<'PY'
import re,subprocess,urllib.parse,os
from pathlib import Path
OUT=Path('/tmp/xxn_pay_out')
h=(OUT/'buy.html').read_text(errors='ignore')
print('buy_len', len(h))
# csrf variants
csrf=None
for pat in [r'name="csrf_token"\s+value="([^"]+)"', r'name=\'csrf_token\'\s+value=\'([^\']+)\'', r'csrf_token"\s*value="([^"]+)"', r'csrf_token[\'\"]?\s*[:=]\s*[\'\"]([^\'\"]+)']:
    m=re.search(pat,h)
    if m:
        csrf=m.group(1); break
hs=re.search(r'var\s+hashsalt\s*=\s*(.+?);',h)
print('csrf', csrf[:20]+'...' if csrf and len(csrf)>20 else csrf)
print('hs', bool(hs))
# inputs
for m in re.findall(r'name="(inputvalue\d*)"[^>]*|placeholder="([^"]+)"', h)[:20]:
    print('field', m)
# alert/inputs labels
for m in re.findall(r'请输入[^<"\']+|联系方式|邮箱|QQ|取卡', h)[:15]:
    print('label', m)
if not hs:
    raise SystemExit('no hashsalt')
open('/tmp/xxn_hs.js','w').write('console.log('+hs.group(1)+')')
r=subprocess.run(['node','/tmp/xxn_hs.js'],capture_output=True,text=True,timeout=30)
hsalt=r.stdout.strip()
print('hashsalt', hsalt)
open(OUT/'hashsalt.txt','w').write(hsalt)
if csrf: open(OUT/'csrf.txt','w').write(csrf)
# save cookie jar path note
PY

HS=$(cat /tmp/xxn_pay_out/hashsalt.txt)
CSRF=$(cat /tmp/xxn_pay_out/csrf.txt 2>/dev/null || echo '')
INPUT=xxn$(date +%H%M%S)
echo "paying tid=$TID input=$INPUT csrf_len=${#CSRF}"

# try several pay payload shapes
for payload in \
  "tid=$TID&num=1&inputvalue=$INPUT&hashsalt=$HS&paytype=alipay" \
  "tid=$TID&num=1&inputvalue=$INPUT&hashsalt=$HS&csrf_token=$CSRF&paytype=alipay" \
  "tid=$TID&num=1&inputvalue=$INPUT&inputvalue2=$INPUT@test.com&hashsalt=$HS&csrf_token=$CSRF&paytype=alipay"; do
  r=$(c -H 'X-Requested-With: XMLHttpRequest' -X POST -d "$payload" "$BASE/ajax.php?act=pay")
  echo "PAY ${payload:0:60}... => ${r:0:350}"
  echo "$r" >> "$OUT/pay_tries.jsonl"
  if echo "$r" | grep -qE 'trade_no|payurl|orderid'; then
    echo "$r" > "$OUT/pay_ok.json"
    break
  fi
done

# re-query with same session after order
echo "=== query after pay ==="
r=$(c -H 'X-Requested-With: XMLHttpRequest' -X POST -d "qq=$INPUT" "$BASE/ajax.php?act=query")
echo "Q input => ${r:0:300}"
r=$(c -H 'X-Requested-With: XMLHttpRequest' -X POST -d "qq=" "$BASE/ajax.php?act=query")
echo "Q empty => ${r:0:300}"

# inspect buy form fields
python3 - <<'PY'
import re
h=open('/tmp/xxn_pay_out/buy.html',encoding='utf-8',errors='ignore').read()
print('inputs', re.findall(r'<input[^>]+name="([^"]+)"[^>]*>', h)[:30])
print('selects', re.findall(r'<select[^>]+name="([^"]+)"', h)[:10])
# verify_open / money
for k in ['verify_open','forcelogin','price','need','money']:
    if k in h: print('has', k)
PY
echo DONE_PAY
