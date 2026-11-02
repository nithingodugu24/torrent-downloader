@echo off
cd /d "%~dp0"

echo Starting Backend...

powershell -NoProfile -Command "if (Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue) { Write-Host 'Backend is already running.' } else { Start-Process -FilePath 'python' -ArgumentList '-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port','8000' -WorkingDirectory '%~dp0.' -WindowStyle Hidden -RedirectStandardOutput 'backend.log' -RedirectStandardError 'backend.err.log' }"

timeout /t 5 /nobreak >nul

echo Starting Frontend...

cd frontend
powershell -NoProfile -Command "if (Get-NetTCPConnection -State Listen -LocalPort 5173 -ErrorAction SilentlyContinue) { Write-Host 'Frontend is already running.' } else { Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','npm run dev' -WorkingDirectory '%~dp0frontend' -WindowStyle Hidden -RedirectStandardOutput '..\frontend.log' -RedirectStandardError '..\frontend.err.log' }"

echo.
echo Backend : http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:5173
echo.
echo Logs:
echo backend.log
echo frontend.log

pause
