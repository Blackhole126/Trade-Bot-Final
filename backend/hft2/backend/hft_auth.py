"""JWT authentication: login, token creation/verification, user storage in MongoDB."""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Load env early
try:
    from dotenv import load_dotenv
    from pathlib import Path
    import os
    # Check current directory and parent directory for 'env' or '.env'
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

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    import sys as _sys
    print(
        "[CRITICAL] JWT_SECRET environment variable is not set!\n"
        "  Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"\n"
        "  Then add JWT_SECRET=<value> to your Render environment variables.",
        file=_sys.stderr
    )
    # Use a temporary random secret so the process doesn't crash,
    # but tokens won't survive restarts. Set JWT_SECRET in production!
    import secrets as _secrets
    JWT_SECRET = _secrets.token_hex(32)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24h default


def _get_users_collection():
    try:
        from db.mongo_client import get_mongo_db
        db = get_mongo_db("trading")
        return db["users"]
    except Exception as e:
        logger.warning(f"MongoDB users collection unavailable: {e}")
        return None


def hash_password(password: str) -> str:
    """Hash password with bcrypt. Bcrypt has a 72-byte limit, so truncate if needed."""
    import bcrypt
    # Bcrypt has a 72-byte limit - truncate password BEFORE hashing
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # Truncate to 72 bytes
            password_bytes = password_bytes[:72]
    else:
        password_bytes = password
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password with bcrypt. Truncate plain password if longer than 72 bytes."""
    import bcrypt
    try:
        # Bcrypt has a 72-byte limit - truncate password BEFORE verification
        if isinstance(plain, str):
            plain_bytes = plain.encode('utf-8')
            if len(plain_bytes) > 72:
                # Truncate to 72 bytes
                plain_bytes = plain_bytes[:72]
        else:
            plain_bytes = plain
        # Verify password - hash should be bytes or string
        if isinstance(hashed, str):
            hashed_bytes = hashed.encode('utf-8')
        else:
            hashed_bytes = hashed
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


def create_token(sub: str, extra: Optional[dict] = None) -> str:
    import jwt
    payload = {
        "sub": sub,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
    }
    if extra:
        payload.update(extra)
    out = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return out if isinstance(out, str) else out.decode("utf-8")


def decode_token(token: str) -> Optional[dict]:
    import jwt
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username (email). Username is normalized to lowercase."""
    col = _get_users_collection()
    if col is None:
        logger.warning("MongoDB collection unavailable - cannot get user")
        return None
    normalized_username = username.lower().strip()
    logger.debug(f"Looking up user: '{normalized_username}'")
    u = col.find_one({"username": normalized_username})
    if u:
        if "_id" in u:
            u["id"] = str(u["_id"])
        logger.debug(f"User found: {u.get('username')}")
        return u
    else:
        logger.warning(f"User not found: {normalized_username}")
        return None


def create_user(username: str, password: str) -> Optional[dict]:
    """Create a new user. Username is normalized to lowercase."""
    try:
        col = _get_users_collection()
        if col is None:
            logger.warning("MongoDB collection unavailable - cannot create user")
            return None
        normalized_username = username.lower().strip()
        logger.debug(f"Creating user: '{normalized_username}'")
        
        # Check if user already exists
        existing = col.find_one({"username": normalized_username})
        if existing:
            logger.warning(f"Username already exists: {normalized_username}")
            return None  # Username already exists
        
        # Hash password and create user document
        password_hash = hash_password(password)
        doc = {
            "username": normalized_username,
            "password_hash": password_hash,
            "created_at": datetime.utcnow(),
        }
        r = col.insert_one(doc)
        doc["id"] = str(r.inserted_id)
        logger.info(f"User created successfully in MongoDB: {normalized_username} (ID: {doc['id']})")
        
        # Verify the user was actually saved
        verify_user = col.find_one({"username": normalized_username})
        if not verify_user:
            logger.error(f"CRITICAL: User {normalized_username} was not saved to MongoDB after insert_one!")
            return None
        
        logger.info(f"User verified in database: {normalized_username}")
        return doc
    except Exception as e:
        logger.error(f"Failed to create user in MongoDB: {e}", exc_info=True)
        # Return None instead of raising - let web_backend handle the 503
        return None


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user by username and password. Returns user dict if successful, None otherwise."""
    try:
        normalized_username = username.lower().strip()
        logger.info(f"Attempting to authenticate user: {normalized_username}")
        user = get_user_by_username(normalized_username)
        if not user:
            logger.warning(f"User not found: {normalized_username}")
            return None
        password_hash = user.get("password_hash", "")
        if not password_hash:
            logger.warning(f"User {normalized_username} has no password hash")
            return None
        if not verify_password(password, password_hash):
            logger.warning(f"Password verification failed for user: {normalized_username}")
            return None
        logger.info(f"User authenticated successfully: {normalized_username}")
        return user
    except Exception as e:
        logger.error(f"Failed to authenticate user from MongoDB: {e}", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Per-user demat (broker) credentials - any broker, token refresh supported
# ---------------------------------------------------------------------------

def get_user_demat(username: str) -> Optional[dict]:
    """Get demat credentials for user. Returns dict with broker, client_id, access_token or None."""
    col = _get_users_collection()
    if col is None:
        return None
    u = col.find_one({"username": username.lower().strip()})
    if not u:
        return None
    broker = u.get("demat_broker")
    client_id = u.get("demat_client_id")
    token = u.get("demat_access_token")
    if not client_id or not token:
        return None
    return {"broker": broker or "dhan", "client_id": client_id, "access_token": token}


def set_user_demat(username: str, broker: str, client_id: str, access_token: str) -> bool:
    """Save or update demat credentials for user. Returns True only when a user document was found and updated.
    Stored in MongoDB: database 'trading', collection 'users', on the document with username (lowercase).
    Fields set: demat_broker, demat_client_id, demat_access_token, demat_updated_at."""
    try:
        col = _get_users_collection()
        if col is None:
            logger.warning("set_user_demat: users collection is None (MongoDB unavailable)")
            return False
        normalized = username.lower().strip()
        result = col.update_one(
            {"username": normalized},
            {"$set": {
                "demat_broker": (broker or "dhan").strip(),
                "demat_client_id": (client_id or "").strip(),
                "demat_access_token": (access_token or "").strip(),
                "demat_updated_at": datetime.utcnow(),
            }},
            upsert=False,
        )
        if result.matched_count > 0:
            logger.info(f"set_user_demat: saved for username={normalized!r} in trading.users (modified_count={result.modified_count})")
        else:
            logger.warning(f"set_user_demat: no document matched username={normalized!r} in trading.users (user may not exist)")
        return result.matched_count > 0
    except Exception as e:
        logger.error(f"set_user_demat failed: {e}")
        return False


def update_user_demat_token(username: str, access_token: str) -> bool:
    """Update only the access token for the same user (refresh token). Returns True on success."""
    try:
        col = _get_users_collection()
        if col is None:
            return False
        normalized = username.lower().strip()
        result = col.update_one(
            {"username": normalized},
            {"$set": {"demat_access_token": (access_token or "").strip(), "demat_updated_at": datetime.utcnow()}},
        )
        return result.modified_count > 0 or result.matched_count > 0
    except Exception as e:
        logger.error(f"update_user_demat_token failed: {e}")
        return False
