#!/bin/bash
LOG=/workspace/siye/results/spray/wait_reg.log
while true; do
  code=$(curl -sS -m 12 -A 'Mozilla/5.0' 'https://siye.lol/shop/user/reg.php' -o /dev/null -w '%{http_code}' 2>/dev/null || echo 000)
  echo "$(date -u +%H:%M:%S) regpage=$code" | tee -a "$LOG"
  if [ "$code" = "200" ]; then
    # avoid colliding with spray for 20s
    sleep 5
    export $(grep -v '^#' /workspace/siye/scripts/2captcha.env | xargs)
    python3 /workspace/siye/scripts/user_reg_login.py 2>&1 | tee -a "$LOG"
    exit 0
  fi
  sleep 60
done
