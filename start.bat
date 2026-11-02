@echo off
setlocal
cd /d "%~dp0"
title Torrent Downloader
where py >nul 2>nul
if not errorlevel 1 (
    py -3.11 --version >nul 2>nul
    if not errorlevel 1 (
        py -3.11 start.py %*
        goto finished
    )
)
where python >nul 2>nul
if not errorlevel 1 (
    python start.py %*
    goto finished
)
echo Python was not found. Install 64-bit Python 3.11 from https://www.python.org/downloads/
echo Enable "Add python.exe to PATH", then run this file again.
pause
exit /b 1
:finished
if errorlevel 1 (
    echo.
    echo Startup failed. Read the message above, then try again.
    pause
    exit /b 1
)
exit /b 0
