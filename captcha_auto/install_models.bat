@echo off
cd /d "%~dp0"
echo Downloading Chinese-CLIP model (first time only, about 400MB)...
echo Please wait...
python -c "from src.local_image_solver import _get_clip; _get_clip(); print('Model OK')"
if errorlevel 1 (
    echo Download failed. Check network and run: python -m pip install -r requirements.txt
    pause
    exit /b 1
)
echo Model ready.
pause
