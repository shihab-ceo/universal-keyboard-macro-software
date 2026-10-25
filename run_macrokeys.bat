@echo off
setlocal
if exist "%LOCALAPPDATA%\Python\pythoncore-3.15-64\pythonw.exe" (
  "%LOCALAPPDATA%\Python\pythoncore-3.15-64\pythonw.exe" "%~dp0macro_keyboard.py"
) else (
  pyw -3 "%~dp0macro_keyboard.py"
)
