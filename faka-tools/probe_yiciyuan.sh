#!/bin/bash
# 异次元网站系统一键探测
set -euo pipefail
FAKA=/data/tools/faka
INPUT="${1:?用法: $0 domain_or_url}"
if [[ "$INPUT" == http* ]]; then
  SHOP="$INPUT"
  DOMAIN=$(echo "$INPUT" | sed -E 's|https?://([^/]+).*|\1|')
else
  DOMAIN="$INPUT"
  SHOP="https://shopping.${DOMAIN}"
fi
UA="Mozilla/5.0 Chrome/120.0.0.0"

echo "[*] 异次元探测 $SHOP"
curl -sS -m 15 -A "$UA" "$SHOP/user/api/index/data" | head -c 200; echo
python3 "$FAKA/sb_subdomain_scan.py" "$DOMAIN" --proxy none 2>/dev/null | tail -5 || true
python3 "$FAKA/acg_idor.py" -u "$SHOP" --trade-list <(echo "903260704032647527") --proxy none 2>/dev/null | tail -3 || true
echo "playbook: /data/recon/playbooks/yiciyuan-faka-playbook.md"
