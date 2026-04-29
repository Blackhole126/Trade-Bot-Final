"""
JWT Authentication Module for FastAPI
Provides token generation and verification using FastAPI dependencies
"""

from datetime import datetime, timedelta
from typing import Optional
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional

from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, ADMIN_USERNAME, ADMIN_PASSWORD, ENABLE_AUTH

logger = logging.getLogger(__name__)

# FastAPI security scheme (optional based on config)
security = HTTPBearer(auto_error=False)  # auto_error=False makes it optional


def generate_token(username: str) -> str:
    """Generate JWT token for a user"""
    payload = {
        'username': username,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """
    FastAPI dependency to get current authenticated user
    Usage: user = Depends(get_current_user)
    Authentication is OPTIONAL if ENABLE_AUTH=False in config
    """
    # If authentication is disabled, return dummy user
    if not ENABLE_AUTH:
        return {"username": "anonymous", "auth_disabled": True}
    
    # Authentication enabled - require token
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = verify_token(token)
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def authenticate_user(username: str, password: str) -> dict:
    """Authenticate user credentials and generate token"""
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = generate_token(username)
        return {
            'success': True,
            'token': token,
            'username': username,
            'expires_in_hours': JWT_EXPIRATION_HOURS
        }
    else:
        return {
            'success': False,
            'error': 'Invalid credentials'
        }
