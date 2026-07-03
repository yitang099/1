#!/bin/bash
# 加载可用代理到环境变量
set -euo pipefail
FAKA=/data/tools/faka
PROXY=$(python3 -c "import sys; sys.path.insert(0,'$FAKA'); from faka_common import resolve_proxy; print(resolve_proxy('auto'))" 2>/dev/null || true)
if [ -n "$PROXY" ]; then
  export QG="$PROXY"
  export http_proxy="$PROXY"
  export https_proxy="$PROXY"
  export FAKA_PROXY="$PROXY"
  echo "Proxy: ${PROXY#*@}"
else
  echo "Proxy: direct (no working tunnel)"
  unset http_proxy https_proxy FAKA_PROXY 2>/dev/null || true
fi
