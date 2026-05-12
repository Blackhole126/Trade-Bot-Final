import os
import sqlite3
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SAMRUDDHI_DB = os.path.join(
    BASE_DIR,
    "hft2",
    "data",
    "samruddhi_memory.db"
)

TRADING_DB = os.path.join(
    BASE_DIR,
    "data",
    "trading.db"
)

def sync_trade_to_trading_db(
    symbol,
    action,
    quantity,
    price
):

    sam_conn = sqlite3.connect(SAMRUDDHI_DB)
    os.makedirs(os.path.dirname(TRADING_DB), exist_ok=True)
    trade_conn = sqlite3.connect(TRADING_DB)

    sam_cursor = sam_conn.cursor()
    trade_cursor = trade_conn.cursor()

    # Create bridge table if not exists
    trade_cursor.execute("""
    CREATE TABLE IF NOT EXISTS bridged_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        action TEXT,
        quantity REAL,
        price REAL,
        timestamp TEXT
    )
    """)

    trade_cursor.execute("""
    INSERT INTO bridged_trades (
        symbol,
        action,
        quantity,
        price,
        timestamp
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        symbol,
        action,
        quantity,
        price,
        datetime.utcnow().isoformat()
    ))

    trade_conn.commit()

    sam_conn.close()
    trade_conn.close()

    print(
        f"[PHASE 7] Bridged trade -> trading.db: "
        f"{symbol} {action}",
        flush=True
    )