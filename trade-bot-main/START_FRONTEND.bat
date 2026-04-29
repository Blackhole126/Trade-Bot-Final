@echo off
echo ================================================================================
echo Starting Frontend on http://localhost:5173
echo ================================================================================
echo.
echo Make sure Backend is running on http://localhost:8000
echo.

cd trading-dashboard
npm run dev

pause
