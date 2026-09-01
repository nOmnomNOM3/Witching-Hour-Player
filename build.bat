@echo off
setlocal
cd /d "%~dp0"

python -m pip install --upgrade pip pyinstaller
python -m PyInstaller --noconfirm WitchingHour.spec

echo.
echo Built folder:
echo   dist\WitchingHour\WitchingHour.exe
echo.
echo Zip that whole dist\WitchingHour folder and give people the folder,
echo not just the exe. Settings JSON files are created next to the exe.
pause