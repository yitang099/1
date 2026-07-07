@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo === 8081 查号测验客户端 打包 ===
python -m pip install -U pip pyinstaller
python -m PyInstaller sms8081_client\sms8081.spec --noconfirm --clean
echo.
echo 输出: dist\8081查号测验.exe
pause
