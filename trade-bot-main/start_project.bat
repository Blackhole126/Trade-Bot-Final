@echo off
echo ========================================
echo Multi-Asset Trading Dashboard Startup
echo ========================================
echo.

REM Check if we're in the project root
if not exist "backend" (
    echo ERROR: backend directory not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

if not exist "trading-dashboard" (
    echo ERROR: trading-dashboard directory not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

echo Starting Backend Server...
start /B "Backend Server" cmd /c "cd backend && python api_server.py"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo.
echo Starting Frontend Development Server...
start /B "Frontend Server" cmd /c "cd trading-dashboard && npm run dev"

echo.
echo ========================================
echo Both servers are starting...
echo.
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:5173
echo API Docs: http://127.0.0.1:8000/docs
echo.
echo Press any key to close this window
echo (Servers will continue running in separate windows)
echo ========================================
pause