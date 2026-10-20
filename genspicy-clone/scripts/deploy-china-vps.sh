#!/bin/bash
# 在已有 Node 的 Linux VPS（如 103）上运行，对外提供 :8080
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/genspicy-clone}"
PORT="${PORT:-8080}"
REPO="${REPO:-https://github.com/yitang099/1.git}"
BRANCH="${BRANCH:-cursor/genspicy-clone-local-10e9}"

command -v node >/dev/null || { echo "请先安装 Node.js 20+"; exit 1; }
command -v pnpm >/dev/null || npm install -g pnpm

mkdir -p "$(dirname "$APP_DIR")"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone --depth 1 --branch "$BRANCH" "$REPO" "$APP_DIR" 2>/dev/null || {
    git clone "$REPO" /tmp/g1 && cp -r /tmp/g1/genspicy-clone "$APP_DIR"
  }
fi
cd "$APP_DIR/genspicy-clone" 2>/dev/null || cd "$APP_DIR"

pnpm install
[ -f server/data/templates.catalog.json ] || pnpm import:templates || true
pnpm build

export HOST=0.0.0.0
export PORT="$PORT"
export NITRO_HOST=0.0.0.0
export NITRO_PORT="$PORT"

echo "站点: http://$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}'):$PORT/"
exec node .output/server/index.mjs
