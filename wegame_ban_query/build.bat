@echo off
setlocal
cd /d "%~dp0"

python -m pip install -r requirements.txt pyinstaller

if not exist "data" mkdir data
if not exist "data\使用说明.txt" (
  echo 把 WeGame data 放进来，然后运行软件查封号。> "data\使用说明.txt"
)

python -m PyInstaller ^
  --noconfirm ^
  --onedir ^
  --windowed ^
  --name "WeGameBanQuery" ^
  --hidden-import=requests ^
  main.py

xcopy /E /I /Y "data" "dist\WeGameBanQuery\data\" >nul

echo.
echo 打包完成:
echo   dist\WeGameBanQuery\WeGameBanQuery.exe
echo   dist\WeGameBanQuery\data\   ^<-- 把 WeGame data 放这里
pause
