@echo off
chcp 65001 >nul
cd /d "%~dp0"

python -m pip install -r requirements.txt -q >nul 2>&1

if not exist config.json (
    copy config.json.example config.json >nul
)

start "" pythonw background.py
echo 已在后台启动（无窗口），日志见 captcha_auto.log
timeout /t 3 >nul
