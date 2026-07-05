@echo off
cd /d "%~dp0"
if not exist config.json (
    copy config.json.example config.json >nul
    echo Please edit config.json first
    pause
)
python -m pip install -r requirements.txt -q >nul 2>&1
echo Background solver running. Log: captcha_auto.log
echo Close this window to stop.
python "%~dp0background.py"
pause
