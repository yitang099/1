#!/usr/bin/env bash
# 在 Root 手机上启动 frida-server（电脑端执行）
set -euo pipefail

ADB="${ADB:-adb}"
FRIDA_VER="${FRIDA_VER:-}"

if [[ -z "$FRIDA_VER" ]]; then
  FRIDA_VER=$(python3 -c "import frida; print(frida.__version__)" 2>/dev/null || true)
fi
if [[ -z "$FRIDA_VER" ]]; then
  echo "请先安装: pip install frida"
  exit 1
fi

ARCH=$($ADB shell getprop ro.product.cpu.abi | tr -d '\r')
case "$ARCH" in
  arm64-v8a) FARCH=arm64 ;;
  armeabi-v7a|armeabi) FARCH=arm ;;
  x86_64) FARCH=x86_64 ;;
  x86) FARCH=x86 ;;
  *) echo "未知架构: $ARCH"; exit 1 ;;
esac

BIN="frida-server-${FRIDA_VER}-android-${FARCH}"
if [[ ! -f "$BIN" ]]; then
  echo "请下载 $BIN 放到当前目录"
  echo "https://github.com/frida/frida/releases/tag/${FRIDA_VER}"
  exit 1
fi

$ADB push "$BIN" /data/local/tmp/frida-server
$ADB shell "su -c 'chmod 755 /data/local/tmp/frida-server && pkill frida-server 2>/dev/null; /data/local/tmp/frida-server -D &'"
sleep 1
frida-ps -U | head -5
echo "frida-server 已启动 (版本 $FRIDA_VER)"
