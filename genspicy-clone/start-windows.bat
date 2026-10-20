@echo off
cd /d "%~dp0"
echo [genspicy-clone] 当前目录: %CD%
where node >nul 2>&1 || (
  echo 未找到 Node.js，请先安装: https://nodejs.org/
  pause
  exit /b 1
)
where pnpm >nul 2>&1 || (
  echo 正在启用 corepack / pnpm...
  call corepack enable 2>nul
  call npm install -g pnpm 2>nul
)
if not exist node_modules (
  echo 首次运行: pnpm install ...
  call pnpm install
)
echo.
echo 启动后请在浏览器打开: http://localhost:3000
echo 按 Ctrl+C 可停止服务
echo.
call pnpm dev
pause
