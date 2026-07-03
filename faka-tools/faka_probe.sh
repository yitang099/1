#!/bin/bash
# 发卡站统一探测入口 — 自动指纹后跑对应 probe
set -euo pipefail
FAKA=/data/tools/faka
URL="${1:?用法: $0 https://target [--full]}"
FULL="${2:-}"

echo "[*] faka_probe $URL"
FP=$(python3 "$FAKA/faka_fingerprint.py" "$URL" --json 2>/dev/null || echo '{}')
SYS=$(echo "$FP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('system','unknown'))" 2>/dev/null || echo unknown)
echo "[*] 体系=$SYS"

case "$SYS" in
  rainbow) bash "$FAKA/probe_rainbow_faka.sh" "$URL" ;;
  acg)     bash "$FAKA/probe_yiciyuan.sh" "$URL" ;;
  pisces)  bash "$FAKA/probe_pisces_faka.sh" "$URL" ;;
  pyfaas)  bash "$FAKA/pyfaas_probe.sh" "$URL" "${3:-}" ;;
  *)       python3 "$FAKA/faka_fingerprint.py" "$URL"; bash "$FAKA/thinkphp_scan.py" -u "$URL" --proxy none ;;
esac

if [ "$FULL" = "--full" ] || [ "$2" = "--full" ]; then
  python3 "$FAKA/faka_run.py" "$URL" --full ${3:+--token $3}
  bash "$FAKA/faka_nuclei.sh" "$URL"
  bash "$FAKA/faka_dirscan.sh" "$URL" 2>/dev/null || true
fi
