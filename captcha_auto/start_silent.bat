@echo off
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and check Add to PATH
    pause
    exit /b 1
)
if not exist config.json copy config.json.example config.json >nul
python -m pip install -r requirements.txt -q >nul 2>&1
start "" pythonw "%~dp0background.py"
echo OK - background started
echo Log: %~dp0captcha_auto.log
timeout /t 3 >nul
