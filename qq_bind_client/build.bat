@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo === QQ 查绑 Hook 工具 打包 ===
python -m pip install -U pip pyinstaller frida frida-tools
python -m PyInstaller qq_bind_client\qq_bind.spec --noconfirm --clean
echo.
echo 输出: dist\QQ查绑Hook.exe
echo.
echo 使用前请将 frida-server-版本-android-arm64 放到 exe 同目录
pause
