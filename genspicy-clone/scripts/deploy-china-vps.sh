#!/bin/bash
# 在国内 VPS 上一键部署（浏览器 SSH 粘贴整段即可）
set -euo pipefail
PORT="${PORT:-8080}"
WORKDIR="${WORKDIR:-/opt/genspicy-clone-app}"
BRANCH="cursor/genspicy-clone-local-10e9"
REPO="https://github.com/yitang099/1.git"

if ! command -v node >/dev/null; then
  echo "未检测到 Node.js，请先安装 Node 20+ 后重试"
  exit 1
fi
command -v pnpm >/dev/null || npm install -g pnpm

rm -rf "$WORKDIR"
git clone --depth 1 --branch "$BRANCH" "$REPO" "$WORKDIR/repo"
cd "$WORKDIR/repo/genspicy-clone"

pnpm install
if [ ! -f server/data/templates.catalog.json ]; then
  pnpm import:templates || echo "模板导入失败，将使用 sample 模板"
fi
pnpm build

export HOST=0.0.0.0 PORT="$PORT" NITRO_HOST=0.0.0.0 NITRO_PORT="$PORT"
IP=$(curl -s --max-time 3 ifconfig.me || hostname -I | awk '{print $1}')
echo ""
echo "=========================================="
echo "  部署完成。浏览器打开:"
echo "  http://${IP}:${PORT}/"
echo "=========================================="
exec node .output/server/index.mjs
