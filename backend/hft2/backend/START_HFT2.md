# How to Run HFT2 with Live Dhan Data

## Quick Start (Easiest)

The frontend now calls hft2 directly on port 5001. Just run:

```powershell
cd c:\Users\pc44\Downloads\trade-bot-main\backend\hft2\backend
python run_hft2.py
```

This starts everything:
- Fyers data service (8002) - mock mode
- MCP server (if deps available)
- Web backend (5000) - optional
- HFT2 API (5001) - REQUIRED (frontend connects here)

## Alternative: With Main Backend Proxy

If you want to use the main backend proxy (port 8000), run:

### 1. Start HFT2 Stack (Port 5001)
```powershell
cd c:\Users\pc44\Downloads\trade-bot-main\backend\hft2\backend
set MAIN_BACKEND_PORT=8000
python run_hft2.py
```

This will also start the main backend proxy on port 8000.

### 2. OR Start Main Backend Separately
In a separate terminal:

```powershell
cd c:\Users\pc44\Downloads\trade-bot-main\backend
set HFT2_BACKEND_URL=http://127.0.0.1:5001
python api_server.py
```

### 3. Start Frontend (Port 5173)
In another terminal:

```powershell
cd c:\Users\pc44\Downloads\trade-bot-main\trading-dashboard
pnpm run dev
```

### 4. Set Mode to "Live Trading" in Dashboard
1. Open `http://localhost:5173/hft`
2. Click the Settings gear icon
3. Select **"Live Trading"** mode
4. Click **"Save Settings"**

### 5. Verify Dhan Connection
Check the logs in the terminal running `run_hft2.py`. You should see:
```
[_get_portfolio] Mode: live
[_get_portfolio] Dhan token available: True
[get_live_portfolio] Dhan API: fund=True, holdings=3, positions=0
[get_live_portfolio] Final portfolio: totalValue=28162.31, holdings=3, symbols=['BANKOFMAHARASHTRA.NS', 'BEL.NS', 'GENUSPOWER.NS']
```

## Troubleshooting

### If you see "₹0.00" and "0 positions":

1. **Check main backend is running:**
   ```powershell
   # Should see: "HFT Bot: proxying to hft2 at http://127.0.0.1:5001"
   ```

2. **Check mode is "live":**
   - Dashboard Settings → Trading Mode → "Live Trading"
   - Or check logs: `[_get_portfolio] Mode: live`

3. **Check Dhan credentials:**
   - File: `backend/hft2/env`
   - Should have: `DHAN_CLIENT_ID` and `DHAN_ACCESS_TOKEN`
   - Check logs: `[get_live_portfolio] Token: True`

4. **Check Dhan API response:**
   - Logs should show: `holdings=3` (or your actual count)
   - If `holdings=0`, check Dhan API is accessible and token is valid

5. **Check Fyers data service:**
   - Should be running on port 8002
   - Logs: `[get_live_portfolio] Final portfolio: ...` shows symbols
   - Fyers LTP will update `currentPrice` for each holding

## Data Flow

```
Frontend (5173)
  ↓ GET /api/bot-data
Main Backend (8000) [with HFT2_BACKEND_URL=http://127.0.0.1:5001]
  ↓ Proxy to /api/bot-data
HFT2 API (5001) - simple_app.py
  ↓ _get_portfolio() → get_live_portfolio()
Dhan API (via dhan_client.py)
  ↓ fetch_holdings() + fetch_positions()
  ↓ For each symbol: _get_fyers_ltp()
Fyers Data Service (8002)
  ↓ Returns live price
  ↓ Updates currentPrice in holdings
  ↓ Returns portfolio to frontend
```

## Quick Test

Test the endpoint directly:
```powershell
curl http://127.0.0.1:5001/api/bot-data
# Should show portfolio with holdings if mode=live
```

Or check main backend proxy:
```powershell
curl http://127.0.0.1:8000/api/bot-data
# Should proxy to hft2 and return same data
```
