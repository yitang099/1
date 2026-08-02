#!/bin/bash
# Run break_by_playbook on CN jump with domestic proxy
set -euo pipefail
JUMP_HOST="${JUMP_HOST:-124.248.67.170}"
JUMP_PASS="${JUMP_PASS:-UzHlZQDUy7XP}"
REMOTE_BIN="/data/automation/bin"
OUT="/data/automation/results/break_playbook_$(date +%Y%m%d_%H%M%S)"

sshpass -p "$JUMP_PASS" ssh -o StrictHostKeyChecking=no root@"$JUMP_HOST" "mkdir -p $REMOTE_BIN"
sshpass -p "$JUMP_PASS" scp -o StrictHostKeyChecking=no \
  /workspace/break_by_playbook.py \
  /workspace/break_targets.txt \
  /workspace/query_pwd_list.txt \
  /workspace/SUCCESS_PLAYBOOK.json \
  root@"$JUMP_HOST:$REMOTE_BIN/"

sshpass -p "$JUMP_PASS" ssh -o StrictHostKeyChecking=no root@"$JUMP_HOST" "
  /data/automation/bin/qg-proxy-fetch.sh
  source /data/config/proxy.env
  export PROXY_URL
  export PWD_FILE=$REMOTE_BIN/query_pwd_list.txt
  export DELAY=${DELAY:-0.2}
  export API_SCAN=${API_SCAN:-100}
  export QUERY_FULL=${QUERY_FULL:-1}
  mkdir -p $OUT
  nohup python3 -u $REMOTE_BIN/break_by_playbook.py $OUT --file $REMOTE_BIN/break_targets.txt \
    > $OUT/nohup.out 2>&1 &
  echo STARTED $OUT
"
