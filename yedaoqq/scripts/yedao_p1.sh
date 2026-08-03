#!/bin/bash
set -u
KEY=C413ED6D; PWD=344F550A6F8B
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://yedaoqq.top/shop
CK=/tmp/yedao.ck; OUT=/tmp/yedao_out; LOG=/tmp/yedao_p1.log
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
c(){ curl -sk --connect-timeout 5 --max-time 25 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -e "$BASE/" "$@"; }

for i in 1 2 3 4 5 6 7 8; do
  refresh
  code=$(curl -sk --max-time 25 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -o "$OUT/home.html" -w "%{http_code}" "$BASE/")
  echo WARM=$code
  [[ "$code" == "200" ]] && break
done
[[ "$code" == "200" ]] || { echo WARM_FAIL; exit 1; }

echo "=== DNS ==="
getent ahosts yedaoqq.top | head -5
echo "=== HOME ==="
python3 - <<'PY'
import re
h=open('/tmp/yedao_out/home.html',encoding='utf-8',errors='ignore').read()
print('len', len(h))
print('title', (re.search(r'<title>([^<]+)',h) or [None,None])[1])
for kw in ['assets/faka','csrf_token','hashsalt','geetest','YKFAKA','彩虹','ajax.php','layui','ThinkPHP']:
  print(kw, kw in h or kw.lower() in h.lower())
print('scripts', re.findall(r'src=["\']([^"\']+)["\']', h)[:20])
text=re.sub(r'\s+',' ', re.sub(r'<script[\s\S]*?</script>|<[^>]+>',' ',h))
print('TEXT', text[:600])
PY

echo "=== rainbow API surface ==="
for p in \
  "ajax.php?act=getcount" \
  "%61pi.php?act=siteinfo" \
  "%61pi.php?act=classlist" \
  "%61pi.php?act=goodslist" \
  "%61pi.php?act=tools&key=" \
  "%61pi.php?act=tools&key=test" \
  "cron.php" "cron.php?key=test" \
  "toollogs.php" "user/login.php" "user/reg.php" \
  "other/getshop.php" "install/"; do
  r=$(c -H 'X-Requested-With: XMLHttpRequest' -o "$OUT/pb" -w "%{http_code}:%{size_download}" "$BASE/$p")
  body=$(head -c 180 "$OUT/pb" | tr '\n' ' ')
  echo "E $p => $r $body"
done

echo "=== getcount/siteinfo pretty ==="
c -H 'X-Requested-With: XMLHttpRequest' -X POST "$BASE/ajax.php?act=getcount" | tee "$OUT/getcount.json"
echo
c "$BASE/%61pi.php?act=siteinfo" | tee "$OUT/siteinfo.json"
echo
c "$BASE/%61pi.php?act=goodslist" -o "$OUT/goods.json" -w "goods=%{http_code}:%{size_download}\n"
python3 - <<'PY'
import json,re
try:
 g=json.load(open('/tmp/yedao_out/goods.json'))
 data=g.get('data') or g
 print('goods', len(data) if isinstance(data,list) else type(data))
 if isinstance(data,list):
  for x in data[:8]:
   print(' ', x.get('tid'), x.get('price'), x.get('stock'), str(x.get('name',''))[:40])
except Exception as e:
 print('goods parse', e, open('/tmp/yedao_out/goods.json',encoding='utf-8',errors='ignore').read()[:200])
si=open('/tmp/yedao_out/siteinfo.json',encoding='utf-8',errors='ignore').read()
print('siteinfo', si[:500])
# contacts
print('USDT', re.findall(r'T[A-Za-z0-9]{30,}', si))
print('TG', re.findall(r'@[\w]+|t\.me/[\w]+', si))
PY

echo "===== P1 DONE ====="
