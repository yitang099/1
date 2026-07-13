@echo off
setlocal
cd /d "%~dp0"

python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "WeGame封号查询" ^
  --hidden-import=requests ^
  main.py

echo.
echo 输出: dist\WeGame封号查询.exe
pause
