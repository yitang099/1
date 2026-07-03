#!/bin/bash
# 发卡工具链最终收尾 — 别名、模板、代理、软链
set -euo pipefail
FAKA=/data/tools/faka
BIN=/data/tools/bin
NUCLEI=/data/nuclei-templates/custom/faka

echo "[*] setup_complete"
bash "$FAKA/setup_complete.sh" 2>&1 | tail -5

echo "[*] nuclei 模板 (10+)"
mkdir -p "$NUCLEI"
cp -f "$FAKA/nuclei-templates/"*.yaml "$NUCLEI/" 2>/dev/null || true
timeout 30 nuclei -validate -t "$NUCLEI" 2>&1 | tail -1 || echo "nuclei validate skipped/timeout"

echo "[*] 工具别名（playbook 兼容名）"
ln -sf "$FAKA/pisces_dump.py" "$BIN/pisces_order_dump" 2>/dev/null || true
ln -sf "$FAKA/rainbow_export.py" "$BIN/export_txt" 2>/dev/null || true
ln -sf "$FAKA/sb_records_dump.py" "$BIN/yiciyuan_records_dump" 2>/dev/null || true
ln -sf "$FAKA/cookie/crack_qq_cookie.py" "$BIN/scan_all_bodies" 2>/dev/null || true
ln -sf "$FAKA/faka_chain.sh" "$BIN/faka_chain" 2>/dev/null || true
ln -sf "$FAKA/cookie/auto_capture.sh" "$BIN/auto_capture" 2>/dev/null || true
ln -sf "$FAKA/cookie/qq8_skey_chain.sh" "$BIN/qq8_skey_chain" 2>/dev/null || true
ln -sf "$FAKA/epay_hashcat.sh" "$BIN/epay_hashcat" 2>/dev/null || true
ln -sf "$FAKA/sqlmap_faka.sh" "$BIN/sqlmap_faka" 2>/dev/null || true

echo "[*] targets_acg 同步"
[ -f /data/recon/tools/targets_acg.txt ] && cp /data/recon/tools/targets_acg.txt "$FAKA/data/targets_acg.txt" || true

echo "[*] 2captcha 配置检查"
if [ -f "$FAKA/cookie/2captcha.env" ]; then
  python3 "$FAKA/cookie/geetest_2captcha.py" --balance 2>/dev/null && echo "2captcha OK" || echo "2captcha key invalid"
else
  echo "WARN: 复制 cookie/2captcha.env.example -> cookie/2captcha.env"
fi

echo "[*] 代理池检查"
python3 -c "
import sys; sys.path.insert(0,'$FAKA')
from faka_common import load_proxy_candidates, check_proxy
cs=load_proxy_candidates()
print(f'candidates={len(cs)}')
for c in cs:
    ok=check_proxy(c, timeout=5)
    print(('OK ' if ok else 'DEAD ') + c.split('@')[-1])
" 2>/dev/null || true

echo "[*] 工具统计"
echo "python: $(ls $FAKA/*.py $FAKA/cookie/*.py 2>/dev/null | wc -l)"
echo "shell:  $(ls $FAKA/*.sh $FAKA/cookie/*.sh 2>/dev/null | wc -l)"
echo "nuclei: $(ls $NUCLEI/*.yaml 2>/dev/null | wc -l)"
echo "bin:    $(ls $BIN/ 2>/dev/null | grep -cE 'faka|rainbow|acg|sb_|skey|probe|pisces|export|chain|capture|epay_hashcat' || true)"

echo "[+] finish_gaps done"
