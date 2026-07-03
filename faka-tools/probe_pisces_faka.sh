#!/bin/bash
# Pisces / acg-faka 一键探测
set -euo pipefail
FAKA=/data/tools/faka
BASE="${1%/}"
[ -z "$BASE" ] && { echo "用法: $0 https://www.target.top"; exit 1; }
UA="Mozilla/5.0 Chrome/120.0.0.0"

API=$(python3 -c "
import re,sys,urllib.request
base=sys.argv[1].rstrip('/')
html=urllib.request.urlopen(base+'/', timeout=20).read().decode('utf-8','replace')
m=re.search(r'assets/index\.[a-f0-9]+\.js', html)
api=base+'/api/v1/pisces'
if m:
    js=urllib.request.urlopen(base+'/'+m.group(0), timeout=20).read().decode('utf-8','replace')
    apis=re.findall(r'\"(/api/v1/[^\"]+)\"', js)
    if apis: api=base+apis[0].rstrip('/')
print(api)
" "$BASE" 2>/dev/null || echo "${BASE}/api/v1/pisces")

echo "[*] Pisces探测 $BASE API=$API"
curl -sS -m 20 -A "$UA" "$API/template" | head -c 300; echo
for st in all admin 1; do
  BODY=$(curl -sS -m 30 -A "$UA" "$API/orderSearch?search_type=$st" 2>/dev/null || true)
  COUNT=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data') or []))" 2>/dev/null || echo 0)
  echo "search_type=$st count=$COUNT"
  [ "${COUNT:-0}" -gt 0 ] && break
done
python3 "$FAKA/pisces_dump.py" "$BASE" 2>/dev/null | tail -3 || true
echo "playbook: /data/recon/playbooks/pisces-faka-ordersearch-playbook.md"
