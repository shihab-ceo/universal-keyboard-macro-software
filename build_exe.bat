@echo off
setlocal
set "PYTHON=%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
"%PYTHON%" -m PyInstaller --noconfirm --clean --onefile --windowed --name MacroKeys macro_keyboard.py
if errorlevel 1 exit /b %errorlevel%
echo.
echo Build complete: dist\MacroKeys.exe
endlocal
