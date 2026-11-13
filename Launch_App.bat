@echo off
title Election Analysis Application - Desktop Mode
cd /d "%~dp0"

echo ======================================================================
echo    Election Analysis Application (2009-2024)
echo ======================================================================
echo.
echo Launching Native Desktop Window...
echo.

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in your PATH!
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

python desktop_app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Desktop window closed or encountered an issue.
    pause
)
