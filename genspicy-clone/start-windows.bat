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



where pnpm >nul 2>&1

if errorlevel 1 (

  echo Enabling pnpm...

  call corepack enable 2>nul

  call npm install -g pnpm 2>nul

)



if not exist "node_modules\" (

  echo First run: pnpm install ^(may take a few minutes^)...

  call pnpm install

  if errorlevel 1 (

    echo pnpm install failed

    pause

    exit /b 1

  )

)



if not exist ".output\server\index.mjs" (

  echo First run: pnpm build...

  call pnpm build

  if errorlevel 1 (

    echo pnpm build failed

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

