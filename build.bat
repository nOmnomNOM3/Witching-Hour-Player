@echo off
setlocal
cd /d "%~dp0"

set "BUILD_ROOT=C:\Users\Stone\Documents\Visual Studio Code\test builds\witching hour"
set "DIST_DIR=%BUILD_ROOT%\dist"
set "WORK_DIR=%BUILD_ROOT%\build"

if not exist "%BUILD_ROOT%" mkdir "%BUILD_ROOT%"
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"
if not exist "%WORK_DIR%" mkdir "%WORK_DIR%"

python -m pip install --upgrade pip pyinstaller PySide6
python -m PyInstaller --noconfirm --clean --distpath "%DIST_DIR%" --workpath "%WORK_DIR%" WitchingHour.spec

echo.
echo Built folder:
echo   %DIST_DIR%\WitchingHour\WitchingHour.exe
echo.
echo Source repo was not used for dist or build output.
pause