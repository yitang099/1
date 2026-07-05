@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt -q
if not exist config.json copy config.json.example config.json >nul
python "%~dp0run.py"
pause
