@echo off
cd /d "%~dp0"
title Genspicy Clone Local
echo.
echo ========================================
echo   Genspicy Clone - local server
echo   Open: http://127.0.0.1:3000
echo ========================================
echo.

where node >nul 2>&1
if errorlevel 1 (
  echo ERROR: Node.js not found. Install LTS 20+ from https://nodejs.org/
  pause
  exit /b 1
)

if not exist "node_modules\nuxt\" (
  echo Installing dependencies ^(first time, 3-10 min^)...
  call npm install
  if errorlevel 1 (
    echo.
    echo npm install failed. Try in this folder:
    echo   npm install
    echo   npm run build
    pause
    exit /b 1
  )
)

if not exist ".output\server\index.mjs" (
  echo Building site ^(first time^)...
  call npm run build
  if errorlevel 1 (
    echo.
    echo Build failed. Try manually:
    echo   cd /d "%~dp0"
    echo   npm install
    echo   npm run build
    pause
    exit /b 1
  )
)

set PORT=3000
set HOST=0.0.0.0
set NITRO_HOST=0.0.0.0
set NITRO_PORT=3000
set NUXT_PUBLIC_SITE_URL=http://127.0.0.1:3000

echo Browser will open in ~8 seconds. Keep this window open.
start "" /B cmd /c "ping -n 8 127.0.0.1 >nul && start http://127.0.0.1:3000/"

node ".output\server\index.mjs"
echo.
echo Server stopped.
pause
