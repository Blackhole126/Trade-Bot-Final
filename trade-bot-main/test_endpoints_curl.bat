@echo off
REM Comprehensive API Endpoint Testing using curl
REM Tests all 13 endpoints and displays results

setlocal enabledelayedexpansion

set BASE_URL=http://127.0.0.1:8000
set PASSED=0
set FAILED=0

echo.
echo ====================================================================
echo              COMPREHENSIVE API ENDPOINT TESTING (CURL)
echo ====================================================================
echo.

REM Test 1: GET /
echo [1/13] Testing GET /
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" %BASE_URL%/
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

REM Test 2: GET /tools/health
echo [2/13] Testing GET /tools/health
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" %BASE_URL%/tools/health
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

REM Test 3: GET /auth/status
echo [3/13] Testing GET /auth/status
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" %BASE_URL%/auth/status
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

REM Test 4: POST /tools/predict (single symbol)
echo [4/13] Testing POST /tools/predict (AAPL)
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" -X POST %BASE_URL%/tools/predict ^
  -H "Content-Type: application/json" ^
  -d "{\"symbols\": [\"AAPL\"], \"timeframe\": \"intraday\"}"
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

REM Test 5: POST /tools/predict (multiple symbols)
echo [5/13] Testing POST /tools/predict (GOOGL, MSFT)
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" -X POST %BASE_URL%/tools/predict ^
  -H "Content-Type: application/json" ^
  -d "{\"symbols\": [\"GOOGL\", \"MSFT\"], \"timeframe\": \"intraday\"}"
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

REM Test 6: POST /tools/scan_all
echo [6/13] Testing POST /tools/scan_all
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" -X POST %BASE_URL%/tools/scan_all ^
  -H "Content-Type: application/json" ^
  -d "{\"limit\": 5}"
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

REM Test 7: POST /tools/analyze
echo [7/13] Testing POST /tools/analyze
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" -X POST %BASE_URL%/tools/analyze ^
  -H "Content-Type: application/json" ^
  -d "{\"symbol\": \"AAPL\", \"current_price\": 150.0, \"predicted_price\": 155.0, \"confidence\": 0.85}"
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

REM Test 8: POST /tools/feedback
echo [8/13] Testing POST /tools/feedback
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" -X POST %BASE_URL%/tools/feedback ^
  -H "Content-Type: application/json" ^
  -d "{\"symbol\": \"AAPL\", \"prediction_id\": \"test-123\", \"feedback_type\": \"correct\"}"
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

REM Test 9: POST /tools/fetch_data
echo [9/13] Testing POST /tools/fetch_data
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" -X POST %BASE_URL%/tools/fetch_data ^
  -H "Content-Type: application/json" ^
  -d "{\"symbols\": [\"AAPL\"], \"start_date\": \"2026-01-01\", \"end_date\": \"2026-01-21\"}"
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

REM Test 10: POST /api/risk/assess
echo [10/13] Testing POST /api/risk/assess
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" -X POST %BASE_URL%/api/risk/assess ^
  -H "Content-Type: application/json" ^
  -d "{\"symbol\": \"AAPL\", \"entry_price\": 150.0, \"current_price\": 152.0, \"portfolio_value\": 10000}"
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

REM Test 11: POST /api/risk/stop-loss
echo [11/13] Testing POST /api/risk/stop-loss
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" -X POST %BASE_URL%/api/risk/stop-loss ^
  -H "Content-Type: application/json" ^
  -d "{\"symbol\": \"AAPL\", \"entry_price\": 150.0, \"stop_loss_percentage\": 5.0}"
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

REM Test 12: POST /api/ai/chat
echo [12/13] Testing POST /api/ai/chat
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" -X POST %BASE_URL%/api/ai/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"What are your thoughts on AAPL?\"}"
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

REM Test 13: Swagger docs
echo [13/13] Testing GET /docs (Swagger)
curl -s -o nul -w "Status: %%{http_code} | Time: %%{time_total}s\n" %BASE_URL%/docs
if !errorlevel! equ 0 (set /a PASSED+=1) else (set /a FAILED+=1)
echo.

echo ====================================================================
echo RESULTS SUMMARY
echo ====================================================================
echo Passed: %PASSED%/13
echo Failed: %FAILED%/13
echo ====================================================================
echo.

pause
