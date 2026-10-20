@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Genspicy Clone 本地站
echo.
echo ========================================
echo   Genspicy Clone - 本机一键启动
echo   浏览器地址: http://127.0.0.1:3000
echo ========================================
echo.

where node >nul 2>&1 || (
  echo [错误] 未安装 Node.js
  echo 请打开 https://nodejs.org/ 安装 LTS 20+ 后重新双击本文件
  pause
  exit /b 1
)

where pnpm >nul 2>&1 || (
  echo [提示] 正在配置 pnpm...
  call corepack enable 2>nul
  call npm install -g pnpm 2>nul
)

if not exist node_modules (
  echo [首次] 正在安装依赖（含 ffmpeg，可能需要 1-3 分钟）...
  call pnpm install
  if errorlevel 1 (
    echo 依赖安装失败，请检查网络后重试
    pause
    exit /b 1
  )
)

if not exist .output\server\index.mjs (
  echo [首次] 正在构建站点...
  call pnpm build
  if errorlevel 1 (
    echo 构建失败
    pause
    exit /b 1
  )
)

set PORT=3000
set HOST=0.0.0.0
set NITRO_HOST=0.0.0.0
set NITRO_PORT=3000
set NUXT_PUBLIC_SITE_URL=http://127.0.0.1:3000

echo [提示] 约 5 秒后会自动打开浏览器；请勿关闭本窗口（关闭=关站）
start "" /B cmd /c "ping -n 8 127.0.0.1 >nul && start http://127.0.0.1:3000/"

node .output\server\index.mjs
echo.
echo 服务已停止
pause
