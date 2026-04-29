@echo off
title Frontend Development Server
color 0B

echo ========================================
echo Starting Frontend Development Server
echo ========================================
echo.

REM Change to trading-dashboard directory (handles paths with spaces)
cd /d "%~dp0"

echo Installing dependencies (if needed)...
call npm install

echo.
echo Starting Vite development server...
echo Server will be available at: http://localhost:5173
echo.
echo Press Ctrl+C to stop the server
echo.

npm run dev

pause





