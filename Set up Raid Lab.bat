@echo off
setlocal
echo Setting up Raid Lab. No Python or coding tools are required.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" -CreateShortcut
if errorlevel 1 (
  echo.
  echo Setup could not finish. Check your internet connection and the message above.
  pause
)
