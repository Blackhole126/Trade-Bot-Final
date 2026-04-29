"""
Load env from backend/hft2/env and fetch live portfolio from Dhan API.
"""
import os
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Cache for get_live_portfolio keyed by access_token to avoid session leakage
_portfolio_cache: Dict[str, Dict] = {}
# Mapping of access_token to the time it was cached
_portfolio_cache_times: Dict[str, float] = {}
_PORTFOLIO_CACHE_TTL: float = 10.0  # seconds

# Rolling in-memory portfolio value snapshots keyed by access_token
# {token: [{"time": ISO str, "value": float}]}
_portfolio_histories: Dict[str, List[Dict]] = {}
_MAX_HISTORY_POINTS: int = 200


def invalidate_portfolio_cache(access_token: str) -> None:
    """Remove cached portfolio data for a specific access token.

    Call this immediately after saving a new access token so the next
    request always fetches fresh data from Dhan rather than returning
    the stale entry that belonged to the old token.
    Also clears the per-token portfolio history so charts reset cleanly.
    """
    if not access_token:
        return
    _portfolio_cache.pop(access_token, None)
    _portfolio_cache_times.pop(access_token, None)
    _portfolio_histories.pop(access_token, None)
    logger.info(
        "[invalidate_portfolio_cache] Cleared stale cache for token ending ...%s",
        access_token[-4:] if len(access_token) >= 4 else "****",
    )


# Load env file from ../env (parent of backend/)
_ENV_LOADED = False


