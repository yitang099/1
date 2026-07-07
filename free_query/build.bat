@echo off
chcp 65001 >nul
setlocal

REM 在仓库根目录执行本脚本: free_query\build.bat
cd /d "%~dp0\.."

echo === 免费查号 Windows 打包 ===
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 python，请先安装 Python 3.10+ 并勾选 "Add to PATH"
    pause
    exit /b 1
)

python --version
echo.

echo [1/3] 安装 PyInstaller...
python -m pip install -U pip pyinstaller
if errorlevel 1 (
    echo [错误] pip 安装失败
    pause
    exit /b 1
)

echo.
echo [2/3] 开始打包（约 1-3 分钟）...
python -m PyInstaller free_query\free_query.spec --noconfirm --clean
if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo [3/3] 完成
echo.
echo 输出文件: %cd%\dist\免费查号.exe
echo.
echo 使用说明:
echo   1. 将 dist\免费查号.exe 复制到任意文件夹
echo   2. 双击运行（同目录会生成 config.json 保存账号）
echo   3. 首次使用: 登录/注册 -^> 补足余额 -^> 填手机号查询
echo.
pause
