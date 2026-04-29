@echo off
echo ===============================================
echo RESTARTING BACKEND SERVER
echo ===============================================

echo.
echo [STEP 1] Stopping existing Python processes...
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo [STEP 2] Starting backend server...
cd /d "d:\blackhole projects\blackhole-infevers trade\Multi-Asset Trading Dashboard\backend"

echo [STEP 3] Running server...
python api_server.py

pause