@echo off
cd /d "%~dp0genspicy-clone"
if not exist package.json (
  echo 找不到 genspicy-clone 目录，请确认仓库完整
  pause
  exit /b 1
)
call start-windows.bat
