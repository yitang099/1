#!/bin/bash
# Deploy xinhe001 CN tooling to domestic jump and start scan
set -euo pipefail
JUMP_HOST="${JUMP_HOST:-124.248.67.170}"
JUMP_PASS="${JUMP_PASS:-UzHlZQDUy7XP}"
JUMP_USER="${JUMP_USER:-root}"
REMOTE_BIN="/data/automation/bin"

sshpass -p "$JUMP_PASS" ssh -o StrictHostKeyChecking=no "${JUMP_USER}@${JUMP_HOST}" "mkdir -p $REMOTE_BIN"

sshpass -p "$JUMP_PASS" scp -o StrictHostKeyChecking=no \
  /workspace/qg_cn_proxy.py \
  /workspace/xinhe001_cn_api_scan.py \
  /workspace/xinhe001_skey_brute.py \
  /workspace/xinhe001_jump_cn.sh \
  "${JUMP_USER}@${JUMP_HOST}:${REMOTE_BIN}/"

sshpass -p "$JUMP_PASS" ssh -o StrictHostKeyChecking=no "${JUMP_USER}@${JUMP_HOST}" \
  "chmod +x ${REMOTE_BIN}/xinhe001_jump_cn.sh"

OUT="/data/automation/results/xinhe001.lol/cn_jump_$(date +%Y%m%d_%H%M%S)"
sshpass -p "$JUMP_PASS" ssh -o StrictHostKeyChecking=no "${JUMP_USER}@${JUMP_HOST}" \
  "mkdir -p '$OUT' && nohup env XINHE_OUT='$OUT' API_N='${API_N:-400}' CN_API_DELAY='${CN_API_DELAY:-4}' SKEY_RANGE='${SKEY_RANGE:-800}' ${REMOTE_BIN}/xinhe001_jump_cn.sh > '${OUT}/nohup.out' 2>&1 & echo STARTED $OUT"

echo "Remote OUT=$OUT"
echo "Poll: sshpass -p '$JUMP_PASS' ssh ${JUMP_USER}@${JUMP_HOST} 'tail -20 ${OUT}/progress.log'"