def _load_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    # Look in current directory and parent for 'env' or '.env'
    _curr = Path(__file__).resolve().parent
    _parent = _curr.parent
    for _p in [_curr, _parent]:
        for _f in ["env", ".env"]:
            _path = _p / _f
            if _path.exists():
                try:
                    with open(_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and "=" in line and not line.startswith("#"):
                                k, _, v = line.partition("=")
                                k, v = k.strip(), v.strip().strip('"').strip("'")
                                os.environ[k] = v
                    _ENV_LOADED = True
                    logger.info("Loaded env from %s", _path)
                    return
                except Exception as e:
                    logger.warning("Failed to load %s: %s", _path, e)
    _ENV_LOADED = True


def get_dhan_token() -> Optional[str]:
    """Deprecated: Dhan credentials are fetched per-user from MongoDB only.
    Use get_dhan_token_for_user(username) instead.
    """
    raise ValueError(
        "Static Dhan access token is disabled. Use get_dhan_token_for_user(username) or fetch from bot config.")


def get_dhan_client_id() -> Optional[str]:
    """Deprecated: Dhan credentials are fetched per-user from MongoDB only.
    Use get_dhan_client_id_for_user(username) instead.
    """
    raise ValueError(
        "Static Dhan client ID is disabled. Use get_dhan_client_id_for_user(username) or fetch from bot config.")


def get_dhan_token_for_user(username: str) -> Optional[str]:
    """Fetch Dhan access token for a specific user from MongoDB."""
    try:
        from hft_auth import get_user_demat
        demat = get_user_demat(username)
        if demat:
            return demat.get("access_token")
    except Exception as e:
        logger.error(f"Error fetching Dhan token for user {username}: {e}")
    return None


def get_dhan_client_id_for_user(username: str) -> Optional[str]:
    """Fetch Dhan client ID for a specific user from MongoDB."""
    try:
        from hft_auth import get_user_demat
        demat = get_user_demat(username)
        if demat:
            return demat.get("client_id")
    except Exception as e:
        logger.error(f"Error fetching Dhan client ID for user {username}: {e}")
    return None


def check_dhan_credentials_status(username: str) -> Dict[str, Any]:
    """Check Dhan credentials status for a user and return detailed diagnostic info.

    Returns:
        Dict with keys:
        - configured: bool - whether credentials exist in database
        - valid: bool - whether credentials are currently valid (API test)
        - error: str or None - error message if any
        - message: str - human-readable status message
        - client_id_masked: str - masked client ID for display (e.g., "1234****5678")
    """
    result = {
        "configured": False,
        "valid": False,
        "error": None,
        "message": "",
        "client_id_masked": None
    }

    if not username or username == "anonymous":
        result["message"] = "No authenticated user. Please log in first."
        return result

    # Fetch credentials from MongoDB
    token = get_dhan_token_for_user(username)
    client_id = get_dhan_client_id_for_user(username)

    if not token or not client_id:
        result["message"] = (
            "Dhan account not linked. Go to Settings → Demat Account → Link your demat "
            "and enter your Client ID and Access Token from web.dhan.co → My Profile → Access DhanHQ APIs."
        )
        return result

    # Credentials exist - mask client ID for display
    masked = f"{client_id[:4]}****{client_id[-4:]}" if len(
        client_id) > 8 else "****"
    result["configured"] = True
    result["client_id_masked"] = masked

    # Test API connection
    try:
        fund = fetch_fund_limit(token, client_id=client_id)
        if fund and isinstance(fund, dict):
            if fund.get("status") == "failure":
                http_code = fund.get("http_code")
                error_info = fund.get("error", {})

                if http_code == 401:
                    error_type = error_info.get("errorType", "Unknown") if isinstance(
                        error_info, dict) else "Unknown"
                    error_code = error_info.get(
                        "errorCode", "DH-901") if isinstance(error_info, dict) else "DH-901"
                    error_msg = error_info.get("errorMessage", "Invalid credentials") if isinstance(
                        error_info, dict) else str(error_info)

                    result["error"] = f"{error_type} ({error_code})"
                    result["message"] = (
                        f"❌ Authentication failed: {error_msg}. "
                        f"Your Dhan access token has expired or is invalid. "
                        f"Tokens typically expire after 24 hours. "
                        f"Please go to Settings → Demat Account and re-link with fresh credentials."
                    )
                    return result
                else:
                    result["error"] = f"API Error (HTTP {http_code})"
                    result["message"] = f"⚠️ Dhan API returned error: {fund.get('remarks') or error_info}"
                    return result
            else:
                # Success!
                result["valid"] = True
                result["message"] = f"✅ Dhan account linked successfully (Client ID: {masked}). Ready to trade."
                return result
        else:
            result["error"] = "Network Error"
            result["message"] = "⚠️ Could not connect to Dhan API. Check internet connection or try again later."
            return result
    except Exception as e:
        result["error"] = "Connection Error"
        result["message"] = f"⚠️ Error testing Dhan connection: {str(e)}"
        return result


def _dhan_request(method: str, path: str, token: str, client_id: Optional[str] = None, **kwargs: Any) -> Any:
    import urllib.request
    import urllib.error
    import json
    url = f"https://api.dhan.co/v2{path}"
    headers = {
        "Content-Type": "application/json",
        "access-token": token,
    }
    if client_id:
        headers["dhanClientId"] = str(client_id)

    # Log request details for debugging (mask sensitive parts)
    logger.debug(f"Dhan API Request: {method} {url}")
    logger.debug(
        f"Headers: access-token={'***' + token[-4:] if token else 'None'}, dhanClientId={client_id}")

    req = urllib.request.Request(url, method=method, headers=headers)
    if kwargs.get("data"):
        req.data = json.dumps(kwargs["data"]).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        # Read and log the Dhan error response body for debugging
        try:
            body = e.read().decode("utf-8", errors="ignore")
            logger.error("Dhan API %s %s HTTP %d: %s",
                         method, path, e.code, body)
            logger.error(
                f"Request details - URL: {url}, Client ID: {client_id}, Token valid: {bool(token)}")

            # Parse and log structured error info
            if body:
                try:
                    error_data = json.loads(body)
                    error_type = error_data.get("errorType", "Unknown")
                    error_code = error_data.get("errorCode", "Unknown")
                    error_msg = error_data.get("errorMessage", "No message")
                    logger.error(
                        f"Dhan Error Details - Type: {error_type}, Code: {error_code}, Message: {error_msg}")

                    # Special handling for FUND_LIMIT_ERROR
                    if error_type == "FUND_LIMIT_ERROR":
                        logger.warning(
                            "⚠️ FUND_LIMIT_ERROR: This may indicate:\n"
                            "  1. Invalid or expired access token\n"
                            "  2. Dhan API server temporarily unavailable\n"
                            "  3. Account permissions issue\n"
                            "  Action: Verify Dhan credentials in Settings → Demat Account"
                        )
                except json.JSONDecodeError:
                    pass

            try:
                return {"status": "failure", "http_code": e.code, "error": json.loads(body)}
            except Exception:
                return {"status": "failure", "http_code": e.code, "error_body": body}
        except Exception:
            logger.error("Dhan API %s %s HTTP %d (no body)",
                         method, path, e.code)
            return {"status": "failure", "http_code": e.code}
    except Exception as e:
        logger.warning("Dhan API %s %s failed: %s", method, path, e)
        return {"status": "failure", "remarks": str(e)}


def fetch_fund_limit(token: str, client_id: Optional[str] = None) -> Optional[Dict]:
    out = _dhan_request("GET", "/fundlimit", token, client_id=client_id)
    return out if isinstance(out, dict) else None


def fetch_holdings(token: str, client_id: Optional[str] = None) -> List[Dict]:
    out = _dhan_request("GET", "/holdings", token, client_id=client_id)
    if isinstance(out, list):
        return out
    return []


def fetch_positions(token: str, client_id: Optional[str] = None) -> List[Dict]:
    out = _dhan_request("GET", "/positions", token, client_id=client_id)
    if isinstance(out, list):
        return out
    return []


def _nse_symbol(s: str, segment: str = "") -> str:
    if not s:
        return s
    if "NSE" in segment or segment == "NSE_EQ" or not segment:
        return f"{s}.NS" if "." not in s else s
    if "BSE" in segment:
        return f"{s}.BO" if "." not in s else s
    return s


def _get_fyers_ltp(symbol: str) -> Optional[float]:
    """Fetch LTP for symbol from Fyers data service (port 8002). Returns price or None."""
    _load_env()
    import urllib.request
    import json
    from urllib.parse import quote
    port = os.environ.get("DATA_SERVICE_PORT", "8002")
    base = f"http://127.0.0.1:{port}"
    url = f"{base}/data/{quote(symbol, safe='')}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as r:
            data = json.loads(r.read().decode())
            if isinstance(data, dict) and "price" in data:
                p = float(data["price"])
                return p if p > 0 else None
    except Exception as e:
        logger.debug("Fyers LTP for %s: %s", symbol, e)
    return None


def _get_dhan_ltps(token: str, instruments: List[Dict], client_id: Optional[str] = None) -> Dict[str, float]:
    """Fetch LTPs for multiple instruments from Dhan Market Feed API.
    instruments is a list of {"exchangeSegment": str, "securityId": str}
    Returns mapping of securityId to price.

    NOTE: For /marketfeed/ltp endpoint, Dhan does NOT require client_id in request.
    Only access-token is needed. Sending client_id causes error 810.
    """
    if not instruments:
        return {}

    # Dhan API expects POST /marketfeed/ltp - NO client_id needed (causes error 810)
    body = {"instruments": instruments}
    try:
        out = _dhan_request("POST", "/marketfeed/ltp", token, data=body)
        prices = {}
        if isinstance(out, list):
            for item in out:
                sid = str(item.get("securityId", ""))
                price = float(item.get("lastPrice", 0.0))
                if sid and price > 0:
                    prices[sid] = price
            logger.info(
                f"[_get_dhan_ltps] Fetched {len(prices)} prices natively from Dhan")
        return prices
    except Exception as e:
        logger.warning("Dhan LTP fetch failed: %s", e)
    return {}


def get_live_portfolio(access_token: Optional[str] = None, client_id: Optional[str] = None) -> Optional[Dict]:
    """Build portfolio dict for HFT dashboard from Dhan: holdings, cash, totalValue, tradeLog.
    access_token and client_id must be provided explicitly (per-user from MongoDB)."""
    global _portfolio_cache, _portfolio_cache_times
    token = access_token   # must be passed explicitly — no global fallback
    cid = client_id
    use_cache = True  # Enable per-user caching
    now = time.time()

    # Check cache for THIS specific token
    if use_cache and token and token in _portfolio_cache:
        cache_time = _portfolio_cache_times.get(token, 0.0)
        if (now - cache_time) < _PORTFOLIO_CACHE_TTL:
            return _portfolio_cache.get(token)

    logger.info(
        f"[get_live_portfolio] Token: {bool(token)}, Client ID: {bool(cid)}")
    if not token:
        logger.warning(
            "[get_live_portfolio] No Dhan token - cannot fetch portfolio")
        return None
    if not cid:
        logger.warning(
            "[get_live_portfolio] No Dhan client ID - cannot fetch portfolio")
        return None
    try:
        fund = fetch_fund_limit(token, client_id=cid)
        holdings_list = fetch_holdings(token, client_id=cid)
        positions_list = fetch_positions(token, client_id=cid)

        # --- ROBUST FAILURE DETECTION ---
        # If any major call returned a failure object (likely 401 or DNS error),
        # use the last known cache to prevent the UI from resetting to zero.
        api_failed = False
        auth_error = False
        for resp in [fund, holdings_list, positions_list]:
            if isinstance(resp, dict) and resp.get("status") == "failure":
                api_failed = True
                fail_msg = resp.get("remarks") or str(
                    resp.get("error", "API error"))
                http_code = resp.get("http_code")

                # Check for authentication errors
                if http_code == 401:
                    auth_error = True
                    error_details = resp.get("error", {})
                    if isinstance(error_details, dict):
                        error_type = error_details.get("errorType", "")
                        error_code = error_details.get("errorCode", "")
                        error_msg = error_details.get("errorMessage", "")
                        logger.error(
                            f"[get_live_portfolio] DHAN AUTHENTICATION FAILED: "
                            f"Type={error_type}, Code={error_code}, Message={error_msg}. "
                            f"Token may be expired. User must refresh token in Settings → Demat Account."
                        )
                else:
                    logger.warning(
                        f"[get_live_portfolio] Dhan API reports failure: {fail_msg}")
                break

        # If authentication failed, DON'T use cache - force user to re-authenticate
        if auth_error:
            logger.error(
                "[get_live_portfolio] Authentication failed - clearing cached portfolio. "
                "User must link/re-link demat account in Settings."
            )
            # Clear cache for this invalid token
            if token in _portfolio_cache:
                del _portfolio_cache[token]
            if token in _portfolio_cache_times:
                del _portfolio_cache_times[token]
            return None

        if api_failed and use_cache and token in _portfolio_cache:
            logger.info(
                "[get_live_portfolio] API failed; returning last known stale cache to prevent UI reset.")
            return _portfolio_cache.get(token)

        # Dhan API sometimes transiently returns empty dicts for funds/holdings
        # instead of an error HTTP code. If we get an empty fund limit but we
        # have a valid cached portfolio, fallback to the cache rather than
        # flashing ₹0.00 on the dashboard.
        if (not fund or api_failed) and use_cache and token in _portfolio_cache:
            logger.warning(
                "[get_live_portfolio] Dhan call issue. Falling back to last known cache to prevent 0.00 flash.")
            return _portfolio_cache.get(token)

        logger.info(
            f"[get_live_portfolio] Dhan API: fund={bool(fund)}, holdings={len(holdings_list)}, positions={len(positions_list)}")
    except Exception as e:
        logger.error(f"[get_live_portfolio] Dhan API exception: {e}")
        # On hard exception (DNS failure, etc.), fallback to cache if available
        if use_cache and token in _portfolio_cache:
            return _portfolio_cache.get(token)
        return None

    today_gain: float = 0.0
    for p in positions_list:
        try:
            # Dhan's dayProfit corresponds to "Today's Profit" in the app
            profit_val = p.get("dayProfit")
            today_profit: float = float(
                profit_val) if profit_val is not None else 0.0
            today_gain += today_profit
        except (TypeError, ValueError):
            pass
    cash = 0.0
    if fund:
        for _cash_key in ("availabelBalance", "availableBalance", "available_balance",
                          "availBalance", "netAvailableBalance", "cash"):
            if fund and _cash_key in fund and fund[_cash_key] is not None:
                try:
                    cash = float(fund[_cash_key])
                    break
                except (TypeError, ValueError):
                    continue
    sod = float(fund.get("sodLimit", 0) or 0) if fund else 0

    holdings: Dict[str, Dict] = {}
    # Delivery holdings (demat)
    for h in holdings_list:
        sym = _nse_symbol(str(h.get("tradingSymbol", "")),
                          str(h.get("exchange", "NSE_EQ")))
        qty = int(h.get("availableQty") or h.get("totalQty") or 0)
        if qty <= 0 or not sym:
            continue        # Robust price lookup — Dhan uses inconsistent field names
        avg = 0.0
        for _avg_key in ("avgCostPrice", "avgCost", "costPrice", "buyAvg", "averagePrice"):
            val = h.get(_avg_key)
            if val is not None:
                try:
                    avg = float(val)
                    if avg > 0:
                        break
                except (TypeError, ValueError):
                    continue

        # Calculate daily MTM if dayProfit is missing
        # Try multiple keys for last price: lastPrice, ltp, currentPrice, current_price
        last_price = 0.0
        for _lp_key in ("lastPrice", "ltp", "currentPrice", "current_price", "price"):
            val = h.get(_lp_key)
            if val is not None:
                try:
                    last_price = float(val)
                    if last_price > 0:
                        break
                except:
                    continue

        # Expansion: Dhan uses many names for previous close. Mapping them all.
        close_price_val = (
            h.get("closePrice") or
            h.get("prevClose") or
            h.get("previousClose") or
            h.get("previousDayClose") or
            h.get("yesterdayClose") or
            h.get("prevDayClose") or
            h.get("prev_close")
        )
        close_price = float(close_price_val) if close_price_val else 0.0

        # Fallback for close_price via Yahoo Finance if Dhan is missing it.
        # This is critical for accurate todayGain/MTM calculation.
        if close_price <= 0 and sym:
            try:
                import yfinance as yf
                yf_sym = sym if "." in sym else f"{sym}.NS"
                ticker = yf.Ticker(yf_sym)
                # fast_info is efficient; fallback to history if needed
                try:
                    close_price = float(ticker.fast_info['previousClose'])
                except:
                    hist = ticker.history(period="2d")
                    if len(hist) >= 2:
                        close_price = float(hist["Close"].iloc[-2])
                    elif not hist.empty:
                        close_price = float(hist["Close"].iloc[-1])

                if close_price > 0:
                    logger.debug(
                        f"[get_live_portfolio] YF fallback close_price for {sym}: {close_price}")
            except Exception as e:
                logger.debug(
                    f"[get_live_portfolio] YF close fallback failed for {sym}: {e}")

        if close_price <= 0:
            close_price = last_price  # last resort

        # If this symbol is NOT in positions_list, we add its daily MTM change to today_gain
        # Note: holdings_list symbols might overlap with positions_list if bought/sold today.
        # We will calculate today_gain for holdings AFTER live prices are fetched
        # to ensure we use the most accurate LTP.
        # (Removed premature calculation here)

        holdings[sym] = {
            "symbol": sym,
            "quantity": qty,
            "avgPrice": avg,
            "currentPrice": last_price,
            "lastAction": "BUY",
            "securityId": str(h.get("securityId", "")),
            "exchangeSegment": str(h.get("exchangeSegment") or h.get("exchange") or "NSE_EQ"),
            "closePrice": close_price,
            "inPositions": any(_nse_symbol(str(p.get("tradingSymbol", ""))) == sym for p in positions_list)
        }
    # Merge positions into holdings
    for p in positions_list:
        if str(p.get("positionType")) == "CLOSED":
            continue
        sym = _nse_symbol(str(p.get("tradingSymbol", "")),
                          str(p.get("exchangeSegment", "NSE_EQ")))
        net_qty = int(p.get("netQty") or 0)
        if net_qty == 0 or not sym:
            continue
        buy_avg = float(p.get("buyAvg") or 0)
        cost_price = float(p.get("costPrice") or buy_avg)
        unrealized = float(p.get("unrealizedProfit") or 0)
        # Calculate currentPrice from positions data if available, otherwise use cost_price as placeholder
        # Will be updated later with live LTP fetch
        current_price = cost_price
        if net_qty != 0:
            # currentPrice such that (currentPrice - costPrice) * netQty = unrealizedProfit
            current_price = cost_price + (unrealized / net_qty)

        if sym in holdings:
            # Merge with existing holding (e.g. same script in CNC + intraday)
            old = holdings[sym]
            logger.debug(
                f"[get_live_portfolio] Merging position {sym}: current={current_price}, cost={cost_price}, existing_avg={old['avgPrice']}")
            tot_qty = old["quantity"] + net_qty
            old_avg = old["avgPrice"] * old["quantity"] + cost_price * net_qty
            holdings[sym]["quantity"] = tot_qty
            holdings[sym]["avgPrice"] = old_avg / \
                tot_qty if tot_qty else old["avgPrice"]
            holdings[sym]["currentPrice"] = current_price
            holdings[sym]["securityId"] = holdings[sym].get(
                "securityId") or str(p.get("securityId", ""))
        else:
            logger.debug(
                f"[get_live_portfolio] New position {sym}: avg={cost_price}, cur={current_price}")
            holdings[sym] = {
                "symbol": sym,
                "quantity": net_qty,
                "avgPrice": cost_price,
                "currentPrice": current_price,
                "lastAction": "BUY" if net_qty > 0 else "SELL",
                "securityId": str(p.get("securityId", "")),
                "exchangeSegment": str(p.get("exchangeSegment", "NSE_EQ")),
            }

    # --- Live LTP Fetching Loop ---
    # We try 3 sources in order:
    # 1. Dhan Native Market Feed (Bulk)
    # 2. Fyers Data Service (Port 8002)
    # 3. Yahoo Finance (Fallback)

    # 1. Try Dhan Native LTP first (Bulk)
    instruments_to_fetch = []
    for h in holdings.values():
        if h.get("securityId") and h.get("exchangeSegment"):
            instruments_to_fetch.append({
                "exchangeSegment": h["exchangeSegment"],
                "securityId": h["securityId"]
            })

    dhan_prices = {}
    if instruments_to_fetch:
        # CRITICAL: Do NOT pass client_id - Dhan /marketfeed/ltp endpoint doesn't need it and returns error 810 if provided
        dhan_prices = _get_dhan_ltps(
            token, instruments_to_fetch)
        for h in holdings.values():
            sid = h.get("securityId")
            if sid in dhan_prices:
                h["currentPrice"] = float(f"{dhan_prices[sid]:.2f}")
                h["source"] = "dhan"

    # 2. Yahoo Finance (Primary Reliability Backup)
    # We use YF before Fyers because YF is often more stable for weekend/off-hours closing prices
    for sym, h in holdings.items():
        if h.get("source") != "dhan":
            # If Dhan Market Feed didn't provide a REAL live price, try YF
            try:
                import yfinance as yf
                yf_sym = sym if "." in sym else f"{sym}.NS"
                ticker_obj = yf.Ticker(yf_sym)
                yf_price = 0.0
                try:
                    yf_price = float(ticker_obj.fast_info['lastPrice'])
                except:
                    hist = ticker_obj.history(period="1d")
                    yf_price = float(hist["Close"].iloc[-1]
                                     ) if not hist.empty else 0.0

                if yf_price > 0:
                    # Verification: If YF price matches avgPrice exactly, it might be stale,
                    # but we'll accept it for now if it's our first real source.
                    h["currentPrice"] = float(f"{yf_price:.2f}")
                    h["source"] = "yahoo"
                    logger.debug(
                        f"[get_live_portfolio] YF LTP for {sym}: {yf_price}")
            except Exception as yf_err:
                logger.debug(
                    f"[get_live_portfolio] YF fetch failed for {sym}: {yf_err}")

    # 3. Fyers Data Service (Secondary Fallback)
    for sym, h in holdings.items():
        if h.get("source") not in ("dhan", "yahoo"):
            ltp = _get_fyers_ltp(sym)
            if ltp is not None and ltp > 0:
                # If LTP matches avgPrice exactly, it's often a mock-service placeholder
                if abs(ltp - float(h.get("avgPrice", 0))) < 0.001:
                    logger.debug(
                        f"[get_live_portfolio] Fyers returned price matching avgPrice for {sym}, skipping.")
                    continue
                h["currentPrice"] = float(f"{ltp:.2f}")
                h["source"] = "fyers"

    # --- FINAL TODAY_GAIN CALCULATION ---
    # Now that we have the best possible LTP in currentPrice, calculate MTM for holdings.
    for sym, h in holdings.items():
        qty = int(h.get("quantity", 0))
        if not h.get("inPositions") and qty > 0:
            cur = float(h.get("currentPrice") or 0)
            cls = float(h.get("closePrice") or cur)
            if cur > 0 and cls > 0:
                mtm = (cur - cls) * qty
                today_gain += mtm
                logger.debug(
                    f"[get_live_portfolio] Added MTM for {sym}: {mtm:.2f} (cur={cur}, cls={cls})")

    equity_value = sum((float(h["currentPrice"]) or float(
        h["avgPrice"])) * int(h["quantity"]) for h in holdings.values())
    total_value = float(cash) + float(equity_value)
    starting_balance = float(sod) if float(sod) > 0 else total_value

    # --- INVESTED VALUE: sum of (avgPrice × qty) for every holding = Dhan's "Investment" column ---
    invested_value = 0.0
    for h in holdings_list:
        qty = int(h.get("availableQty") or h.get("totalQty") or 0)
        avg = 0.0
        for _avg_key in ("avgCostPrice", "avgCost", "costPrice", "buyAvg", "averagePrice"):
            val = h.get(_avg_key)
            if val is not None:
                try:
                    avg = float(val)
                    if avg > 0:
                        break
                except (TypeError, ValueError):
                    continue
        invested_value: float = invested_value + float(avg * qty)

    # --- PORTFOLIO HISTORY: rolling snapshots for the performance chart ---
    global _portfolio_histories
    import datetime

    # Initialize history for this token if not exists
    if token not in _portfolio_histories:
        _portfolio_histories[token] = []

    snapshot = {
        "time": datetime.datetime.now().strftime("%H:%M"),
        "value": float(f"{total_value:.2f}"),
    }
    _portfolio_histories[token].append(snapshot)
    if isinstance(_portfolio_histories[token], list) and len(_portfolio_histories[token]) > _MAX_HISTORY_POINTS:
        _portfolio_histories[token] = _portfolio_histories[token][-_MAX_HISTORY_POINTS:]

    result = {
        "totalValue": float(f"{total_value:.2f}"),
        "cash": float(f"{cash:.2f}"),
        "startingBalance": float(f"{starting_balance:.2f}"),
        "investedValue": float(f"{invested_value:.2f}"),
        "todayGain": float(f"{today_gain:.2f}"),
        "portfolioHistory": list(_portfolio_histories[token]),
        "holdings": holdings,
        "tradeLog": [],
    }
    logger.info(
        f"[get_live_portfolio] Final portfolio: totalValue={result['totalValue']}, investedValue={result['investedValue']}, todayGain={result['todayGain']}, holdings={len(holdings)}, symbols={list(holdings.keys())}")
    if use_cache and token:
        _portfolio_cache[token] = result
        _portfolio_cache_times[token] = time.time()
    return result


def get_live_portfolio_with_creds(client_id: str, access_token: str) -> Optional[Dict]:
    """Compatibility wrapper for get_live_portfolio with explicit credentials."""
    return get_live_portfolio(access_token=access_token, client_id=client_id)


def get_live_trades(limit: int = 50, access_token: Optional[str] = None, client_id: Optional[str] = None) -> List[Dict]:
    """Dhan doesn't expose trade history in same API; return empty or derive from positions."""
    return []


# ---------------------------------------------------------------------------
# DhanAPIClient class for web_backend.py / live_executor.py (same env, same API)
# ---------------------------------------------------------------------------

class DhanAPIClient:
    """Dhan API client used by live_executor and web_backend. Uses backend/hft2/env for credentials."""

    def __init__(self, client_id: str, access_token: str):
        _load_env()
        self.client_id = client_id
        self.access_token = access_token
        if not self.access_token:
            raise ValueError("DHAN_ACCESS_TOKEN required")

    def validate_connection(self) -> Dict[str, Any]:
        """Verify connection and return detailed status with specific error messages."""
        fund = fetch_fund_limit(self.access_token, client_id=self.client_id)
        if fund is not None and isinstance(fund, dict):
            if fund.get("status") == "failure":
                code = fund.get("http_code")
                error_info = fund.get("error", {})

                if code == 401:
                    error_type = error_info.get("errorType", "Unknown") if isinstance(
                        error_info, dict) else "Unknown"
                    error_code = error_info.get(
                        "errorCode", "DH-901") if isinstance(error_info, dict) else "DH-901"
                    error_msg = error_info.get("errorMessage", "Invalid credentials") if isinstance(
                        error_info, dict) else str(error_info)

                    return {
                        "connected": False,
                        "error": "Authentication Failed",
                        "code": 401,
                        "message": f"{error_msg} (Type: {error_type}, Code: {error_code}). "
                        f"Please go to Settings → Demat Account and re-link your Dhan account with fresh credentials.",
                        "error_details": error_info
                    }
                elif code == 403:
                    return {"connected": False, "error": "Forbidden", "code": 403, "message": "Access denied. Check if your Dhan account has API access enabled."}
                elif code >= 500:
                    return {"connected": False, "error": "Dhan API Server Error", "code": code, "message": "Dhan API is temporarily unavailable. Please try again in a few moments."}
                else:
                    return {"connected": False, "error": "API Failure", "code": code, "message": fund.get("remarks") or "Unknown error"}
            return {"connected": True, "error": None, "code": 200}
        return {"connected": False, "error": "Network Error", "code": 500, "message": "Failed to reach Dhan API"}

    def get_funds(self) -> Dict[str, Any]:
        """Return fund limit dict (availabelBalance, sodLimit, etc.)."""
        fund = fetch_fund_limit(self.access_token, client_id=self.client_id)
        if fund is not None and isinstance(fund, dict):
            return fund
        return {}

    def get_holdings(self) -> List[Dict]:
        """Return raw Dhan holdings list (tradingSymbol, totalQty, avgCostPrice, etc.)."""
        return fetch_holdings(self.access_token, client_id=self.client_id)

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """LTP/quote for symbol. Not implemented here; returns None."""
        return None

    def place_order(self, **kwargs: Any) -> Any:
        """Place order via Dhan (MARKET or LIMIT orders)."""
        symbol = kwargs.get("symbol", "")
        side = (kwargs.get("side") or "BUY").upper()
        quantity = int(kwargs.get("quantity", 0))
        order_type = (kwargs.get("order_type") or "MARKET").upper()
        price = kwargs.get("price")

        if not symbol or quantity <= 0:
            return None

        return place_dhan_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=float(price) if price is not None else 0.0,
            access_token=self.access_token,
            client_id=self.client_id,
        )

    def get_orders(self) -> List[Dict]:
        """Fetch orders. Stub; implement with Dhan orders API if needed."""
        return []

    def get_market_status(self) -> Optional[Dict]:
        """Market status. Stub."""
        return None

    def get_profile(self) -> Optional[Dict]:
        """User profile. Stub."""
        return None

    def is_market_open(self) -> bool:
        """Stub; assume open during market hours if needed."""
        return True

    def get_security_id(self, ticker: str) -> Optional[str]:
        """Get security ID for a ticker symbol.

        Args:
            ticker: Trading symbol (e.g., 'TATAMOTORS.NS', 'RELIANCE.NS')

        Returns:
            Security ID string or None if not found
        """
        try:
            # Clean ticker symbol - remove .NS suffix if present
            sym_clean = ticker.replace('.NS', '').replace('.BO', '')

            # Use the existing resolution function
            security_id, _ = _resolve_dhan_security_id(sym_clean)

            if security_id:
                logger.info(f"Found security ID for {ticker}: {security_id}")
            else:
                logger.warning(f"Security ID not found for {ticker}")

            return security_id

        except Exception as e:
            logger.error(f"Error getting security ID for {ticker}: {e}")
            return None


