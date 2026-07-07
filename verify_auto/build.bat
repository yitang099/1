@echo off
setlocal
cd /d %~dp0..
python -m pip install -U pip
python -m pip install -r verify_auto\requirements-build.txt
python -m PyInstaller verify_auto\verify_auto.spec --noconfirm --clean
echo.
echo 输出: dist\两步验证助手.exe
pause
