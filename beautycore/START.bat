@echo off
setlocal
cd /d "%~dp0"
python "%~dp0scripts\capstone_launcher.py" %*
set "CAPSTONE_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %CAPSTONE_EXIT%
