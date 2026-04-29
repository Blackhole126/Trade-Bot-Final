@echo off
REM ============================================================================
REM Multi-Asset Trading Dashboard - Complete Startup Script
REM Version 1.0.0
REM Purpose: Start both backend and frontend servers with one command
REM ============================================================================

echo.
echo ============================================================================
echo     BLACKHOLE INFEVERSE TRADING DASHBOARD - STARTUP SCRIPT
echo ============================================================================
echo.

REM Get the current directory
set "SCRIPT_DIR=%~dp0"
echo Script directory: %SCRIPT_DIR%

REM Check if we're in the right directory
if not exist "backend\api_server.py" (
    echo.
    echo ERROR: Could not find backend\api_server.py
    echo Please run this script from the Multi-Asset Trading Dashboard directory
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo STARTING SERVERS
echo ============================================================================
echo.

REM Start backend in a new window
echo [1/2] Starting Backend API Server (http://localhost:8000)...
echo        Command: python api_server.py
start "Backend API Server" /D "%SCRIPT_DIR%backend" cmd /k python api_server.py

REM Wait a moment for backend to start
timeout /t 3 /nobreak

REM Start frontend in a new window
echo [2/2] Starting Frontend Development Server (http://localhost:5173)...
echo        Command: npm run dev
start "Frontend Development Server" /D "%SCRIPT_DIR%trading-dashboard" cmd /k npm run dev

REM Wait a moment for frontend to start
timeout /t 2 /nobreak

echo.
echo ============================================================================
echo SERVERS STARTING...
echo ============================================================================
echo.
echo Your Trading Dashboard is starting up!
echo.
echo ENDPOINTS:
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo The frontend window will open in 3 seconds...
echo.

REM Wait and then open the browser
timeout /t 3 /nobreak
start http://localhost:5173

echo.
echo ============================================================================
echo STARTUP COMPLETE
echo ============================================================================
echo.
echo Status:
echo   Backend Server:  Starting on http://localhost:8000
echo   Frontend Server: Starting on http://localhost:5173
echo   Browser:        Opening http://localhost:5173
echo.
echo Both servers are now running in separate windows.
echo.
echo To stop the servers, close the individual windows or press Ctrl+C.
echo.
echo NEXT STEPS:
echo   1. Wait for the browser to load (might take 10-20 seconds)
echo   2. Navigate to the Trading Hub in the sidebar
echo   3. Test each component (Trading Panel, Scanner, Risk Calculator)
echo   4. Check documentation if you need help
echo.
echo Documentation files:
echo   - QUICK_START.md              (Start here!)
echo   - STATUS.md                   (System status)
echo   - TRADING_HUB_DOCUMENTATION.md (Features)
echo   - SETUP_INTEGRATION_GUIDE.md  (Integration)
echo.
echo ============================================================================
echo Happy Trading! 📈
echo ============================================================================
echo.