# Cache for Dhan instruments to avoid repeated downloads
_dhan_instruments_cache: Dict = {}
_dhan_instruments_cache_ts: float = 0.0
_DHAN_INSTRUMENTS_TTL: float = 3600.0  # 1 hour


def _fetch_dhan_instruments() -> Dict[str, Dict]:
    """Download and cache Dhan compact instruments CSV to resolve security IDs by trading symbol."""
    global _dhan_instruments_cache, _dhan_instruments_cache_ts

    # Force cache refresh if it contains invalid "ALL" exchange segments
    if (_dhan_instruments_cache and
            any(info.get("exchange_segment") == "ALL_EQ" for info in _dhan_instruments_cache.values())):
        logger.warning(
            "[_fetch_dhan_instruments] Clearing corrupted cache with 'ALL' segments")
        _dhan_instruments_cache = {}
        _dhan_instruments_cache_ts = 0

    if _dhan_instruments_cache and (time.time() - _dhan_instruments_cache_ts) < _DHAN_INSTRUMENTS_TTL:
        return _dhan_instruments_cache
    try:
        import urllib.request
        import csv
        import io
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        with urllib.request.urlopen(url, timeout=15) as r:
            content = r.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(content))
        instruments: Dict[str, Dict] = {}
        for row in reader:
            sym = str(row.get("SEM_TRADING_SYMBOL") or row.get(
                "TRADING_SYMBOL") or "").strip().upper()
            seg = str(row.get("SEM_EXM_EXCH_ID") or row.get(
                "EXCH_ID") or "NSE").strip().upper()
            sid = str(row.get("SEM_SMST_SECURITY_ID")
                      or row.get("SECURITY_ID") or "").strip()

            # Fix: Handle "ALL" exchange segment - treat as NSE
            if seg == "ALL":
                seg = "NSE"

            # Only accept valid exchanges
            if sym and sid and seg in ("NSE", "BSE"):
                key = f"{seg}:{sym}"
                instruments[key] = {"securityId": sid,
                                    "exchange_segment": f"{seg}_EQ"}
                if sym not in instruments:
                    instruments[sym] = {"securityId": sid,
                                        "exchange_segment": f"{seg}_EQ"}
        _dhan_instruments_cache = instruments
        _dhan_instruments_cache_ts = time.time()
        logger.info("Dhan instruments cache loaded: %d symbols",
                    len(instruments))
    except Exception as e:
        logger.warning("Failed to load Dhan instruments CSV: %s", e)
    return _dhan_instruments_cache


