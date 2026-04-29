"""
Minimal Dhan API client for the main backend (Render / single-service deploy).
Uses only os.environ - no env file. Set DHAN_ACCESS_TOKEN and DHAN_CLIENT_ID in Render env.
No Fyers dependency; currentPrice comes from Dhan position data (unrealized P&L).
"""
import os
import logging
import urllib.request
import urllib.error
import json
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def get_dhan_token() -> Optional[str]:
    """Return token stripped of whitespace (Render env can have trailing newline when pasted)."""
    raw = os.environ.get("DHAN_ACCESS_TOKEN") or os.environ.get(
        "DHAN_ACCESS_TOKEN_KEY") or ""
    t = raw.strip()
    return t if t else None


def get_dhan_client_id() -> Optional[str]:
    """Return client ID stripped (must match the account that generated the token)."""
    raw = os.environ.get("DHAN_CLIENT_ID") or ""
    t = raw.strip()
    return t if t else None


def _dhan_request(method: str, path: str, token: str, client_id: Optional[str] = None, **kwargs: Any) -> Any:
    url = f"https://api.dhan.co/v2{path}"
    headers = {"Content-Type": "application/json", "access-token": token}
    if client_id:
        headers["dhanClientId"] = str(client_id)
    req = urllib.request.Request(url, method=method, headers=headers)
    if kwargs.get("data"):
        req.data = json.dumps(kwargs["data"]).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode()
            out = json.loads(raw)
            # Some brokers wrap in {"data": ...} or {"status": "success", "data": ...}
            if isinstance(out, dict) and "data" in out:
                out = out["data"]
            return out
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:500]
        except Exception:
            pass
        logger.warning("Dhan API %s %s HTTP %s: %s",
                       method, path, e.code, body or str(e))
        if e.code == 401:
            raise RuntimeError(
                "Dhan token invalid or expired (DH-901). "
                "Generate a new token at web.dhan.co → My Profile → Access DhanHQ APIs, "
                "then set DHAN_ACCESS_TOKEN in Render Environment. Tokens expire (e.g. 24h)."
            ) from e
        raise RuntimeError(
            f"Dhan API {path}: HTTP {e.code} - {body or str(e)}") from e
    except Exception as e:
        logger.warning("Dhan API %s %s failed: %s", method, path, e)
        raise


def _fetch_fund_limit(token: str, client_id: Optional[str] = None) -> Optional[Dict]:
    out = _dhan_request("GET", "/fundlimit", token, client_id=client_id)
    return out if isinstance(out, dict) else None


def _fetch_holdings(token: str, client_id: Optional[str] = None) -> List[Dict]:
    out = _dhan_request("GET", "/holdings", token, client_id=client_id)
    if isinstance(out, list):
        return out
    if isinstance(out, dict) and "data" in out and isinstance(out["data"], list):
        return out["data"]
    return []


def _fetch_positions(token: str, client_id: Optional[str] = None) -> List[Dict]:
    out = _dhan_request("GET", "/positions", token, client_id=client_id)
    if isinstance(out, list):
        return out
    if isinstance(out, dict) and "data" in out and isinstance(out["data"], list):
        return out["data"]
    return []


def _nse_symbol(s: str, segment: str = "") -> str:
    """Deprecated: Use symbol_utils.normalize_symbol() instead."""
    import sys
    from pathlib import Path
    # Add backend/hft2/backend to path for symbol_utils import
    hft2_backend = Path(__file__).parent / "hft2" / "backend"
    if hft2_backend.exists():
        sys.path.insert(0, str(hft2_backend))

    try:
        from symbol_utils import normalize_symbol
        return normalize_symbol(s, segment)
    except ImportError:
        # Fallback to old logic if symbol_utils not available
        if not s:
            return s
        if "NSE" in segment or segment == "NSE_EQ" or not segment:
            return f"{s}.NS" if "." not in s else s
        if "BSE" in segment:
            return f"{s}.BO" if "." not in s else s
        return s


def get_live_portfolio() -> Optional[Dict]:
    """Build portfolio dict for HFT dashboard from Dhan. Uses env only (Render-safe)."""
    token = get_dhan_token()
    if not token:
        return None
    client_id = get_dhan_client_id()
    try:
        fund = _fetch_fund_limit(token, client_id)
        holdings_list = _fetch_holdings(token, client_id)
        positions_list = _fetch_positions(token, client_id)
    except Exception as e:
        logger.info("Dhan API error (check token/network): %s", e)
        raise

    cash = 0.0
    if fund and "availabelBalance" in fund:
        cash = float(fund["availabelBalance"])
    elif fund and "availableBalance" in fund:
        cash = float(fund["availableBalance"])
    sod = float(fund.get("sodLimit", 0) or 0) if fund else 0

    holdings: Dict[str, Dict] = {}
    for h in holdings_list:
        sym = _nse_symbol(str(h.get("tradingSymbol", "")),
                          str(h.get("exchange", "NSE_EQ")))
        qty = int(h.get("availableQty") or h.get("totalQty") or 0)
        if qty <= 0 or not sym:
            continue
        avg = float(h.get("avgCostPrice") or 0)
        holdings[sym] = {
            "symbol": sym,
            "quantity": qty,
            "avgPrice": avg,
            "currentPrice": avg,
            "lastAction": "BUY",
        }

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
        current_price = cost_price + \
            (unrealized / net_qty) if (net_qty and cost_price) else buy_avg
        if sym in holdings:
            old = holdings[sym]
            tot_qty = old["quantity"] + net_qty
            old_avg = old["avgPrice"] * old["quantity"] + cost_price * net_qty
            holdings[sym]["quantity"] = tot_qty
            holdings[sym]["avgPrice"] = old_avg / \
                tot_qty if tot_qty else old["avgPrice"]
            holdings[sym]["currentPrice"] = round(current_price, 2)
        else:
            holdings[sym] = {
                "symbol": sym,
                "quantity": net_qty,
                "avgPrice": cost_price,
                "currentPrice": round(current_price, 2),
                "lastAction": "BUY" if net_qty > 0 else "SELL",
            }

    equity_value = sum(
        (h.get("currentPrice") or h["avgPrice"]) * h["quantity"] for h in holdings.values())
    total_value = cash + equity_value
    starting_balance = sod if sod > 0 else total_value

    return {
        "totalValue": round(total_value, 2),
        "cash": round(cash, 2),
        "startingBalance": round(starting_balance, 2),
        "holdings": holdings,
        "tradeLog": [],
    }
