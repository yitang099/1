@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "SOFTWARE_DIR=%~dp0.."
echo ========================================
echo  WeGameTQ - Clean CEF cache and restart
echo ========================================
echo Software dir: %SOFTWARE_DIR%
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0wegame_batch_helper.ps1" -SoftwareDir "%SOFTWARE_DIR%" -AutoStart -WaitSeconds 3
echo.
pause
