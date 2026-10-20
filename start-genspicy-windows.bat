@echo off

cd /d "%~dp0genspicy-clone"

if not exist "package.json" (

  echo ERROR: folder genspicy-clone not found. Use branch cursor/genspicy-clone-local-10e9

  pause

  exit /b 1

)

call "%~dp0genspicy-clone\start-windows.bat"