def _resolve_dhan_security_id(sym_clean: str) -> tuple:
    """Resolve Dhan securityId for a trading symbol. Returns (security_id, exchange_segment) or (None, 'NSE_EQ')."""
    instruments = _fetch_dhan_instruments()

    # Debug logging to see what we're getting
    logger.debug(f"[_resolve_dhan_security_id] Looking up: {sym_clean}")
    logger.debug(
        f"[_resolve_dhan_security_id] Available instruments count: {len(instruments)}")

    # Try NSE first, then BSE
    for prefix in ("NSE", "BSE"):
        key = f"{prefix}:{sym_clean}"
        if key in instruments:
            info = instruments[key]
            sec_id = info.get("securityId")
            exch_seg = info.get("exchange_segment", f"{prefix}_EQ")
            logger.debug(
                f"[_resolve_dhan_security_id] Found {key}: secId={sec_id}, segment={exch_seg}")
            # Validate exchange segment - must be valid format
            if exch_seg and exch_seg not in ("NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO", "NSE_CD", "BSE_CD"):
                logger.warning(
                    f"[_resolve_dhan_security_id] Invalid exchange segment '{exch_seg}' for {sym_clean}, using {prefix}_EQ")
                exch_seg = f"{prefix}_EQ"
            return sec_id, exch_seg

    # Try plain symbol
    if sym_clean in instruments:
        info = instruments[sym_clean]
        sec_id = info.get("securityId")
        exch_seg = info.get("exchange_segment", "NSE_EQ")
        logger.debug(
            f"[_resolve_dhan_security_id] Found plain {sym_clean}: secId={sec_id}, segment={exch_seg}")
        # Validate exchange segment
        if exch_seg and exch_seg not in ("NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO", "NSE_CD", "BSE_CD"):
            logger.warning(
                f"[_resolve_dhan_security_id] Invalid exchange segment '{exch_seg}' for {sym_clean}, using NSE_EQ")
            exch_seg = "NSE_EQ"
        return sec_id, exch_seg

    logger.warning(f"[_resolve_dhan_security_id] Not found: {sym_clean}. Available symbols: {list(instruments.keys())[:20]}")
    return None, "NSE_EQ"


