#!/bin/bash
# netexec/nxc 包装器 — GitHub/apt 不可用时回退 impacket
VENV=/data/tools/venv/bin
NXC_SRC=/data/src/NetExec

if [ -x "$VENV/nxc" ]; then
  exec "$VENV/nxc" "$@"
fi
if [ -x "$VENV/netexec" ]; then
  exec "$VENV/netexec" "$@"
fi
if command -v nxc >/dev/null 2>&1 && [ ! -L "$(command -v nxc)" ]; then
  exec nxc "$@"
fi
if [ -f "$NXC_SRC/nxc/cli.py" ]; then
  exec python3 -m nxc "$@" 2>/dev/null || exec python3 "$NXC_SRC/nxc/cli.py" "$@"
fi

echo "netexec/nxc 未安装（需 GitHub 可达 + aardwolf 编译）" >&2
echo "可用 impacket 替代:" >&2
echo "  $VENV/smbexec.py  $VENV/wmiexec.py  $VENV/psexec.py  $VENV/atexec.py" >&2
exit 1
