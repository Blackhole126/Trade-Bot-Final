#!/usr/bin/env python3
"""
Dhan Account Sync Service - Real-time background sync with Dhan account
"""

import os
import json
import sqlite3
import asyncio
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
try:
    from pathlib import Path
    from dotenv import load_dotenv
    _curr = Path(__file__).resolve().parent
    _parent = _curr.parent
    for _p in [_curr, _parent]:
        for _f in ["env", ".env"]:
            _path = _p / _f
            if _path.exists():
                load_dotenv(_path)
                break
except Exception:
    pass

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DhanSyncService:
    """Background service to sync portfolio with Dhan account in real-time"""

    def __init__(self, username: str, client_id: str, access_token: str, sync_interval: int = 300):
        """
        Initialize Dhan sync service for a specific user.
        Credentials must come from MongoDB (per-user demat) — NOT from env vars.

        Args:
            username: Username for session isolation
            client_id: Dhan client ID from user's linked demat (MongoDB)
            access_token: Dhan access token from user's linked demat (MongoDB)
            sync_interval: Sync interval in seconds (default: 300 seconds)
        """
        if not client_id or not access_token:
            raise ValueError(
                "Dhan credentials required. Link your demat account in Settings → Demat first."
            )
        self.username = username
        self.sync_interval = sync_interval
        self.client_id = client_id
        self.access_token = access_token
        self.is_running = False
        self.last_sync_time = None
        self.last_known_balance = 0.0

        # Create user-specific data directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        self.user_data_dir = os.path.join(
            project_root, 'data', 'users', username)
        os.makedirs(self.user_data_dir, exist_ok=True)

        logger.debug(
            f"Dhan Sync Service initialized with {sync_interval}s interval")

    def get_dhan_funds(self) -> Optional[Dict[str, Any]]:
        """Get current funds from Dhan API"""
        try:
            headers = {
                'access-token': self.access_token,
                'dhanClientId': str(self.client_id),
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            # First try fundlimit endpoint as it provides accurate real-time balance with zero parameters
            try:
                response = requests.get(
                    "https://api.dhan.co/v2/fundlimit",
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    funds_data = response.json()
                    logger.debug(
                        f"Fetched funds data from fundlimit: {funds_data}")
                    return funds_data
                else:
                    logger.warning(
                        f"Fundlimit endpoint returned status {response.status_code}: {response.text}")
            except Exception as fundlimit_error:
                logger.error(
                    f"Fundlimit endpoint failed: {fundlimit_error}")

            # Fallback to profile endpoint
            try:
                response = requests.get(
                    "https://api.dhan.co/v2/profile",
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    profile_data = response.json()
                    logger.debug(f"Fetched profile data: {profile_data}")
                    # Convert profile data to funds-like structure
                    return {
                        "availableBalance": profile_data.get("availableBalance", 0.0),
                        "marginUsed": profile_data.get("marginUsed", 0.0),
                        "totalBalance": profile_data.get("totalBalance", 0.0),
                        "clientName": profile_data.get("clientName", "Unknown"),
                        "clientId": profile_data.get("clientId", self.client_id)
                    }
            except Exception as profile_error:
                logger.error(
                    f"Profile endpoint failed for funds: {profile_error}")

            return None

        except Exception as e:
            logger.error(f"Error fetching funds from Dhan API: {e}")
            return None

    def get_dhan_holdings(self) -> Optional[list]:
        """Get current holdings from Dhan API"""
        try:
            headers = {
                'access-token': self.access_token,
                'dhanClientId': str(self.client_id),
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            try:
                response = requests.get(
                    "https://api.dhan.co/v2/holdings",
                    headers=headers,
                    timeout=10
                )
            except Exception as holdings_error:
                logger.debug(f"Holdings endpoint failed: {holdings_error}")
                # Return empty list for any holdings error
                return []

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Dhan holdings API returned status {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching holdings from Dhan API: {e}")
            return []

    def update_database(self, cash_amount: float, holdings: list) -> bool:
        """Update the database with new portfolio data"""
        try:
            # Use user-specific database path
            db_path = os.path.join(self.user_data_dir, 'trading.db')

            if not os.path.exists(db_path):
                logger.error(f"Database not found at {db_path}")
                return False

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Only update cash if it's a valid, non-zero amount
            # This prevents resetting balance to 0 when API fails
            effective_cash = cash_amount if cash_amount > 0 else None

            if effective_cash is not None:
                cursor.execute("""
                    UPDATE portfolios 
                    SET cash = ?, last_updated = ?
                    WHERE mode = 'live'
                """, (effective_cash, datetime.now().isoformat()))
            else:
                # Don't update cash if it's zero or invalid - keep existing value
                cursor.execute("""
                    UPDATE portfolios 
                    SET last_updated = ?
                    WHERE mode = 'live'
                """, (datetime.now().isoformat(),))

            if cursor.rowcount == 0:
                # Insert new live portfolio if it doesn't exist
                # Only use cash_amount if it's valid and non-zero, otherwise use default
                # Default starting balance
                effective_cash = cash_amount if cash_amount > 0 else 50000.0
                # Default starting balance
                effective_starting_balance = cash_amount if cash_amount > 0 else 50000.0
                cursor.execute("""
                    INSERT INTO portfolios (mode, cash, starting_balance, realized_pnl, unrealized_pnl, last_updated)
                    VALUES ('live', ?, ?, 0.0, 0.0, ?)
                """, (effective_cash, effective_starting_balance, datetime.now().isoformat()))
                if cash_amount <= 0:
                    logger.info(
                        f"Created new live portfolio with default cash (API returned invalid balance: Rs.{cash_amount:.2f})")
                else:
                    logger.info(
                        f"Created new live portfolio with cash from Dhan: Rs.{effective_cash:.2f}")

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Database update failed: {e}")
            return False

    def update_json_files(self, cash_amount: float, holdings: list) -> bool:
        """Update JSON files with new portfolio data"""
        try:
            # Import symbol normalization utility
            from symbol_utils import normalize_symbol

            # Prepare Holdings data with proper normalization
            holdings_dict = {}
            for holding in holdings:
                raw_symbol = holding.get("tradingSymbol", "")
                exchange_segment = holding.get(
                    "exchangeSegment", holding.get("exchange", "NSE_EQ"))
                quantity = int(holding.get("totalQty")
                               or holding.get("availableQty") or 0)
                avg_price = float(holding.get("avgCostPrice")
                                  or holding.get("avgCost") or 0)

                # CRITICAL FIX: Normalize symbol to prevent duplicates
                symbol = normalize_symbol(raw_symbol, exchange_segment)

                if quantity > 0 and symbol:
                    # Check if we already have this symbol - net quantities
                    if symbol in holdings_dict:
                        existing_qty = holdings_dict[symbol]["qty"]
                        existing_avg = holdings_dict[symbol]["avg_price"]

                        # Net the quantities
                        new_total_qty = existing_qty + quantity

                        if abs(new_total_qty) < 1:
                            # Fully squared off - remove
                            logger.info(
                                f"[dhan_sync] Position squared off, removing {symbol}")
                            del holdings_dict[symbol]
                        else:
                            # Calculate weighted average if same direction
                            if (existing_qty > 0 and quantity > 0) or (existing_qty < 0 and quantity < 0):
                                new_avg = (existing_avg * existing_qty +
                                           avg_price * quantity) / new_total_qty
                                holdings_dict[symbol] = {
                                    "qty": new_total_qty,
                                    "avg_price": new_avg,
                                    "last_price": avg_price
                                }
                            else:
                                # Opposite directions - keep existing avg
                                holdings_dict[symbol] = {
                                    "qty": new_total_qty,
                                    "avg_price": existing_avg,
                                    "last_price": avg_price
                                }
                    else:
                        holdings_dict[symbol] = {
                            "qty": quantity,
                            "avg_price": avg_price,
                            "last_price": avg_price
                        }
                        logger.debug(
                            f"[dhan_sync] Added holding: {symbol} (qty={quantity}, avg={avg_price:.2f})")

            # Calculate total holdings value
            total_holdings_value = sum(
                h["qty"] * h["avg_price"] for h in holdings_dict.values()
            )

            # Use user-specific data directory
            data_dir = self.user_data_dir

            # Update portfolio_india_live.json
            # Only use cash_amount if it's valid and non-zero, otherwise keep existing cash
            effective_cash = cash_amount if cash_amount > 0 else self.last_known_balance
            effective_starting_balance = max(
                cash_amount, self.last_known_balance) if cash_amount > 0 else self.last_known_balance
            portfolio_data = {
                "cash": effective_cash,
                "holdings": holdings_dict,
                "starting_balance": effective_starting_balance,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "last_updated": datetime.now().isoformat()
            }

            portfolio_file = os.path.join(
                data_dir, 'portfolio_india_live.json')
            with open(portfolio_file, 'w') as f:
                json.dump(portfolio_data, f, indent=4)

            # Update live_portfolio.json
            # Only use cash_amount if it's valid and non-zero, otherwise keep existing cash
            effective_cash = cash_amount if cash_amount > 0 else self.last_known_balance
            effective_total_value = (cash_amount + total_holdings_value) if cash_amount > 0 else (
                self.last_known_balance + total_holdings_value)
            effective_starting_balance = max(
                cash_amount, self.last_known_balance) if cash_amount > 0 else self.last_known_balance
            live_portfolio_data = {
                "cash": effective_cash,
                "total_value": effective_total_value,
                "starting_balance": effective_starting_balance,
                "holdings": holdings_dict,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "last_updated": datetime.now().isoformat()
            }

            live_portfolio_file = os.path.join(data_dir, 'live_portfolio.json')
            with open(live_portfolio_file, 'w') as f:
                json.dump(live_portfolio_data, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"JSON update failed: {e}")
            return False

    def sync_once(self) -> bool:
        """Perform a single sync operation"""
        try:
            # Get data from Dhan
            funds_data = self.get_dhan_funds()
            holdings_data = self.get_dhan_holdings()

            if funds_data is None:
                logger.warning("Failed to fetch funds data from Dhan")
                return False

            if holdings_data is None:
                holdings_data = []

            # Extract cash balance (tolerant to different key names / typos)
            current_balance = 0.0
            try:
                logger.debug(
                    f"Dhan funds data keys: {list(funds_data.keys()) if isinstance(funds_data, dict) else 'Not a dict'}")

                # Common keys returned by Dhan endpoints (with more comprehensive list)
                possible_keys = [
                    'availableBalance', 'availablebalance', 'available_balance',
                    'sodLimit', 'sodlimit', 'sod_limit',
                    'netBalance', 'netbalance', 'net_balance',
                    'availablecash', 'available_cash', 'availableCash',
                    'netAvailableMargin', 'netAvailableCash',
                    'usableCash', 'usable_cash', 'UsableCash',
                    'cash', 'Cash'
                ]

                for key in possible_keys:
                    if isinstance(funds_data, dict) and key in funds_data:
                        value = funds_data[key]
                        if value is not None:
                            try:
                                current_balance = float(value)
                                logger.debug(
                                    f"Found balance in key '{key}': ₹{current_balance}")
                                break
                            except (ValueError, TypeError):
                                continue

                # If still no balance found, try to find the first numeric value in the dict
                if current_balance == 0.0 and isinstance(funds_data, dict):
                    for k, v in funds_data.items():
                        if isinstance(v, (int, float)) and 'balance' in k.lower():
                            current_balance = float(v)
                            logger.debug(
                                f"Found balance in '{k}' field: ₹{current_balance}")
                            break

                if current_balance == 0.0 and isinstance(funds_data, dict):
                    for k, v in funds_data.items():
                        if isinstance(v, (int, float)) and v > 100:  # Likely a balance amount
                            current_balance = float(v)
                            logger.debug(
                                f"Using first large numeric value from '{k}' field: ₹{current_balance}")
                            break

            except Exception as e:
                logger.error(f"Error extracting balance from funds data: {e}")
                current_balance = 0.0

            # Check if balance changed
            balance_changed = abs(
                current_balance - self.last_known_balance) > 0.01

            if balance_changed:
                logger.info(
                    f"💰 Balance changed: ₹{self.last_known_balance} → ₹{current_balance}")

                # Update database and JSON files
                db_success = self.update_database(
                    current_balance, holdings_data)
                json_success = self.update_json_files(
                    current_balance, holdings_data)

                if db_success and json_success:
                    self.last_known_balance = current_balance
                    self.last_sync_time = datetime.now()
                    logger.debug(
                        f"✅ Portfolio synced successfully: ₹{current_balance}")
                    return True
                else:
                    logger.error("Failed to update portfolio data")
                    return False
            else:
                logger.debug(f"No balance change detected: ₹{current_balance}")
                self.last_sync_time = datetime.now()
                return True

        except Exception as e:
            logger.error(f"Sync operation failed: {e}")
            return False

    async def start_background_sync(self):
        """Start the background sync service"""
        self.is_running = True
        logger.info(
            f"🚀 Starting Dhan sync service (every {self.sync_interval}s)")

        # Initial sync
        self.sync_once()

        while self.is_running:
            try:
                await asyncio.sleep(self.sync_interval)
                if self.is_running:
                    self.sync_once()

            except Exception as e:
                logger.error(f"Error in background sync loop: {e}")
                await asyncio.sleep(5)  # Wait 5 seconds before retrying

    def stop(self):
        """Stop the background sync service"""
        self.is_running = False
        logger.info("🛑 Dhan sync service stopped")


# Global sync services mapping: username -> DhanSyncService
_sync_services: Dict[str, DhanSyncService] = {}
_sync_services_lock = asyncio.Lock()


def get_sync_service(username: str) -> Optional[DhanSyncService]:
    """Get the sync service instance for a specific user."""
    return _sync_services.get(username)


async def start_sync_service(username: str, sync_interval: int = 300) -> Optional[DhanSyncService]:
    """Start the sync service for a specific authenticated user."""
    if not username:
        return None

    # Use a lock to prevent concurrent start/stop issues
    async with _sync_services_lock:
        if username in _sync_services:
            return _sync_services[username]

        try:
            # Fetch per-user demat credentials from MongoDB
            try:
                from hft_auth import get_user_demat
            except ImportError:
                try:
                    from backend.hft2.backend.hft_auth import get_user_demat
                except ImportError:
                    from hft2.backend.hft_auth import get_user_demat

            demat = get_user_demat(username)
            if not demat or not demat.get("client_id") or not demat.get("access_token"):
                logger.warning(
                    f"[sync_service] No demat credentials found for user '{username}' — sync service not started"
                )
                return None

            service = DhanSyncService(
                username=username,
                client_id=demat["client_id"],
                access_token=demat["access_token"],
                sync_interval=sync_interval,
            )
            _sync_services[username] = service
            asyncio.create_task(service.start_background_sync())
            logger.info(
                f"Dhan sync service started for user '{username}' (interval={sync_interval}s)")
            return service
        except Exception as e:
            logger.error(
                f"Failed to start sync service for '{username}': {e}", exc_info=True)
            return None


async def stop_sync_service(username: str = None):
    """Stop sync service(s). If username is None, stops ALL services."""
    async with _sync_services_lock:
        if username:
            if username in _sync_services:
                service = _sync_services.pop(username)
                service.stop()
                logger.info(f"Dhan sync service stopped for user '{username}'")
        else:
            # Stop all
            usernames = list(_sync_services.keys())
            for uname in usernames:
                service = _sync_services.pop(uname)
                service.stop()
            logger.info("All Dhan sync services stopped")


if __name__ == "__main__":
    # Test the sync service - needs proper credentials from MongoDB or env
    async def test_sync():
        logger.info(
            "DhanSyncService test block: requires manual credentials setup.")
        # service = DhanSyncService("test_user", "client_id", "access_token", sync_interval=10)
        # await service.start_background_sync()

    # asyncio.run(test_sync())
