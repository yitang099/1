@echo off
chcp 65001 >nul
cd /d "%~dp0"

python -m pip install -r requirements.txt -q >nul 2>&1

if not exist config.json (
    copy config.json.example config.json >nul
    echo [提示] 首次使用请先运行 校准区域.bat，并填写 config.json 图灵账号
    pause
)

echo 后台过码已启动，日志 captcha_auto.log
echo 关闭本窗口即停止
echo.

python background.py
