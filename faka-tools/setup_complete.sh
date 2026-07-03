#!/bin/bash
# 发卡工具链一键收尾
set -euo pipefail

FAKA=/data/tools/faka
BIN=/data/tools/bin
NUCLEI_CUSTOM=/data/nuclei-templates/custom/faka

echo "[*] pip 源 -> pypi.org"
mkdir -p /etc/pip
cat > /etc/pip.conf <<'EOF'
[global]
index-url = https://pypi.org/simple
timeout = 120
EOF

echo "[*] 磁盘清理"
apt-get clean -y 2>/dev/null || true
journalctl --vacuum-size=200M 2>/dev/null || true
rm -f /data/wordlists/dl_*.txt 2>/dev/null || true

echo "[*] merchant_apis 内置"
mkdir -p "$FAKA/data"
if [ -f /data/tmp/vuln-deep/merchant_apis.txt ] && [ ! -f "$FAKA/data/merchant_apis.txt" ]; then
  cp /data/tmp/vuln-deep/merchant_apis.txt "$FAKA/data/merchant_apis.txt"
fi
[ ! -f "$FAKA/data/merchant_apis.txt" ] && cp "$FAKA/data/merchant_apis_fallback.txt" "$FAKA/data/merchant_apis.txt" 2>/dev/null || true

echo "[*] nuclei faka 模板"
mkdir -p "$NUCLEI_CUSTOM"
cp -f "$FAKA/nuclei-templates/"*.yaml "$NUCLEI_CUSTOM/" 2>/dev/null || true

echo "[*] 统一 skey_exploit_queue"
for d in /data/recon/*/; do
  [ -f "${d}skey_exploit_queue.py" ] || continue
  cp -f "$FAKA/skey_exploit_queue.py" "${d}skey_exploit_queue.py"
done

echo "[*] faka 工具软链"
chmod +x "$FAKA"/*.py "$FAKA"/*.sh "$FAKA"/cookie/*.py 2>/dev/null || true
for f in "$FAKA"/*.py "$FAKA"/*.sh; do
  [ -f "$f" ] || continue
  base=$(basename "$f" .py); base=$(basename "$base" .sh)
  ln -sf "$f" "$BIN/$base" 2>/dev/null || true
done
ln -sf "$FAKA/skey_exploit_queue.py" "$BIN/skey_exploit_queue" 2>/dev/null || true
ln -sf "$FAKA/faka_probe.sh" "$BIN/faka_probe" 2>/dev/null || true

echo "[*] netexec 包装器"
chmod +x "$FAKA/netexec_wrapper.sh"
ln -sf "$FAKA/netexec_wrapper.sh" "$BIN/netexec" 2>/dev/null || true
ln -sf "$FAKA/netexec_wrapper.sh" "$BIN/nxc" 2>/dev/null || true

echo "[*] 验证"
python3 "$FAKA/faka_fingerprint.py" https://zhanghao9.com 2>/dev/null | head -3 || true
nuclei -validate -t "$NUCLEI_CUSTOM" 2>/dev/null | tail -1 || true
ls "$FAKA"/*.py 2>/dev/null | wc -l | xargs -I{} echo "python tools: {}"
ls "$NUCLEI_CUSTOM" 2>/dev/null | wc -l | xargs -I{} echo "nuclei templates: {}"
df -h / /data | tail -2
echo "[+] setup_complete done"