def place_dhan_order(symbol: str, side: str, quantity: int, order_type: str = "MARKET", price: float = 0.0, product_type: str = "CNC", trigger_price: Optional[float] = None, access_token: Optional[str] = None, client_id: Optional[str] = None, security_id: Optional[str] = None, exchange_segment: Optional[str] = None, is_short_sell: bool = False) -> Optional[Dict]:
    """Place MARKET or LIMIT order via Dhan.
    access_token and client_id must be provided (per-user credentials from MongoDB).
    security_id and exchange_segment skip the symbol resolution if provided.
    
    Args:
        is_short_sell: If True and side is SELL with MIS product type, this is a short-sell order (sell first, buy later)
    """
    token = access_token
    cid = client_id
    if not token or not cid:
        return None
    
    # Log short-sell configuration
    if is_short_sell and side == "SELL" and product_type == "MIS":
        logger.info(f"🔴 SHORT-SELL ORDER DETECTED: {symbol} | Qty: {quantity} | Product: MIS (Intraday)")
        logger.info(f"   This will open a short position that must be squared off by buying before market close")

    # Symbol from frontend e.g. RELIANCE.NS or TCS.NS; Dhan uses RELIANCE, TCS
    sym_clean = (symbol or "").replace(
        ".NS", "").replace(".BO", "").strip().upper()

    # Use provided security_id/segment, or resolve them
    sec_id = security_id
    exch_seg = exchange_segment or "NSE_EQ"

    # CRITICAL: Validate and sanitize exchange_segment BEFORE using it
    # Dhan API rejects invalid segments like "ALL" or "ALL_EQ"
    if exch_seg in ("ALL", "ALL_EQ"):
        logger.warning(
            f"[place_dhan_order] Received invalid exchange_segment '{exch_seg}' from request, overriding to 'NSE_EQ' for {symbol}")
        exch_seg = "NSE_EQ"

    if not sec_id:
        sec_id, resolved_exch_seg = _resolve_dhan_security_id(sym_clean)

        # CRITICAL FIX: Override invalid "ALL" or "ALL_EQ" exchange segments from instrument data
        if resolved_exch_seg in ("ALL", "ALL_EQ") or not resolved_exch_seg:
            logger.warning(
                f"[place_dhan_order] Overriding invalid exchange segment '{resolved_exch_seg}' to 'NSE_EQ' for {symbol}")
            resolved_exch_seg = "NSE_EQ"

        # Only use resolved values if sec_id was not provided
        if not sec_id:
            exch_seg = resolved_exch_seg

    if not sec_id:
        # Fallback to current holdings/positions
        holdings_list = fetch_holdings(token, client_id=cid)
        for h in holdings_list:
            if str(h.get("tradingSymbol", "")).upper() == sym_clean:
                sec_id = str(h.get("securityId", ""))
                break
        if not sec_id:
            for p in fetch_positions(token, client_id=cid):
                if str(p.get("tradingSymbol", "")).upper() == sym_clean:
                    sec_id = str(p.get("securityId", ""))
                    exch_seg = str(p.get("exchangeSegment")
                                   or p.get("exchange") or "NSE_EQ")
                    break

    if not sec_id:
        logger.warning("Could not resolve securityId for %s (clean: %s). Available holdings: %s", symbol, sym_clean, [
                       h.get("tradingSymbol") for h in holdings_list] if 'holdings_list' in locals() else "none")
        return {"status": "failure", "errorType": "Input_Exception", "errorCode": "DH-905", "errorMessage": f"Could not resolve security ID for {symbol}. Please ensure the symbol is valid and market is open."}

    # Validate parameters before building request
    if not sym_clean:
        logger.error("Symbol is empty after cleaning: %s", symbol)
        return {"status": "failure", "errorType": "Input_Exception", "errorCode": "DH-905", "errorMessage": "Invalid or empty symbol provided"}

    if quantity <= 0:
        logger.error("Invalid quantity: %d for %s", quantity, symbol)
        return {"status": "failure", "errorType": "Input_Exception", "errorCode": "DH-905", "errorMessage": "Quantity must be greater than 0"}

    if side not in ("BUY", "SELL"):
        logger.error("Invalid transaction type: %s for %s", side, symbol)
        return {"status": "failure", "errorType": "Input_Exception", "errorCode": "DH-905", "errorMessage": "Side must be BUY or SELL"}

    if order_type.upper() not in ("MARKET", "LIMIT"):
        logger.error("Invalid order type: %s for %s", order_type, symbol)
        return {"status": "failure", "errorType": "Input_Exception", "errorCode": "DH-905", "errorMessage": "Order type must be MARKET or LIMIT"}

    # Build request body - only include fields that are needed
    # Dhan API requires specific fields and rejects invalid values
    body = {
        "dhanClientId": cid,
        "correlationId": f"hft_{int(time.time()*1000)}",
        "transactionType": side.upper(),
        "exchangeSegment": exch_seg,
        "productType": product_type,
        "orderType": order_type.upper(),
        "validity": "DAY",
        "tradingSymbol": sym_clean,
        "securityId": str(sec_id),
        "quantity": int(quantity),
        "disclosedQuantity": 0,
        "afterMarketOrder": False,
    }

    # Only add price for LIMIT orders (MARKET orders should not have price field)
    if order_type.upper() == "LIMIT":
        body["price"] = float(price)

    # Add trigger price only for SL orders
    if trigger_price and trigger_price > 0:
        body["triggerPrice"] = float(trigger_price)
    else:
        body["triggerPrice"] = 0.0

    # BO/CO specific fields (set to 0 for regular CNC/MIS orders)
    body["boProfitValue"] = 0
    body["boStopLossValue"] = 0

    # Log full request payload for debugging DH-905 errors
    logger.info(
        f"[place_dhan_order] Placing {order_type} {side} for {symbol}")
    logger.info(
        f"  → Clean Symbol: {sym_clean}")
    logger.info(
        f"  → Security ID: {sec_id}")
    logger.info(
        f"  → Exchange Segment: {exch_seg}")
    logger.info(
        f"  → Quantity: {quantity}")
    logger.info(
        f"  → Price: {price} (0.0 for MARKET, {price} for LIMIT)")
    logger.info(
        f"  → Order Type in Body: {body['orderType']}")

    # CRITICAL: Log exactly what fields are in the body
    logger.info(f"[place_dhan_order] Request body fields: {list(body.keys())}")
    if 'price' in body:
        logger.info(f"  → Price field PRESENT in body: {body['price']}")
    else:
        logger.info(
            f"  → Price field ABSENT from body (correct for MARKET orders)")

    logger.debug(f"[place_dhan_order] Full request body: {body}")
    out = _dhan_request("POST", "/orders", token, client_id=cid, data=body)

    if isinstance(out, dict) and out.get("status") == "failure":
        logger.error(
            f"[place_dhan_order] Dhan API failure for {side} {sym_clean}: {out}")
        return out

    if out is None:
        logger.error(
            f"[place_dhan_order] Dhan API returned empty response for {side} {sym_clean}")
        return {"status": "failure", "remarks": "Empty response from broker"}

    logger.info(
        f"[place_dhan_order] Dhan response for {side} {sym_clean}: {out}")
    return out if isinstance(out, dict) else None


def place_order_market(symbol: str, side: str, quantity: int, product_type: str = "CNC", trigger_price: Optional[float] = None, access_token: Optional[str] = None, client_id: Optional[str] = None) -> Optional[Dict]:
    """Legacy wrapper for backward compatibility."""
    return place_dhan_order(
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type="MARKET",
        product_type=product_type,
        trigger_price=trigger_price,
        access_token=access_token,
        client_id=client_id
    )
