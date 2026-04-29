"""
Configuration module for trading bot
Provides centralized configuration management
"""
import os

from .environment_manager import (
    EnvironmentManager,
    get_environment_manager,
    get_service_url,
    get_config
)

# JWT auth: allow "from config import JWT_SECRET_KEY" (used by some auth flows)
JWT_SECRET_KEY = os.getenv("JWT_SECRET", os.getenv("JWT_SECRET_KEY", "change-me-in-production-use-long-secret"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
JWT_EXPIRATION_HOURS = JWT_EXPIRE_MINUTES / 60.0

# Admin credentials (optional, for legacy compatibility)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "true").lower() == "true"

__all__ = [
    'EnvironmentManager',
    'get_environment_manager',
    'get_service_url',
    'get_config',
    'JWT_SECRET_KEY',
    'JWT_ALGORITHM',
    'JWT_EXPIRE_MINUTES',
    'JWT_EXPIRATION_HOURS',
    'ADMIN_USERNAME',
    'ADMIN_PASSWORD',
    'ENABLE_AUTH',
]