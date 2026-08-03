#!/bin/bash
# xxn7788 — 2Captcha Geetest register (needs hashsalt from reg.php)
set -u
KEY=C413ED6D; PWD=344F550A6F8B
TWOCAP=685ea1068774ca8f8e9a292a08da66d6
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://xxn7788.top/shop
CK=/tmp/xxn_login3.ck
OUT=/tmp/xxn_login3_out
LOG=/tmp/xxn_login3.log
rm -rf "$OUT"; mkdir -p "$OUT"; rm -f "$CK"
exec > >(tee -a "$LOG") 2>&1

refresh(){
  RESP=$(curl -s --max-time 10 "https://share.proxy.qg.net/get?key=${KEY}&num=1" || true)
  SERVER=$(python3 -c "import json,sys
try:
 d=json.loads(sys.argv[1]); print(d['data'][0]['server'] if d.get('code')=='SUCCESS' and d.get('data') else '')
except Exception:
 print('')" "$RESP")
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
[[ "$code" == "200" ]] || { echo WARM_FAIL; exit 1; }

# MUST load reg.php first for hashsalt in session
curl -sk --max-time 25 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -o "$OUT/reg.html" -w "REGPAGE=%{http_code}\n" "$BASE/user/reg.php"
python3 - <<'PY'
import re,subprocess
h=open('/tmp/xxn_login3_out/reg.html',encoding='utf-8',errors='ignore').read()
csrf=re.search(r'var\s+csrf_token\s*=\s*"([^"]+)"',h)
hs=re.search(r'var\s+hashsalt\s*=\s*(.+?);',h,re.S)
print('csrf', bool(csrf), 'hs', bool(hs), 'hs_len', len(hs.group(1)) if hs else 0)
if not hs: raise SystemExit('no hashsalt on reg page')
open('/tmp/xxn_login3_out/hs.js','w').write('console.log('+hs.group(1)+')\n')
hsalt=subprocess.check_output(['node','/tmp/xxn_login3_out/hs.js'],text=True).strip().splitlines()[-1]
print('HS', hsalt)
open('/tmp/xxn_login3_out/hs.txt','w').write(hsalt)
open('/tmp/xxn_login3_out/csrf.txt','w').write(csrf.group(1) if csrf else '')
PY
HS=$(cat "$OUT/hs.txt")
CSRF=$(cat "$OUT/csrf.txt")
echo HS_LEN=${#HS} CSRF_LEN=${#CSRF}

BAL=$(curl -s --max-time 15 "http://2captcha.com/res.php?key=${TWOCAP}&action=getbalance")
echo BALANCE=$BAL

# captcha with same cookie/session as reg.php
r=$(c -e "$BASE/user/reg.php" -X POST -d "csrf_token=$CSRF" "$BASE/ajax.php?act=captcha")
echo CAPTCHA=$r
echo "$r" > "$OUT/captcha.json"
GT=$(python3 -c "import json;print(json.load(open('/tmp/xxn_login3_out/captcha.json')).get('gt',''))")
CH=$(python3 -c "import json;print(json.load(open('/tmp/xxn_login3_out/captcha.json')).get('challenge',''))")
echo GT=$GT CH=$CH
[[ -n "$GT" && -n "$CH" ]] || { echo NO_GT; exit 2; }

CREATE=$(curl -s --max-time 30 "http://2captcha.com/in.php?key=${TWOCAP}&method=geetest&gt=${GT}&challenge=${CH}&pageurl=${BASE}/user/reg.php&json=1")
echo CREATE=$CREATE
RID=$(python3 -c "import json,sys
try:
 j=json.loads(sys.argv[1]); print(j.get('request') if j.get('status')==1 else '')
except Exception:
 print('')" "$CREATE")
echo RID=$RID
[[ -n "$RID" ]] || { echo CREATE_FAIL; exit 3; }

SOL=""
for t in $(seq 1 30); do
  sleep 5
  RES=$(curl -s --max-time 20 "http://2captcha.com/res.php?key=${TWOCAP}&action=get&id=${RID}&json=1")
  echo "RES[$t]=$RES"
  ST=$(python3 -c "import json,sys
try:
 j=json.loads(sys.argv[1]); print(j.get('status'))
except Exception:
 print(0)" "$RES")
  if [[ "$ST" == "1" ]]; then
    echo "$RES" > "$OUT/sol.json"
    SOL=1
    break
  fi
  echo "$RES" | grep -q ERROR && break
done
[[ -n "$SOL" ]] || { echo SOLVE_FAIL; exit 4; }

python3 - <<'PY'
import json
sol=json.load(open('/tmp/xxn_login3_out/sol.json'))
req=sol.get('request')
data=req if isinstance(req,dict) else {}
ch=data.get('geetest_challenge') or data.get('challenge','')
va=data.get('geetest_validate') or data.get('validate','')
se=data.get('geetest_seccode') or data.get('seccode') or (va+'|jordan' if va else '')
open('/tmp/xxn_login3_out/gee.txt','w').write(f'{ch}\n{va}\n{se}\n')
print('gee', ch[:36], va[:32])
PY
mapfile -t GF < "$OUT/gee.txt"
GCH="${GF[0]}"; VA="${GF[1]}"; SE="${GF[2]}"

USER="xxn$(date +%s | tail -c 8)"
PASS='Xxn7788!aB'
QQ=123456789
echo "REGUSER=$USER"

r=$(c -e "$BASE/user/reg.php" -X POST \
  --data-urlencode "user=$USER" \
  --data-urlencode "pwd=$PASS" \
  --data-urlencode "qq=$QQ" \
  --data-urlencode "hashsalt=$HS" \
  --data-urlencode "geetest_challenge=$GCH" \
  --data-urlencode "geetest_validate=$VA" \
  --data-urlencode "geetest_seccode=$SE" \
  --data-urlencode "csrf_token=$CSRF" \
  "$BASE/user/ajax.php?act=reguser")
echo "REG=>$r"
echo "$r" > "$OUT/reg.json"
echo "$USER:$PASS" > "$OUT/creds.txt"

if echo "$r" | grep -qE '"code":1'; then
  echo "=== REG OK ==="
  r=$(c -X POST -d "csrf_token=$CSRF" "$BASE/ajax.php?act=checklogin")
  echo "checklogin=>$r"
  # member pages
  for p in "user/" "user/index.php" "user/shop.php" "user/recharge.php"; do
    code=$(c -o "$OUT/p.body" -w "%{http_code}:%{size_download}" "$BASE/$p")
    echo "P $p => $code"
  done
  # query self (even if 500, try)
  r=$(c -e "$BASE/?mod=query" -X POST -d "qq=&csrf_token=$CSRF" "$BASE/ajax.php?act=query")
  echo "Qself=>$r"
  # payrmb probe
  r=$(c -X POST -d "orderid=20260803103955319&csrf_token=$CSRF" "$BASE/ajax.php?act=payrmb")
  echo "payrmb=>$r"
else
  echo REG_FAIL
  # if geetest ok but other issue, show
fi

echo "===== LOGIN3 DONE ====="
ls -la "$OUT"
