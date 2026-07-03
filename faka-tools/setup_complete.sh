#!/bin/bash
# 发卡工具链一键收尾 — 在 42.240.167.114 上执行
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
docker system prune -f 2>/dev/null || true
rm -f /data/wordlists/dl_*.txt 2>/dev/null || true

echo "[*] 安装 netexec (apt)"
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq netexec 2>/dev/null || true
if command -v netexec >/dev/null; then
  ln -sf "$(command -v netexec)" "$BIN/netexec"
  ln -sf "$(command -v netexec)" /usr/local/bin/nxc 2>/dev/null || true
else
  chmod +x "$FAKA/netexec_wrapper.sh"
  ln -sf "$FAKA/netexec_wrapper.sh" "$BIN/netexec"
  ln -sf "$FAKA/netexec_wrapper.sh" "$BIN/nxc"
  ln -sf "$FAKA/netexec_wrapper.sh" /usr/local/bin/nxc 2>/dev/null || true
fi

echo "[*] apkid 已在 venv"
[ -x /data/tools/venv/bin/apkid ] && ln -sf /data/tools/venv/bin/apkid "$BIN/apkid" 2>/dev/null || true

echo "[*] nuclei faka 模板"
mkdir -p "$NUCLEI_CUSTOM"
cp -f "$FAKA/nuclei-templates/"*.yaml "$NUCLEI_CUSTOM/" 2>/dev/null || true

echo "[*] 统一 skey_exploit_queue 软链"
for d in /data/recon/*/; do
  [ -f "${d}skey_exploit_queue.py" ] || continue
  cp -f "$FAKA/skey_exploit_queue.py" "${d}skey_exploit_queue.py"
done
ln -sf "$FAKA/skey_exploit_queue.py" "$BIN/skey_exploit_queue" 2>/dev/null || true

echo "[*] faka 工具软链"
for f in "$FAKA"/*.py "$FAKA"/*.sh; do
  [ -f "$f" ] || continue
  base=$(basename "$f" .py)
  base=$(basename "$base" .sh)
  ln -sf "$f" "$BIN/$base" 2>/dev/null || true
done

echo "[*] pwndbg/gef (gdb 插件，可选)"
if command -v gdb >/dev/null; then
  [ ! -d /opt/pwndbg ] && git clone --depth 1 https://github.com/pwndbg/pwndbg /opt/pwndbg 2>/dev/null && \
    (cd /opt/pwndbg && ./setup.sh 2>/dev/null) || true
  [ ! -f /root/.gdbinit-gef.py ] && wget -q -O /root/.gdbinit-gef.py https://gef.blah.cat/pygef.py 2>/dev/null || true
fi

echo "[*] MobSF 健康检查"
if docker ps --format '{{.Names}}' | grep -q '^mobsf$'; then
  docker restart mobsf 2>/dev/null || true
  sleep 15
  docker inspect mobsf --format 'MobSF health={{.State.Health.Status}}' 2>/dev/null || true
fi

echo "[*] kali 容器补工具"
if docker ps --format '{{.Names}}' | grep -q '^kali$'; then
  docker exec kali bash -c 'apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl wget nmap 2>/dev/null' || true
fi

echo "[*] 验证"
hashcat --version | head -1
feroxbuster --version 2>/dev/null | head -1 || true
nuclei -version 2>/dev/null | head -1 || true
python3 "$FAKA/faka_fingerprint.py" https://zhanghao9.com 2>/dev/null | head -3 || true
python3 "$FAKA/pay_order_brute.py" -u https://s.sggyx.com --token xiaoy --goods n06507 --probe price --proxy none 2>/dev/null | head -5 || true
ls "$NUCLEI_CUSTOM" 2>/dev/null | wc -l | xargs -I{} echo "nuclei faka templates: {}"
df -h / /data | tail -2

echo "[+] setup_complete done"
