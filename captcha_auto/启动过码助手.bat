@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  安装依赖（首次运行）
echo ========================================
python -m pip install -r requirements.txt -q

if not exist config.json (
    copy config.json.example config.json >nul
    echo.
    echo [提示] 已生成 config.json，请先填写图灵账号密码
    echo        并运行 calibrate.bat 校准验证码区域
    echo.
    pause
)

python run.py
pause
