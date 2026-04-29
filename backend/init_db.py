import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hft2", "data", "trading.db")

# Ensure folder exists
os.makedirs(os.path.join(BASE_DIR, "hft2", "data"), exist_ok=True)


def init_db():
    print("INIT_DB PATH:", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        status TEXT,
        current_price REAL,
        predicted_price REAL,
        predicted_return REAL,
        action TEXT,
        confidence REAL,
        error TEXT,
        timestamp TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        predicted_action TEXT,
        user_feedback TEXT,
        actual_return REAL,
        timestamp TEXT
    )
    """)

    cursor.execute("""
CREATE TABLE IF NOT EXISTS portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id TEXT,
    symbol TEXT,
    shares INTEGER,
    avg_price REAL,
    current_price REAL
)
""")
    
    cursor.execute("""
CREATE TABLE IF NOT EXISTS api_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT,
    request_data TEXT,
    response_data TEXT,
    success INTEGER,
    error TEXT,
    timestamp TEXT
)
""")

    conn.commit()
    conn.close()

    print("✅ Database initialized with tables.")


if __name__ == "__main__":
    init_db()