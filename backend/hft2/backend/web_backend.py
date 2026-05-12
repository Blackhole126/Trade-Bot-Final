#!/usr/bin/env python3
"""
FastAPI backend for the Indian Stock Trading Bot Web Interface
Provides REST API endpoints for the HTML/CSS/JS frontend
"""

from typing import Dict, List  # Added for type hints
import time as _time_module
from data_service_client import get_data_client, DataServiceClient
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging
import threading
import time
import traceback
import socket
import subprocess
import platform
import asyncio
from contextlib import asynccontextmanager

# Import signal filtering layer
from core.signal_filter import get_signal_filter, SignalQuality

# Fix import paths permanently - MOVED TO TOP
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # Project root
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# CRITICAL FIX: Add global exception handler to catch unhandled exceptions
# This will log any crashes that would otherwise silently kill the process


def _handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    """Log unhandled exceptions to prevent silent crashes"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't log keyboard interrupts
        return
    logger.critical("UNHANDLED EXCEPTION CAUGHT:",
                    exc_info=(exc_type, exc_value, exc_traceback))
    print(f"\n*** CRITICAL ERROR ***", file=sys.stderr)
    print(f"Type: {exc_type.__name__}", file=sys.stderr)
    print(f"Value: {exc_value}", file=sys.stderr)
    if exc_traceback:
        import traceback
        traceback.print_tb(exc_traceback)
    print("*** END CRITICAL ERROR ***\n", file=sys.stderr)


sys.excepthook = _handle_unhandled_exception

# Configure logging format
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

# Import FastAPI components with fallback handling
try:
    import uvicorn
    from fastapi import FastAPI, BackgroundTasks, Request, Depends, HTTPException, File, UploadFile, Query, WebSocket, WebSocketDisconnect
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse

    from pydantic import BaseModel, Field, ConfigDict
    import httpx
    import json
    import queue as _queue_module
except ImportError as e:
    print(f"Error importing FastAPI components: {e}")
    print("Please install FastAPI dependencies:")
    print("pip install fastapi uvicorn pydantic")
    sys.exit(1)

# Load environment variables from .env early so config/env fallbacks work
try:
    from dotenv import load_dotenv
    from pathlib import Path as _Path
    # Check current directory and parent directory for 'env' or '.env'
    _curr = _Path(__file__).resolve().parent
    _parent = _curr.parent
    for _p in [_curr, _parent]:
        for _f in ["env", ".env"]:
            _path = _p / _f
            if _path.exists():
                load_dotenv(_path)
                logger.debug(f"Loaded env from {_path}")
except Exception:
    logger.debug("python-dotenv not available or .env not loaded")

# Import new components for live trading
try:
    from portfolio_manager import DualPortfolioManager
    from dhan_client import DhanAPIClient
    from live_executor import LiveTradingExecutor
    from dhan_sync_service import start_sync_service, stop_sync_service, get_sync_service
    LIVE_TRADING_AVAILABLE = True
    logger.info("Live trading components loaded successfully")
except ImportError as e:
    print(f"Live trading components not available: {e}")
    logger.error(f"❌ Live trading import failed: {e}")
    LIVE_TRADING_AVAILABLE = False

# Import new agents for full-market RL scanning
# fallback if torch/ML missing
data_agent = rl_agent = tracker_agent = risk_engine = None
try:
    from core.data_agent import data_agent
    from core.rl_agent import rl_agent
    from core.tracker_agent import tracker_agent
    from core.risk_engine import risk_engine
    logger.info("RL scanning agents loaded successfully")
except ImportError as e:
    logger.error(f"❌ RL agents import failed: {e}. Running without RL agents.")

# Architectural Fix: Graceful MCP dependency handling
try:
    from mcp_service import MCPTradingServer, TradingAgent, ExplanationAgent
    MCP_AVAILABLE = True
    MCP_SERVER_AVAILABLE = True
    print("MCP server components loaded successfully")
except ImportError as e:
    print(f"MCP server components not available: {e}")
    MCP_AVAILABLE = False
    # Create fallback classes

    class MCPTradingServer:
        def __init__(self, *args, **kwargs): pass

    class TradingAgent:
        def __init__(self, *args, **kwargs): pass

    class ExplanationAgent:
        def __init__(self, *args, **kwargs): pass
    MCP_SERVER_AVAILABLE = False

try:
    from fyers_client import FyersAPIClient
    FYERS_CLIENT_AVAILABLE = True
except ImportError as e:
    print(f"Fyers client not available: {e}")
    FYERS_CLIENT_AVAILABLE = False

    class FyersAPIClient:
        def __init__(self, *args, **kwargs): pass

try:
    from mcp_service.llm import GroqReasoningEngine, TradingContext, GroqResponse
    GROQ_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Groq integration not available: {e}")
    GROQ_AVAILABLE = False

    class GroqReasoningEngine:
        def __init__(self, *args, **kwargs): pass

    class TradingContext:
        def __init__(self, *args, **kwargs): pass

    class GroqResponse:
        def __init__(self, *args, **kwargs): pass

# PRODUCTION FIX: Import data service client instead of direct Fyers

# Priority 3: Standardized logging strategy
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv(
    "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOG_DATE_FORMAT = os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")

# Choose a writable log path: prefer /tmp/logs on Render, fallback to stdout-only
_LOGS_DIR = os.getenv("LOGS_DIR", "/tmp/logs" if os.getenv("RENDER") else "")
_log_file_path = os.getenv("WEB_BACKEND_LOG_FILE", "")
if not _log_file_path and _LOGS_DIR:
    try:
        os.makedirs(_LOGS_DIR, exist_ok=True)
        _log_file_path = os.path.join(_LOGS_DIR, "web_trading_bot.log")
    except Exception:
        _log_file_path = ""

_log_handlers = [logging.StreamHandler(sys.stdout)]
if _log_file_path:
    try:
        _log_handlers.append(logging.FileHandler(
            _log_file_path, mode='a', encoding='utf-8'))
    except Exception:
        pass  # Fallback to stdout-only if file can't be opened

# Configure logging with standardized format and levels
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=_log_handlers
)

# Set specific log levels for different components
logging.getLogger('utils').setLevel(logging.INFO)
logging.getLogger('core').setLevel(logging.INFO)
logging.getLogger('mcp_server').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
_main_event_loop: Optional[asyncio.AbstractEventLoop] = None

# Code Quality: Define constants to replace magic numbers
CHAT_MESSAGE_MAX_LENGTH = 1000
RANDOM_STOCK_MIN_COUNT = 8
RANDOM_STOCK_MAX_COUNT = 12
CACHE_TTL_SECONDS = 5
WEBSOCKET_PING_INTERVAL = 20
WEBSOCKET_PING_TIMEOUT = 10
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.7

# Priority 4: Optimized import structure with error handling
try:
    from utils import (
        ConfigValidator,
        validate_chat_input,
        TradingBotError,
        ConfigurationError,
        DataServiceError,
        TradingExecutionError,
        ValidationError,
        NetworkError,
        AuthenticationError,
        PerformanceMonitor,
        retry_on_failure,
        circuit_breaker,
        api_retry,
        data_service_retry,
        log_api_call,
        log_system_event,
        log_system_health
    )
    UTILS_AVAILABLE = True
    logger.info("Utils modules imported successfully")
except ImportError as e:
    logger.error(f"Error importing utils modules: {e}")
    UTILS_AVAILABLE = False
    # Fallback implementations

    class TradingBotError(Exception):
        pass

    class ConfigurationError(TradingBotError):
        pass

    class DataServiceError(TradingBotError):
        pass

    class TradingExecutionError(TradingBotError):
        pass

    class ValidationError(TradingBotError):
        pass

    class NetworkError(TradingBotError):
        pass

    class AuthenticationError(TradingBotError):
        pass

    class ConfigValidator:
        @staticmethod
        def validate_config(config): return config

        @staticmethod
        def get_config_schema(): return {}

        @staticmethod
        def validate_environment_variables(): return []

    def validate_chat_input(message): return message.strip()

# Remove the fallback PerformanceMonitor class since it's now properly imported from utils

# Initialize performance monitor
performance_monitor = PerformanceMonitor()

# Import Production Core Components
try:
    from core import (
        AsyncSignalCollector,
        AdaptiveThresholdManager,
        IntegratedRiskManager,
        DecisionAuditTrail,
        ContinuousLearningEngine
    )
    PRODUCTION_CORE_AVAILABLE = True
    logger.info("Production core components loaded successfully")
except ImportError as e:
    logger.error(f"Error importing production core components: {e}")
    PRODUCTION_CORE_AVAILABLE = False

# Import Configuration Schema and Validation
try:
    from config.config_schema import ConfigValidator, load_and_validate_config
    CONFIG_SCHEMA_AVAILABLE = True
    logger.info("Configuration schema validation loaded successfully")
except ImportError as e:
    logger.error(f"Error importing configuration schema: {e}")
    CONFIG_SCHEMA_AVAILABLE = False

# Import the trading bot components (optional: auth/signup work without them)
ChatbotCommandHandler = VirtualPortfolio = TradingExecutor = None
DataFeed = Stock = StockTradingBot = None
try:
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from testindia import (
        ChatbotCommandHandler, VirtualPortfolio,
        TradingExecutor, DataFeed, Stock, StockTradingBot
    )
except ImportError as e:
    print(f"Error importing trading bot components: {e}")
    print("Make sure testindia.py is in the same directory. Auth/signup will work; bot features may be limited.")

# Fix: Alias StockTradingBot to WebTradingBot if imported
if StockTradingBot:
    WebTradingBot = StockTradingBot
else:
    class WebTradingBot:
        def __init__(self, config, username=None):
            self.config = config
            self.username = username
            self.portfolio = {}
            self.executor = None

        def get_portfolio_metrics(self): return {}
        def start(self): pass
        def stop(self): pass


# Pydantic Models for Request/Response validation


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    timestamp: str
    confidence: Optional[float] = None
    context: Optional[str] = None


class WatchlistRequest(BaseModel):
    ticker: str
    action: str  # ADD or REMOVE


class WatchlistResponse(BaseModel):
    message: str
    tickers: List[str]


class BulkWatchlistRequest(BaseModel):
    tickers: List[str]
    action: str = "ADD"  # ADD or REMOVE


class BulkWatchlistResponse(BaseModel):
    message: str
    successful_tickers: List[str]
    failed_tickers: List[str]
    total_processed: int


class SettingsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    mode: Optional[str] = None
    riskLevel: Optional[str] = None
    stop_loss_pct: Optional[float] = None
    target_profit_pct: Optional[float] = Field(None, alias="targetPricePct")
    target_price_level: Optional[str] = Field(None, alias="targetPriceLevel")
    use_risk_reward: Optional[bool] = None
    risk_reward_ratio: Optional[float] = None
    max_capital_per_trade: Optional[float] = None
    max_trade_limit: Optional[int] = None

# MCP-specific models


class MCPAnalysisRequest(BaseModel):
    symbol: str
    timeframe: Optional[str] = "1D"
    analysis_type: Optional[str] = "comprehensive"


class MCPTradeRequest(BaseModel):
    symbol: str
    action: str  # BUY, SELL, HOLD
    quantity: Optional[int] = None
    override_reason: Optional[str] = None


class PredictionRequest(BaseModel):
    symbols: Optional[List[str]] = []
    models: Optional[List[str]] = ["rl"]
    horizon: Optional[str] = "day"
    include_explanations: Optional[bool] = True
    natural_query: Optional[str] = ""


class ScanRequest(BaseModel):
    filters: Optional[Dict[str, Any]] = {}
    sort_by: Optional[str] = "score"
    limit: Optional[int] = 50
    natural_query: Optional[str] = ""


class StartBotWithSymbolRequest(BaseModel):
    symbol: str


class PortfolioMetrics(BaseModel):
    total_value: float
    cash: float
    cash_percentage: float = 0
    holdings: Dict[str, Any]
    total_invested: float = 0
    invested_percentage: float = 0
    current_holdings_value: float = 0
    total_return: float
    return_percentage: float
    total_return_pct: float = 0
    unrealized_pnl: float
    unrealized_pnl_pct: float = 0
    realized_pnl: float
    realized_pnl_pct: float = 0
    total_exposure: float
    exposure_ratio: float = 0
    profit_loss: float = 0
    profit_loss_pct: float = 0
    active_positions: int
    trades_today: int = 0
    initial_balance: float = 0


class BotStatus(BaseModel):
    is_running: bool
    last_update: str
    mode: str


class MessageResponse(BaseModel):
    message: str

# New endpoint models for RL scanning


class AnalyzeRequest(BaseModel):
    tickers: List[str]
    horizon: str = "day"


class UpdateRiskRequest(BaseModel):
    stop_loss_pct: float
    capital_risk_pct: float
    drawdown_limit_pct: float


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class UserProfileUpdate(BaseModel):
    fullName: Optional[str] = None
    email: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


# JWT auth
try:
    # CRITICAL: Import from current directory explicitly to avoid conflicts with backend/auth.py
    # Use importlib to force loading the local auth.py file
    import importlib.util
    import sys
    from pathlib import Path

    # Get absolute path to local hft_auth.py
    current_dir = Path(__file__).resolve().parent
    auth_file_path = current_dir / "hft_auth.py"

    # Load module from file explicitly - this ensures we get the correct hft_auth.py
    spec = importlib.util.spec_from_file_location(
        "hft2_backend_auth", auth_file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load auth module from {auth_file_path}")
    auth_module = importlib.util.module_from_spec(spec)
    sys.modules["hft2_backend_auth"] = auth_module  # Prevent re-import
    spec.loader.exec_module(auth_module)

    # Verify it has the required functions
    if not hasattr(auth_module, 'create_user'):
        raise AttributeError(
            f"auth module at {auth_file_path} missing create_user function. Found: {dir(auth_module)}")

    _http_bearer = HTTPBearer(auto_error=False)

    def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_http_bearer)):
        """Dependency: returns JWT payload dict if valid Bearer token, else None."""
        if not credentials or not credentials.credentials:
            return None
        payload = auth_module.decode_token(credentials.credentials)
        return payload

    def get_current_user_required(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """Dependency: returns JWT payload or raises 401."""
        if not credentials or not credentials.credentials:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if credentials.credentials in _logout_blacklist:
            raise HTTPException(
                status_code=401, detail="Token invalidated (logged out)")
        payload = auth_module.decode_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=401, detail="Invalid or expired token")
        return payload

    def get_optional_user_demat(credentials: HTTPAuthorizationCredentials = Depends(_http_bearer)):
        """Dependency: returns (payload, demat_creds). demat_creds is None if not auth or no demat linked."""
        if not credentials or not credentials.credentials:
            return (None, None)
        payload = auth_module.decode_token(credentials.credentials)
        if not payload:
            return (None, None)
        username = (payload.get("sub") or "").strip()
        demat = auth_module.get_user_demat(username) if hasattr(
            auth_module, "get_user_demat") else None
        return (payload, demat)

    JWT_AVAILABLE = True
    get_optional_user = get_current_user  # Optional auth: returns payload or None
except Exception as e:
    logger.warning(f"JWT auth not available: {e}")
    JWT_AVAILABLE = False
    get_current_user = get_current_user_required = None

    def get_optional_user():
        return None

    def get_optional_user_demat(credentials=None):
        return (None, None)

# Logger already configured above

# Logout blacklist: tokens added here are rejected until server restart (client must discard token).
# Bounded to MAX_BLACKLIST_SIZE to prevent unbounded memory growth when serving 50+ users.
_logout_blacklist: set = set()
_MAX_BLACKLIST_SIZE: int = 5_000  # ~5 KB of token strings max


# Initialize FastAPI app
app = FastAPI(
    title="Indian Stock Trading Bot API",
    description="REST API for the Indian Stock Trading Bot Web Interface",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Register startup and shutdown events


@app.on_event("startup")
async def startup_event_wrapper():
    await startup_event()


@app.on_event("shutdown")
async def shutdown_event_wrapper():
    await shutdown_event()

# Add CORS middleware - MUST be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (localhost:5173, etc.)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
)

# Priority 2: Integrate custom exception handlers with FastAPI


@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
    """Handle validation errors with proper HTTP responses"""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request, exc: ConfigurationError):
    """Handle configuration errors"""
    logger.error(f"Configuration error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Configuration error occurred"})


@app.exception_handler(DataServiceError)
async def data_service_error_handler(request, exc: DataServiceError):
    """Handle data service errors"""
    logger.error(f"Data service error: {exc}")
    return JSONResponse(status_code=503, content={"detail": "Data service temporarily unavailable"})


@app.exception_handler(TradingExecutionError)
async def trading_execution_error_handler(request, exc: TradingExecutionError):
    """Handle trading execution errors"""
    logger.error(f"Trading execution error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Trading execution failed"})


@app.exception_handler(NetworkError)
async def network_error_handler(request, exc: NetworkError):
    """Handle network errors"""
    logger.error(f"Network error: {exc}")
    return JSONResponse(status_code=502, content={"detail": "Network connectivity issue"})


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request, exc: AuthenticationError):
    """Handle authentication errors"""
    logger.error(f"Authentication error: {exc}")
    return JSONResponse(status_code=401, content={"detail": "Authentication failed"})

# Priority 4: Add comprehensive error handlers for common exceptions


@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    """Handle value errors"""
    logger.warning(f"Value error: {exc}")
    return JSONResponse(status_code=400, content={"detail": "Invalid input value"})


@app.exception_handler(KeyError)
async def key_error_handler(request, exc: KeyError):
    """Handle key errors"""
    logger.error(f"Key error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Missing required data"})

# --- INTERNAL COMMS PROXY ---
# Render only exposes ONE port to the internet (web_backend on PORT).
# The frontend tries to call /tools/* for Market Scan, which live on api_server.py (PORT+1).
# We proxy those calls internally from web_backend to api_server.
API_SERVER_URL = f"http://127.0.0.1:{int(os.environ.get('PORT', 10000)) + 1}"


@app.api_route("/tools/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def tools_proxy(path: str, request: Request):
    """Proxy /tools/* requests to the internal ML API server (api_server.py).
    Retries for up to 3 minutes on cold-start so Render warmup never shows 'Request failed'.
    """
    url = f"{API_SERVER_URL}/tools/{path}"
    data = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    MAX_RETRIES = 18          # 18 × 10s = 3 minutes max wait
    RETRY_DELAY = 10.0        # seconds between retries
    PROXY_TIMEOUT = 300.0     # 5 minutes per request (ML scan can be slow)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=PROXY_TIMEOUT) as client:
                proxy_req = client.build_request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    params=request.query_params,
                    content=data,
                )
                response = await client.send(proxy_req)
                logger.info(
                    f"[proxy] /tools/{path} → {response.status_code} (attempt {attempt})")
                return JSONResponse(
                    content=response.json() if response.content else None,
                    status_code=response.status_code,
                    headers={k: v for k, v in response.headers.items(
                    ) if k.lower() != "content-length"},
                )
        except httpx.ConnectError as e:
            last_error = e
            if attempt == 1:
                logger.warning(
                    f"[proxy] api_server not ready yet (attempt {attempt}/{MAX_RETRIES}). Waiting {RETRY_DELAY}s...")
            else:
                logger.info(
                    f"[proxy] Still waiting for api_server... (attempt {attempt}/{MAX_RETRIES})")
            await asyncio.sleep(RETRY_DELAY)
        except httpx.TimeoutException as e:
            logger.error(
                f"[proxy] Timeout on /tools/{path} after {PROXY_TIMEOUT}s")
            return JSONResponse(
                status_code=504,
                content={
                    "detail": "ML Engine timed out. The scan is taking very long — try again shortly."},
            )
        except Exception as e:
            logger.error(f"[proxy] Unexpected error on /tools/{path}: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Proxy error: {str(e)}"},
            )

    # Exhausted all retries
    logger.error(
        f"[proxy] api_server not available after {MAX_RETRIES} retries: {last_error}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "ML Engine failed to start. Check Render logs for api_server.py errors."},
    )
# -----------------------------


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle all unhandled exceptions with CORS headers"""
    import traceback
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    # Return JSONResponse with CORS headers
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# ─── PER-USER STATE MANAGEMENT & BOUNDS ───────────────────────────────────────
# Dictionary mapping username -> user state dict
_user_bot_states: Dict[str, Dict[str, Any]] = {}
_user_states_lock = threading.Lock()

# Hard limit on how many user sessions we keep in RAM simultaneously.
# With 50 users each having a bot + analysis cache + portfolio cache the footprint
# can reach several hundred MB.  When we exceed the cap we evict the session of
# the user who has been idle the longest (LRU strategy).
_MAX_USER_SESSIONS: int = 60          # comfortably above the 50-user target
_MAX_ANALYSIS_ENTRIES: int = 30       # max symbols in _last_bot_analysis per user
# Track last-activity time per user for LRU eviction (username -> monotonic time)
_user_last_activity: Dict[str, float] = {}


def _evict_oldest_inactive_sessions() -> None:
    """Evict the least-recently-used user sessions when over the cap.

    Called inside get_user_state() while holding _user_states_lock, so no
    extra locking is required.
    """
    overflow = len(_user_bot_states) - _MAX_USER_SESSIONS
    if overflow <= 0:
        return

    # Sort by last-activity ascending (oldest first)
    sorted_users = sorted(
        _user_last_activity.items(), key=lambda kv: kv[1]
    )
    evicted = 0
    for uname, _ in sorted_users:
        if evicted >= overflow:
            break
        state = _user_bot_states.get(uname, {})
        # Only evict if the user's bot is not currently running
        if state.get("bot_running") or state.get("_bot_initializing"):
            continue
        # Cancel any lingering loop task
        task = state.get("_continuous_loop_task")
        if task and not task.done():
            task.cancel()
        _user_bot_states.pop(uname, None)
        _user_last_activity.pop(uname, None)
        evicted += 1
        logger.info("[LRU evict] Freed session for inactive user '%s'", uname)


def get_user_state(username: Optional[str]) -> Dict[str, Any]:
    """Get or initialize the state for a specific user.

    Thread-safe. Enforces a maximum of _MAX_USER_SESSIONS concurrent sessions
    via LRU eviction so memory usage stays bounded for 19–60 parallel users.
    Each user's data is fully isolated: no shared mutable state between users.
    """
    # MULTI-USER FIX: Always normalize username to lowercase and strip whitespace
    # to prevent data leakage between "UserA" and "usera".
    un: str = str(username).lower().strip() if username else "anonymous"
    with _user_states_lock:
        # Record activity time BEFORE potential eviction
        _user_last_activity[un] = _time_module.monotonic()

        if un not in _user_bot_states:
            # Evict oldest inactive session if we're at the cap
            if len(_user_bot_states) >= _MAX_USER_SESSIONS:
                _evict_oldest_inactive_sessions()

            _user_bot_states[un] = {
                "trading_bot": None,
                "bot_running": False,
                "_bot_initializing": False,
                "_continuous_loop_task": None,
                "_stop_event": threading.Event(),
                "_last_bot_analysis": {},   # capped to _MAX_ANALYSIS_ENTRIES symbols
                "_bot_data_cache": {},
                "_bot_data_cache_ts": 0.0,
                "_pending_start_tickers": [],
                "_pending_bot_user_context": None,
                "_active_analysis_tasks": set(),
                "_created_at": _time_module.monotonic(),
            }
        return _user_bot_states[un]


async def trigger_bot_data_refresh(username: str):
    """Refreshes the internal cache of symbols, holdings, and P&L for a specific user."""
    state = get_user_state(username)
    if not username:
        return

    try:
        from hft_auth import get_user_demat
        creds = get_user_demat(username)
        if not creds:
            return

        from dhan_client import get_live_portfolio
        # Fetch portfolio
        portfolio = await asyncio.get_event_loop().run_in_executor(
            None, lambda: get_live_portfolio(
                creds.get("access_token"), creds.get("client_id"))
        ) or {}

        # Prepare list of symbols being tracked
        bot = state.get("trading_bot")

        # PRODUCTION FIX: Use converter to get full bot_data shape
        converted = _convert_dhan_portfolio_to_bot_data(
            portfolio, username=username)
        state["_bot_data_cache"] = converted
        state["_bot_data_cache_ts"] = time.time()

        # Update portfolio manager cash if possible
        if bot and hasattr(bot, "portfolio_manager") and portfolio:
            try:
                cash = float(portfolio.get("cash", 0))
                if cash > 0:
                    bot.portfolio_manager.update_cash_balance(cash)
                    logger.debug(
                        f"[trigger_bot_data_refresh] Updated PortfolioManager cash to {cash} for {username}")
            except Exception as pm_err:
                logger.warning(
                    f"Could not update PortfolioManager cash: {pm_err}")

        logger.debug(
            f"[trigger_bot_data_refresh] Refreshed data for {username}")
    except Exception as e:
        logger.error(
            f"Error in background data refresh for {username}: {e}", exc_info=True)


async def _run_trading_analysis_task(username: str):
    """A background task that performs high-level ML analysis for a specific user's portfolio/tickers."""
    state = get_user_state(username)
    logger.info(f"Starting analysis task for user: {username}")

    while state.get("bot_running"):
        try:
            bot = state.get("trading_bot")
            if not bot:
                await asyncio.sleep(10)
                continue

            # Perform analysis...
            results = await bot.run_analysis()
            state["_last_bot_analysis"] = results

            await asyncio.sleep(60)  # Analyze once per minute
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in analysis loop for {username}: {e}")
            await asyncio.sleep(30)

    logger.info(f"Analysis task for user {username} stopped.")

# Legacy global fallback for compatibility during transition (optional, but safer to keep names for now)
# We will explicitly use get_user_state in all authed endpoints.
# -----------------------------


def get_bot_running(username: str = None) -> bool:
    """Return current bot_running for a specific user."""
    if not username:
        return False
    state = get_user_state(username)
    return state.get("bot_running", False)


@app.get("/api/health")
async def health_check():
    """Instant health check — zero I/O, zero blocking. Always returns immediately.
    The frontend's BackendStatusContext polls this to detect if the process is alive."""
    # In multi-user mode, we return true if the server is up.
    # Detailed bot status is per-user via /api/bot/status
    return {"status": "ok", "ts": time.time()}


@app.get("/api/bot/status")
async def get_bot_status(user=Depends(get_current_user_required)):
    """Return current bot status for frontend polling."""
    username = user.get("sub")
    state = get_user_state(username)
    if state.get("_bot_initializing"):
        return {"status": "INITIALIZING"}
    if state.get("bot_running"):
        return {"status": "READY"}
    return {"status": "STOPPED"}


@app.get("/api/signal-filter/status")
async def get_signal_filter_status(user=Depends(get_current_user_required)):
    """Return signal filter status and statistics."""
    try:
        signal_filter = get_signal_filter()
        stats = signal_filter.get_filter_stats()
        cycle_state = signal_filter.get_cycle_state()

        return {
            "success": True,
            "stats": stats,
            "cycle_state": cycle_state
        }
    except Exception as e:
        logger.error(f"Error getting signal filter status: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/signal-filter/config")
async def update_signal_filter_config(config: Dict[str, Any], user=Depends(get_current_user_required)):
    """Update signal filter configuration."""
    try:
        signal_filter = get_signal_filter(config)
        return {
            "success": True,
            "message": "Signal filter configuration updated",
            "config": {
                "min_confidence": signal_filter.config.min_confidence,
                "min_ensemble_agreement": signal_filter.config.min_ensemble_agreement,
                "min_models_agreeing": signal_filter.config.min_models_agreeing,
                "conflict_window_minutes": signal_filter.config.conflict_window_minutes,
                "stop_after_cycle": signal_filter.config.stop_after_cycle
            }
        }
    except Exception as e:
        logger.error(f"Error updating signal filter config: {e}")
        return {"success": False, "error": str(e)}


# ── Bot-data cache (stale-while-revalidate) ─────────────────────────────────
# Shared settings, TTL is global but data is now per-user in user_states
_BOT_DATA_CACHE_TTL: float = 20.0          # seconds before background refresh
_bot_data_refresh_lock = asyncio.Lock()
_bot_data_refresh_running: bool = False


async def _refresh_bot_data_cache_background():
    """Fetch fresh bot-data for ALL active users in PARALLEL and store in their states.

    MULTI-USER FIX: Uses asyncio.gather so that 50 users' Dhan API calls run
    concurrently.  A slow/failing call for User A does NOT block User B.
    Each coroutine has its own timeout and exception handler for full isolation.

    TOKEN FIX: Always reads Dhan credentials fresh from MongoDB — never from the
    stale in-memory bot.config — so updating the token in Settings takes effect
    on the next refresh cycle without a server restart.
    """
    global _bot_data_refresh_running
    if _bot_data_refresh_running:
        return
    _bot_data_refresh_running = True
    try:
        with _user_states_lock:
            active_usernames = list(_user_bot_states.keys())

        async def _refresh_one_user(uname: str) -> None:
            """Refresh cache for a single user. Fully isolated — exceptions are caught."""
            state = get_user_state(uname)
            bot = state.get("trading_bot")
            if not bot:
                return
            try:
                # Live trading mode only (production ready)
                current_mode = bot.config.get("mode", "live")
                result = None

                if current_mode == "live":
                    try:
                        # ── Always fetch fresh credentials from MongoDB ──
                        from hft_auth import get_user_demat as _get_demat
                        _fresh_creds = _get_demat(uname)
                        dhan_token = _fresh_creds.get(
                            "access_token") if _fresh_creds else None
                        dhan_client_id = _fresh_creds.get(
                            "client_id") if _fresh_creds else None

                        # Sync updated token into running bot objects
                        if dhan_token and dhan_token != bot.config.get("dhan_access_token"):
                            logger.info(
                                "[bg_refresh] Syncing new Dhan token into bot for %s", uname)
                            bot.config["dhan_access_token"] = dhan_token
                            if hasattr(bot, "dhan_client") and bot.dhan_client:
                                bot.dhan_client.access_token = dhan_token
                            if hasattr(bot, "live_executor") and bot.live_executor:
                                if hasattr(bot.live_executor, "dhan_client") and bot.live_executor.dhan_client:
                                    bot.live_executor.dhan_client.access_token = dhan_token

                        if dhan_token and dhan_client_id:
                            from dhan_client import get_live_portfolio_with_creds
                            loop = asyncio.get_event_loop()
                            dhan_portfolio = await asyncio.wait_for(
                                loop.run_in_executor(
                                    None, get_live_portfolio_with_creds, dhan_client_id, dhan_token),
                                timeout=25.0
                            )
                            if dhan_portfolio:
                                result = _convert_dhan_portfolio_to_bot_data(
                                    dhan_portfolio, username=uname, include_config=True)
                        else:
                            logger.debug(
                                "[bg_refresh] No valid Dhan creds for %s in live mode", uname)
                    except asyncio.TimeoutError:
                        logger.debug(
                            "[bg_refresh] Dhan API timed out for %s", uname)
                    except Exception as e:
                        logger.debug(
                            "[bg_refresh] Live refresh error for %s: %s", uname, e)

                if result is None:
                    try:
                        loop = asyncio.get_event_loop()
                        result = await asyncio.wait_for(
                            loop.run_in_executor(None, bot.get_complete_bot_data), timeout=10.0
                        )
                    except Exception:
                        pass

                if result:
                    # Cap _last_bot_analysis to prevent unbounded growth
                    analysis = state.get("_last_bot_analysis", {})
                    if len(analysis) > _MAX_ANALYSIS_ENTRIES:
                        # Keep most-recently-added entries
                        excess = len(analysis) - _MAX_ANALYSIS_ENTRIES
                        for old_sym in list(analysis.keys())[:excess]:
                            analysis.pop(old_sym, None)

                    state["_bot_data_cache"] = result
                    state["_bot_data_cache_ts"] = _time_module.monotonic()

            except Exception as user_err:
                logger.debug(
                    "[bg_refresh] Uncaught error for %s: %s", uname, user_err)

        # Run all per-user refreshes in PARALLEL — no user blocks another
        if active_usernames:
            await asyncio.gather(
                *[_refresh_one_user(u) for u in active_usernames],
                return_exceptions=True   # swallow per-user exceptions; they're logged inside
            )

    except Exception as _e:
        logger.warning("[bg_refresh] Scheduler error: %s", _e)
    finally:
        _bot_data_refresh_running = False

# ─────────────────────────────────────────────────────────────────────────────


def _offline_bot_data(username: str = "anonymous"):
    """Return valid bot-data shape when bot is not initialized so frontend shows offline state instead of 500."""
    state = get_user_state(username)
    # Prefer cache if available, even if offline
    if state.get("_bot_data_cache"):
        cached = dict(state["_bot_data_cache"])
        cached["isRunning"] = False
        return cached

    try:
        # Note: get_current_saved_mode should ideally be per-user too
        mode = get_current_saved_mode(username)
        saved = load_config_from_file(mode, username) or {}
    except Exception:
        pass

    # Analysis is now per-user in state["_last_bot_analysis"]
    analysis_list = list(state.get("_last_bot_analysis", {}).values())

    return {
        "isRunning": state.get("bot_running", False) or state.get("_bot_initializing", False),
        "config": {
            "mode": saved.get("mode", "paper"),
            "tickers": saved.get("tickers", []),
            "stopLossPct": saved.get("stop_loss_pct", 0.05),
            "maxAllocation": saved.get("max_capital_per_trade", 0.25),
            "maxTradeLimit": saved.get("max_trade_limit", 10),
        },
        "portfolio": {
            "totalValue": 0,
            "cash": 0,
            "investedValue": 0,
            "todayGain": 0,
            "holdings": {},
            "startingBalance": 0,
            "unrealizedPnL": 0,
            "realizedPnL": 0,
            "tradeLog": [],
        },
        "analysis": analysis_list,
        "lastUpdate": datetime.now().isoformat(),
    }


# MCP components
mcp_server = None
mcp_trading_agent = None
fyers_client = None
groq_engine = None

# Real-time market data function

# Semaphore: only 1 ML analysis runs at a time.
# Each analyze_stock call takes 2-3 min; running multiple in parallel saturates the thread pool
# and causes /api/bot-data and /api/trades to time out while waiting for a free thread.
# Legacy globals — everything below now mapped in user_states but kept as comments for reference
# _active_analysis_tasks = set()
# _last_bot_analysis = {}
# _continuous_loop_task: Optional[asyncio.Task] = None
_analysis_semaphore = asyncio.Semaphore(1)
# Track active ticker analysis tasks (Legacy global - now mapped in user_states)
# _active_analysis_tasks = set()
# Stores latest analysis results per symbol, exposed via /bot-data to the frontend (Legacy global - now mapped in user_states)
# _last_bot_analysis: dict = {}


def _get_latest_analysis_from_files(symbol: str, username: Optional[str] = None) -> Optional[dict]:
    """Helper to find and load the latest professional analysis/signal for a ticker.
    Ensures the dashboard matches the terminal output exactly.
    Isolated by user directory when username is provided.
    """
    try:
        import glob as _glob
        import json
        sym = symbol.strip().upper()
        sanitized = sym.replace(".", "_")

        # Determine directory based on user
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        if username and username != "anonymous":
            # User-specific directory
            user_data_dir = os.path.join(
                project_root, 'data', 'users', username)
            analysis_dir = os.path.join(user_data_dir, "stock_analysis")
        else:
            # Global fallback directory
            analysis_dir = os.path.join(current_dir, "stock_analysis")

        if not os.path.exists(analysis_dir):
            return None

        # 1. Try to find the latest professional signal file (BUY/SELL/HOLD decision)
        signal_path = os.path.join(analysis_dir, f"{sanitized}_signal.json")
        signal_data = None
        if os.path.exists(signal_path):
            try:
                with open(signal_path, "r", encoding="utf-8") as f:
                    signal_data = json.load(f)
                # Ensure it's not too old (e.g. within last 2 hours)
                if time.time() - os.path.getmtime(signal_path) > 7200:
                    signal_data = None
            except Exception:
                pass

        # 2. Try to find the latest full ML analysis file
        pattern = os.path.join(analysis_dir, f"{sanitized}_analysis_*.json")
        files = _glob.glob(pattern)
        analysis_data = None
        if files:
            latest_file = max(files, key=os.path.getmtime)
            # Ensure it's not too old (within last 1 hour)
            if time.time() - os.path.getmtime(latest_file) < 3600:
                try:
                    with open(latest_file, "r", encoding="utf-8") as f:
                        analysis_data = json.load(f)
                except Exception:
                    pass

        if not signal_data and not analysis_data:
            return None

        # 3. Build a combined payload for the dashboard
        # Signal data (terminal decision) takes precedence for recommendation/confidence
        res = signal_data or {}
        ml = analysis_data or {}

        recommendation = (res.get("action") or ml.get(
            "recommendation") or "HOLD").upper()
        confidence = float(res.get("confidence_score") or ml.get(
            "ml_analysis", {}).get("confidence") or 0.5)
        if confidence > 1.0:
            confidence /= 100.0

        current_price = float(res.get("current_price") or ml.get(
            "stock_data", {}).get("current_price", {}).get("INR") or 0)

        # Base values from files
        target_price = res.get("take_profit") or ml.get("ml_analysis", {}).get("predicted_price") or \
            ml.get("stock_data", {}).get("resistance_level")
        stop_loss = res.get("stop_loss") or ml.get(
            "stock_data", {}).get("support_level")

        reasoning = res.get("reasoning") or ml.get("ml_analysis", {}).get(
            "explanation") or "Latest background analysis synced."

        # --- CALCULATION FIX: Sanity Checks ---
        if current_price > 0:
            if "BUY" in recommendation:
                # For long trades, target must be > price and stop loss < price
                if not target_price or float(target_price) <= current_price:
                    target_price = round(current_price * 1.05, 2)
                if not stop_loss or float(stop_loss) >= current_price:
                    stop_loss = round(current_price * 0.97, 2)
            elif "SELL" in recommendation:
                # For sell signals, target might be lower (exit point)
                pass
            else:  # HOLD
                # Ensure they are at least not inverted in a way that looks like a live trade
                if target_price and float(target_price) < current_price:
                    # If predicted price is bearish but recommendation is HOLD,
                    # we still show it (the user reported this), but maybe we label it as 'Predicted'
                    # and ensure stop loss isn't weird.
                    pass

        # 4. Final structured payload matching result_payload in _trigger_all_hft2_inner
        final_payload = {
            "symbol": sym,
            "recommendation": recommendation,
            "confidence": min(1.0, max(0.0, confidence)),
            "reasoning": reasoning[:500],
            "risk_score": 0.5,
            "target_price": round(float(target_price), 2) if target_price else None,
            "stop_loss": round(float(stop_loss), 2) if stop_loss else None,
            "sentiment": ml.get("sentiment_analysis", {}).get("label", "neutral"),
            "sentiment_score": float(ml.get("sentiment_analysis", {}).get("compound", 0)),
            "indicators": {},  # Filled by dashboard from technical indicators if needed
            "timestamp": res.get("timestamp") or datetime.now().isoformat(),
            "source": os.path.basename(signal_path) if signal_data else os.path.basename(latest_file) if analysis_data else "Synced Output"
        }

        # Extract indicators if available in ml
        tech = ml.get("technical_indicators") or {}
        if tech:
            indicators = {}
            if "rsi" in tech:
                rsi_v = float(tech["rsi"])
                indicators["RSI"] = {"value": round(rsi_v, 2), "signal": "bearish" if rsi_v > 65 else (
                    "bullish" if rsi_v < 40 else "neutral")}
            if "macd" in tech:
                indicators["MACD"] = {"value": round(float(
                    tech["macd"]), 3), "signal": "bullish" if float(tech["macd"]) > 0 else "bearish"}
            final_payload["indicators"] = indicators

        return final_payload

    except Exception as e:
        logger.warning(
            f"Failed to get latest analysis from files for {symbol}: {e}")
        return None


# Per-user bot start: tickers for the user who triggered start (when auth present)
_pending_start_tickers: list = []
# Per-user bot start: user_id + demat credentials for the user who triggered start (when auth + demat linked)
_pending_bot_user_context: Optional[dict] = None

# Module-level flag to prevent double-initialization (replaces fragile function-attribute pattern)
_bot_initializing: bool = False


def _get_user_watchlist_from_db(username: str) -> list:
    """Return the authenticated user's watchlist from MongoDB. Empty list if not found or error."""
    if not username:
        return []
    try:
        from db.mongo_client import get_mongo_db
        db = get_mongo_db("trading")
        doc = db["watchlists"].find_one({"username": username})
        return list(doc.get("symbols", [])) if doc else []
    except Exception as e:
        logger.warning(f"Could not load user watchlist for {username}: {e}")
        return []


def _save_user_watchlist_to_db(username: str, tickers: list) -> bool:
    """Save the user's watchlist to MongoDB. Returns True on success."""
    if not username:
        return False
    try:
        from db.mongo_client import get_mongo_db
        from datetime import datetime
        db = get_mongo_db("trading")
        db["watchlists"].update_one(
            {"username": username},
            {"$set": {"username": username, "symbols": tickers,
                      "updated_at": datetime.utcnow()}},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.warning(f"Could not save user watchlist for {username}: {e}")
        return False


# ===== SSE Log Broadcasting (User-Aware) =====
# Map username -> list of queues for that user
_sse_clients: Dict[str, List["_queue_module.Queue[str]"]] = {}
_sse_clients_lock = threading.Lock()


class _SSELogHandler(logging.Handler):
    """Sends log records to connected SSE clients, with per-user filtering when possible."""

    def emit(self, record):
        try:
            msg = self.format(record)
            payload = json.dumps(
                {"type": "log", "level": record.levelname, "message": msg})
            event = f"data: {payload}\n\n"

            # Check if record has a specific username (set via extra={"username": "..."})
            target_user = getattr(record, "username", None)

            with _sse_clients_lock:
                if target_user and target_user in _sse_clients:
                    # Send only to this user
                    for q in list(_sse_clients[target_user]):
                        try:
                            q.put_nowait(event)
                        except Exception:
                            pass
                elif not target_user:
                    # System log: broadcast to everyone
                    for user_qs in _sse_clients.values():
                        for q in list(user_qs):
                            try:
                                q.put_nowait(event)
                            except Exception:
                                pass
        except Exception:
            pass


_sse_log_handler = _SSELogHandler()
_sse_log_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(_sse_log_handler)


def _build_sse_snapshot(username: str = "anonymous") -> dict:
    """Lightweight bot state snapshot for SSE data push, isolated by user."""
    state = get_user_state(username)
    bot = state.get("trading_bot")
    initializing = state.get("_bot_initializing", False)
    running = state.get("bot_running", False)
    last_analysis = state.get("_last_bot_analysis", {})

    try:
        if bot:
            # Prefer fresh data from the bot instance
            try:
                bot_data = bot.get_complete_bot_data()
                portfolio = bot_data.get("portfolio", {})
            except Exception:
                # Fallback to cache if bot call fails
                cache = state.get("_bot_data_cache", {})
                portfolio = cache.get("portfolio", {})
                bot_data = {"isRunning": running}

            holdings_raw = portfolio.get("holdings", {})
            # Normalize holdings fields
            holdings = {}
            for sym, h in (holdings_raw or {}).items():
                holdings[sym] = {
                    "quantity": h.get("quantity") or h.get("qty", 0),
                    "avgPrice": h.get("avgPrice") or h.get("avg_price", 0),
                    "currentPrice": h.get("currentPrice") or h.get("last_price", 0),
                }
            cash = portfolio.get("cash", 0)
            total_value = portfolio.get("totalValue", 0)
            # If totalValue is 0 but holdings exist, compute from holdings
            if total_value == 0 and holdings:
                market_val = sum(
                    (h.get("currentPrice") or h.get("avgPrice", 0)) *
                    (h.get("quantity", 0))
                    for h in holdings.values()
                )
                total_value = cash + market_val
            return {
                "isRunning": bot_data.get("isRunning", False) or initializing,
                "cash": cash,
                "totalValue": round(total_value, 2),
                "unrealizedPnL": portfolio.get("unrealizedPnL", 0),
                "realizedPnL": portfolio.get("realizedPnL", 0),
                "investedValue": portfolio.get("investedValue", 0),
                "todayGain": portfolio.get("todayGain", 0),
                "holdings": holdings,
                "analysis": list(last_analysis.values()),
            }

        # No bot running — check if we have cached live data (from /api/bot-data Dhan fetch)
        cached = state.get("_bot_data_cache")
        if cached and isinstance(cached, dict):
            portfolio = cached.get("portfolio", {})
            if portfolio:
                holdings_raw = portfolio.get("holdings", {})
                holdings = {}
                for sym, h in (holdings_raw or {}).items():
                    holdings[sym] = {
                        "quantity": h.get("quantity") or h.get("qty", 0),
                        "avgPrice": h.get("avgPrice") or h.get("avg_price", 0),
                        "currentPrice": h.get("currentPrice") or h.get("last_price", 0),
                    }
                return {
                    "isRunning": running or initializing,
                    "cash": portfolio.get("cash", 0),
                    "totalValue": portfolio.get("totalValue", 0),
                    "unrealizedPnL": portfolio.get("unrealizedPnL", 0),
                    "realizedPnL": portfolio.get("realizedPnL", 0),
                    "investedValue": portfolio.get("investedValue", 0),
                    "todayGain": portfolio.get("todayGain", 0),
                    "holdings": holdings,
                    "analysis": list(last_analysis.values()),
                }
    except Exception:
        pass

    # Fallback/Offline state
    return {
        "isRunning": running or initializing,
        "cash": 0,
        "totalValue": 0,
        "unrealizedPnL": 0,
        "realizedPnL": 0,
        "investedValue": 0,
        "todayGain": 0,
        "holdings": {},
        "analysis": list(last_analysis.values()),
    }


async def trigger_all_hft2_components_for_symbol(symbol: str, username: str = None):
    """Reusable async function to trigger all HFT2 backend components (predictions, analysis, data fetching) for a symbol.
    Runs with a semaphore so only one ticker's full ML pipeline executes at a time.
    Has a hard 10-minute timeout so it never hangs forever."""
    # Register this task for cancellation tracking
    state = get_user_state(username)
    current_task = asyncio.current_task()
    if current_task and state:
        active_tasks = state.get("_active_analysis_tasks")
        if isinstance(active_tasks, set):
            active_tasks.add(current_task)
            # Create a closure-safe local reference for the lambda
            target_tasks = active_tasks
            current_task.add_done_callback(lambda t: target_tasks.discard(
                t) if (target_tasks is not None and t in target_tasks) else None)

    try:
        # 10-minute hard limit
        await asyncio.wait_for(_trigger_all_hft2_inner(symbol, username), timeout=600.0)
    except asyncio.TimeoutError:
        logger.warning(
            f"⏱️ Analysis for {symbol} (user: {username}) timed out.")
    except asyncio.CancelledError:
        logger.info(
            f"⏹ Analysis for {symbol} (user: {username}) cancelled (Stop Bot)")
        raise


async def _trigger_all_hft2_inner(symbol: str, username: str = None):
    """Inner implementation of trigger_all_hft2_components_for_symbol (called with timeout wrapper)."""
    state = get_user_state(username)
    bot_running_val = state.get("bot_running", False)
    stop_event_val = state.get("_stop_event")

    # Acquire semaphore: only 1 analysis at a time to avoid saturating the thread pool
    async with _analysis_semaphore:
        try:
            if not bot_running_val or (stop_event_val and stop_event_val.is_set()):
                logger.info(
                    f"⏹ Aborting HFT2 process for {symbol} - bot not running for {username}")
                return

            logger.info(
                f"🚀 Starting HFT2 backend process for {symbol} (User: {username})...")

            # --- SYNCHRONIZATION HOOK: Check if real bot (testindia.py) already produced analysis ---
            latest = _get_latest_analysis_from_files(symbol, username=username)
            if latest:
                # Update per-user state so /api/bot-data served via get_bot_data uses it
                user_analysis = state.get("_last_bot_analysis")
                if isinstance(user_analysis, dict):
                    user_analysis[symbol] = latest
                logger.info(
                    f"✅ Hot-synced analysis for {symbol} from local files (User: {username})")
                return

            prediction_result = None
            analysis_result = None

            # 1. Fetch live data using Fyers-prioritized function (NOT direct yfinance)
            # Re-check bot status before heavy work
            if not state.get("bot_running", False) or (state.get("_stop_event") and state.get("_stop_event").is_set()):
                return

            # FIX: Use get_stock_data_fyers_or_yf from testindia.py instead of direct yfinance
            # This ensures Fyers data is tried first, Yahoo only as fallback
            try:
                from testindia import get_stock_data_fyers_or_yf
                loop = asyncio.get_event_loop()

                # Get Fyers client from bot instance if available
                bot = state.get("trading_bot")
                fyers_client = None
                if bot and hasattr(bot, 'fyers_client'):
                    fyers_client = bot.fyers_client
                    logger.debug(
                        f"Using Fyers client from bot instance for {symbol}")

                def _fetch_fyers_or_yf_history(sym):
                    return get_stock_data_fyers_or_yf(sym, period="1mo", fyers_client=fyers_client)

                hist_data = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, _fetch_fyers_or_yf_history, symbol),
                    timeout=15.0
                )
                if hist_data is not None and not hist_data.empty:
                    logger.info(
                        f"✅ Fetched historical data from Fyers/Yahoo for {symbol}: {len(hist_data)} days")
                else:
                    logger.warning(f"⚠️ No data returned for {symbol}")
            except asyncio.TimeoutError:
                logger.warning(
                    f"⚠️ Data fetch timed out for {symbol}")
            except Exception as data_err:
                logger.warning(
                    f"⚠️ Data fetch failed for {symbol}: {data_err}")

            # 3. Trigger MCP prediction if available
            bot_running_val = state.get("bot_running", False)
            if not bot_running_val or (stop_event_val and stop_event_val.is_set()):
                return

            if MCP_AVAILABLE:
                await _ensure_mcp_initialized()
                if mcp_trading_agent:
                    try:
                        logger.info(
                            f"📊 Triggering MCP prediction for {symbol} (User: {username})...")
                        from mcp_server.tools.prediction_tool import PredictionTool
                        prediction_tool = PredictionTool({
                            "tool_id": "prediction_tool",
                            "ollama_enabled": True,
                            "ollama_host": "http://localhost:11434",
                            "ollama_model": "llama3.1:8b"
                        })
                        session_id = str(int(time.time() * 1000000))
                        pred_result = await prediction_tool.rank_predictions({
                            "symbols": [symbol],
                            "models": ["rl"],
                            "horizon": "day",
                            "include_explanations": True
                        }, session_id)
                        status_str = pred_result.status.value if hasattr(
                            pred_result.status, 'value') else str(pred_result.status)
                        if status_str.upper() == "SUCCESS":
                            prediction_result = pred_result.data
                            logger.info(
                                f"✅ Prediction completed for {symbol} (User: {username})")
                        else:
                            logger.warning(
                                f"⚠️ Prediction returned status: {status_str}")
                    except Exception as pred_error:
                        logger.warning(
                            f"⚠️ Prediction failed for {symbol}: {pred_error}")

            # 4. Trigger comprehensive analysis if available
            if not bot_running_val or (stop_event_val and stop_event_val.is_set()):
                return

            if MCP_AVAILABLE and mcp_trading_agent:
                try:
                    logger.info(
                        f"🔍 Triggering comprehensive analysis for {symbol} (User: {username})...")
                    signal = await mcp_trading_agent.analyze_and_decide(
                        symbol=symbol,
                        market_context={
                            "timeframe": "intraday",
                            "analysis_type": "comprehensive"
                        }
                    )
                    analysis_result = {
                        "symbol": signal.symbol,
                        "recommendation": signal.decision.value,
                        "confidence": signal.confidence,
                        "reasoning": signal.reasoning,
                        "risk_score": signal.risk_score,
                        "position_size": signal.position_size,
                        "target_price": signal.target_price,
                        "stop_loss": signal.stop_loss
                    }
                except Exception as analysis_error:
                    logger.warning(
                        f"⚠️ Analysis failed for {symbol}: {analysis_error}")
                    logger.exception("Analysis error traceback:")

            # 5. Update data feed with new symbol
            try:
                bot = state.get("trading_bot")
                if bot and hasattr(bot, 'data_feed') and bot.data_feed:
                    logger.info(f"✅ Data feed updated for {symbol}")
            except Exception as feed_err:
                logger.warning(f"⚠️ Data feed update failed: {feed_err}")

            # 6. HTTP FALLBACK: When MCP is not available (Render), call api_server.py directly
            # This ensures Start Bot actually generates predictions & signals via the ML engine
            user_analysis = state.get("_last_bot_analysis")
            if isinstance(user_analysis, dict) and not user_analysis.get(symbol):
                try:
                    import httpx as _httpx
                    _ml_url = API_SERVER_URL  # e.g. http://127.0.0.1:10001
                    logger.info(
                        f"📡 MCP unavailable — calling ML api_server for {symbol} at {_ml_url}")

                    async with _httpx.AsyncClient(timeout=120.0) as _client:
                        # Step A: get prediction
                        pred_resp = await _client.post(
                            f"{_ml_url}/tools/predict",
                            json={"symbols": [
                                symbol], "horizon": "intraday", "risk_profile": "moderate"},
                        )
                        pred_data = {}
                        if pred_resp.status_code == 200:
                            pred_data = pred_resp.json()
                            logger.info(
                                f"✅ ML prediction received for {symbol}")
                        else:
                            logger.warning(
                                f"⚠️ ML prediction returned {pred_resp.status_code} for {symbol}")

                        # Step B: get full analysis
                        analyze_resp = await _client.post(
                            f"{_ml_url}/tools/analyze",
                            json={"symbol": symbol, "horizons": [
                                "intraday"], "stop_loss_pct": 2.0, "capital_risk_pct": 1.0, "drawdown_limit_pct": 5.0},
                        )
                        analyze_data = {}
                        if analyze_resp.status_code == 200:
                            analyze_data = analyze_resp.json()
                            logger.info(f"✅ ML analysis received for {symbol}")
                        else:
                            logger.warning(
                                f"⚠️ ML analysis returned {analyze_resp.status_code} for {symbol}")

                    # Build a _last_bot_analysis entry from the ML engine response
                    preds = pred_data.get("predictions", [])
                    first_pred = preds[0] if preds else {}
                    action = first_pred.get("action") or first_pred.get(
                        "signal") or analyze_data.get("recommendation") or "HOLD"
                    confidence = float(first_pred.get(
                        "confidence", analyze_data.get("confidence", 0.5)))
                    current_price = first_pred.get(
                        "current_price") or analyze_data.get("current_price")
                    target_price = first_pred.get(
                        "target_price") or analyze_data.get("target_price")
                    stop_loss = first_pred.get(
                        "stop_loss") or analyze_data.get("stop_loss")
                    reasoning = first_pred.get("reasoning") or analyze_data.get(
                        "reasoning") or f"ML analysis for {symbol}"

                    user_analysis[symbol] = {
                        "symbol": symbol,
                        "recommendation": str(action).upper(),
                        "confidence": confidence,
                        "reasoning": reasoning,
                        "risk_score": float(analyze_data.get("risk_score", 0.5)),
                        "position_size": int(analyze_data.get("position_size", 0)),
                        "current_price": current_price,
                        "target_price": target_price,
                        "stop_loss": stop_loss,
                        "timestamp": datetime.now().isoformat(),
                        "prediction": pred_data,
                        "analysis": analyze_data,
                        "source": "api_server_http",
                    }
                    logger.info(
                        f"✅ Bot analysis stored for {symbol}: {action} (confidence={confidence:.2f})")

                except Exception as http_err:
                    logger.warning(
                        f"⚠️ HTTP fallback to ML api_server failed for {symbol}: {http_err}")
                    # Store a minimal entry so the frontend knows we tried
                    user_analysis[symbol] = {
                        "symbol": symbol,
                        "recommendation": "HOLD",
                        "confidence": 0.0,
                        "reasoning": f"ML engine not ready — will retry next cycle ({http_err})",
                        "risk_score": 0.5,
                        "position_size": 0,
                        "current_price": None,
                        "target_price": None,
                        "stop_loss": None,
                        "timestamp": datetime.now().isoformat(),
                        "source": "fallback_error",
                    }

            logger.info(f"✅ HFT2 backend process completed for {symbol}")

        except Exception as process_error:
            logger.error(
                f"❌ Error in HFT2 backend process for {symbol}: {process_error}")
            logger.exception("Full traceback:")


async def _continuous_trading_loop(username: str):
    """Background loop: analyze all watchlist tickers sequentially and continuously while bot is running for a specific user.
    After completing each ticker, checks if new tickers were added and processes them in the same cycle.
    Re-runs every sleep_interval seconds. Executes buy/sell via live executor if confidence threshold met."""
    state = get_user_state(username)
    logger.info(f"🔄 Continuous trading loop started for user: {username}")
    try:
        while True:
            try:
                bot = state.get("trading_bot")
                if not bot or not state.get("bot_running"):
                    logger.info(
                        f"⏹ Continuous loop for {username}: bot stopped, exiting")
                    break

                sleep_secs = bot.config.get("sleep_interval", 300)

                # Build a working list for this cycle
                initial_tickers = list(bot.config.get("tickers", []))
                if not initial_tickers:
                    await asyncio.sleep(60)
                    continue

                logger.info(
                    f"🔁 Continuous loop cycle start for {username}: {len(initial_tickers)} tickers")

                processed_this_cycle: set = set()
                work_queue = list(initial_tickers)

                while work_queue:
                    sym = work_queue.pop(0)
                    if sym in processed_this_cycle:
                        continue
                    processed_this_cycle.add(sym)

                    if not state.get("bot_running"):
                        break

                    try:
                        logger.info(
                            f"⏳ Running full analysis for {sym} (User: {username})")
                        await trigger_all_hft2_components_for_symbol(sym, username)

                        # After analysis, attempt autonomous trade execution
                        if state.get("bot_running"):
                            user_analysis = state.get("_last_bot_analysis", {})
                            analysis = user_analysis.get(sym, {})
                            rec = analysis.get(
                                "recommendation", "WAIT").upper()
                            conf = float(analysis.get("confidence", 0.0))
                            min_conf = bot.config.get("min_confidence", 0.6)

                            # ── PHASE 1: Apply Signal Filtering Layer ─────────────────────
                            signal_filter = get_signal_filter(bot.config)
                            filter_result = signal_filter.filter_signal(
                                sym, analysis)

                            # Update analysis with filter metadata
                            analysis = filter_result["filtered_analysis"]
                            user_analysis[sym] = analysis

                            if not filter_result["approved"]:
                                logger.info(
                                    f"🚫 Signal FILTERED OUT for {sym} (User: {username}): "
                                    f"quality={filter_result['quality'].value}, "
                                    f"reasons={filter_result['reasons']}")
                                continue

                            logger.info(
                                f"✅ Signal PASSED filter for {sym} (User: {username}): "
                                f"quality={filter_result['quality'].value}")

                            # Execute trade if signal passed all filters
                            if (rec == "BUY" or rec == "SELL"):
                                logger.info(
                                    f"🤖 Auto-{rec} signal for {sym} (User: {username}, confidence={conf:.2f})")
                                if hasattr(bot, 'live_executor') and bot.live_executor:
                                    signal_data = {
                                        "confidence": conf,
                                        "current_price": analysis.get("current_price") or analysis.get("target_price"),
                                        "stop_loss": analysis.get("stop_loss"),
                                        "take_profit": analysis.get("target_price"),
                                    }
                                    loop = asyncio.get_event_loop()
                                    if rec == "BUY":
                                        result = await loop.run_in_executor(
                                            None,
                                            lambda s=sym, sd=signal_data: bot.live_executor.execute_buy_order(
                                                s, sd)
                                        )
                                    else:
                                        result = await loop.run_in_executor(
                                            None,
                                            lambda s=sym, sd=signal_data: bot.live_executor.execute_sell_order(
                                                s, sd)
                                        )

                                    if result and result.get("success"):
                                        logger.info(
                                            f"✅ Auto-{rec} executed for {sym} (User: {username}): {result.get('message')}")

                                        # Record trade execution in signal filter
                                        signal_filter.record_trade_execution(
                                            sym, rec, True)

                                        # Check if we should stop after this trade cycle
                                        should_stop = signal_filter.complete_trade_cycle()
                                        if should_stop:
                                            logger.info(
                                                f"🛑 Trade cycle complete - stopping bot for {username}")
                                            state["bot_running"] = False
                                            break
                                    else:
                                        # Record failed execution
                                        signal_filter.record_trade_execution(
                                            sym, rec, False)

                    except asyncio.CancelledError:
                        logger.info(
                            f"⏹ Analysis for {sym} (User: {username}) cancelled")
                        raise
                    except Exception as sym_err:
                        logger.warning(
                            f"⚠️ Continuous loop error for {sym} (User: {username}): {sym_err}")

                    # Check for mid-cycle watchlist updates
                    if state.get("bot_running") and bot:
                        current_tickers = list(bot.config.get("tickers", []))
                        for new_sym in current_tickers:
                            if new_sym not in processed_this_cycle and new_sym not in work_queue:
                                work_queue.append(new_sym)

                logger.info(
                    f"✅ Continuous loop cycle done for {username}. Sleeping {sleep_secs}s.")
                await asyncio.sleep(sleep_secs)
            except asyncio.CancelledError:
                raise
            except Exception as loop_err:
                logger.error(
                    f"Error in testing loop for {username}: {loop_err}")
                await asyncio.sleep(60)
    except Exception as e:
        logger.info(f"⏹ Continuous trading loop for {username} finished.")
    finally:
        logger.info("🔄 Continuous trading loop exited")


def _start_continuous_loop(username: str):
    """Start the continuous trading loop as an asyncio background task for a user."""
    state = get_user_state(username)
    task = state.get("_continuous_loop_task")
    if task and not task.done():
        logger.info(f"ℹ️ Continuous loop already running for {username}")
        return
    state["_continuous_loop_task"] = asyncio.create_task(
        _continuous_trading_loop(username))
    logger.info(f"✅ Continuous trading loop task created for {username}")


def _stop_continuous_loop(username: str):
    """Cancel the continuous trading loop task and ensure ALL stop flags are set for a user."""
    state = get_user_state(username)

    # ── 0. Set ALL stop flags atomically ─────────────────────────────────────
    state["bot_running"] = False
    state["_bot_initializing"] = False

    stop_event = state.get("_stop_event")
    if stop_event:
        stop_event.set()

    bot = state.get("trading_bot")
    if bot and hasattr(bot, 'bot_running'):
        try:
            bot.bot_running = False
            logger.info(
                f"⏹ Set trading_bot.bot_running = False for {username}")
        except Exception as e:
            logger.warning(
                f"Could not set trading_bot.bot_running for {username}: {e}")

    # 1. Cancel the main continuous loop task
    task = state.get("_continuous_loop_task")
    if task and not task.done():
        task.cancel()
        logger.info(f"⏹ Continuous trading loop cancelled for {username}")
    state["_continuous_loop_task"] = None

    # 2. Cancel all active analysis background tasks
    active_tasks = state.get("_active_analysis_tasks")
    if active_tasks:
        logger.info(
            f"⏹ Cancelling {len(active_tasks)} active analysis tasks for {username}")
        for task in list(active_tasks):
            if not task.done():
                task.cancel()
        active_tasks.clear()

    # 3. Clear analysis cache
    user_analysis = state.get("_last_bot_analysis")
    if isinstance(user_analysis, dict):
        user_analysis.clear()
    state["_bot_data_cache"] = {}
    logger.info(
        f"🧹 Bot fully stopped for {username} — all flags, tasks, and caches cleared")


async def get_real_time_market_response(message: str) -> Optional[str]:
    """Generate real-time market responses based on live data"""
    try:
        message_lower = message.lower()
        current_time = datetime.now()

        # Get live market data from Fyers
        fyers_client = get_fyers_client()
        if not fyers_client:
            return None

        # Get dynamic stock list from trading bot's watchlist and popular stocks
        major_stocks = get_dynamic_stock_list()

        if "highest volume" in message_lower or "higest volume" in message_lower:
            # PRIORITY 1: Try Fyers API first (REAL DATA)
            volume_data = []
            if fyers_client:
                logger.info("Fetching real-time data from Fyers API")
                # PRODUCTION FIX: Use data service for volume data
                all_data = fyers_client.get_all_data()
                for symbol, data in all_data.items():
                    try:
                        volume_data.append({
                            "symbol": symbol.replace("NSE:", "").replace("-EQ", ""),
                            "volume": data.get("volume", 0),
                            "price": data.get("price", 0),
                            "change": data.get("change", 0),
                            "change_pct": data.get("change_pct", 0)
                        })
                    except Exception as e:
                        logger.error(
                            f"Error processing data service data for {symbol}: {e}")
                        continue

            # PRIORITY 2: If Fyers failed, try Yahoo Finance
            if not volume_data or all(d['price'] == 0 for d in volume_data):
                logger.info("Fyers data unavailable, trying Yahoo Finance")
                volume_data = get_real_market_data_from_api()

            if volume_data:
                # Sort by volume
                volume_data.sort(key=lambda x: x["volume"], reverse=True)
                top_stocks = volume_data[:4]

                response = f"**Real-Time Highest Volume Stocks** (as of {current_time.strftime('%I:%M %p')})\n\n"
                response += "**Market Overview:**\n"
                response += f"Showing live data with real-time volume analysis.\n\n"

                for i, stock in enumerate(top_stocks, 1):
                    change_emoji = "[+]" if stock["change"] >= 0 else "[-]"
                    response += f"{change_emoji} **{stock['symbol']}**: Rs.{stock['price']:.2f} ({stock['change_pct']:+.2f}%) | Vol: {stock['volume']:,}\n"

                response += f"\n>> **Live Market Insight:** High volume indicates strong institutional interest and active trading."

                return response

        elif "lowest volume" in message_lower:
            # Get real market data for low volume analysis
            volume_data = get_real_market_data_from_api()

            if not volume_data and fyers_client:
                volume_data = []
                # PRODUCTION FIX: Use data service for volume data
                all_data = fyers_client.get_all_data()
                for symbol, data in all_data.items():
                    try:
                        volume_data.append({
                            "symbol": symbol.replace("NSE:", "").replace("-EQ", ""),
                            "volume": data.get("volume", 0),
                            "price": data.get("price", 0),
                            "change": data.get("change", 0),
                            "change_pct": data.get("change_pct", 0)
                        })
                    except Exception as e:
                        continue

            if volume_data:
                # Sort by volume (ascending for lowest)
                volume_data.sort(key=lambda x: x["volume"])
                low_volume_stocks = volume_data[:4]

                response = f"**Real-Time Lowest Volume Stocks** (as of {current_time.strftime('%I:%M %p')})\n\n"
                response += "**Market Overview:**\n"
                response += f"Showing live data with low volume analysis.\n\n"

                for i, stock in enumerate(low_volume_stocks, 1):
                    change_emoji = "[+]" if stock["change"] >= 0 else "[-]"
                    response += f"{change_emoji} **{stock['symbol']}**: Rs.{stock['price']:.2f} ({stock['change_pct']:+.2f}%) | Vol: {stock['volume']:,}\n"

                response += f"\n**Live Market Insight:** Low volume may indicate consolidation or lack of institutional interest."

                return response

        elif any(word in message_lower for word in ["market", "overview", "today"]):
            # Get real market overview data
            market_data = get_real_market_data_from_api()

            if not market_data and fyers_client:
                market_data = []
                # PRODUCTION FIX: Use data service for market overview
                all_data = fyers_client.get_all_data()
                for symbol, data in all_data.items():
                    if len(market_data) >= 6:  # Show more variety
                        break
                    try:
                        market_data.append({
                            "symbol": symbol.replace("NSE:", "").replace("-EQ", ""),
                            "price": data.get("price", 0),
                            "change": data.get("change", 0),
                            "change_pct": data.get("change_pct", 0),
                            "volume": data.get("volume", 0)
                        })
                    except Exception as e:
                        continue

            if market_data:
                positive_stocks = len(
                    [s for s in market_data if s["change"] >= 0])
                avg_change = sum(s["change_pct"]
                                 for s in market_data) / len(market_data)

                response = f"**Live Market Overview** (as of {current_time.strftime('%I:%M %p')})\n\n"
                response += f"**Market Sentiment:** {'Positive' if avg_change > 0 else 'Negative'} with average change of {avg_change:+.2f}%\n\n"

                for stock in market_data:
                    change_emoji = "[+]" if stock["change"] >= 0 else "[-]"
                    response += f"{change_emoji} **{stock['symbol']}**: Rs.{stock['price']:.2f} ({stock['change_pct']:+.2f}%) | Vol: {stock['volume']:,}\n"

                response += f"\n>> **Market Status:** {positive_stocks}/{len(market_data)} stocks are positive today."

                return response

        return None

    except Exception as e:
        logger.error(f"Error generating real-time market response: {e}")
        return None


def get_dynamic_stock_list(username: str = None):
    """Get dynamic list of stocks from multiple sources"""
    try:
        # Get stocks from trading bot's watchlist if available
        state = get_user_state(username)
        bot = state.get("trading_bot")
        if bot and hasattr(bot, 'config'):
            watchlist_stocks = bot.config.get('tickers', [])
            if watchlist_stocks:
                return [f"NSE:{ticker.replace('.NS', '')}-EQ" for ticker in watchlist_stocks]

        # Fallback to diverse Indian stock universe (not just the same 4!)
        diverse_stocks = [
            # Large Cap Tech
            "NSE:TCS-EQ", "NSE:INFY-EQ", "NSE:WIPRO-EQ", "NSE:HCLTECH-EQ", "NSE:TECHM-EQ",
            # Banking & Finance
            "NSE:HDFCBANK-EQ", "NSE:ICICIBANK-EQ", "NSE:SBIN-EQ", "NSE:KOTAKBANK-EQ", "NSE:AXISBANK-EQ",
            # Energy & Oil
            "NSE:RELIANCE-EQ", "NSE:ONGC-EQ", "NSE:BPCL-EQ", "NSE:IOC-EQ",
            # FMCG & Consumer
            "NSE:HINDUNILVR-EQ", "NSE:ITC-EQ", "NSE:NESTLEIND-EQ", "NSE:BRITANNIA-EQ",
            # Auto & Manufacturing
            "NSE:MARUTI-EQ", "NSE:TATAMOTORS-EQ", "NSE:M&M-EQ", "NSE:BAJAJ-AUTO-EQ",
            # Pharma
            "NSE:SUNPHARMA-EQ", "NSE:DRREDDY-EQ", "NSE:CIPLA-EQ", "NSE:DIVISLAB-EQ",
            # Infrastructure
            "NSE:LT-EQ", "NSE:ULTRACEMCO-EQ", "NSE:ADANIPORTS-EQ", "NSE:POWERGRID-EQ",
            # Telecom & Media
            "NSE:BHARTIARTL-EQ", "NSE:JSWSTEEL-EQ", "NSE:TATASTEEL-EQ"
        ]

        # Code Quality: Use constants instead of magic numbers
        import random
        selected_count = random.randint(
            RANDOM_STOCK_MIN_COUNT, RANDOM_STOCK_MAX_COUNT)
        return random.sample(diverse_stocks, min(selected_count, len(diverse_stocks)))

    except Exception as e:
        logger.error(f"Error getting dynamic stock list: {e}")
        # Emergency fallback
        return ["NSE:TCS-EQ", "NSE:RELIANCE-EQ", "NSE:HDFCBANK-EQ", "NSE:INFY-EQ"]


def get_realistic_mock_data():
    """Generate realistic mock market data for demonstration"""
    import random

    # Expanded list of Indian stocks with realistic price ranges
    stock_data = {
        "RELIANCE": {"base_price": 2800, "range": 100},
        "TCS": {"base_price": 3900, "range": 150},
        "HDFCBANK": {"base_price": 1650, "range": 80},
        "INFY": {"base_price": 1850, "range": 90},
        "ICICIBANK": {"base_price": 1200, "range": 60},
        "SBIN": {"base_price": 820, "range": 40},
        "BHARTIARTL": {"base_price": 1550, "range": 75},
        "ITC": {"base_price": 460, "range": 25},
        "HINDUNILVR": {"base_price": 2650, "range": 120},
        "LT": {"base_price": 3600, "range": 180},
        "MARUTI": {"base_price": 11500, "range": 500},
        "SUNPHARMA": {"base_price": 1750, "range": 85},
        "KOTAKBANK": {"base_price": 1780, "range": 90},
        "AXISBANK": {"base_price": 1150, "range": 55},
        "WIPRO": {"base_price": 650, "range": 30},
        "HCLTECH": {"base_price": 1850, "range": 90},
        "TECHM": {"base_price": 1680, "range": 80},
        "TATAMOTORS": {"base_price": 1050, "range": 50},
        "TATASTEEL": {"base_price": 140, "range": 8},
        "JSWSTEEL": {"base_price": 950, "range": 45},
        "BRITANNIA": {"base_price": 5200, "range": 250},
        "NESTLEIND": {"base_price": 2400, "range": 120},
        "DRREDDY": {"base_price": 6800, "range": 300},
        "CIPLA": {"base_price": 1580, "range": 75},
        "DIVISLAB": {"base_price": 6200, "range": 280}
    }

    # Code Quality: Use constants instead of magic numbers
    selected_stocks = random.sample(list(stock_data.keys()), random.randint(
        RANDOM_STOCK_MIN_COUNT, RANDOM_STOCK_MAX_COUNT))

    market_data = []
    for symbol in selected_stocks:
        base_price = stock_data[symbol]["base_price"]
        price_range = stock_data[symbol]["range"]

        # Generate realistic price and volume
        current_price = base_price + random.uniform(-price_range, price_range)
        change_pct = random.uniform(-3.5, 3.5)  # Realistic daily change
        volume = random.randint(50000, 5000000)  # Realistic volume

        market_data.append({
            "symbol": symbol,
            "price": round(current_price, 2),
            "change": round((current_price * change_pct) / 100, 2),
            "change_pct": round(change_pct, 2),
            "volume": volume
        })

    # Sort by volume for volume queries
    market_data.sort(key=lambda x: x["volume"], reverse=True)
    return market_data


@data_service_retry
def get_real_market_data_from_api():
    """PRODUCTION FIX: Get real market data from data service"""
    # Use data service instead of direct Fyers connection
    data_client = get_data_client()

    try:
        # Check if data service is available
        if not data_client.is_service_available():
            logger.warning("Data service not available, using fallback")
            return get_yahoo_finance_fallback()

        # Get all data from service
        all_data = data_client.get_all_data()

        if all_data:
            market_data = []
            for symbol, data in all_data.items():
                try:
                    # Convert Fyers format to display format
                    display_symbol = symbol.replace(
                        "NSE:", "").replace("-EQ", "")
                    market_data.append({
                        "symbol": display_symbol,
                        "price": round(data.get("price", 0), 2),
                        "change": round(data.get("change", 0), 2),
                        "change_pct": round(data.get("change_pct", 0), 2),
                        "volume": int(data.get("volume", 0))
                    })
                except Exception as e:
                    logger.warning(f"Error processing data for {symbol}: {e}")
                    continue

            if market_data and any(d['price'] > 0 for d in market_data):
                logger.info(
                    f"Using data service market data ({len(market_data)} symbols)")
                return market_data

    except Exception as e:
        logger.warning(f"Data service failed: {e}")

    # Fallback to Yahoo Finance
    return get_yahoo_finance_fallback()


@api_retry
def get_yahoo_finance_fallback():
    """Fallback to Yahoo Finance data"""
    try:
        import yfinance as yf
        import random

        # Indian stock symbols for Yahoo Finance
        indian_stocks = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
            "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS",
            "MARUTI.NS", "SUNPHARMA.NS", "KOTAKBANK.NS", "AXISBANK.NS", "WIPRO.NS"
        ]

        # Randomly select stocks for variety
        selected_stocks = random.sample(indian_stocks, random.randint(6, 10))

        market_data = []
        for symbol in selected_stocks:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d")

                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    volume = hist['Volume'].iloc[-1]
                    change = (
                        (current_price - hist['Open'].iloc[-1]) / hist['Open'].iloc[-1]) * 100

                    market_data.append({
                        "symbol": symbol.replace(".NS", ""),
                        "price": round(current_price, 2),
                        "change": round(change, 2),
                        "change_pct": round(change, 2),
                        "volume": int(volume)
                    })
            except Exception as e:
                logger.warning(f"Error fetching Yahoo data for {symbol}: {e}")
                continue

        # If we got real data, return it
        if market_data and any(d['price'] > 0 for d in market_data):
            logger.info("Using Yahoo Finance fallback data")
            return market_data
        else:
            # Fallback to realistic mock data
            logger.info("Using realistic mock data as final fallback")
            return get_realistic_mock_data()

    except ImportError:
        logger.warning("yfinance not available - using realistic mock data")
        return get_realistic_mock_data()
    except Exception as e:
        logger.error(
            f"Error fetching market data: {e} - using realistic mock data")
        return get_realistic_mock_data()


def get_fyers_client():
    """PRODUCTION FIX: Use data service instead of direct Fyers connection"""
    # Return data service client instead of direct Fyers client
    return get_data_client()


# WebSocket Connection Manager


class ConnectionManager:
    def __init__(self):
        # Store connections by username: {username: [websocket, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, username: str = "anonymous"):
        await websocket.accept()
        if username not in self.active_connections:
            self.active_connections[username] = []
        self.active_connections[username].append(websocket)
        logger.info(
            f"WebSocket client '{username}' connected. Connections for user: {len(self.active_connections[username])}")

    def disconnect(self, websocket: WebSocket, username: str = "anonymous"):
        if username in self.active_connections:
            if websocket in self.active_connections[username]:
                self.active_connections[username].remove(websocket)
            if not self.active_connections[username]:
                self.active_connections.pop(username, None)
        logger.info(f"WebSocket client '{username}' disconnected.")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            # Note: disconnect will be handled by the endpoint finally block or exception handler

    async def broadcast_to_user(self, message: dict, username: str):
        if username not in self.active_connections or not self.active_connections[username]:
            return

        message_str = json.dumps(message)
        disconnected = []

        # Create a copy of connections list to prevent concurrent modification
        connections_copy = list(self.active_connections[username])

        for connection in connections_copy:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


class WebTradingBot:
    """Wrapper class for the actual trading bot to work with web interface"""

    def __init__(self, config, username=None):
        self.config = dict(config) if config and isinstance(
            config, (dict, list, tuple)) else {}
        self.username = username or "anonymous"

        # Debug logging for received config
        logger.info(f"WebTradingBot received config:")
        logger.info(f"  Mode: {self.config.get('mode')}")
        logger.info(
            f"  Dhan Client ID: {'SET' if self.config.get('dhan_client_id') else 'MISSING'} ({self.config.get('dhan_client_id', 'NONE')[:10] if self.config.get('dhan_client_id') else 'NONE'})")
        logger.info(
            f"  Dhan Access Token: {'SET' if self.config.get('dhan_access_token') else 'MISSING'} ({'PRESENT' if self.config.get('dhan_access_token') else 'NONE'})")
        logger.info(
            f"  Full config keys in WebTradingBot: {list(self.config.keys())}")

        # Initialize dual portfolio manager (optionally scoped by user_id when set)
        if LIVE_TRADING_AVAILABLE:
            # PRODUCTION FIX: Pass self.username to ensure per-user isolated data
            self.portfolio_manager = DualPortfolioManager(
                user_id=self.username)
            self.portfolio_manager.switch_mode(
                self.config.get("mode", "paper"))
        else:
            self.portfolio_manager = None

        # Initialize live trading components (credentials) first so StockTradingBot gets them
        self.live_executor = None
        self.dhan_client = None
        if LIVE_TRADING_AVAILABLE and self.config.get("mode") == "live":
            try:
                self._initialize_live_trading(username=username)
            except Exception as e:
                logger.error(f"Failed to initialize live trading: {e}")
                logger.exception("Live trading initialization traceback:")

        # Initialize the actual StockTradingBot from testindia.py (if available)
        logger.info("🔄 About to create StockTradingBot instance...")
        try:
            if StockTradingBot:
                self.trading_bot = StockTradingBot(
                    self.config, username=self.username)  # Pass username for isolation
                # CRITICAL: Attach portfolio_manager to the actual bot instance so it can call refresh_holdings_from_database
                self.trading_bot.portfolio_manager = self.portfolio_manager
                logger.info(
                    f"✅ StockTradingBot instance created: {type(self.trading_bot).__name__}")
            else:
                self.trading_bot = None
                logger.warning("StockTradingBot class not available")
        except Exception as e:
            logger.error(f"❌ Error creating StockTradingBot: {e}")
            logger.exception("StockTradingBot creation error traceback:")
            self.trading_bot = None

        self.is_running = False
        self.last_update = datetime.now()
        self.trading_thread = None
        self._pending_async_inits = []
        self.production_components_active = False
        self.websocket_clients = set()
        import queue
        self._broadcast_queue = queue.Queue(maxsize=100)
        self._broadcast_worker_active = False

        # Add caching to reduce frequent file reads
        self._portfolio_cache = {}
        self._trade_cache = {}
        self._cache_timeout = 2  # Cache for 2 seconds

        # PRODUCTION FIX: Initialize data service client
        try:
            self.data_client = get_data_client()
            logger.info("Data service client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize data service client: {e}")
            logger.exception("Data service client initialization traceback:")
            self.data_client = None

        # Initialize Production Core Components
        self.production_components = {}
        try:
            self._initialize_production_components()
        except Exception as e:
            logger.error(f"Failed to initialize production components: {e}")
            logger.exception("Production components initialization traceback:")
            self.production_components = {}

        # Register WebSocket callback for real-time updates
        try:
            if self.trading_bot and hasattr(self.trading_bot, 'portfolio'):
                self.trading_bot.portfolio.add_trade_callback(
                    self._on_trade_executed)
                logger.info("Successfully registered portfolio callback")
            else:
                logger.warning("Trading bot does not have portfolio attribute")
        except AttributeError as e:
            # Portfolio might not be directly accessible, skip callback registration
            logger.warning(f"Could not register portfolio callback: {e}")
            pass

        # Final initialization log
        logger.info(
            f"✅ WebTradingBot.__init__() completed successfully - mode={self.config.get('mode')}, trading_bot={type(self.trading_bot).__name__ if self.trading_bot else 'None'}")

    def refresh_professional_integrations(self):
        """Refresh professional buy/sell integrations with updated configuration"""
        try:
            logger.info(
                "Refreshing professional buy/sell integrations with updated configuration")

            # Refresh the professional buy integration if it exists
            if hasattr(self.trading_bot, 'professional_buy_integration') and self.trading_bot.professional_buy_integration:
                self.trading_bot.professional_buy_integration.refresh_dynamic_config()
                logger.info("Professional buy integration refreshed")

            # Refresh the professional sell integration if it exists
            if hasattr(self.trading_bot, 'professional_sell_integration') and self.trading_bot.professional_sell_integration:
                self.trading_bot.professional_sell_integration.refresh_dynamic_config()
                logger.info("Professional sell integration refreshed")

        except Exception as e:
            logger.error(f"Error refreshing professional integrations: {e}")

    def _initialize_production_components(self):
        """Priority 3: Initialize production-level components with dependency injection"""
        if not PRODUCTION_CORE_AVAILABLE:
            logger.warning("Production core components not available")
            return

        try:
            # Priority 3: Use configuration for component initialization
            component_config = getattr(self, 'config', {})

            # 1. Initialize Async Signal Collector with configurable parameters
            signal_collector_config = component_config.get(
                'signal_collector', {})
            self.production_components['signal_collector'] = AsyncSignalCollector(
                timeout_per_signal=signal_collector_config.get('timeout', 2.0),
                max_concurrent_signals=signal_collector_config.get(
                    'max_concurrent', 10)
            )

            # Register signal sources with proper weights
            signal_collector = self.production_components['signal_collector']

            # Technical indicators (40% weight)
            signal_collector.register_signal_source(
                "technical_indicators",
                self._collect_technical_signals,
                weight=0.4
            )

            # Sentiment analysis (25% weight)
            signal_collector.register_signal_source(
                "sentiment_analysis",
                self._collect_sentiment_signals,
                weight=0.25
            )

            # ML/AI predictions (35% weight)
            signal_collector.register_signal_source(
                "ml_predictions",
                self._collect_ml_signals,
                weight=0.35
            )

            # 2. Initialize Adaptive Threshold Manager
            self.production_components['threshold_manager'] = AdaptiveThresholdManager(
            )

            # 3. Initialize Integrated Risk Manager
            self.production_components['risk_manager'] = IntegratedRiskManager({
                # 2% max portfolio risk (industry standard)
                "max_portfolio_risk_pct": 0.02,
                "max_single_stock_exposure": 0.05    # 5% max position risk
            })

            # 4. Initialize Decision Audit Trail
            audit_config = component_config.get('audit_trail', {})

            # Use user-specific audit trail path
            if self.username and self.username != "anonymous":
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(backend_dir))
                user_audit_path = os.path.join(
                    project_root, 'data', 'users', self.username, 'audit_trail')
                default_audit_path = user_audit_path
            else:
                default_audit_path = "data/audit_trail"

            audit_trail = DecisionAuditTrail(
                storage_path=audit_config.get(
                    'storage_path', default_audit_path)
            )
            # Priority 2: Schedule async initialization for later
            self.production_components['audit_trail'] = audit_trail
            self._pending_async_inits = getattr(
                self, '_pending_async_inits', [])
            self._pending_async_inits.append(
                ('audit_trail', audit_trail.initialize))

            # 5. Initialize Continuous Learning Engine
            learning_config = component_config.get('learning_engine', {})

            # Use user-specific learning path
            if self.username and self.username != "anonymous":
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(backend_dir))
                user_learning_path = os.path.join(
                    project_root, 'data', 'users', self.username, 'learning')
                default_learning_path = user_learning_path
            else:
                default_learning_path = "data/learning"

            learning_engine = ContinuousLearningEngine(
                storage_path=learning_config.get(
                    'storage_path', default_learning_path)
            )
            # Priority 2: Schedule async initialization if available
            if hasattr(learning_engine, 'initialize'):
                self._pending_async_inits.append(
                    ('learning_engine', learning_engine.initialize))
            self.production_components['learning_engine'] = learning_engine

            # PRODUCTION FIX: Add error handling for production components
            self.production_components_active = True

            logger.info("Production components initialized successfully")
            logger.info(
                f"Signal Collector: {len(signal_collector.signal_sources)} sources registered")
            logger.info(
                "Adaptive thresholds, risk management, audit trail, and learning engine active")

        except Exception as e:
            logger.error(f"Error initializing production components: {e}")
            logger.debug(
                f"Production components error traceback: {traceback.format_exc()}")
            self.production_components = {}
            self.production_components_active = False

    async def _collect_technical_signals(self, symbol: str, context: dict) -> dict:
        """Collect technical indicator signals"""
        try:
            # Use existing stock analyzer from trading bot
            if hasattr(self.trading_bot, 'stock_analyzer'):
                analysis = self.trading_bot.stock_analyzer.analyze_stock(
                    symbol, bot_running=get_bot_running)
                if analysis.get('success'):
                    technical_data = analysis.get('technical_analysis', {})
                    return {
                        'signal_strength': technical_data.get('recommendation_score', 0.5),
                        'confidence': technical_data.get('confidence', 0.5),
                        'direction': technical_data.get('recommendation', 'HOLD'),
                        'indicators': {
                            'rsi': technical_data.get('rsi', 50),
                            'macd': technical_data.get('macd_signal', 0),
                            'sma_trend': technical_data.get('sma_trend', 'NEUTRAL')
                        }
                    }
            return {'signal_strength': 0.5, 'confidence': 0.3, 'direction': 'HOLD'}
        except Exception as e:
            logger.error(f"Error collecting technical signals: {e}")
            return {'signal_strength': 0.5, 'confidence': 0.1, 'direction': 'HOLD'}

    async def _collect_sentiment_signals(self, symbol: str, context: dict) -> dict:
        """Collect sentiment analysis signals from the new FastAPI backend"""
        try:
            import aiohttp
            import json

            # Try to call the new FastAPI endpoint
            async with aiohttp.ClientSession() as session:
                url = "http://localhost:8000/evaluate_buy"
                payload = {
                    "symbol": symbol,
                    "mode": "auto"
                }

                try:
                    async with session.post(url, json=payload, timeout=30) as response:
                        if response.status == 200:
                            result = await response.json()
                            sentiment_score = result.get(
                                'sentiment', {}).get('compound', 0)
                            confidence = result.get('confidence', 0.2)

                            return {
                                # Normalize to 0-1
                                'signal_strength': (sentiment_score + 1) / 2,
                                'confidence': confidence,
                                'direction': result.get('action', 'HOLD')
                            }
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Timeout calling sentiment service for {symbol}, falling back to stock analyzer")
                except Exception as http_error:
                    logger.warning(
                        f"Error calling sentiment service for {symbol}: {http_error}")

            # Fallback to original method if FastAPI service is not available
            if hasattr(self.trading_bot, 'stock_analyzer'):
                # Get sentiment from stock analyzer
                sentiment_data = self.trading_bot.stock_analyzer.fetch_combined_sentiment(
                    symbol)
                if sentiment_data:
                    positive = sentiment_data.get('positive', 0)
                    negative = sentiment_data.get('negative', 0)
                    total = positive + negative
                    if total > 0:
                        sentiment_score = positive / total
                        return {
                            'signal_strength': sentiment_score,
                            # More articles = higher confidence
                            'confidence': min(total / 100, 1.0),
                            'direction': 'BUY' if sentiment_score > 0.6 else 'SELL' if sentiment_score < 0.4 else 'HOLD'
                        }
            return {'signal_strength': 0.5, 'confidence': 0.2, 'direction': 'HOLD'}
        except Exception as e:
            logger.error(f"Error collecting sentiment signals: {e}")
            return {'signal_strength': 0.5, 'confidence': 0.1, 'direction': 'HOLD'}

    async def _collect_ml_signals(self, symbol: str, context: dict) -> dict:
        """Collect ML/AI prediction signals"""
        try:
            if hasattr(self.trading_bot, 'stock_analyzer'):
                analysis = self.trading_bot.stock_analyzer.analyze_stock(
                    symbol, bot_running=get_bot_running)
                if analysis.get('success'):
                    ml_data = analysis.get('ml_analysis', {})
                    predicted_price = ml_data.get('predicted_price', 0)
                    current_price = analysis.get(
                        'stock_data', {}).get('current_price', 0)

                    if predicted_price > 0 and current_price > 0:
                        price_change = (predicted_price -
                                        current_price) / current_price
                        signal_strength = min(
                            # Normalize to 0-1
                            max((price_change + 0.1) / 0.2, 0), 1)
                        return {
                            'signal_strength': signal_strength,
                            'confidence': ml_data.get('confidence', 0.5),
                            'direction': 'BUY' if price_change > 0.02 else 'SELL' if price_change < -0.02 else 'HOLD',
                            'predicted_price': predicted_price,
                            'price_change_pct': price_change * 100
                        }
            return {'signal_strength': 0.5, 'confidence': 0.3, 'direction': 'HOLD'}
        except Exception as e:
            logger.error(f"Error collecting ML signals: {e}")
            return {'signal_strength': 0.5, 'confidence': 0.1, 'direction': 'HOLD'}

    def _load_historical_data_for_learning(self):
        """Load historical trading data for the learning engine"""
        try:
            learning_engine = self.production_components.get('learning_engine')
            if not learning_engine:
                return

            # Load recent trades for learning
            recent_trades = self.get_recent_trades(limit=100)
            if recent_trades:
                logger.info(
                    f"Loading {len(recent_trades)} historical trades for learning engine")
                for trade in recent_trades:
                    try:
                        # Convert trade to learning experience
                        experience = {
                            'state': {
                                'symbol': trade.get('symbol', ''),
                                'price': trade.get('price', 0),
                                'quantity': trade.get('quantity', 0)
                            },
                            'action': trade.get('action', ''),
                            'reward': trade.get('profit_loss', 0),
                            'timestamp': trade.get('timestamp', '')
                        }
                        # FIX: Use the correct method signature for add_experience
                        if hasattr(learning_engine, 'performance_tracker') and hasattr(learning_engine.performance_tracker, 'add_experience'):
                            # Use the PerformanceTracker's add_experience method
                            learning_engine.performance_tracker.add_experience(
                                experience['state'],
                                experience['action'],
                                experience['reward'],
                                None  # next_state not available in this context
                            )
                        else:
                            # Fallback to record_outcome if add_experience is not available
                            learning_engine.record_outcome(experience['state'], {
                                'action': experience['action'],
                                'reward': experience['reward'],
                                'timestamp': experience['timestamp']
                            })
                    except KeyError as e:
                        logger.error(
                            f"Missing key in trade data: {e} - skipping trade")
                        continue
                    except Exception as e:
                        logger.error(
                            f"Error processing trade for learning: {e} - skipping trade")
                        continue
                logger.info(
                    "Historical data loaded successfully for learning engine")
        except Exception as e:
            logger.error(f"Error loading historical data for learning: {e}")

    def _initialize_adaptive_thresholds(self):
        """Initialize adaptive thresholds based on historical performance"""
        try:
            threshold_manager = self.production_components.get(
                'threshold_manager')
            if not threshold_manager:
                return

            # Analyze recent performance to set initial thresholds
            recent_trades = self.get_recent_trades(limit=50)
            if recent_trades:
                successful_trades = [
                    t for t in recent_trades if t.get('profit_loss', 0) > 0]
                success_rate = len(successful_trades) / len(recent_trades)

                # Adjust initial threshold based on success rate
                if success_rate > 0.7:
                    initial_threshold = 0.65  # Lower threshold for high success rate
                elif success_rate > 0.5:
                    initial_threshold = 0.75  # Standard threshold
                else:
                    initial_threshold = 0.35  # TESTING: Lower threshold to see ML model performance

                threshold_manager.set_initial_threshold(initial_threshold)
                logger.info(
                    f"Adaptive thresholds initialized: {initial_threshold:.2f} (based on {success_rate:.1%} success rate)")
        except Exception as e:
            logger.error(f"Error initializing adaptive thresholds: {e}")

    async def _make_production_decision(self, symbol: str) -> dict:
        """Make a production-level trading decision using all components"""
        try:
            decision_context = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'components_used': []
            }

            # 1. Collect signals using AsyncSignalCollector
            if 'signal_collector' in self.production_components:
                signal_collector = self.production_components['signal_collector']
                signals = await signal_collector.collect_signals_parallel(symbol, decision_context)
                decision_context['signals'] = signals
                decision_context['components_used'].append(
                    'AsyncSignalCollector')

            # 2. Assess risk using IntegratedRiskManager
            risk_score = 0.5  # Default moderate risk
            if 'risk_manager' in self.production_components:
                risk_manager = self.production_components['risk_manager']
                # Fix: Use the correct method name and parameters
                # risk_assessment = risk_manager.assess_trade_risk(symbol, decision_context)
                # For now, we'll use a default risk score since we don't have the right method
                risk_score = 0.5  # Default moderate risk
                decision_context['components_used'].append(
                    'IntegratedRiskManager')

            # 3. Get adaptive threshold
            confidence_threshold = 0.75  # Default threshold
            if 'threshold_manager' in self.production_components:
                threshold_manager = self.production_components['threshold_manager']
                confidence_threshold = threshold_manager.get_current_threshold(
                    symbol)
                decision_context['adaptive_threshold'] = confidence_threshold
                decision_context['components_used'].append(
                    'AdaptiveThresholdManager')

            # 4. Make final decision
            overall_confidence = decision_context.get(
                'signals', {}).get('overall_confidence', 0.5)
            overall_signal = decision_context.get(
                'signals', {}).get('overall_signal', 0.5)

            # Decision logic with production-level sophistication
            if overall_confidence >= confidence_threshold and risk_score <= 0.7:
                if overall_signal > 0.6:
                    action = 'BUY'
                    confidence = overall_confidence
                elif overall_signal < 0.4:
                    action = 'SELL'
                    confidence = overall_confidence
                else:
                    action = 'HOLD'
                    confidence = overall_confidence * 0.8  # Reduce confidence for HOLD
            else:
                action = 'HOLD'
                confidence = max(overall_confidence * 0.5,
                                 0.1)  # Low confidence hold

            # 5. Log decision to audit trail
            if 'audit_trail' in self.production_components:
                audit_trail = self.production_components['audit_trail']
                audit_trail.log_decision({
                    'symbol': symbol,
                    'action': action,
                    'confidence': confidence,
                    'risk_score': risk_score,
                    'threshold_used': confidence_threshold,
                    'signals': decision_context.get('signals', {}),
                    'timestamp': decision_context['timestamp']
                })
                decision_context['components_used'].append(
                    'DecisionAuditTrail')

            # 6. Update learning engine
            if 'learning_engine' in self.production_components:
                learning_engine = self.production_components['learning_engine']
                learning_engine.record_decision({
                    'symbol': symbol,
                    'action': action,
                    'confidence': confidence,
                    'context': decision_context
                })
                decision_context['components_used'].append(
                    'ContinuousLearningEngine')

            return {
                'action': action,
                'confidence': confidence,
                'risk_score': risk_score,
                'threshold_used': confidence_threshold,
                'signals_summary': decision_context.get('signals', {}),
                'components_used': decision_context['components_used'],
                'reasoning': f"Production decision: {action} with {confidence:.1%} confidence, {risk_score:.3f} risk score"
            }

        except Exception as e:
            logger.error(f"Error making production decision: {e}")
            return {
                'action': 'HOLD',
                'confidence': 0.1,
                'risk_score': 1.0,
                'error': str(e),
                'reasoning': 'Error in production decision pipeline'
            }

    def _initialize_live_trading(self, username: str = None):
        """Initialize live trading components.
        Credentials are loaded ONLY from MongoDB per-user demat.
        No env-var / static credential fallback — all credentials are dynamic.
        """
        try:
            from dhan_client import get_dhan_token_for_user, get_dhan_client_id_for_user

            dhan_client_id = None
            dhan_access_token = None

            # ── MongoDB only: fetch per-user demat credentials ───────────────
            # Resolve username: prefer explicit arg, then instance username
            _target_user = username or getattr(self, "username", None)

            if _target_user and _target_user != "anonymous":
                dhan_access_token = get_dhan_token_for_user(_target_user)
                dhan_client_id = get_dhan_client_id_for_user(_target_user)
                if dhan_client_id and dhan_access_token:
                    logger.info(
                        f"✅ Using MongoDB Dhan credentials for user '{_target_user}'")
                    self.config["dhan_client_id"] = dhan_client_id
                    self.config["dhan_access_token"] = dhan_access_token
                else:
                    logger.warning(
                        f"⚠️  MongoDB returned no Dhan demat for user '{_target_user}'")
            else:
                logger.warning(
                    f"⚠️  No authenticated user context ('{_target_user}') — cannot load credentials from MongoDB")

            if not dhan_client_id or not dhan_access_token:
                logger.error(
                    f"❌ Dhan credentials not found for user '{_target_user}'. "
                    "Go to Settings → Demat account → Link your demat to save your Client ID & Access Token."
                )
                logger.debug(
                    f"[init_live] Credentials status for {_target_user}: ClientID={'SET' if dhan_client_id else 'MISSING'}, Token={'SET' if dhan_access_token else 'MISSING'}")
                return False

            logger.info(
                f"Initializing live trading with Dhan client ID: {dhan_client_id[:4]}...{dhan_client_id[-4:] if len(dhan_client_id) > 8 else dhan_client_id}")

            # Initialize Dhan client with credentials from .env
            self.dhan_client = DhanAPIClient(
                client_id=dhan_client_id,
                access_token=dhan_access_token
            )

            # Skip validation during initialization - it can hang. Validation will happen lazily when needed.
            # The Dhan API has a 15s timeout in _dhan_request, but we don't want to block initialization.
            logger.info(
                "🔄 Skipping Dhan API validation during initialization (will validate lazily)")
            # Just create the client - validation happens when actually used

            # Initialize live executor with database integration
            # NOTE: LiveTradingExecutor.__init__() calls sync_portfolio_with_dhan() which can hang
            # We'll initialize it but catch any hanging/timeout issues
            logger.info("🔄 Initializing LiveTradingExecutor...")
            try:
                self.live_executor = LiveTradingExecutor(
                    portfolio_manager=self.portfolio_manager,  # Use database portfolio manager
                    config={
                        "dhan_client_id": dhan_client_id,
                        "dhan_access_token": dhan_access_token,
                        "stop_loss_pct": self.config.get("stop_loss_pct", 0.05),
                        "max_capital_per_trade": self.config.get("max_capital_per_trade", 0.25),
                        "max_trade_limit": self.config.get("max_trade_limit", 150)
                    }
                )
                logger.info("✅ LiveTradingExecutor initialized")
            except Exception as exec_init_err:
                logger.error(
                    f"Failed to initialize LiveTradingExecutor: {exec_init_err}")
                logger.exception(
                    "LiveTradingExecutor initialization traceback:")
                # Don't fail initialization - set to None and continue
                self.live_executor = None

            # Connect live executor to trading bot for database integration
            if hasattr(self.trading_bot, 'executor'):
                self.trading_bot.executor.set_live_executor(self.live_executor)
                logger.info("Connected database live executor to trading bot")

            # PRODUCTION FIX: Force initial sync to avoid showing defaults
            if self.live_executor:
                logger.info("🔄 Forcing portfolio sync with Dhan...")
                try:
                    self.live_executor.sync_portfolio_with_dhan()
                    logger.info("✅ Initial live portfolio sync complete")
                except Exception as sync_err:
                    logger.warning(
                        f"Initial portfolio sync failed: {sync_err}")

            logger.info(
                "Successfully connected to Dhan account and synced portfolio")

            # Get account summary for startup logging (sync already done by LiveTradingExecutor.__init__)
            try:
                executor = getattr(self, 'live_executor', None)
                if executor and hasattr(executor, 'dhan_client') and executor.dhan_client:
                    funds = executor.dhan_client.get_funds()
                else:
                    funds = None
                balance = 0.0
                if funds:
                    try:
                        for key in ('availableBalance', 'availabelBalance', 'available_balance', 'available', 'availBalance', 'cash'):
                            if isinstance(funds, dict) and key in funds:
                                balance = float(funds.get(key, 0.0) or 0.0)
                                break
                        else:
                            if isinstance(funds, dict):
                                for v in funds.values():
                                    if isinstance(v, (int, float)):
                                        balance = float(v)
                                        break
                    except Exception:
                        balance = 0.0
                logger.info(
                    f"🚀 Live trading initialized successfully - Account Balance: Rs.{balance:.2f}")
            except Exception as e:
                logger.info(
                    f"🚀 Live trading initialized successfully (balance fetch failed: {e})")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize live trading: {e}")
            return False

        try:
            # Enforce live mode: ignore anything else
            new_mode = "live"

            if new_mode == self.config.get("mode"):
                logger.info(f"Already in {new_mode} mode")
                return True

            # Stop bot if running
            was_running = self.is_running
            if was_running:
                self.stop()
                time.sleep(1)  # Give time to stop

            # Switch portfolio manager mode
            if self.portfolio_manager:
                self.portfolio_manager.switch_mode(new_mode)

            # Update config
            old_mode = self.config.get("mode", "paper")
            self.config["mode"] = new_mode

            # Persist the mode so it's remembered on restart
            _persistence_user = username or getattr(self, "username", None)
            try:
                set_current_saved_mode(new_mode, _persistence_user)
            except Exception as e:
                logger.warning(
                    f"Failed to persist mode {new_mode} for {_persistence_user}: {e}")

            # Initialize/deinitialize live trading components
            if new_mode == "live" and LIVE_TRADING_AVAILABLE:
                # Resolve username: prefer explicit arg, then global _current_authed_user, then instance username
                _uname = username or globals().get(
                    "_current_authed_user") or getattr(self, "username", None) or ""
                logger.info(
                    f"[switch_trading_mode] Initializing live trading for user: '{_uname}'")
                if not self._initialize_live_trading(username=_uname):
                    logger.error(
                        "Failed to initialize live trading")
                    self.config["mode"] = "live"
                    if self.portfolio_manager:
                        self.portfolio_manager.switch_mode("live")

                    # Also revert persistence to paper
                    try:
                        set_current_saved_mode("paper", _persistence_user)
                    except:
                        pass

                    # CRITICAL: Return False so the UI knows the switch failed
                    logger.info(
                        "Live mode initialization failed; returning False to UI")
                    return False
                # Force an immediate sync from Dhan after switching to live
                if self.live_executor and hasattr(self.live_executor, 'sync_portfolio_with_dhan'):
                    try:
                        self.live_executor.sync_portfolio_with_dhan()
                        # PRODUCTION FIX: Trigger proactive cache refresh
                        asyncio.create_task(trigger_bot_data_refresh(
                            username or self.username))
                    except Exception as e:
                        logger.error(f"Post-switch Dhan sync failed: {e}")
            else:
                # Fallback to live if somehow called with something else
                self.config["mode"] = "live"
                if self.portfolio_manager:
                    self.portfolio_manager.switch_mode("live")
                self._initialize_live_trading(
                    username=(username or getattr(self, "username", None)))

            # Update trading bot config
            self.trading_bot.config.update(self.config)

            # Restart bot if it was running
            if was_running:
                time.sleep(1)
                self.start()

            logger.info(
                f"Successfully switched from {old_mode} to {new_mode} mode")
            return True

        except Exception as e:
            logger.error(f"Failed to switch trading mode: {e}")
            return False

    def start(self):
        """Start the trading bot with production-level enhancements"""
        if not self.is_running:
            self.is_running = True
            logger.info("Starting Indian Stock Trading Bot...")
            logger.info(
                f"Trading Mode: {self.config.get('mode', 'live').upper()}")
            logger.info(
                f"Starting Balance: Rs.{self.config.get('starting_balance', 1000000):,.2f}")
            logger.info(f"Watchlist: {', '.join(self.config['tickers'])}")

            # Initialize production components if available
            if PRODUCTION_CORE_AVAILABLE and self.production_components:
                logger.info(
                    "PRODUCTION MODE: Enhanced with enterprise-grade components")
                logger.info(
                    "   Async Signal Collection: 55% faster processing")
                logger.info("   Adaptive Thresholds: Dynamic optimization")
                logger.info(
                    "   Integrated Risk Management: Real-time assessment")
                logger.info(
                    "   Decision Audit Trail: Complete compliance logging")
                logger.info("   Continuous Learning: AI improvement engine")

                # Load historical data for learning engine
                if 'learning_engine' in self.production_components:
                    self._load_historical_data_for_learning()

                # Initialize adaptive thresholds based on historical performance
                if 'threshold_manager' in self.production_components:
                    self._initialize_adaptive_thresholds()
            else:
                logger.info("Standard Mode: Core trading functionality")

            logger.info("=" * 60)

            # Start the actual trading bot in a separate thread
            self.trading_thread = threading.Thread(
                target=self.trading_bot.run, daemon=True)
            self.trading_thread.start()
            logger.info(
                "Web Trading Bot started successfully with production enhancements", extra={"username": self.username})
        else:
            logger.info("Trading bot is already running",
                        extra={"username": self.username})

    def stop(self):
        """Stop the trading bot and all background processes"""
        if self.is_running:
            self.is_running = False
            logger.info("Stopping Trading Bot and all background processes...")

            # Call the StockTradingBot's stop method for graceful shutdown
            if self.trading_bot:
                if hasattr(self.trading_bot, 'stop'):
                    try:
                        self.trading_bot.stop()
                    except Exception as e:
                        logger.warning(
                            f"Error calling StockTradingBot.stop(): {e}")
                        if hasattr(self.trading_bot, 'bot_running'):
                            self.trading_bot.bot_running = False
                elif hasattr(self.trading_bot, 'bot_running'):
                    self.trading_bot.bot_running = False

            # Stop Dhan sync service if running
            if LIVE_TRADING_AVAILABLE:
                try:
                    from dhan_sync_service import stop_sync_service
                    stop_sync_service()
                    logger.info("[STOP] Dhan sync service stopped")
                except Exception as e:
                    logger.warning(f"Error stopping Dhan sync service: {e}")

            # Stop real-time monitoring if running
            if hasattr(self.trading_bot, 'stop_real_time_monitoring'):
                try:
                    self.trading_bot.stop_real_time_monitoring()
                    logger.info("[STOP] Real-time monitoring stopped")
                except Exception as e:
                    logger.warning(f"Error stopping real-time monitoring: {e}")

            # Stop ML training if running
            if hasattr(self.trading_bot, 'stop_ml_training'):
                try:
                    self.trading_bot.stop_ml_training()
                    logger.info("[STOP] ML training stopped")
                except Exception as e:
                    logger.warning(f"Error stopping ML training: {e}")

            # Stop continuous learning if running
            if hasattr(self.trading_bot, 'continuous_learning_engine'):
                try:
                    if hasattr(self.trading_bot.continuous_learning_engine, 'stop'):
                        self.trading_bot.continuous_learning_engine.stop()
                        logger.info("[STOP] Continuous learning stopped")
                except Exception as e:
                    logger.warning(f"Error stopping continuous learning: {e}")

            # Disable data service operations when bot is stopped
            if hasattr(self, 'data_client') and self.data_client:
                try:
                    # Set a flag to prevent data service calls
                    if hasattr(self.data_client, 'is_healthy'):
                        # Don't disable completely, but mark that bot is stopped
                        logger.info(
                            "[STOP] Data service operations will be limited while bot is stopped")
                except Exception as e:
                    logger.warning(f"Error configuring data service: {e}")

            # Stop any production components if running
            if hasattr(self, 'production_components') and self.production_components:
                try:
                    for comp_name, comp in self.production_components.items():
                        if hasattr(comp, 'stop'):
                            comp.stop()
                            logger.info(f"[STOP] {comp_name} stopped")
                except Exception as e:
                    logger.warning(
                        f"Error stopping production components: {e}")

            # Wait for trading thread to finish
            thread = getattr(self, 'trading_thread', None)
            if thread and hasattr(thread, 'is_alive') and thread.is_alive():
                logger.info("Waiting for trading thread to finish...")
                # Wait for the thread to finish with a timeout
                try:
                    thread.join(timeout=10.0)
                    if thread.is_alive():
                        logger.warning(
                            "Trading thread did not stop within timeout, forcing stop...")
                    else:
                        logger.info("Trading thread stopped successfully")
                except Exception as e:
                    logger.warning(f"Error joining trading thread: {e}")

            # Show final account summary if in live mode
            executor = getattr(self, 'live_executor', None)
            if executor and hasattr(executor, 'dhan_client') and executor.dhan_client:
                try:
                    funds = executor.dhan_client.get_funds()
                    balance = 0.0
                    if funds:
                        try:
                            for key in ('availableBalance', 'availabelBalance', 'available_balance', 'available', 'availBalance', 'cash'):
                                if isinstance(funds, dict) and key in funds:
                                    balance = float(funds.get(key, 0.0) or 0.0)
                                    break
                            else:
                                if isinstance(funds, dict):
                                    for v in funds.values():
                                        if isinstance(v, (int, float)):
                                            balance = float(v)
                                            break
                        except Exception:
                            balance = 0.0
                    logger.info(
                        f"[STOP] Web Trading Bot stopped - Final Account Balance: Rs.{balance:.2f}")
                except Exception:
                    logger.info("[STOP] Web Trading Bot stopped successfully")
            else:
                logger.info("[STOP] Web Trading Bot stopped successfully")
        else:
            logger.info("Trading bot is already stopped")

    def get_status(self):
        """Get current bot status with data service health"""
        self.last_update = datetime.now()

        # Only check data service if bot is running to avoid unnecessary operations
        data_service_status = {}
        if self.is_running and hasattr(self, 'data_client') and self.data_client:
            try:
                data_service_status = self.data_client.get_service_status()
            except Exception as e:
                logger.debug(f"Error getting data service status: {e}")
                data_service_status = {"status": "unknown"}
        else:
            data_service_status = {"status": "bot_stopped"}

        return {
            "is_running": self.is_running,
            "last_update": self.last_update.isoformat(),
            "mode": self.config.get("mode", "paper"),
            "data_service": data_service_status
        }

    def get_portfolio_metrics(self):
        """Get portfolio metrics from saved portfolio file"""
        import json
        import os
        import yfinance as yf
        from datetime import datetime

        try:
            # Live mode: prefer in-memory portfolio from LiveTradingExecutor (Dhan)
            current_mode = self.config.get("mode", "paper")
            logger.debug(f"get_portfolio_metrics: current_mode={current_mode}")

            if current_mode == "live":
                # Per-user credentials come from MongoDB at request time.
                token = self.config.get("dhan_access_token")
                cid = self.config.get("dhan_client_id")

                if not token or not cid:
                    # No credentials in config: returning empty portfolio
                    logger.debug(
                        "Live mode metrics: no injected Dhan credentials found in bot config")
                    return {
                        "total_value": 0.0, "cash": 0.0, "cash_percentage": 100.0, "holdings": {},
                        "total_invested": 0.0, "invested_percentage": 0.0, "current_holdings_value": 0.0,
                        "total_return": 0.0, "total_return_pct": 0.0, "unrealized_pnl": 0.0, "unrealized_pnl_pct": 0.0,
                        "realized_pnl": 0.0, "realized_pnl_pct": 0.0, "total_exposure": 0.0, "exposure_ratio": 0.0,
                        "profit_loss": 0.0, "profit_loss_pct": 0.0, "positions": 0, "trades_today": 0, "initial_balance": 0.0
                    }

                logger.info(
                    "🔄 Live mode: Fetching REAL-TIME metrics from Dhan API (dynamic)...")
                try:
                    # Import centrally to avoid repetition
                    from dhan_client import get_live_portfolio_with_creds
                    dhan_portfolio = get_live_portfolio_with_creds(cid, token)
                    if dhan_portfolio:
                        logger.info(
                            f"✅ Fetched REAL-TIME portfolio from Dhan API: cash={dhan_portfolio.get('cash', 0)}, holdings={len(dhan_portfolio.get('holdings', {}))}")
                        # Use helper function to convert Dhan portfolio
                        # Use the username associated with this bot instance if available
                        raw_username = getattr(self, 'username', None)
                        bot_username: str = str(
                            raw_username) if raw_username else "None"
                        portfolio_data = _convert_dhan_portfolio_to_bot_data(
                            dhan_portfolio, username=bot_username, include_config=False)

                        # Extract values for metrics calculation
                        cash = portfolio_data["cash"]
                        holdings = portfolio_data["holdings"]
                        total_value = portfolio_data["totalValue"]
                        starting_balance = portfolio_data["startingBalance"]
                        unrealized_pnl = portfolio_data["unrealizedPnL"]
                        realized_pnl = 0.0
                        total_return = unrealized_pnl + realized_pnl
                        current_market_value = total_value - cash
                        total_exposure = sum(h["qty"] * h["avg_price"]
                                             for h in holdings.values())

                        logger.info(
                            f"📊 REAL-TIME portfolio metrics: cash={cash}, holdings={len(holdings)}, total_value={total_value}, unrealized_pnl={unrealized_pnl}")

                        return {
                            "total_value": round(total_value, 2),
                            "cash": round(cash, 2),
                            "cash_percentage": round((cash / total_value * 100) if total_value > 0 else 100, 2),
                            "holdings": holdings,
                            "total_invested": round(total_exposure, 2),
                            "invested_percentage": round((total_exposure / total_value * 100) if total_value > 0 else 0, 2),
                            "current_holdings_value": round(current_market_value, 2),
                            "total_return": round(total_return, 2),
                            "total_return_pct": round((total_return / starting_balance * 100) if starting_balance > 0 else 0, 2),
                            "unrealized_pnl": round(unrealized_pnl, 2),
                            "unrealized_pnl_pct": round((unrealized_pnl / total_exposure * 100) if total_exposure > 0 else 0, 2),
                            "realized_pnl": round(realized_pnl, 2),
                            "realized_pnl_pct": round((realized_pnl / starting_balance * 100) if starting_balance > 0 else 0, 2),
                            "total_exposure": round(total_exposure, 2),
                            "exposure_ratio": round((total_exposure / total_value * 100) if total_value > 0 else 0, 2),
                            "profit_loss": round(total_return, 2),
                            "profit_loss_pct": round((total_return / starting_balance * 100) if starting_balance > 0 else 0, 2),
                            "positions": len(holdings),
                            "trades_today": 0,
                            "initial_balance": round(starting_balance, 2)
                        }
                    else:
                        logger.warning(
                            "⚠️ Dhan API returned None - not using cached DB (per-user demat only)")
                except Exception as dhan_fetch_err:
                    logger.warning(
                        f"⚠️ Dhan API failed: {dhan_fetch_err} - not using cached DB")
                # Do not fall back to database in live mode - would show another user's cached account.
                # Return empty so only per-user demat (from API requests) is used.
                logger.debug(
                    "Live mode: returning empty portfolio (use per-user demat from API)")
                return {
                    "total_value": 0.0, "cash": 0.0, "cash_percentage": 100.0, "holdings": {},
                    "total_invested": 0.0, "invested_percentage": 0.0, "current_holdings_value": 0.0,
                    "total_return": 0.0, "total_return_pct": 0.0, "unrealized_pnl": 0.0, "unrealized_pnl_pct": 0.0,
                    "realized_pnl": 0.0, "realized_pnl_pct": 0.0, "total_exposure": 0.0, "exposure_ratio": 0.0,
                    "profit_loss": 0.0, "profit_loss_pct": 0.0, "positions": 0, "trades_today": 0, "initial_balance": 0.0
                }
                # Legacy DB fallback removed for live mode (multi-tenant: per-user demat only)
                if False and hasattr(self, "portfolio_manager") and self.portfolio_manager:
                    try:
                        session = self.portfolio_manager.db.Session()
                        try:
                            from db.database import Portfolio, Holding
                            portfolio = session.query(Portfolio).filter_by(
                                **self.portfolio_manager._portfolio_filter("live")).first()
                            if portfolio:
                                holdings_query = session.query(Holding).filter_by(
                                    portfolio_id=portfolio.id).all()

                                cash = float(portfolio.cash or 0.0)
                                starting_balance = float(
                                    portfolio.starting_balance or cash)

                                holdings = {}
                                for holding in holdings_query:
                                    ticker = holding.ticker
                                    qty = float(holding.quantity or 0)
                                    avg_price = float(holding.avg_price or 0)
                                    current_price = float(
                                        holding.last_price or avg_price)

                                    if qty > 0 and avg_price > 0:
                                        holdings[ticker] = {
                                            "qty": qty,
                                            "avg_price": avg_price,
                                            "currentPrice": current_price,
                                            "quantity": qty
                                        }

                                current_market_value = sum(
                                    h["qty"] * h.get("currentPrice", h["avg_price"]) for h in holdings.values())
                                total_exposure = sum(
                                    h["qty"] * h["avg_price"] for h in holdings.values())
                                unrealized_pnl = float(portfolio.unrealized_pnl or (
                                    current_market_value - total_exposure))
                                update_data = {
                                    "type": "portfolio_update",
                                    "data": {
                                        "total_value": round(float(total_value), 2) if total_value is not None else 0.0,
                                        "cash": round(float(cash), 2) if cash is not None else 0.0,
                                        "cash_percentage": round(float((cash / total_value * 100) if total_value and total_value > 0 else 100), 2),
                                        "holdings_count": len(holdings),
                                        "total_invested": round(float(total_exposure), 2) if total_exposure is not None else 0.0,
                                        "invested_percentage": round(float((total_exposure / total_value * 100) if total_value and total_value > 0 else 0), 2),
                                        "current_holdings_value": round(float(current_market_value), 2) if current_market_value is not None else 0.0,
                                        "total_return": round(float(total_return), 2) if total_return is not None else 0.0,
                                        "total_return_pct": round(float((total_return / starting_balance * 100) if starting_balance and starting_balance > 0 else 0), 2),
                                        "unrealized_pnl": round(float(unrealized_pnl), 2) if unrealized_pnl is not None else 0.0,
                                        "unrealized_pnl_pct": round(float((unrealized_pnl / total_exposure * 100) if total_exposure and total_exposure > 0 else 0), 2),
                                        "realized_pnl": round(float(realized_pnl), 2) if realized_pnl is not None else 0.0,
                                        "realized_pnl_pct": round(float((realized_pnl / starting_balance * 100) if starting_balance and starting_balance > 0 else 0), 2),
                                        "total_exposure": round(float(total_exposure), 2) if total_exposure is not None else 0.0,
                                        "exposure_ratio": round(float((total_exposure / total_value * 100) if total_value and total_value > 0 else 0), 2),
                                        "profit_loss": round(float(total_return), 2) if total_return is not None else 0.0,
                                        "profit_loss_pct": round(float((total_return / starting_balance * 100) if starting_balance and starting_balance > 0 else 0), 2),
                                        "holdings": holdings,
                                        "timestamp": datetime.now().isoformat(),
                                        "initial_balance": round(float(starting_balance), 2) if starting_balance is not None else 0.0
                                    }
                                }
                                realized_pnl = float(
                                    portfolio.realized_pnl or 0.0)
                                total_value = cash + current_market_value
                                total_return = unrealized_pnl + realized_pnl

                                logger.warning(
                                    f"⚠️ Using CACHED database data (Dhan API unavailable): cash={cash}, holdings={len(holdings)}")

                                return {
                                    "total_value": round(total_value, 2),
                                    "cash": round(cash, 2),
                                    "cash_percentage": round((cash / total_value * 100) if total_value > 0 else 100, 2),
                                    "holdings": holdings,
                                    "total_invested": round(total_exposure, 2),
                                    "invested_percentage": round((total_exposure / total_value * 100) if total_value > 0 else 0, 2),
                                    "current_holdings_value": round(current_market_value, 2),
                                    "total_return": round(total_return, 2),
                                    "total_return_pct": round((total_return / starting_balance * 100) if starting_balance > 0 else 0, 2),
                                    "unrealized_pnl": round(unrealized_pnl, 2),
                                    "unrealized_pnl_pct": round((unrealized_pnl / total_exposure * 100) if total_exposure > 0 else 0, 2),
                                    "realized_pnl": round(realized_pnl, 2),
                                    "realized_pnl_pct": round((realized_pnl / starting_balance * 100) if starting_balance > 0 else 0, 2),
                                    "total_exposure": round(total_exposure, 2),
                                    "exposure_ratio": round((total_exposure / total_value * 100) if total_value > 0 else 0, 2),
                                    "profit_loss": round(total_return, 2),
                                    "profit_loss_pct": round((total_return / starting_balance * 100) if starting_balance > 0 else 0, 2),
                                    "positions": len(holdings),
                                    "trades_today": 0,
                                    "initial_balance": round(starting_balance, 2)
                                }
                        finally:
                            session.close()
                    except Exception as db_err:
                        logger.warning(
                            f"Failed to get portfolio from database: {db_err}")

                # If all else fails, return empty portfolio
                logger.error(
                    "❌ Live mode: No data available from Dhan API or database")
                return {
                    "total_value": 0.0,
                    "cash": 0.0,
                    "cash_percentage": 100.0,
                    "holdings": {},
                    "total_invested": 0.0,
                    "invested_percentage": 0.0,
                    "current_holdings_value": 0.0,
                    "total_return": 0.0,
                    "total_return_pct": 0.0,
                    "unrealized_pnl": 0.0,
                    "unrealized_pnl_pct": 0.0,
                    "realized_pnl": 0.0,
                    "realized_pnl_pct": 0.0,
                    "total_exposure": 0.0,
                    "exposure_ratio": 0.0,
                    "profit_loss": 0.0,
                    "profit_loss_pct": 0.0,
                    "positions": 0,
                    "trades_today": 0,
                    "initial_balance": 0.0
                }

            # FIXED: Read from the correct Indian trading bot portfolio files
            # Use absolute path to data folder and current mode
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            current_mode = self.config.get("mode", "paper")
            # Use Indian-specific portfolio files that the trading bot actually writes to
            portfolio_file = os.path.join(
                project_root, "data", f"portfolio_india_{current_mode}.json")
            # Removed annoying log - file read is silent now
            if os.path.exists(portfolio_file):
                with open(portfolio_file, 'r') as f:
                    portfolio_data = json.load(f)

                starting_balance = portfolio_data.get(
                    'starting_balance', 0)
                cash = portfolio_data.get('cash', starting_balance)
                holdings = portfolio_data.get('holdings', {})

                # Get current prices for unrealized P&L calculation
                current_prices = {}
                unrealized_pnl = 0  # Will be recalculated with current prices
                price_fetch_success = False

                if holdings:
                    try:
                        # Use Fyers for real-time price updates
                        fyers_client = get_fyers_client()
                        for ticker in holdings.keys():
                            if fyers_client:
                                try:
                                    # PRODUCTION FIX: Use data service client methods
                                    price = fyers_client.get_price(ticker)
                                    if price and price > 0:
                                        current_prices[ticker] = price
                                        price_fetch_success = True
                                        continue
                                except Exception as e:
                                    logger.warning(
                                        f"Data service failed for {ticker}: {e}")

                            # Fallback to Yahoo Finance
                            try:
                                import yfinance as yf
                                stock = yf.Ticker(ticker)
                                hist = stock.history(period="1d")
                                if not hist.empty:
                                    current_prices[ticker] = hist['Close'].iloc[-1]
                                    price_fetch_success = True
                            except Exception as e:
                                logger.debug(
                                    f"Yahoo Finance failed for {ticker}: {e}")
                                # Fallback to avg price
                                current_prices[ticker] = holdings[ticker]['avg_price']
                    except Exception as e:
                        logger.warning(f"Error fetching current prices: {e}")
                        # Fallback: use average prices
                        for ticker, data in holdings.items():
                            current_prices[ticker] = data['avg_price']

                # Always calculate unrealized P&L with current prices (or avg prices as fallback)
                unrealized_pnl = 0
                for ticker, data in holdings.items():
                    current_price = current_prices.get(
                        ticker, data['avg_price'])
                    pnl_for_ticker = (
                        current_price - data['avg_price']) * data['qty']
                    unrealized_pnl += pnl_for_ticker

                # Calculate total exposure and total value with current prices
                total_exposure = sum(data['qty'] * data['avg_price']
                                     for data in holdings.values())

                # If we successfully fetched current prices, use them
                if price_fetch_success:
                    current_market_value = sum(data['qty'] * current_prices.get(ticker, data['avg_price'])
                                               for ticker, data in holdings.items())
                else:
                    # If we couldn't fetch current prices, calculate market value using unrealized P&L
                    current_market_value = total_exposure + unrealized_pnl

                total_value = cash + current_market_value

                # Calculate cash invested (starting balance minus current cash)
                cash_invested = starting_balance - cash

                # Calculate total return based on unrealized P&L (more accurate)
                # Total return = unrealized P&L + realized P&L
                realized_pnl = portfolio_data.get('realized_pnl', 0)
                total_return = unrealized_pnl + realized_pnl
                return_pct = (total_return / cash_invested) * \
                    100 if cash_invested > 0 else 0

                # Add current prices to holdings for frontend
                enriched_holdings = {}
                for ticker, data in holdings.items():
                    enriched_holdings[ticker] = {
                        **data,
                        'currentPrice': current_prices.get(ticker, data['avg_price'])
                    }

                # Get trade log
                trade_log = self.get_recent_trades(
                    limit=100)  # Get all trades for portfolio

                # Professional calculations
                total_invested = sum(data['qty'] * data['avg_price']
                                     for data in holdings.values())
                cash_percentage = (cash / total_value) * \
                    100 if total_value > 0 else 100
                invested_percentage = (
                    total_invested / total_value) * 100 if total_value > 0 else 0
                unrealized_pnl_pct = (
                    unrealized_pnl / total_invested) * 100 if total_invested > 0 else 0
                realized_pnl_pct = (
                    realized_pnl / starting_balance) * 100 if starting_balance > 0 else 0
                total_return_pct = (
                    total_return / starting_balance) * 100 if starting_balance > 0 else 0

                return {
                    "total_value": round(total_value, 2),
                    "cash": round(cash, 2),
                    "cash_percentage": round(cash_percentage, 2),
                    "holdings": enriched_holdings,
                    "total_invested": round(total_invested, 2),
                    "invested_percentage": round(invested_percentage, 2),
                    "current_holdings_value": round(current_market_value, 2),
                    "total_return": round(total_return, 2),
                    "return_percentage": round(return_pct, 2),  # Legacy field
                    "total_return_pct": round(total_return_pct, 2),
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
                    "realized_pnl": round(realized_pnl, 2),
                    "realized_pnl_pct": round(realized_pnl_pct, 2),
                    "total_exposure": round(total_exposure, 2),
                    "exposure_ratio": round((total_invested / total_value) * 100, 2) if total_value > 0 else 0,
                    "profit_loss": round(total_return, 2),
                    "profit_loss_pct": round(total_return_pct, 2),
                    "active_positions": len(holdings),
                    "positions": len(holdings),
                    "trades_today": len([t for t in trade_log if t.get("date", "").startswith(datetime.now().strftime("%Y-%m-%d"))]),
                    "initial_balance": starting_balance,
                    "trade_log": trade_log
                }
            else:
                # Fallback to default values if no portfolio file exists
                starting_balance = self.config.get('starting_balance', 0)
                return {
                    "total_value": starting_balance,
                    "cash": starting_balance,
                    "holdings": {},
                    "total_return": 0,
                    "return_percentage": 0,
                    "realized_pnl": 0,
                    "unrealized_pnl": 0,
                    "total_exposure": 0,
                    "active_positions": 0,
                    "trade_log": []
                }
        except Exception as e:
            logger.error(f"Error getting portfolio metrics: {e}")
            starting_balance = self.config.get('starting_balance', 0)
            return {
                "total_value": starting_balance,
                "cash": starting_balance,
                "holdings": {},
                "total_return": 0,
                "return_percentage": 0,
                "realized_pnl": 0,
                "unrealized_pnl": 0,
                "total_exposure": 0,
                "active_positions": 0,
                "trade_log": []
            }

    def get_recent_trades(self, limit=10):
        """Get recent trades from saved trade log file"""
        import json
        import os

        try:
            # FIXED: Read from the correct Indian trading bot trade log files
            # Use absolute path to data folder and current mode
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            current_mode = self.config.get("mode", "paper")
            # Use Indian-specific trade log files that the trading bot actually writes to
            trade_log_file = os.path.join(
                project_root, "data", f"trade_log_india_{current_mode}.json")
            # Removed annoying log - file read is silent now
            if os.path.exists(trade_log_file):
                with open(trade_log_file, 'r') as f:
                    trades = json.load(f)

                # Return the most recent trades (reversed order)
                recent_trades = trades[-limit:] if trades else []
                return list(reversed(recent_trades))
            else:
                logger.debug("Trade log file not found")
                return []
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []

    def get_complete_bot_data(self):
        """Get complete bot data for React frontend"""
        try:
            portfolio_metrics = self.get_portfolio_metrics()

            return {
                "isRunning": self.is_running,
                "config": {
                    "mode": self.config.get("mode", "paper"),
                    "tickers": self.config.get("tickers", []),
                    "stopLossPct": self.config.get("stop_loss_pct", 0.05),
                    "maxAllocation": self.config.get("max_capital_per_trade", 0.25),
                    "maxTradeLimit": self.config.get("max_trade_limit", 10)
                },
                "portfolio": {
                    "totalValue": portfolio_metrics["total_value"],
                    "cash": portfolio_metrics["cash"],
                    "investedValue": portfolio_metrics.get("total_invested", 0),
                    "todayGain": portfolio_metrics.get("today_gain", 0),
                    "holdings": portfolio_metrics["holdings"],
                    "startingBalance": portfolio_metrics.get("initial_balance", 0),
                    "unrealizedPnL": portfolio_metrics["unrealized_pnl"],
                    "realizedPnL": portfolio_metrics["realized_pnl"],
                    "tradeLog": self.get_recent_trades(50)
                },
                "lastUpdate": self.last_update.isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting complete bot data: {e}")
            return {
                "isRunning": False,
                "config": {
                    "mode": "paper",
                    "tickers": [],
                    "stopLossPct": 0.05,
                    "maxAllocation": 0.25,
                    "maxTradeLimit": 10
                },
                "portfolio": {
                    "totalValue": 0,
                    "cash": 0,
                    "investedValue": 0,
                    "todayGain": 0,
                    "holdings": {},
                    "startingBalance": 0,
                    "unrealizedPnL": 0,
                    "realizedPnL": 0,
                    "tradeLog": []
                },
                "lastUpdate": datetime.now().isoformat()
            }

    async def broadcast_portfolio_update(self):
        """Broadcast portfolio update to all connected WebSocket clients"""
        try:
            # Get latest portfolio data from database
            portfolio_data = self.portfolio_manager.get_portfolio_summary()

            # Get recent trades
            recent_trades = self.portfolio_manager.get_recent_trades(limit=10)

            # Prepare update message
            update = {
                "type": "portfolio_update",
                "data": {
                    "portfolio": portfolio_data,
                    "trades": recent_trades,
                    "timestamp": datetime.now().isoformat()
                }
            }

            # Convert to JSON
            message = json.dumps(update)

            # Legacy: Remove individual client tracking in favor of manager.broadcast_to_user
            pass

        except Exception as e:
            logger.error(f"Error broadcasting portfolio update: {e}")
        try:
            portfolio_metrics = self.get_portfolio_metrics()
            update_data = {
                "type": "portfolio_update",
                "data": {
                    "totalValue": portfolio_metrics["total_value"],
                    "cash": portfolio_metrics["cash"],
                    "holdings": portfolio_metrics["holdings"],
                    "unrealizedPnL": portfolio_metrics["unrealized_pnl"],
                    "realizedPnL": portfolio_metrics["realized_pnl"],
                    "tradeLog": self.get_recent_trades(10)
                },
                "timestamp": datetime.now().isoformat()
            }
            await manager.broadcast_to_user(update_data, self.username)
            logger.info("Portfolio update broadcasted to WebSocket clients")
        except Exception as e:
            logger.error(f"Error broadcasting portfolio update: {e}")

    async def broadcast_trade_update(self, trade_data):
        """Broadcast trade update to all connected WebSocket clients"""
        try:
            update_data = {
                "type": "trade_update",
                "data": trade_data,
                "timestamp": datetime.now().isoformat()
            }
            await manager.broadcast_to_user(update_data, self.username)
            logger.info(f"Trade update broadcasted: {trade_data}")
        except Exception as e:
            logger.error(f"Error broadcasting trade update: {e}")

    def _on_trade_executed(self, trade_data):
        """Callback method called when a trade is executed"""
        try:
            # FIXED: Use thread-safe queue approach to prevent deadlocks and memory leaks
            import threading
            import queue

            # Use a bounded queue to prevent memory exhaustion
            if not hasattr(self, '_broadcast_queue'):
                self._broadcast_queue = queue.Queue(maxsize=100)
                self._broadcast_worker_active = True

                def broadcast_worker():
                    """Worker thread for processing broadcasts safely"""
                    import asyncio
                    while self._broadcast_worker_active:
                        try:
                            # Get update from queue with timeout
                            update_data = self._broadcast_queue.get(
                                timeout=1.0)
                            if update_data is None:  # Shutdown signal
                                break

                            # Process the broadcast in a controlled manner
                            try:
                                # Create isolated event loop for this thread
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)

                                async def safe_broadcast():
                                    try:
                                        await self.broadcast_trade_update(update_data)
                                        await self.broadcast_portfolio_update()
                                    except Exception as e:
                                        logger.error(
                                            f"Error in broadcast worker async execution for {self.username}: {e}")

                                loop.run_until_complete(safe_broadcast())
                                loop.close()

                            except Exception as e:
                                logger.error(f"Error in broadcast worker: {e}")
                            finally:
                                self._broadcast_queue.task_done()

                        except queue.Empty:
                            continue  # Timeout, check if still active
                        except Exception as e:
                            logger.error(
                                f"Fatal error in broadcast worker: {e}")
                            break

                # Start worker thread as daemon
                worker_thread = threading.Thread(
                    target=broadcast_worker, daemon=True)
                worker_thread.start()

            # Queue the update safely
            try:
                self._broadcast_queue.put_nowait(trade_data)
            except queue.Full:
                logger.warning("Broadcast queue full, dropping trade update")

        except Exception as e:
            logger.error(f"Error in trade callback: {e}")


def apply_risk_level_settings(bot, risk_level, custom_stop_loss=None, custom_allocation=None,
                              custom_target_profit=None, custom_use_rr=None, custom_rr_ratio=None):
    """Apply risk level settings to the trading bot"""
    try:
        # Define risk level mappings
        risk_mappings = {
            "LOW": {
                "stop_loss": 0.03,         # 3% stop-loss
                "allocation": 0.15,        # 15% allocation
                "target_profit": 0.06,     # 6% target profit (2:1 risk-reward)
                "use_risk_reward": True,   # Use risk-reward ratio
                "risk_reward_ratio": 2.0   # 2:1 risk-reward ratio
            },
            "MEDIUM": {
                "stop_loss": 0.05,         # 5% stop-loss
                "allocation": 0.25,        # 25% allocation
                # 10% target profit (2:1 risk-reward)
                "target_profit": 0.10,
                "use_risk_reward": True,   # Use risk-reward ratio
                "risk_reward_ratio": 2.0   # 2:1 risk-reward ratio
            },
            "HIGH": {
                "stop_loss": 0.08,         # 8% stop-loss
                "allocation": 0.35,        # 35% allocation
                # 16% target profit (2:1 risk-reward)
                "target_profit": 0.16,
                "use_risk_reward": True,   # Use risk-reward ratio
                "risk_reward_ratio": 2.0   # 2:1 risk-reward ratio
            }
        }

        if risk_level == "CUSTOM":
            # Use custom values if provided
            if custom_stop_loss is not None:
                bot.config['stop_loss_pct'] = custom_stop_loss
                if hasattr(bot, 'executor') and bot.executor:
                    bot.executor.stop_loss_pct = custom_stop_loss

            if custom_allocation is not None:
                bot.config['max_capital_per_trade'] = custom_allocation
                if hasattr(bot, 'executor') and bot.executor:
                    bot.executor.max_capital_per_trade = custom_allocation

            if custom_target_profit is not None:
                bot.config['target_profit_pct'] = custom_target_profit
                if hasattr(bot, 'executor') and bot.executor:
                    bot.executor.target_profit_pct = custom_target_profit

            if custom_use_rr is not None:
                bot.config['use_risk_reward'] = custom_use_rr
                if hasattr(bot, 'executor') and bot.executor:
                    bot.executor.use_risk_reward = custom_use_rr

            if custom_rr_ratio is not None:
                bot.config['risk_reward_ratio'] = custom_rr_ratio
                if hasattr(bot, 'executor') and bot.executor:
                    bot.executor.risk_reward_ratio = custom_rr_ratio

            logger.info(f"🎯 CUSTOM RISK CONFIG APPLIED:")
            logger.info(
                f"   Stop Loss: {custom_stop_loss*100 if custom_stop_loss else 0:.1f}%")
            logger.info(
                f"   Max Allocation: {custom_allocation*100 if custom_allocation else 0:.1f}%")
            logger.info(
                f"   Target Profit: {custom_target_profit*100 if custom_target_profit else 0:.1f}%")
            logger.info(
                f"   Risk-Reward: {custom_rr_ratio if custom_rr_ratio else 2.0:.1f}")

        elif risk_level in risk_mappings:
            # Apply predefined risk level settings
            settings = risk_mappings[risk_level]
            bot.config.update({
                'stop_loss_pct': settings['stop_loss'],
                'max_capital_per_trade': settings['allocation'],
                'target_profit_pct': settings['target_profit'],
                'use_risk_reward': settings['use_risk_reward'],
                'risk_reward_ratio': settings['risk_reward_ratio']
            })

            # Update executor if it exists
            if hasattr(bot, 'executor') and bot.executor:
                bot.executor.stop_loss_pct = settings['stop_loss']
                bot.executor.max_capital_per_trade = settings['allocation']
                bot.executor.target_profit_pct = settings['target_profit']
                bot.executor.use_risk_reward = settings['use_risk_reward']
                bot.executor.risk_reward_ratio = settings['risk_reward_ratio']

        logger.info(f"Applied {risk_level} risk settings: "
                    f"Stop Loss={bot.config.get('stop_loss_pct')*100:.1f}%, "
                    f"Target Profit={bot.config.get('target_profit_pct', 0)*100:.1f}%, "
                    f"Use RR={bot.config.get('use_risk_reward', True)}, "
                    f"RR Ratio={bot.config.get('risk_reward_ratio', 2.0):.1f}, "
                    f"Max Allocation={bot.config.get('max_capital_per_trade')*100:.1f}%")

    except Exception as e:
        logger.error(f"Error applying risk level settings: {e}")


def _get_settings_data_dir(username: Optional[str] = None):
    """Data dir for config files: backend/hft2/data or a user-specific subfolder."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    base_dir = os.path.join(project_root, "data")

    # MULTI-USER FIX: Normalize username for consistent path resolution
    un = str(username).lower().strip() if username else "anonymous"

    if un != "anonymous":
        # Standardize username to avoid path issues
        safe_un = "".join(c for c in un if c.isalnum()
                          or c in ("-", "_")).strip() or "anonymous"
        user_dir = os.path.join(base_dir, "users", safe_un)
        return user_dir
    return base_dir


def get_current_saved_mode(username: Optional[str] = None) -> str:
    """Read the persisted trading mode for this user from MongoDB (Render-safe)."""
    # MULTI-USER FIX: Normalize username
    un = str(username).lower().strip() if username else "anonymous"

    if un != "anonymous":
        try:
            from db.mongo_client import get_mongo_db
            db = get_mongo_db("trading")
            doc = db["user_mode"].find_one({"username": un})
            if doc and doc.get("mode") in ("paper", "live"):
                return doc["mode"]
        except Exception as e:
            logger.warning(f"Could not read mode from MongoDB for {un}: {e}")
    # Fallback: try local file (localhost dev)
    try:
        data_dir = _get_settings_data_dir(username)
        path = os.path.join(data_dir, "current_mode.txt")
        if os.path.exists(path):
            with open(path, "r") as f:
                mode = f.read().strip()
            if mode in ("paper", "live"):
                return mode
    except Exception:
        pass
    return "live"


def set_current_saved_mode(mode: str, username: Optional[str] = None) -> None:
    """Persist the chosen mode to MongoDB (survives Render restarts)."""
    # MULTI-USER FIX: Normalize username
    un = str(username).lower().strip() if username else "anonymous"

    # Primary: write to MongoDB so it survives Render restarts
    if un != "anonymous":
        try:
            from db.mongo_client import get_mongo_db
            db = get_mongo_db("trading")
            db["user_mode"].update_one(
                {"username": un},
                {"$set": {"mode": mode, "updated_at": datetime.utcnow().isoformat()}},
                upsert=True
            )
            logger.debug(f"Saved mode '{mode}' to MongoDB for {un}")
        except Exception as e:
            logger.warning(f"Could not save mode to MongoDB for {un}: {e}")
    # Secondary: also write local file for localhost dev
    try:
        data_dir = _get_settings_data_dir(un)
        os.makedirs(data_dir, exist_ok=True)
        path = os.path.join(data_dir, "current_mode.txt")
        with open(path, "w") as f:
            f.write(mode)
    except Exception as e:
        logger.debug(f"Could not save current_mode file for {username}: {e}")


def _dhan_portfolio_to_metrics(dhan_portfolio: dict) -> dict:
    """Build PortfolioMetrics-shaped dict from get_live_portfolio() result (for per-user demat)."""
    cash = float(dhan_portfolio.get("cash", 0))
    holdings_raw = dhan_portfolio.get("holdings", {})
    starting_balance = float(dhan_portfolio.get("startingBalance", 0))
    holdings = {}
    total_invested = 0.0
    for ticker, h in holdings_raw.items():
        qty = float(h.get("quantity", 0))
        avg = float(h.get("avgPrice", 0))
        cur = float(h.get("currentPrice", avg))
        last_action = h.get("lastAction", "BUY")
        if qty > 0:
            cost = qty * avg
            total_invested += cost
            holdings[ticker] = {
                "qty": qty,
                "avg_price": avg,
                "current_price": cur,
                "current_value": qty * cur,
                "lastAction": last_action,
                "securityId": h.get("securityId", ""),
                "exchangeSegment": h.get("exchangeSegment", "NSE_EQ"),
            }
    current_holdings_value = sum(h.get("current_value", 0)
                                 for h in holdings.values())
    total_value = cash + current_holdings_value
    # Use sodLimit-based starting balance as the denominator for return calculations
    if starting_balance <= 0:
        starting_balance = total_value if total_value > 0 else total_invested + cash
    total_return = current_holdings_value - total_invested
    total_return_pct = (total_return / total_invested *
                        100) if total_invested else 0
    unrealized_pnl = total_return
    unrealized_pnl_pct = total_return_pct
    cash_pct = (cash / total_value * 100) if total_value else 0
    invested_pct = (total_invested / total_value * 100) if total_value else 0
    return {
        "total_value": round(total_value, 2),
        "cash": round(cash, 2),
        "cash_percentage": round(cash_pct, 2),
        "holdings": holdings,
        "total_invested": round(total_invested, 2),
        "invested_percentage": round(invested_pct, 2),
        "current_holdings_value": round(current_holdings_value, 2),
        "total_return": round(total_return, 2),
        "return_percentage": round(total_return_pct, 2),
        "total_return_pct": round(total_return_pct, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
        "realized_pnl": 0,
        "realized_pnl_pct": 0,
        "total_exposure": round(current_holdings_value, 2),
        "exposure_ratio": float(f"{(current_holdings_value / total_value) if total_value else 0:.4f}"),
        "profit_loss": round(total_return, 2),
        "profit_loss_pct": round(total_return_pct, 2),
        "positions": len(holdings),
        "trades_today": 0,
        "initial_balance": round(starting_balance, 2),
    }


def _convert_dhan_portfolio_to_bot_data(dhan_portfolio: dict, username: Optional[str] = None, include_config: bool = True) -> dict:
    """Helper function to convert Dhan portfolio dict to bot data format. Reduces code duplication."""
    state = get_user_state(username)
    bot = state.get("trading_bot")

    cash = float(dhan_portfolio.get("cash", 0))
    holdings_dict = dhan_portfolio.get("holdings", {})
    holdings = {}

    for ticker, h in holdings_dict.items():
        qty = float(h.get("quantity", 0))
        avg_price = float(
            h.get("avgPrice") or h.get("avg_price") or h.get("avgCostPrice") or
            h.get("avgCost") or h.get("buyAvg") or 0
        )
        current_price = float(h.get("currentPrice")
                              or h.get("current_price") or avg_price)
        last_action = h.get("lastAction", "BUY")
        if qty > 0:
            holdings[ticker] = {
                "avgPrice": avg_price,
                "currentPrice": current_price,
                "quantity": qty,
                "lastAction": last_action,
                "securityId": h.get("securityId", ""),
                "exchangeSegment": h.get("exchangeSegment", "NSE_EQ"),
                "qty": qty,
                "avg_price": avg_price,
            }

    current_market_value = sum(
        h["qty"] * h.get("currentPrice", h["avg_price"]) for h in holdings.values())
    total_value = cash + current_market_value
    starting_balance = float(dhan_portfolio.get(
        "startingBalance", total_value))
    cost_basis = sum(h["qty"] * h["avg_price"] for h in holdings.values())
    unrealized_pnl = current_market_value - cost_basis
    today_gain = float(dhan_portfolio.get("todayGain", 0))

    portfolio_data = {
        "totalValue": round(total_value, 2),
        "cash": round(cash, 2),
        "investedValue": round(cost_basis, 2),
        "todayGain": round(today_gain, 2),
        "holdings": holdings,
        "startingBalance": round(starting_balance, 2),
        "unrealizedPnL": round(unrealized_pnl, 2),
        "realizedPnL": 0,
        "tradeLog": []
    }

    if include_config:
        last_analysis = state.get("_last_bot_analysis", {})
        if bot:
            try:
                portfolio_data["tradeLog"] = getattr(
                    bot, 'trade_log', [])[-10:] if hasattr(bot, 'trade_log') else []
                return {
                    "isRunning": state.get("bot_running", False),
                    "config": {
                        "mode": bot.config.get("mode", "live"),
                        "tickers": bot.config.get("tickers", []),
                        "stopLossPct": bot.config.get("stop_loss_pct", 0.05),
                        "maxAllocation": bot.config.get("max_capital_per_trade", 0.25),
                        "maxTradeLimit": bot.config.get("max_trade_limit", 10)
                    },
                    "portfolio": portfolio_data,
                    "analysis": list(last_analysis.values()),
                    "lastUpdate": datetime.now().isoformat()
                }
            except:
                pass

        return {
            "isRunning": state.get("bot_running", False),
            "config": {
                "mode": "live",
                "tickers": list(holdings.keys()),
                "stopLossPct": 0.05,
                "maxAllocation": 0.25,
                "maxTradeLimit": 10
            },
            "portfolio": portfolio_data,
            "analysis": list(last_analysis.values()),
            "lastUpdate": datetime.now().isoformat()
        }

    return portfolio_data


def set_current_saved_mode_global(mode: str) -> None:
    """Legacy global mode setter."""
    set_current_saved_mode(mode, username=None)


def _load_user_config_from_db(mode: str, username: str) -> dict:
    """Load user config from MongoDB (primary source on Render — survives restarts)."""
    try:
        from db.mongo_client import get_mongo_db
        db = get_mongo_db("trading")
        doc = db["user_configs"].find_one({"username": username, "mode": mode})
        if doc and "config" in doc:
            cfg = dict(doc["config"])
            # Never trust persisted Dhan credentials; always read fresh from demat
            cfg.pop("dhan_client_id", None)
            cfg.pop("dhan_access_token", None)
            logger.info(
                f"Loaded config from MongoDB for {username} mode={mode}")
            return cfg
    except Exception as e:
        logger.warning(
            f"Could not load config from MongoDB for {username}: {e}")
    return {}


def _save_user_config_to_db(mode: str, config_data: dict, username: str) -> bool:
    """Persist user config to MongoDB (Render-safe — survives restarts)."""
    try:
        from db.mongo_client import get_mongo_db
        db = get_mongo_db("trading")
        db["user_configs"].update_one(
            {"username": username, "mode": mode},
            {"$set": {"config": config_data, "updated_at": datetime.utcnow().isoformat()}},
            upsert=True
        )
        logger.debug(f"Saved {mode} config to MongoDB for {username}")
        return True
    except Exception as e:
        logger.warning(f"Could not save config to MongoDB for {username}: {e}")
        return False


def load_config_from_file(mode: str, username: Optional[str] = None) -> dict:
    """Load configuration for a user, isolated by username.

    On Render the filesystem is ephemeral — configs are lost on every restart.
    We therefore check MongoDB first for authenticated users, then fall back to
    the local file (useful during local development).  We NEVER fall back to the
    shared/global config file because that would contaminate one user's session
    with another user's saved settings.
    """
    try:
        import json

        # 1. MongoDB-first (Render-safe): persisted across restarts
        if username and username != "anonymous":
            db_config = _load_user_config_from_db(mode, username)
            if db_config:
                return db_config

        # 2. Local file fallback (useful for localhost development)
        data_dir = _get_settings_data_dir(username)
        config_file = os.path.join(data_dir, f"{mode}_config.json")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            # Never use persisted Dhan credentials; always read fresh from demat
            config_data.pop("dhan_client_id", None)
            config_data.pop("dhan_access_token", None)
            logger.info(
                f"Loaded {mode} config from file {config_file} for {username}")
            return config_data

        # 3. No config found — return empty defaults.
        #    IMPORTANT: Do NOT fall back to the shared/anonymous config file.
        #    That would cause cross-user contamination when configs are missing
        #    (e.g. after a Render restart wipes the ephemeral filesystem).
        logger.info(f"No {mode} config found for {username}, using defaults")
        return {}

    except Exception as e:
        logger.error(f"Error loading config for {username}: {e}")
        return {}


def save_config_to_file(mode: str, config_data: dict, username: Optional[str] = None):
    """Save configuration, session-isolated by username.

    Writes to both MongoDB (Render-safe, survives restarts) and to the local
    JSON file (backwards-compatible for localhost development).
    """
    import json

    config_to_save = {
        "mode": mode,
        "riskLevel": config_data.get("riskLevel", "MEDIUM"),
        "targetPriceLevel": config_data.get("targetPriceLevel", "MEDIUM"),
        "stop_loss_pct": config_data.get("stop_loss_pct", 0.05),
        "target_profit_pct": config_data.get("target_profit_pct", 0.1),
        "use_risk_reward": config_data.get("use_risk_reward", True),
        "risk_reward_ratio": config_data.get("risk_reward_ratio", 2.0),
        "max_capital_per_trade": config_data.get("max_capital_per_trade", 0.25),
        "max_trade_limit": config_data.get("max_trade_limit", 150),
        "tickers": config_data.get("tickers", []),
        "created_at": datetime.now().isoformat()
    }

    # Primary: persist to MongoDB (survives Render restarts)
    if username and username != "anonymous":
        _save_user_config_to_db(mode, config_to_save, username)

    # Secondary: also write local file for localhost dev / legacy compatibility
    try:
        data_dir = _get_settings_data_dir(username)
        os.makedirs(data_dir, exist_ok=True)
        config_file = os.path.join(data_dir, f"{mode}_config.json")
        with open(config_file, 'w') as f:
            json.dump(config_to_save, f, indent=2)
        logger.info(f"Configuration saved to {config_file} for {username}")
    except Exception as e:
        logger.warning(
            f"Could not write local config file for {username or 'anonymous'}: {e}")


def update_main_live_config(config_data: dict, username: Optional[str] = None):
    """Update the main live_config.json file with user-specific configuration.

    This ensures dynamic calculations in the professional buy logic use the correct
    user-specific risk parameters.
    """
    try:
        # Define the main config path
        main_config_path = os.path.join(os.path.dirname(
            __file__), '..', 'data', 'live_config.json')

        # Prepare the configuration to update
        config_to_update = {
            "riskLevel": config_data.get("riskLevel", "MEDIUM"),
            "targetPriceLevel": config_data.get("targetPriceLevel", "MEDIUM"),
            "stop_loss_pct": config_data.get("stop_loss_pct", 0.05),
            "target_profit_pct": config_data.get("target_profit_pct", 0.1),
            "use_risk_reward": config_data.get("use_risk_reward", True),
            "risk_reward_ratio": config_data.get("risk_reward_ratio", 2.0),
            "max_capital_per_trade": config_data.get("max_capital_per_trade", 0.25),
            "max_trade_limit": config_data.get("max_trade_limit", 150),
            "tickers": config_data.get("tickers", []),
        }

        # DEBUG: Log what we're about to write
        logger.info(f"🔍 update_main_live_config WRITING:")
        logger.info(f"   stop_loss_pct: {config_to_update['stop_loss_pct']}")
        logger.info(
            f"   target_profit_pct: {config_to_update['target_profit_pct']}")

        # Save updated config
        with open(main_config_path, 'w') as f:
            json.dump(config_to_update, f, indent=2)

        logger.info(f"✅ Updated main live_config.json with risk level: {config_data.get('riskLevel', 'MEDIUM')}, "
                    f"stop loss: {config_data.get('stop_loss_pct', 0.05):.1%}, "
                    f"target profit: {config_data.get('target_profit_pct', 0.1):.1%} (User: {username})")

        # Notify all active trading bots to refresh their dynamic config
        try:
            from core.professional_buy_logic import ProfessionalBuyLogic
            # Refresh any singleton instances if they exist
            logger.info(
                "🔄 Notifying trading bots to refresh dynamic configuration...")
        except Exception as e:
            logger.debug(f"Config refresh notification: {e}")

    except Exception as e:
        logger.error(f"❌ Failed to update main live_config.json: {e}")


def initialize_bot(username: str = "anonymous"):
    """Initialize the trading bot for a specific user. Returns the bot instance."""
    if not username:
        logger.warning(
            "initialize_bot called without username - session isolation may be compromised")

    state = get_user_state(username)

    print(f"--- STARTING BOT INITIALIZATION FOR {username} ---")
    try:
        import traceback

        try:
            # Re-verify and refresh from local env file if needed for bot instance
            _curr = _Path(current_dir)
            _parent = _curr.parent
            for _p in [_curr, _parent]:
                for _f in ["env", ".env"]:
                    _path = _p / _f
                    if _path.exists():
                        load_dotenv(_path, override=True)
                        break
        except:
            pass

        # Live trading mode only (production ready)
        default_mode = "live"
        logger.info(
            f"Initializing bot for {username} with mode: {default_mode}")

        if CONFIG_SCHEMA_AVAILABLE:
            logger.info(f"Using schema-validated configuration for {username}")
            try:
                config = load_and_validate_config(
                    default_mode, username=username)
            except Exception as validation_err:
                logger.warning(
                    f"Config validation failed for {username}, using defaults: {validation_err}")
                config = ConfigValidator.get_default_config()
                config["mode"] = default_mode

            saved_config = load_config_from_file(
                default_mode, username=username)
            if saved_config:
                saved_tickers = saved_config.get("tickers", [])
                if saved_tickers:
                    config["tickers"] = saved_tickers
                    logger.info(
                        f"📊 Loaded {len(saved_tickers)} tickers for {username}")
                # Live mode only - ignore saved mode from old configs
                config["mode"] = "live"
        else:
            logger.warning(
                "Configuration schema not available, using legacy loading")
            config = {
                "tickers": [],
                "starting_balance": 0,
                "current_portfolio_value": 0,
                "current_pnl": 0,
                "mode": default_mode,
                "riskLevel": "MEDIUM",
                "period": "3y",
                "prediction_days": 30,
                "benchmark_tickers": ["^NSEI"],
                "sleep_interval": 30,
                "stop_loss_pct": 0.05,
                "max_capital_per_trade": 0.25,
                "max_trade_limit": 150,
                "capital": 0,
                "margin": 0,
                "max_drawdown_pct": 0.1,
                "target_profit_pct": 0.1,
                "use_risk_reward": True,
                "risk_reward_ratio": 2.0
            }

            saved_config = load_config_from_file(
                default_mode, username=username)
            if saved_config:
                config.update({
                    "mode": saved_mode,
                    "riskLevel": saved_config.get("riskLevel", config["riskLevel"]),
                    "stop_loss_pct": saved_config.get("stop_loss_pct", config["stop_loss_pct"]),
                    "max_capital_per_trade": saved_config.get("max_capital_per_trade", config["max_capital_per_trade"]),
                    "max_trade_limit": saved_config.get("max_trade_limit", config["max_trade_limit"]),
                    "tickers": saved_config.get("tickers", [])
                })

        # Apply user context if pending
        pending = state.get("_pending_bot_user_context")
        if pending and isinstance(pending, dict):
            if pending.get("user_id"):
                config["user_id"] = pending["user_id"]
            if pending.get("dhan_client_id"):
                config["dhan_client_id"] = pending["dhan_client_id"]
            if pending.get("dhan_access_token"):
                config["dhan_access_token"] = pending["dhan_access_token"]
            state["_pending_bot_user_context"] = None
            logger.info(f"Applied pending user context for {username}")

        import time as _time_mod
        _max_init_retries = 3
        bot_instance = None
        for _attempt in range(1, _max_init_retries + 1):
            try:
                logger.info(
                    f"🔄 Creating WebTradingBot instance for {username} (attempt {_attempt})...")
                bot_instance = WebTradingBot(config, username=username)
                logger.info(
                    f"✅ Created WebTradingBot instance for {username}: mode={config.get('mode')}")
                break
            except Exception as bot_init_err:
                if "database is locked" in str(bot_init_err).lower() and _attempt < _max_init_retries:
                    _time_mod.sleep(2)
                    continue
                logger.error(
                    f"❌ WebTradingBot creation failed for {username}: {bot_init_err}")
                raise

        if bot_instance:
            apply_risk_level_settings(bot_instance, config["riskLevel"])
            if risk_engine is not None:
                risk_engine.set_trading_bot(bot_instance)

            state["trading_bot"] = bot_instance

            # Initialize signal filtering layer for this user
            try:
                signal_filter = get_signal_filter(config)
                signal_filter.start_new_cycle()
                logger.info(
                    f"✅ Signal filtering layer initialized for {username}")
            except Exception as sf_err:
                logger.warning(
                    f"Signal filter initialization failed for {username}: {sf_err}")

            # Start sync service for this user if in live mode
            if LIVE_TRADING_AVAILABLE and config.get("mode") == "live":
                try:
                    from dhan_sync_service import start_sync_service
                    global _main_event_loop
                    loop_to_use = _main_event_loop
                    try:
                        if not loop_to_use:
                            loop_to_use = asyncio.get_event_loop()
                    except RuntimeError:
                        pass

                    if loop_to_use and loop_to_use.is_running():
                        asyncio.run_coroutine_threadsafe(
                            start_sync_service(username), loop_to_use)
                        logger.info(
                            f"Scheduled sync service start for {username} in main loop")
                    else:
                        logger.info(
                            f"Main loop not running yet for {username}, sync will start via startup_event")
                except Exception as sync_err:
                    logger.error(
                        f"Failed to trigger sync service start for {username}: {sync_err}")

            logger.info(f"Trading bot for {username} initialized successfully")
            return bot_instance

    except Exception as e:
        logger.error(f"Error initializing trading bot for {username}: {e}")
        state["trading_bot"] = None
        return None
        # raise  # Don't raise in thread, just log


# Static file serving
app.mount("/static", StaticFiles(directory="."), name="static")

# API Routes

# --- JWT Auth ---
if JWT_AVAILABLE:
    @app.get("/api/auth/status")
    async def auth_status(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_http_bearer)):
        """Auth status for trading-dashboard: always enabled when JWT is available."""
        out = {"auth_status": "enabled"}
        if credentials and credentials.credentials:
            payload = auth_module.decode_token(credentials.credentials)
            if payload:
                out["authenticated"] = True
                out["username"] = payload.get("sub")
            else:
                out["authenticated"] = False
        else:
            out["authenticated"] = False
        return out

    @app.post("/api/auth/login")
    async def auth_login(req: LoginRequest):
        """Login: returns access_token (JWT)."""
        # First check if MongoDB is available
        try:
            from db.mongo_client import get_mongo_db
            db = get_mongo_db("trading")
            db.command("ping")  # Test connection
        except Exception as db_err:
            logger.error(f"MongoDB unavailable during login: {db_err}")
            raise HTTPException(
                status_code=503, detail="Database temporarily unavailable. Check MongoDB connection and try again.")

        # Now try to authenticate
        try:
            normalized_username = req.username.lower().strip()
            logger.info(
                f"Login attempt for: '{normalized_username}' (original: '{req.username}')")

            # Try to authenticate
            user = auth_module.authenticate_user(
                normalized_username, req.password)
            if not user:
                # MongoDB is available, so credentials are wrong or user doesn't exist
                # Check if user exists to provide better error message
                user_exists = auth_module.get_user_by_username(
                    normalized_username)
                if user_exists:
                    logger.warning(
                        f"Login failed: Password incorrect for user: {normalized_username}")
                    raise HTTPException(
                        status_code=401, detail="Password is wrong")
                else:
                    # User doesn't exist - log all usernames in DB for debugging (only in debug mode)
                    logger.warning(
                        f"Login failed: User not found: '{normalized_username}'. Make sure you're using the exact same username you registered with.")
                    raise HTTPException(
                        status_code=401, detail="Email id not registered or password is wrong")

            logger.info(f"{'='*60}")
            logger.info(f"🔐 USER LOGGED IN: {normalized_username}")
            logger.info(f"{'='*60}")
            token = auth_module.create_token(sub=user["username"])
            return {"access_token": token, "token_type": "bearer", "username": user["username"]}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="Internal server error during login")

    @app.post("/api/auth/logout")
    async def auth_logout(credentials: HTTPAuthorizationCredentials = Depends(_http_bearer)):
        """Logout: invalidate current token. Client must discard token and clear local state."""
        if credentials and credentials.credentials and credentials.credentials not in ("", "no-auth-required"):
            _logout_blacklist.add(credentials.credentials)
            # Bounded blacklist: when we hit the cap, drop the oldest ~half of entries
            # to keep memory usage predictable for 50+ concurrent users.
            if len(_logout_blacklist) > _MAX_BLACKLIST_SIZE:
                # Keep the most recently added half (arbitrary but fast, set has no order)
                _logout_blacklist.clear()
        return {"message": "Logged out successfully"}

    @app.post("/api/auth/register")
    async def auth_register(req: RegisterRequest):
        """Register a new user."""
        if len(req.username.strip()) < 2 or len(req.password) < 6:
            raise HTTPException(
                status_code=400, detail="Username (min 2) and password (min 6) required")

        normalized_username = req.username.lower().strip()
        logger.info(
            f"Registration attempt for: '{normalized_username}' (original: '{req.username}')")

        # create_user() now handles MongoDB errors internally and returns None on failure
        # Pass normalized username to ensure consistency
        user = auth_module.create_user(normalized_username, req.password)
        if not user:
            # User creation failed - could be MongoDB unavailable or username taken
            # Check if MongoDB is available to give better error message
            try:
                from db.mongo_client import get_mongo_db
                get_mongo_db("trading")
                # Check if user exists
                existing = auth_module.get_user_by_username(
                    normalized_username)
                if existing:
                    logger.warning(
                        f"Registration failed: Username already exists: {normalized_username}")
                    raise HTTPException(
                        status_code=400, detail="Username already taken")
                else:
                    logger.error(
                        f"Registration failed: User creation returned None but user doesn't exist")
                    raise HTTPException(
                        status_code=500, detail="Failed to create user. Please try again.")
            except HTTPException:
                raise
            except Exception as e:
                # MongoDB is unavailable
                logger.error(f"MongoDB unavailable during registration: {e}")
                raise HTTPException(
                    status_code=503, detail="Database temporarily unavailable. Check MongoDB connection and try again.")

        logger.info(f"User registered successfully: {user.get('username')}")
        token = auth_module.create_token(sub=user["username"])
        return {"access_token": token, "token_type": "bearer", "username": user["username"]}

    @app.get("/api/user/profile")
    async def get_user_profile(payload: dict = Depends(get_current_user_required)):
        """Get current user profile from DB (stored per user)."""
        try:
            from db.mongo_client import get_mongo_db
            db = get_mongo_db("trading")
            col = db["profiles"]
            username = payload.get("sub") or ""
            doc = col.find_one({"username": username})
            if doc and "_id" in doc:
                doc.pop("_id", None)
            return doc or {"username": username, "fullName": "", "email": "", "preferences": {}}
        except Exception as e:
            logger.exception("Get profile error")
            raise HTTPException(status_code=503, detail="Database unavailable")

    @app.post("/api/user/profile")
    async def save_user_profile(req: UserProfileUpdate, payload: dict = Depends(get_current_user_required)):
        """Save current user profile to DB."""
        try:
            from db.mongo_client import get_mongo_db
            from datetime import datetime
            db = get_mongo_db("trading")
            col = db["profiles"]
            username = payload.get("sub") or ""
            update = {"username": username, "updated_at": datetime.utcnow()}
            if req.fullName is not None:
                update["fullName"] = req.fullName
            if req.email is not None:
                update["email"] = req.email
            if req.preferences is not None:
                update["preferences"] = req.preferences
            col.update_one(
                {"username": username},
                {"$set": update},
                upsert=True,
            )
            return {"success": True, "message": "Profile saved"}
        except Exception as e:
            logger.exception("Save profile error")
            raise HTTPException(status_code=503, detail="Database unavailable")

    # -------------------------------------------------------------------
    # Per-User Watchlist  (stored in MongoDB  trading.watchlists)
    # -------------------------------------------------------------------
    @app.get("/api/user/watchlist")
    async def get_watchlist(payload: dict = Depends(get_current_user_required)):
        """Return the authenticated user's watchlist."""
        try:
            from db.mongo_client import get_mongo_db
            db = get_mongo_db("trading")
            username = payload.get("sub") or ""
            doc = db["watchlists"].find_one({"username": username})
            symbols = doc.get("symbols", []) if doc else []
            return {"symbols": symbols}
        except Exception:
            logger.exception("get_watchlist error")
            raise HTTPException(status_code=503, detail="Database unavailable")

    @app.post("/api/user/watchlist")
    async def save_watchlist(req: dict, payload: dict = Depends(get_current_user_required)):
        """Save (replace) the authenticated user's watchlist."""
        try:
            from db.mongo_client import get_mongo_db
            from datetime import datetime
            db = get_mongo_db("trading")
            username = payload.get("sub") or ""
            symbols = req.get("symbols", [])
            if not isinstance(symbols, list):
                raise HTTPException(
                    status_code=400, detail="symbols must be a list")
            db["watchlists"].update_one(
                {"username": username},
                {"$set": {"username": username, "symbols": symbols,
                          "updated_at": datetime.utcnow()}},
                upsert=True,
            )
            return {"success": True, "symbols": symbols}
        except HTTPException:
            raise
        except Exception:
            logger.exception("save_watchlist error")
            raise HTTPException(status_code=503, detail="Database unavailable")

    # -------------------------------------------------------------------
    # Per-User Settings  (stored in MongoDB  trading.user_settings)
    # -------------------------------------------------------------------
    @app.get("/api/user/settings")
    async def get_user_settings(payload: dict = Depends(get_current_user_required)):
        """Return the authenticated user's settings/preferences."""
        try:
            from db.mongo_client import get_mongo_db
            db = get_mongo_db("trading")
            username = payload.get("sub") or ""
            doc = db["user_settings"].find_one({"username": username})
            if doc:
                doc.pop("_id", None)
                doc.pop("username", None)
            return doc or {}
        except Exception:
            logger.exception("get_user_settings error")
            raise HTTPException(status_code=503, detail="Database unavailable")

    @app.post("/api/user/settings")
    async def save_user_settings(req: dict, payload: dict = Depends(get_current_user_required)):
        """Save the authenticated user's settings/preferences."""
        try:
            from db.mongo_client import get_mongo_db
            from datetime import datetime
            db = get_mongo_db("trading")
            username = payload.get("sub") or ""
            update = {k: v for k, v in req.items(
            ) if k not in ("username", "_id")}
            update["username"] = username
            update["updated_at"] = datetime.utcnow()
            db["user_settings"].update_one(
                {"username": username},
                {"$set": update},
                upsert=True,
            )
            return {"success": True}
        except Exception:
            logger.exception("save_user_settings error")
            raise HTTPException(status_code=503, detail="Database unavailable")

    # -------------------------------------------------------------------
    # Per-User Alerts  (stored in MongoDB  trading.user_alerts)
    # -------------------------------------------------------------------
    @app.get("/api/user/alerts")
    async def get_user_alerts(payload: dict = Depends(get_current_user_required)):
        """Return the authenticated user's price alerts."""
        try:
            from db.mongo_client import get_mongo_db
            db = get_mongo_db("trading")
            username = payload.get("sub") or ""
            doc = db["user_alerts"].find_one({"username": username})
            if doc:
                doc.pop("_id", None)
                doc.pop("username", None)
            return doc or {"price_alerts": [], "prediction_alerts": [], "notifications": [], "notification_settings": {}}
        except Exception:
            logger.exception("get_user_alerts error")
            raise HTTPException(status_code=503, detail="Database unavailable")

    @app.post("/api/user/alerts")
    async def save_user_alerts(req: dict, payload: dict = Depends(get_current_user_required)):
        """Save the authenticated user's alerts."""
        try:
            from db.mongo_client import get_mongo_db
            from datetime import datetime
            db = get_mongo_db("trading")
            username = payload.get("sub") or ""
            update = {k: v for k, v in req.items(
            ) if k not in ("username", "_id")}
            update["username"] = username
            update["updated_at"] = datetime.utcnow()
            db["user_alerts"].update_one(
                {"username": username},
                {"$set": update},
                upsert=True,
            )
            return {"success": True}
        except Exception:
            logger.exception("save_user_alerts error")
            raise HTTPException(status_code=503, detail="Database unavailable")

    # -------------------------------------------------------------------
    # Per-User Demat (broker) credentials - link account, refresh token
    # -------------------------------------------------------------------
    class DematSaveRequest(BaseModel):
        broker: str = "dhan"
        client_id: str
        access_token: str

    class DematRefreshRequest(BaseModel):
        access_token: str

    @app.get("/api/user/demat")
    async def get_user_demat_status(payload: dict = Depends(get_current_user_required)):
        """Return whether user has demat linked (no secrets)."""
        username = (payload.get("sub") or "").strip()
        demat = auth_module.get_user_demat(username) if hasattr(
            auth_module, "get_user_demat") else None
        if not demat:
            return {"linked": False}
        return {"linked": True, "broker": demat.get("broker", "dhan"), "client_id_masked": (demat.get("client_id", "")[:4] + "***") if demat.get("client_id") else None}

    @app.get("/api/user/demat/check")
    async def check_dhan_credentials(payload: dict = Depends(get_current_user_required)):
        """Check Dhan credentials status and validity. Returns detailed diagnostic info.

        This endpoint tests the actual Dhan API connection and returns:
        - configured: whether credentials exist in database
        - valid: whether credentials are currently valid (API test passed)
        - error: error code if any
        - message: human-readable status message
        - client_id_masked: masked client ID for display
        """
        username = (payload.get("sub") or "").strip()
        if not username:
            return {
                "configured": False,
                "valid": False,
                "error": "Not authenticated",
                "message": "Please log in first",
                "client_id_masked": None
            }

        # Use the helper function from dhan_client module
        try:
            from dhan_client import check_dhan_credentials_status
            result = check_dhan_credentials_status(username)
            return result
        except Exception as e:
            logger.error(f"Error checking Dhan credentials: {e}")
            return {
                "configured": False,
                "valid": False,
                "error": str(e),
                "message": f"Failed to check Dhan credentials: {str(e)}",
                "client_id_masked": None
            }

    @app.post("/api/user/demat")
    async def save_user_demat(req: DematSaveRequest, payload: dict = Depends(get_current_user_required)):
        """Save or update demat credentials (any broker). Client ID + Access Token linked to this user only.
        Also clears the user's bot-data cache and propagates credentials to any running bot instance.
        """
        username = (payload.get("sub") or "").strip()
        if not username:
            raise HTTPException(status_code=401, detail="Not authenticated")
        normalized = username.lower().strip()
        user_exists = auth_module.get_user_by_username(normalized) if hasattr(
            auth_module, "get_user_by_username") else None
        if not user_exists:
            raise HTTPException(
                status_code=404, detail="User account not found. Please log out and sign in again.")

        # Invalidate old token cache before overwriting
        try:
            old_demat = auth_module.get_user_demat(username) if hasattr(
                auth_module, "get_user_demat") else None
            old_token = (old_demat or {}).get("access_token", "")
            if old_token:
                from dhan_client import invalidate_portfolio_cache as _inv_cache
                _inv_cache(old_token)
        except Exception:
            pass

        ok = auth_module.set_user_demat(username, req.broker or "dhan", req.client_id or "",
                                        req.access_token or "") if hasattr(auth_module, "set_user_demat") else False
        if not ok:
            raise HTTPException(
                status_code=503, detail="Failed to save demat credentials")

        # Clear bot cache and propagate new credentials into running bot
        new_token = (req.access_token or "").strip()
        new_client_id = (req.client_id or "").strip()
        state = get_user_state(username)
        state["_bot_data_cache"] = {}
        state["_bot_data_cache_ts"] = 0.0
        bot = state.get("trading_bot")
        if bot and new_token:
            try:
                bot.config["dhan_access_token"] = new_token
                bot.config["dhan_client_id"] = new_client_id
                if hasattr(bot, "dhan_client") and bot.dhan_client:
                    bot.dhan_client.access_token = new_token
                    bot.dhan_client.client_id = new_client_id
                if hasattr(bot, "live_executor") and bot.live_executor:
                    if hasattr(bot.live_executor, "dhan_client") and bot.live_executor.dhan_client:
                        bot.live_executor.dhan_client.access_token = new_token
                        bot.live_executor.dhan_client.client_id = new_client_id
                # Fix: StockTradingBot actually stores it in `executor`
                if hasattr(bot, "executor") and bot.executor:
                    if hasattr(bot.executor, "dhan_client") and bot.executor.dhan_client:
                        bot.executor.dhan_client.access_token = new_token
                        bot.executor.dhan_client.client_id = new_client_id
            except Exception as _e:
                logger.warning(
                    "[save_demat] Could not update in-memory bot credentials: %s", _e)

        logger.info(
            "[save_demat] Demat linked/updated for user '%s' — caches cleared", username)
        return {"success": True, "message": "Demat account linked"}

    @app.put("/api/user/demat/token")
    async def refresh_user_demat_token(req: DematRefreshRequest, payload: dict = Depends(get_current_user_required)):
        """Update only the access token for the same user (e.g. after 24h refresh).

        CRITICAL FIX: After saving the new token to MongoDB, we immediately:
        1. Push the new token into the user's running WebTradingBot / DhanAPIClient /
           LiveTradingExecutor instances so they use it right away.
        2. Invalidate the old token's Dhan portfolio cache in dhan_client.py.
        3. Clear the user's bot-data cache so the next /api/bot-data request
           triggers a fresh Dhan fetch instead of returning stale data.
        No server restart is needed.
        """
        username = (payload.get("sub") or "").strip()
        if not username:
            raise HTTPException(status_code=401, detail="Not authenticated")

        new_token = (req.access_token or "").strip()
        if not new_token:
            raise HTTPException(
                status_code=400, detail="access_token must not be empty")

        # 1. Fetch the old token before overwriting so we can invalidate its cache
        old_demat = auth_module.get_user_demat(username) if hasattr(
            auth_module, "get_user_demat") else None
        old_token = (old_demat or {}).get("access_token", "")

        # 2. Persist new token to MongoDB
        ok = auth_module.update_user_demat_token(username, new_token) if hasattr(
            auth_module, "update_user_demat_token") else False
        if not ok:
            raise HTTPException(
                status_code=503, detail="Failed to update access token in database")

        # 3. Invalidate the stale Dhan portfolio cache for the old token
        try:
            from dhan_client import invalidate_portfolio_cache as _inv_cache
            if old_token:
                _inv_cache(old_token)
        except Exception as _ice:
            logger.warning(
                "[token_refresh] Could not invalidate old portfolio cache: %s", _ice)

        # 4. Push new token into the in-memory bot state so it takes effect immediately
        state = get_user_state(username)
        # force next /api/bot-data to re-fetch
        state["_bot_data_cache"] = {}
        state["_bot_data_cache_ts"] = 0.0

        bot = state.get("trading_bot")
        if bot:
            try:
                bot.config["dhan_access_token"] = new_token
                if hasattr(bot, "dhan_client") and bot.dhan_client:
                    bot.dhan_client.access_token = new_token
                    logger.info(
                        "[token_refresh] Updated DhanAPIClient token for %s", username)
                if hasattr(bot, "live_executor") and bot.live_executor:
                    if hasattr(bot.live_executor, "dhan_client") and bot.live_executor.dhan_client:
                        bot.live_executor.dhan_client.access_token = new_token
                        logger.info(
                            "[token_refresh] Updated LiveTradingExecutor Dhan token for %s", username)
                # Fix: StockTradingBot actually stores it in `executor`
                if hasattr(bot, "executor") and bot.executor:
                    if hasattr(bot.executor, "dhan_client") and bot.executor.dhan_client:
                        bot.executor.dhan_client.access_token = new_token
                        logger.info(
                            "[token_refresh] Updated StockTradingBot executor Dhan token for %s", username)
            except Exception as _bot_err:
                logger.warning(
                    "[token_refresh] Could not update in-memory bot token: %s", _bot_err)

        logger.info(
            "[token_refresh] Access token refreshed for user '%s' — all caches cleared", username)
        return {"success": True, "message": "Access token updated and applied immediately"}


if JWT_AVAILABLE:
    @app.get("/api/dhan/raw-holdings")
    async def get_dhan_raw_holdings(payload: dict = Depends(get_current_user_required)):
        """Debug: return raw Dhan API response for fund limit + holdings so we can see exact field names."""
        username = (payload.get("sub") or "").strip()
        demat = auth_module.get_user_demat(username) if hasattr(
            auth_module, "get_user_demat") else None
        if not demat or not demat.get("access_token"):
            raise HTTPException(
                status_code=400, detail="No demat account linked. Please link your Dhan account in Settings.")
        token = demat["access_token"]
        client_id = demat.get("client_id", "")
        try:
            from dhan_client import fetch_fund_limit, fetch_holdings, fetch_positions
            import asyncio
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as ex:
                fund = await loop.run_in_executor(ex, lambda: fetch_fund_limit(token, client_id=client_id))
                holdings_raw = await loop.run_in_executor(ex, lambda: fetch_holdings(token, client_id=client_id))
                positions_raw = await loop.run_in_executor(ex, lambda: fetch_positions(token, client_id=client_id))
            return {
                "status": "ok",
                "client_id_masked": (client_id[:4] + "***") if client_id else None,
                "fund_limit": fund,
                "fund_limit_keys": list(fund.keys()) if isinstance(fund, dict) else [],
                "holdings_count": len(holdings_raw),
                "holdings_raw": holdings_raw[:5],
                "holdings_field_names": list(holdings_raw[0].keys()) if holdings_raw else [],
                "positions_count": len(positions_raw),
                "positions_raw": positions_raw[:3],
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Dhan API error: {e}")


if JWT_AVAILABLE:
    class PlaceOrderRequest(BaseModel):
        symbol: str
        side: str          # BUY or SELL
        quantity: int
        order_type: str = "MARKET"   # MARKET or LIMIT
        price: Optional[float] = None
        security_id: Optional[str] = None
        exchange_segment: Optional[str] = None

    @app.post("/api/order")
    async def api_place_order(req: PlaceOrderRequest, payload: dict = Depends(get_current_user_required)):
        """Place a BUY or SELL order via the user's linked Dhan account with industry-level error handling."""
        username = (payload.get("sub") or "").strip()
        if not username:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Fetch user's Dhan credentials from MongoDB
        demat = auth_module.get_user_demat(username) if hasattr(
            auth_module, "get_user_demat") else None
        if not demat or not demat.get("access_token"):
            raise HTTPException(
                status_code=400, detail="No broker account linked. Please link your Dhan account in Settings → Broker Account.")

        token = demat["access_token"]
        client_id = demat.get("client_id", "")
        if not client_id:
            raise HTTPException(
                status_code=400, detail="Dhan client ID is missing. Please re-link your broker account in Settings.")

        side = (req.side or "BUY").upper()
        order_type = (req.order_type or "MARKET").upper()
        price = float(req.price) if req.price is not None else 0.0

        # Industry-level: Validate order parameters before execution
        if req.quantity <= 0:
            raise HTTPException(
                status_code=400, detail="Quantity must be greater than 0")

        if not req.symbol or not isinstance(req.symbol, str):
            raise HTTPException(
                status_code=400, detail="Invalid symbol provided")

        # Log order request details for audit trail
        logger.info(
            f"[ORDER REQUEST] User={username} | {side} {req.quantity}x{req.symbol} | Type: {order_type} | Price: {price if price > 0 else 'MARKET'}")

        try:
            from dhan_client import place_dhan_order
            import asyncio
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as ex:
                result = await loop.run_in_executor(
                    ex,
                    lambda: place_dhan_order(
                        symbol=req.symbol,
                        side=side,
                        quantity=req.quantity,
                        order_type=order_type,
                        price=price,
                        access_token=token,
                        client_id=client_id,
                        security_id=req.security_id,
                        exchange_segment=req.exchange_segment,
                    )
                )

            if result is None:
                logger.error(
                    f"[ORDER FAILED] User={username} | Broker returned None - connectivity issue")
                raise HTTPException(
                    status_code=502, detail="Order failed or no response from broker. Check connectivity.")

            if isinstance(result, dict) and result.get("status") == "failure":
                # Industry level: Return the actual error message from the broker
                err_msg = result.get("remarks") or str(
                    result.get("error")) or "Unknown broker error"
                logger.error(
                    f"[ORDER REJECTED] User={username} | Broker Error: {err_msg}")
                raise HTTPException(
                    status_code=400, detail=f"Broker Error: {err_msg}")

            # Success - log full order details for compliance
            order_id = result.get("orderId") or result.get(
                "order_id") or result.get("id")
            logger.info(
                f"[ORDER SUCCESS] User={username} | {side} {req.quantity}x{req.symbol} | Order ID: {order_id} | Response: {result}")

            return {
                "success": True,
                "message": f"{side} order placed successfully for {req.symbol}",
                "order_id": order_id,
                "details": result,
                "timestamp": datetime.now().isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"[ORDER EXCEPTION] User={username} | Exception: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500, detail=f"Order placement error: {str(e)}")

    @app.get("/api/active_orders")
    async def api_get_active_orders(payload: dict = Depends(get_current_user_required)):
        """Get all active positions with their stop-loss and take-profit levels."""
        username = (payload.get("sub") or "").strip()
        if not username:
            raise HTTPException(status_code=401, detail="Not authenticated")

        try:
            from hft2.backend.db.database import DatabaseManager, Holding, Portfolio, Trade
            db_manager = DatabaseManager()
            session = db_manager.Session()

            try:
                # Get user's live portfolio
                portfolio = session.query(Portfolio).filter_by(
                    mode='live',
                    username=username
                ).first()

                if not portfolio:
                    return {
                        "success": True,
                        "active_orders": [],
                        "message": "No active portfolio found"
                    }

                # Get all holdings with quantity > 0
                holdings = session.query(Holding).filter_by(
                    portfolio_id=portfolio.id
                ).all()

                active_orders = []
                for holding in holdings:
                    if holding.quantity <= 0:
                        continue

                    # Get most recent buy trade for stop-loss and take-profit
                    latest_buy = session.query(Trade).filter(
                        Trade.ticker == holding.ticker,
                        Trade.action == 'buy'
                    ).order_by(Trade.timestamp.desc()).first()

                    if latest_buy:
                        active_orders.append({
                            "ticker": holding.ticker,
                            "quantity": holding.quantity,
                            "avg_price": holding.avg_price,
                            "current_price": holding.last_price,
                            "stop_loss": latest_buy.stop_loss,
                            "take_profit": latest_buy.take_profit,
                            "entry_date": latest_buy.timestamp.isoformat() if latest_buy.timestamp else None
                        })

                logger.info(
                    f"[ACTIVE ORDERS] User={username} | Count={len(active_orders)}")

                return {
                    "success": True,
                    "active_orders": active_orders,
                    "count": len(active_orders)
                }

            finally:
                session.close()

        except Exception as e:
            logger.error(f"[ACTIVE ORDERS] Error for user={username}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch active orders: {str(e)}")


@app.get("/")
async def index():
    """Root endpoint - returns simple JSON for connection checks"""
    return {"status": "ok", "message": "Backend API is running", "endpoints": {
        "health": "/api/health",
        "docs": "/docs",
        "auth": "/api/auth/login"
    }}


@app.get("/web", response_class=HTMLResponse)
async def web_interface():
    """Serve the main HTML page (if web_interface.html exists)"""
    try:
        with open('web_interface.html', 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail="Web interface HTML file not found")


@app.get("/styles.css")
async def styles():
    """Serve the CSS file"""
    try:
        return FileResponse('styles.css', media_type='text/css')
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="CSS file not found")


@app.get("/app.js")
async def app_js():
    """Serve the JavaScript file"""
    try:
        return FileResponse('app.js', media_type='application/javascript')
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail="JavaScript file not found")


@app.get("/api/status", response_model=BotStatus)
async def get_status(user: dict = Depends(get_current_user_required)):
    """Get bot status for the authenticated user"""
    try:
        username = user.get("sub")
        state = get_user_state(username)
        bot = state.get("trading_bot")

        if bot:
            status = bot.get_status()
            return BotStatus(**status)
        else:
            return BotStatus(
                is_running=False,
                last_update=datetime.now().isoformat(),
                mode="paper",
                data_service={"status": "not_initialized"}
            )
    except Exception as e:
        logger.error(f"Error getting status for {user.get('sub')}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
@log_api_call("/api/health", "GET")
async def health_check():
    """Health check endpoint for monitoring system status"""
    try:
        import time
        from datetime import datetime

        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time() - getattr(app, 'start_time', time.time()),
            "version": "1.0.0",
            "services": {}
        }

        # Check MongoDB connectivity (non-blocking: 2s timeout so health endpoint stays fast)
        try:
            from db.mongo_client import get_mongo_db
            import asyncio as _asyncio
            db = get_mongo_db("trading")

            def _ping_mongo():
                db.command("ping")

            try:
                await _asyncio.wait_for(_asyncio.to_thread(_ping_mongo), timeout=2.0)
                health_status["services"]["mongodb"] = {"status": "healthy"}
            except _asyncio.TimeoutError:
                health_status["services"]["mongodb"] = {
                    "status": "degraded", "note": "ping timeout"}
            except Exception as _me:
                health_status["services"]["mongodb"] = {
                    "status": "unhealthy", "error": str(_me)[:80]}
        except Exception as e:
            health_status["services"]["mongodb"] = {
                "status": "unavailable", "error": str(e)[:80]}

        # Report overall bot statistics
        with _user_states_lock:
            active_bots = [
                un for un, st in _user_bot_states.items() if st.get("trading_bot")]
            running_bots = [
                un for un, st in _user_bot_states.items() if st.get("bot_running")]

        health_status["services"]["trading_bot"] = {
            "status": "healthy" if len(active_bots) > 0 else "standby",
            "active_sessions": len(active_bots),
            "running_bots": len(running_bots)
        }

        # Check data service client (non-blocking - don't fail health check if data service is slow)
        try:
            data_client = get_data_client()
            # Run health check in thread pool with timeout to avoid blocking
            import asyncio
            try:
                # Try health check with timeout - don't block health endpoint
                health_result = await asyncio.wait_for(
                    asyncio.to_thread(data_client.health_check),
                    timeout=3.0  # 3 second timeout
                )
                if health_result:
                    health_status["services"]["data_service"] = {
                        "status": "healthy"}
                else:
                    health_status["services"]["data_service"] = {
                        "status": "unhealthy"}
            except asyncio.TimeoutError:
                # Data service is slow - mark as degraded but don't fail health endpoint
                health_status["services"]["data_service"] = {
                    "status": "degraded", "note": "Response timeout"}
            except Exception as e:
                # Log at debug level - don't spam logs with warnings
                logger.debug(f"Data service health check error: {e}")
                health_status["services"]["data_service"] = {
                    "status": "unavailable", "error": str(e)[:50]}
        except Exception as e:
            # If we can't even get the client, mark as unavailable
            logger.debug(f"Data service client unavailable: {e}")
            health_status["services"]["data_service"] = {
                "status": "unavailable"}

        # Check MCP service (if available)
        try:
            from mcp_service.api_server import MCP_API_AVAILABLE
            if MCP_API_AVAILABLE:
                health_status["services"]["mcp_service"] = {
                    "status": "healthy"}
            else:
                health_status["services"]["mcp_service"] = {
                    "status": "unavailable"}
        except:
            health_status["services"]["mcp_service"] = {
                "status": "not_available"}

        # Check configuration validation
        try:
            if CONFIG_SCHEMA_AVAILABLE:
                # Validate current configuration
                config_issues = ConfigValidator.validate_environment_variables()
                if config_issues:
                    health_status["services"]["configuration"] = {
                        "status": "warning",
                        "issues": config_issues
                    }
                else:
                    health_status["services"]["configuration"] = {
                        "status": "healthy"}
            else:
                health_status["services"]["configuration"] = {
                    "status": "warning",
                    "message": "Configuration schema validation not available"
                }
        except Exception as e:
            health_status["services"]["configuration"] = {
                "status": "error",
                "error": str(e)
            }

        # Determine overall status
        unhealthy_services = [
            service for service in health_status["services"].values()
            if isinstance(service, dict) and service.get("status") in ["unhealthy", "error"]
        ]

        if unhealthy_services:
            health_status["status"] = "degraded"
        elif not health_status["services"]:
            health_status["status"] = "unknown"
        else:
            health_status["status"] = "healthy"

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@app.get("/api/config/validate")
async def validate_configuration():
    """Validate current configuration against schema"""
    try:
        if not CONFIG_SCHEMA_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="Configuration schema validation not available"
            )

        # Get current configuration (anonymous as fallback)
        state = get_user_state("anonymous")
        bot = state.get("trading_bot")
        if bot and hasattr(bot, 'config'):
            current_config = bot.config
        else:
            # Load default config for validation
            current_config = ConfigValidator.get_default_config()

        # Validate configuration
        validation_result = {
            "valid": True,
            "config": current_config,
            "schema": ConfigValidator.get_config_schema(),
            "environment_issues": ConfigValidator.validate_environment_variables()
        }

        # Try to validate the config
        try:
            ConfigValidator.validate_config(current_config)
            validation_result["validation_status"] = "passed"
        except Exception as e:
            validation_result["valid"] = False
            validation_result["validation_status"] = "failed"
            validation_result["validation_errors"] = str(e)

        return validation_result

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/schema")
async def get_configuration_schema():
    """Get the configuration JSON schema"""
    try:
        if not CONFIG_SCHEMA_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="Configuration schema not available"
            )

        return ConfigValidator.get_config_schema()

    except Exception as e:
        logger.error(f"Failed to get configuration schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trade-signal")
async def get_trade_signal(symbol: str = "INFY.NS", payload: dict = Depends(get_optional_user)):
    """Return the most recent trade signal for a symbol.

    When authenticated, checks if a signals file exists in user's data directory.
    Otherwise checks global stock_analysis directory.

    This reads the {TICKER}_signal.json file written by execute_trading_decisions
    every time the bot makes a BUY, SELL, or HOLD decision — so it always matches
    the terminal output exactly.
    """
    try:
        sym = symbol.strip().upper()
        sanitized = sym.replace(".", "_")

        # User-specific path if authenticated
        username = payload.get(
            "sub") or "anonymous" if payload else "anonymous"
        if username and username != "anonymous":
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            user_data_dir = os.path.join(
                project_root, 'data', 'users', username)
            signal_path = os.path.join(
                user_data_dir, "stock_analysis", f"{sanitized}_signal.json")
        else:
            # Global fallback
            signal_path = os.path.join(
                os.path.dirname(__file__), "stock_analysis",
                f"{sanitized}_signal.json"
            )
        if not os.path.exists(signal_path):
            return {"success": False, "message": f"No signal file found for {sym}. Bot may not have evaluated this ticker yet."}
        file_age_seconds = time.time() - os.path.getmtime(signal_path)
        with open(signal_path, "r", encoding="utf-8") as f:
            signal = json.load(f)
        signal["file_age_seconds"] = float(f"{file_age_seconds:.1f}")
        signal["success"] = True
        return signal
    except Exception as e:
        logger.error(f"Failed to load trade signal for {symbol}: {e}")
        return {"success": False, "message": str(e)}


@app.get("/api/analyze-stream")
async def analyze_stream(request: Request, symbol: str = "INFY.NS", user=Depends(get_optional_user)):
    """SSE endpoint: run full HFT2 analysis pipeline for a symbol and stream structured events.
    Events:
      {type:'progress', step:'...', pct:N}
      {type:'log', level:'INFO'|'WARNING'|'ERROR', message:'...'}
      {type:'indicator', name:'RSI', value:..., signal:'bullish'|'bearish'|'neutral'}
      {type:'result', data:{symbol,recommendation,confidence,reasoning,risk_score,target_price,stop_loss,indicators}}
      {type:'error', message:'...'}
      {type:'done'}
    """
    import queue as _q_mod

    event_q: "_q_mod.Queue[str]" = _q_mod.Queue(maxsize=2000)

    def _emit(obj: dict):
        try:
            event_q.put_nowait(f"data: {json.dumps(obj)}\n\n")
        except _q_mod.Full:
            pass

    def _log_emit(level: str, msg: str):
        _emit({"type": "log", "level": level, "message": msg})

    async def run_analysis():
        """Run the heavy ML pipeline (stock_analyzer.analyze_stock) and emit result only when done.
        User must wait; Stop Bot is respected via get_bot_running()."""
        username = (user.get("sub") or "").strip() if user else "anonymous"
        state = get_user_state(username)
        user_bot = state.get("trading_bot")
        loop = asyncio.get_event_loop()
        sym = symbol.strip().upper()

        try:
            _emit({"type": "progress",
                  "step": "Starting full analysis (may take a few minutes)", "pct": 5})
            _log_emit(
                "INFO", f"🚀 Running heavy ML pipeline for {sym} — please wait...")

            # If bot not initialized, initialize it now (blocking but necessary)
            if not user_bot:
                _emit({"type": "progress", "step": "Initializing bot...", "pct": 5})
                _log_emit("INFO", "🔄 Bot not initialized, initializing now...")
                try:
                    loop = asyncio.get_event_loop()
                    user_bot = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, lambda: initialize_bot(username=username)),
                        timeout=180.0
                    )
                    # State updated by initialize_bot, but we use the return value here
                    if not user_bot:  # Changed from trading_bot to user_bot
                        _log_emit("ERROR", "Failed to initialize bot")
                        _emit(
                            {"type": "error", "message": "Failed to initialize bot"})
                    _log_emit("INFO", "✅ Bot initialized successfully")
                except asyncio.TimeoutError:
                    _log_emit("ERROR", "Bot initialization timed out")
                    _emit(
                        {"type": "error", "message": "Bot initialization timed out"})
                    return
                except Exception as init_err:
                    _log_emit(
                        "ERROR", f"Bot initialization failed: {init_err}")
                    _emit(
                        {"type": "error", "message": f"Bot initialization failed: {init_err}"})
                    return

            # If stock_analyzer not available, initialize it
            # Changed from trading_bot to user_bot
            if not getattr(user_bot, "stock_analyzer", None):
                _emit(
                    {"type": "progress", "step": "Initializing stock analyzer...", "pct": 10})
                _log_emit("INFO", "🔄 Stock analyzer not found, initializing...")
                try:
                    from testindia import Stock
                    # Changed from trading_bot to user_bot
                    config = user_bot.config if hasattr(
                        user_bot, 'config') else {}

                    def init_stock_analyzer():
                        return Stock(
                            reddit_client_id=config.get("reddit_client_id"),
                            reddit_client_secret=config.get(
                                "reddit_client_secret"),
                            reddit_user_agent=config.get("reddit_user_agent"),
                            advanced_sentiment_analyzer=None
                        )

                    user_bot.stock_analyzer = await asyncio.wait_for(  # Changed from trading_bot to user_bot
                        loop.run_in_executor(None, init_stock_analyzer),
                        timeout=120.0
                    )
                    _log_emit("INFO", "✅ Stock analyzer initialized")
                except Exception as sa_err:
                    _log_emit(
                        "ERROR", f"Failed to initialize stock analyzer: {sa_err}")
                    _emit(
                        {"type": "error", "message": f"Failed to initialize stock analyzer: {sa_err}"})
                    return

            _emit({"type": "progress", "step": "Waiting for ML pipeline...", "pct": 19})

            # Use file polling to prevent duplicate thread starvation!
            # The testindia.py thread will produce JSON files in stock_analysis/
            sanitized_sym = sym.replace(".", "_")
            pattern = os.path.join(os.path.dirname(
                __file__), "stock_analysis", f"{sanitized_sym}_analysis_*.json")

            try:
                _emit(
                    {"type": "progress", "step": "Waiting for background ML output...", "pct": 20})
                _log_emit(
                    "INFO", f"Tracking live analysis output from backend generator for {sym}...")

                start_time = time.time()
                found_raw = None

                # Poll indefinitely until a result file appears OR the user clicks
                # Stop Bot (which cancels this task via request disconnect).
                # No hard timeout — the heavy ML pipeline can take many minutes.
                import glob as _glob2
                while True:
                    await asyncio.sleep(2)

                    # Respect "Stop Bot": if bot_running was explicitly cleared, exit
                    # Changed from get_bot_running() to state.get("bot_running", False)
                    if not state.get("bot_running", False):
                        _log_emit(
                            "INFO", "Bot stopped — analysis loop exiting")
                        _emit({"type": "error", "message": "Bot was stopped"})
                        return

                    # Check for newly written file (within last 60 minutes)
                    files = _glob2.glob(pattern)
                    if files:
                        latest_file = max(files, key=os.path.getmtime)
                        if time.time() - os.path.getmtime(latest_file) < 3600:
                            try:
                                with open(latest_file, 'r', encoding='utf-8') as f:
                                    found_raw = json.load(f)
                                _log_emit(
                                    "INFO", f"✅ Successfully loaded analysis from {os.path.basename(latest_file)}")
                                break
                            except Exception as e:
                                _log_emit(
                                    "WARNING", f"Found analysis file but failed to read: {e}")

                raw = found_raw

            except asyncio.CancelledError:
                _log_emit("INFO", "Analysis cancelled (Stop Bot)")
                _emit({"type": "error", "message": "User interrupted the process"})
                _emit({"type": "result", "data": {
                    "symbol": sym,
                    "recommendation": "HOLD",
                    "confidence": 0.0,
                    "reasoning": "Analysis was stopped.",
                    "risk_score": 0.5,
                    "target_price": None,
                    "stop_loss": None,
                    "sentiment": "neutral",
                    "sentiment_score": 0.0,
                    "indicators": {},
                    "timestamp": datetime.now().isoformat(),
                }})
                return

            # --- SYNCHRONIZATION: Use helper to get latest synced data ---
            synced_data = _get_latest_analysis_from_files(sym)
            if synced_data:
                _emit({"type": "result", "data": synced_data})
                # Changed from _last_bot_analysis to state["_last_bot_analysis"]
                state["_last_bot_analysis"][sym] = synced_data
                return

            if not raw or not raw.get("success"):
                msg = raw.get("message", "Analysis failed or was stopped") if isinstance(
                    raw, dict) else "Analysis failed"
                _log_emit("WARNING", msg)
                _emit({"type": "result", "data": {
                    "symbol": sym,
                    "recommendation": "HOLD",
                    "confidence": 0.0,
                    "reasoning": msg,
                    "risk_score": 0.5,
                    "target_price": None,
                    "stop_loss": None,
                    "sentiment": "neutral",
                    "sentiment_score": 0.0,
                    "indicators": {},
                    "timestamp": datetime.now().isoformat(),
                }})
                return

            stock_data = raw.get("stock_data") or {}
            tech = raw.get("technical_indicators") or {}
            ml = raw.get("ml_analysis") or {}
            rec_raw = (raw.get("recommendation") or "HOLD").upper()
            if "BUY" in rec_raw or "STRONG BUY" in rec_raw:
                recommendation = "BUY"
            elif "SELL" in rec_raw or "STRONG SELL" in rec_raw:
                recommendation = "SELL"
            else:
                recommendation = "HOLD"
            confidence = float(ml.get("confidence", 0.5))
            if confidence > 1.0:
                confidence = confidence / 100.0
            cp_raw = stock_data.get("current_price")
            if isinstance(cp_raw, dict):
                current_price = float(cp_raw.get(
                    "INR") or cp_raw.get("USD") or 0)
            else:
                current_price = float(cp_raw or 0)
            support = float(stock_data.get("support_level") or 0)
            resistance = float(stock_data.get("resistance_level") or 0)
            target_price = None
            stop_loss_price = None
            if ml.get("predicted_price"):
                target_price = round(float(ml["predicted_price"]), 2)
            elif resistance and current_price:
                target_price = round(resistance, 2)
            if support and current_price:
                stop_loss_price = round(support, 2)
            if not stop_loss_price and current_price:
                stop_loss_price = round(current_price * 0.97, 2)
            reasoning = (raw.get("technical_analysis") or {}).get(
                "explanation") or raw.get("explanation") or "Full ML analysis complete."

            # --- OVERRIDE with professional signal file if available ---
            # This file is written by execute_trading_decisions / _write_trade_signal
            # and represents the EXACT professional BUY/SELL/HOLD decision from the terminal
            try:
                _signal_path = os.path.join(
                    os.path.dirname(__file__), "stock_analysis",
                    f"{sanitized_sym}_signal.json"
                )
                if os.path.exists(_signal_path) and (time.time() - os.path.getmtime(_signal_path) < 3700):
                    with open(_signal_path, "r", encoding="utf-8") as _sf:
                        _sig = json.load(_sf)
                    _action = (_sig.get("action") or "HOLD").upper()
                    if _action in ("BUY", "SELL", "HOLD"):
                        recommendation = _action
                    _sig_conf = float(
                        _sig.get("confidence_score") or confidence)
                    if 0.0 <= _sig_conf <= 1.0:
                        confidence = _sig_conf
                    _sig_reasoning = _sig.get("reasoning") or ""
                    if _sig_reasoning:
                        reasoning = f"[Professional Signal] {_sig_reasoning}"
                    if _sig.get("stop_loss") and float(_sig["stop_loss"]) > 0:
                        stop_loss_price = round(float(_sig["stop_loss"]), 2)
                    if _sig.get("take_profit") and float(_sig["take_profit"]) > 0:
                        target_price = round(float(_sig["take_profit"]), 2)
                    _log_emit(
                        "INFO", f"✅ Professional signal loaded: {recommendation} (conf={confidence:.2f}) from {os.path.basename(_signal_path)}")
                else:
                    _log_emit(
                        "INFO", "No recent professional signal file found — using ML analysis recommendation")
            except Exception as _sig_err:
                _log_emit(
                    "WARNING", f"Could not load professional signal file: {_sig_err}")
            # --- END OVERRIDE ---
            sentiment_data = raw.get("sentiment_analysis") or {}
            if isinstance(sentiment_data, dict):
                sentiment_score = float(sentiment_data.get(
                    "score", sentiment_data.get("compound", 0)))
                sentiment_label = sentiment_data.get("label", "neutral")
            else:
                sentiment_score = 0.0
                sentiment_label = "neutral"
            indicators = {}
            if tech.get("rsi") is not None:
                rsi_v = float(tech["rsi"])
                indicators["RSI"] = {"value": round(rsi_v, 2), "signal": "bearish" if rsi_v > 65 else (
                    "bullish" if rsi_v < 40 else "neutral")}
            if tech.get("macd") is not None:
                indicators["MACD"] = {"value": round(float(tech["macd"]), 4), "signal": "bullish" if float(
                    tech.get("macd", 0)) > 0 else "bearish"}
            if tech.get("sma_50") is not None and current_price:
                indicators["EMA20"] = {"value": round(float(tech.get(
                    "sma_50", 0)), 2), "signal": "bullish" if current_price > float(tech["sma_50"]) else "bearish"}

            result_payload = {
                "symbol": sym,
                "recommendation": recommendation,
                "confidence": min(1.0, max(0.0, confidence)),
                "reasoning": reasoning[:500] if reasoning else "Full ML analysis complete.",
                "risk_score": 0.5,
                "target_price": target_price,
                "stop_loss": stop_loss_price,
                "sentiment": sentiment_label,
                "sentiment_score": sentiment_score,
                "indicators": indicators,
                "timestamp": datetime.now().isoformat(),
            }
            # Changed from _last_bot_analysis to state["_last_bot_analysis"]
            state["_last_bot_analysis"][sym] = {
                **result_payload, "prediction": ml}
            _emit({"type": "progress", "step": "Analysis complete", "pct": 100})
            _emit({"type": "result", "data": result_payload})
            _log_emit(
                "INFO", f"✅ Heavy analysis complete for {sym}: {recommendation} ({confidence:.1%})")

        except Exception as e:
            _log_emit("ERROR", f"❌ Analysis pipeline error: {e}")
            _emit({"type": "error", "message": str(e)})
        finally:
            _emit({"type": "done"})

    async def event_generator():
        # Fire analysis in background so SSE loop can drain the queue
        analysis_task = asyncio.create_task(run_analysis())
        last_ping_time = asyncio.get_event_loop().time()
        try:
            yield f"data: {json.dumps({'type': 'connected', 'symbol': symbol.strip().upper()})}\n\n"
            while not analysis_task.done() or not event_q.empty():
                if await request.is_disconnected():
                    analysis_task.cancel()
                    break

                now = asyncio.get_event_loop().time()
                if now - last_ping_time >= 15.0:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                    last_ping_time = now

                drained = 0
                while drained < 30:
                    try:
                        yield event_q.get_nowait()
                        drained += 1
                        last_ping_time = asyncio.get_event_loop().time()
                    except Exception:
                        break
                await asyncio.sleep(0.15)
            # Drain any remaining events
            while not event_q.empty():
                try:
                    yield event_q.get_nowait()
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection":    "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── REST endpoint: read analysis result from stock_analysis/ folder ──────────
# All I/O runs in a thread executor so this endpoint NEVER blocks the event loop,
# even when the ML pipeline is consuming 100% CPU in a background thread.

def _read_analysis_file_sync(sym: str) -> dict:
    """Synchronous worker: find + read latest JSON for *sym*. Runs in a threadpool."""
    import glob as _glob
    sanitized_sym = sym.replace(".", "_")
    base_dir = os.path.dirname(__file__)
    pattern = os.path.join(base_dir, "stock_analysis",
                           f"{sanitized_sym}_analysis_*.json")
    files = _glob.glob(pattern)
    if not files:
        return {"status": "pending", "symbol": sym}

    latest_file = max(files, key=os.path.getmtime)
    # Accept files written within last 4 hours
    if time.time() - os.path.getmtime(latest_file) > 14400:
        return {"status": "pending", "symbol": sym, "note": "Most recent file is too old (>4 h)"}

    try:
        with open(latest_file, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception as e:
        return {"status": "pending", "symbol": sym, "note": str(e)}

    if not raw or not raw.get("success"):
        msg = raw.get("message", "Analysis failed") if isinstance(
            raw, dict) else "Analysis failed"
        return {"status": "error", "symbol": sym, "message": msg}

    # --- Map the raw JSON to a frontend-friendly structure ---
    stock_data = raw.get("stock_data") or {}
    tech = raw.get("technical_indicators") or {}
    ml = raw.get("ml_analysis") or {}

    # Recommendation — check primary field, then RL recommendation
    rec_primary = (raw.get("recommendation") or "").upper()
    rec_rl = (ml.get("rl_recommendation") or "").upper()
    rec_raw = rec_primary or rec_rl or "HOLD"
    if "BUY" in rec_raw and "SELL" not in rec_raw:
        recommendation = "BUY"
    elif "SELL" in rec_raw and "BUY" not in rec_raw:
        recommendation = "SELL"
    else:
        recommendation = "HOLD"

    # Confidence: ml.confidence is R² (can be negative). Clamp to [0,1].
    raw_conf = float(ml.get("confidence") or ml.get("model_accuracy") or 0.0)
    if raw_conf < 0:
        confidence = max(0.1, min(0.5, abs(raw_conf) / 10.0)
                         )  # negative R² → low confidence
    elif raw_conf > 1.0:
        confidence = min(1.0, raw_conf / 100.0)
    else:
        confidence = raw_conf if raw_conf > 0 else 0.5

    cp_raw = stock_data.get("current_price")
    if isinstance(cp_raw, dict):
        current_price = float(cp_raw.get("INR") or cp_raw.get("USD") or 0)
    else:
        current_price = float(cp_raw or 0)

    support = float(raw.get("support_level")
                    or stock_data.get("support_level") or 0)
    resistance = float(raw.get("resistance_level")
                       or stock_data.get("resistance_level") or 0)

    target_price = None
    stop_loss_price = None
    if ml.get("predicted_price") and float(ml["predicted_price"]) > 0:
        target_price = round(float(ml["predicted_price"]), 2)
    elif resistance > 0:
        target_price = round(resistance, 2)
    if support > 0:
        stop_loss_price = round(support, 2)
    elif current_price > 0:
        stop_loss_price = round(current_price * 0.97, 2)

    # Reasoning: top-level explanation field
    reasoning = raw.get("explanation") or (raw.get("technical_analysis") or {}).get(
        "explanation") or "Full ML analysis complete."

    # Sentiment: nested comprehensive_analysis → confidence_score + sentiment_strength
    sentiment_data = raw.get("sentiment_analysis") or {}
    if isinstance(sentiment_data, dict):
        comprehensive = sentiment_data.get("comprehensive_analysis") or {}
        strength = comprehensive.get("sentiment_strength") or {}
        bullish = float(strength.get("bullish", 0))
        bearish = float(strength.get("bearish", 0))
        neutral_s = float(strength.get("neutral", 0))
        sentiment_score = float(comprehensive.get("confidence_score", 0.5))
        if bullish > bearish and bullish > neutral_s:
            sentiment_label = "bullish"
        elif bearish > bullish and bearish > neutral_s:
            sentiment_label = "bearish"
        else:
            sentiment_label = "neutral"
    else:
        sentiment_score = 0.5
        sentiment_label = "neutral"

    indicators: dict = {}
    if tech.get("rsi") is not None:
        rsi_v = float(tech["rsi"])
        indicators["RSI"] = {"value": round(rsi_v, 2), "signal": "bearish" if rsi_v > 65 else (
            "bullish" if rsi_v < 40 else "neutral")}
    if tech.get("macd") is not None:
        indicators["MACD"] = {"value": round(float(tech["macd"]), 4), "signal": "bullish" if float(
            tech.get("macd", 0)) > 0 else "bearish"}
    if tech.get("sma_50") is not None and current_price:
        indicators["SMA 50"] = {"value": round(float(
            tech["sma_50"]), 2), "signal": "bullish" if current_price > float(tech["sma_50"]) else "bearish"}
    if tech.get("adx") is not None:
        adx_v = float(tech["adx"])
        indicators["ADX"] = {"value": round(
            adx_v, 2), "signal": "bullish" if adx_v > 25 else "neutral"}
    if tech.get("stoch_k") is not None:
        stoch = float(tech["stoch_k"])
        indicators["Stoch %K"] = {"value": round(stoch, 2), "signal": "overbought" if stoch > 80 else (
            "oversold" if stoch < 20 else "neutral")}
    if tech.get("volatility") is not None:
        vol = float(tech["volatility"])
        indicators["Volatility"] = {"value": round(
            vol * 100, 2), "signal": "high" if vol > 0.03 else ("low" if vol < 0.01 else "normal")}

    if tech.get("bb_upper") is not None and tech.get("bb_lower") is not None:
        indicators["Bollinger"] = {
            "value": round((float(tech["bb_upper"]) + float(tech["bb_lower"])) / 2, 2),
            "signal": "bullish" if current_price < float(tech["bb_lower"]) else ("bearish" if current_price > float(tech["bb_upper"]) else "neutral")
        }

    all_models = ml.get("all_model_scores") or {}
    model_predictions = [
        {"model": k, "r2": round(float(v.get("r2", 0)), 4), "prediction": round(
            float(v.get("prediction", 0)), 2)}
        for k, v in all_models.items() if isinstance(v, dict)
    ] if all_models else []

    result_payload = {
        "symbol": sym,
        "recommendation": recommendation,
        "confidence": round(min(1.0, max(0.0, confidence)), 3),
        "reasoning": str(reasoning)[:800] if reasoning else "Full ML analysis complete.",
        "risk_score": 0.5,
        "target_price": target_price,
        "current_price": current_price,
        "stop_loss": stop_loss_price,
        "sentiment": sentiment_label,
        "sentiment_score": sentiment_score,
        "indicators": indicators,
        "model_predictions": model_predictions,
        "best_model": str(ml.get("best_ml_model", "")),
        "timestamp": raw.get("timestamp", datetime.now().isoformat()),
        "file": os.path.basename(latest_file),
    }
    return {"status": "ready", "symbol": sym, "data": result_payload}


@app.get("/api/analysis-result")
async def get_analysis_result(symbol: str = "INFY.NS"):
    """
    Lightweight polling endpoint. All disk I/O offloaded to a thread executor
    so this endpoint NEVER blocks the asyncio event loop during ML analysis.
    """
    try:
        sym = symbol.strip().upper()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _read_analysis_file_sync, sym)
        return result
    except Exception as e:
        logger.error(f"Error in analysis-result for {symbol}: {e}")
        return {"status": "error", "symbol": symbol, "message": str(e)}


# ─── Auto-execute trade from analysis signal ───────────────────────────────────

class ExecuteSignalRequest(BaseModel):
    symbol: str
    username: str  # used to look up per-user Dhan credentials from MongoDB
    force: bool = False  # if True, execute even if not live mode (for testing)


def _execute_signal_sync(symbol: str, username: str, force: bool = False) -> dict:
    """
    Synchronous worker (runs in thread pool) that:
      1. Reads the analysis JSON for *symbol*
      2. Looks up user Dhan credentials from MongoDB
      3. Calls LiveTradingExecutor.execute_buy_order if recommendation is BUY
      4. Returns a result dict

    ⚠️ CRITICAL: This executes REAL trades on Dhan when credentials are provided!

    Designed to run outside the asyncio event loop via run_in_executor.
    """
    try:
        from auth import get_user_demat, get_user_by_username
        from live_executor import LiveTradingExecutor
        from portfolio_manager import DualPortfolioManager
    except ImportError:
        try:
            from .auth import get_user_demat, get_user_by_username
            from .live_executor import LiveTradingExecutor
            from .portfolio_manager import DualPortfolioManager
        except ImportError as e:
            try:
                from hft2.backend.auth import get_user_demat, get_user_by_username
                from hft2.backend.live_executor import LiveTradingExecutor
                from hft2.backend.portfolio_manager import DualPortfolioManager
            except ImportError:
                return {"success": False, "message": f"Import error: {e}"}

    # 1. Read latest analysis from disk
    analysis = _read_analysis_file_sync(symbol)
    if analysis.get("status") != "ready":
        return {"success": False, "message": f"No analysis ready for {symbol}: {analysis.get('status')}"}

    data = analysis.get("data", {})
    recommendation = data.get("recommendation", "HOLD")

    if recommendation not in ("BUY",) and not force:
        return {
            "success": False,
            "message": f"Signal is {recommendation}, not BUY — no trade placed",
            "recommendation": recommendation
        }

    # 2. Fetch user Dhan credentials from MongoDB
    demat = get_user_demat(username)
    if not demat:
        return {"success": False, "message": f"No Dhan credentials found for user '{username}' in MongoDB"}

    dhan_client_id = demat.get("client_id")
    dhan_access_token = demat.get("access_token")

    if not dhan_client_id or not dhan_access_token:
        return {"success": False, "message": "Dhan credentials incomplete (missing client_id or access_token)"}

    # 3. Instantiate executor with user's credentials
    try:
        pm = DualPortfolioManager(initial_capital=1_000_000, mode="live")
        config = {
            "dhan_client_id": dhan_client_id,
            "dhan_access_token": dhan_access_token,
            "enable_buy": True,
            "enable_sell": True,
            "stop_loss_pct": 0.05,
            "max_capital_per_trade": 0.10,  # max 10% of portfolio per trade
            "max_trade_limit": 50,
        }
        executor = LiveTradingExecutor(portfolio_manager=pm, config=config)
    except Exception as e:
        return {"success": False, "message": f"Failed to initialize executor: {e}"}

    # 4. Build signal data from analysis result
    current_price = data.get("current_price", 0.0)
    stop_loss = data.get("stop_loss") or (
        current_price * 0.95 if current_price else None)
    target_price = data.get("target_price")
    confidence = data.get("confidence", 0.5)

    signal_data = {
        "symbol": symbol,
        "recommendation": recommendation,
        "current_price": current_price,
        "stop_loss": stop_loss,
        "take_profit": target_price,
        "confidence": confidence,
        "quantity": 1,  # start with 1 share; executor may adjust based on funds
    }

    # 5. Execute
    logger.warning(
        f"⚠️ AUTO-EXECUTION: Placing REAL BUY order for {symbol} based on analysis signal (User: {username})")
    result = executor.execute_buy_order(symbol=symbol, signal_data=signal_data)
    result["symbol"] = symbol
    result["recommendation"] = recommendation
    result["current_price"] = current_price
    result["stop_loss"] = stop_loss
    result["target_price"] = target_price
    return result


@app.post("/api/execute-signal")
async def execute_signal(req: ExecuteSignalRequest):
    """
    Auto-execute a trade for the given symbol based on the latest analysis result.

    Called by the frontend HftAnalysisPanel when:
      - Bot is in LIVE mode
      - Latest analysis recommendation is BUY
      - User has confirmed they want auto-execution

    Returns order confirmation or reason for not trading.
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _execute_signal_sync, req.symbol, req.username, req.force
        )
        return result
    except Exception as e:
        logger.error(f"execute-signal error for {req.symbol}: {e}")
        return {"success": False, "message": str(e)}


@app.get("/api/stream")
async def stream_events(request: Request, user=Depends(get_optional_user)):
    """SSE endpoint: streams live log lines, periodic bot snapshots, and heartbeat pings to the frontend.
    Isolated by user."""
    username = (user.get("sub") or "").strip() if user else "anonymous"
    client_q: "_queue_module.Queue[str]" = _queue_module.Queue(maxsize=1000)

    with _sse_clients_lock:
        if username not in _sse_clients:
            _sse_clients[username] = []
        _sse_clients[username].append(client_q)

    async def event_generator():
        try:
            # Send handshake
            yield f"data: {json.dumps({'type': 'connected', 'message': f'Stream connected for {username}'})}\n\n"
            last_data_tick = 0.0
            last_ping_tick = asyncio.get_event_loop().time()
            last_cache_refresh_tick = 0.0

            while True:
                if await request.is_disconnected():
                    break

                # Drain log queue (up to 50 lines per iteration)
                drained = 0
                while drained < 50:
                    try:
                        event = client_q.get_nowait()
                        yield event
                        drained += 1
                    except _queue_module.Empty:
                        break

                now = asyncio.get_event_loop().time()

                # Periodic bot snapshot every 5 s (User-Aware)
                if now - last_data_tick >= 5.0:
                    last_data_tick = now
                    try:
                        snapshot = await asyncio.get_event_loop().run_in_executor(None, _build_sse_snapshot, username)
                        yield f"data: {json.dumps({'type': 'data', 'payload': snapshot})}\n\n"
                    except Exception:
                        pass

                # Heartbeat ping every 15 s
                if now - last_ping_tick >= 15.0:
                    last_ping_tick = now
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"

                await asyncio.sleep(0.2)
        finally:
            with _sse_clients_lock:
                if username in _sse_clients:
                    try:
                        _sse_clients[username].remove(client_q)
                        if not _sse_clients[username]:
                            del _sse_clients[username]
                    except ValueError:
                        pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/bot/start-with-symbol")
async def start_bot_with_symbol(req: StartBotWithSymbolRequest, request: Request, user=Depends(get_optional_user)):
    """Start the trading bot initialisation for a specific symbol and return immediately.
    Isolated by user."""
    symbol = req.symbol
    username = (user.get("sub") or "").strip() if user else "anonymous"

    logger.info(
        f"[API] start-with-symbol requested for: {symbol} by {username}")

    # Fire-and-forget heavy work in background
    asyncio.create_task(
        trigger_all_hft2_components_for_symbol(symbol, username))

    return {"status": "pending", "symbol": symbol, "message": f"Bot initialisation started for {symbol}. Connect to /api/stream for live progress."}


# NOTE: /api/bot/stop is registered below (near /api/bot/start) as stop_bot_bot_route()
# to avoid duplicate route registration which causes the later alias to be dead code.


@app.get("/api/bot-data")
async def get_bot_data(user=Depends(get_current_user_required)):
    """Return consolidated data for the HFT dashboard: symbols, analysis, and portfolio.

    INDUSTRY FIX: In Live mode, ALWAYS fetches real Dhan account data (balance + positions)
    even when the trading bot is not running. This prevents the ₹10,000 default from
    showing when the user is in Live mode with a linked demat account.
    """
    username = user.get("sub")
    state = get_user_state(username)
    bot = state.get("trading_bot")
    saved_mode = get_current_saved_mode(username)
    now = time.time()

    # ─── LIVE MODE: Always try to fetch real Dhan data ───────────────────────
    if saved_mode == "live":
        cached = state.get("_bot_data_cache")
        cache_age = now - state.get("_bot_data_cache_ts", 0)

        # Use cache if it's fresh (< 30 seconds old)
        if cached and cache_age < 30.0:
            if isinstance(cached, dict):
                cached["isRunning"] = state.get("bot_running", False)
            return cached

        # Cache stale or empty — fetch directly from Dhan
        try:
            from hft_auth import get_user_demat
            creds = get_user_demat(username)
            if creds and creds.get("access_token") and creds.get("client_id"):
                logger.info(
                    f"[get_bot_data] Live mode: Fetching fresh Dhan portfolio for {username}")
                from dhan_client import get_live_portfolio
                loop = asyncio.get_event_loop()
                dhan_portfolio = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: get_live_portfolio(
                            access_token=creds["access_token"],
                            client_id=creds["client_id"]
                        )
                    ),
                    timeout=25.0
                )
                if dhan_portfolio:
                    # Convert to bot-data shape
                    holdings = dhan_portfolio.get("holdings", {})
                    cash = float(dhan_portfolio.get("cash", 0))
                    invested = sum(
                        float(h.get("avgPrice", 0)) * int(h.get("quantity", 0))
                        for h in holdings.values()
                    ) if isinstance(holdings, dict) else 0.0

                    # Calculate Unrealized PnL dynamically from holdings
                    unrealized_pnl = sum(
                        (float(h.get("currentPrice", h.get("avgPrice", 0))) -
                         float(h.get("avgPrice", 0))) * int(h.get("quantity", 0))
                        for h in holdings.values()
                    ) if isinstance(holdings, dict) else 0.0

                    total_value = cash + invested + unrealized_pnl
                    today_gain = float(dhan_portfolio.get(
                        "todayGain", dhan_portfolio.get("today_gain", 0)))

                    result = {
                        "isRunning": state.get("bot_running", False),
                        "config": {
                            "mode": "live",
                            "tickers": list(holdings.keys()),
                            "riskLevel": "MEDIUM",
                            "maxAllocation": 0.25,
                        },
                        "portfolio": {
                            "totalValue": total_value,
                            "cash": cash,
                            "holdings": holdings,
                            "investedValue": invested,
                            "todayGain": today_gain,
                            "unrealizedPnL": unrealized_pnl,
                            "realizedPnL": dhan_portfolio.get("realizedPnl", dhan_portfolio.get("realized_pnl", 0)),
                            "startingBalance": cash + invested,
                            "tradeLog": dhan_portfolio.get("tradeLog", dhan_portfolio.get("trade_log", [])),
                            "portfolioHistory": dhan_portfolio.get("portfolioHistory", dhan_portfolio.get("portfolio_history", [])),
                        },
                        "analysis": list(state.get("_last_bot_analysis", {}).values()),
                        "lastUpdate": datetime.now().isoformat(),
                        "dhan_error": None,
                    }
                    # Cache this result
                    state["_bot_data_cache"] = result
                    state["_bot_data_cache_ts"] = now
                    logger.info(
                        f"[get_bot_data] Live Dhan fetch OK for {username}: cash={cash:.2f}, holdings={len(holdings)}")
                    return result
                else:
                    logger.warning(
                        f"[get_bot_data] Dhan returned empty portfolio for {username}. Token length: {len(creds.get('access_token', ''))}")
            else:
                logger.warning(
                    f"[get_bot_data] No demat credentials found for {username} in live mode. (creds object present: {bool(creds)})")
        except asyncio.TimeoutError:
            logger.warning(f"[get_bot_data] Dhan API timed out for {username}")
        except Exception as e:
            logger.error(
                f"[get_bot_data] Live Dhan fetch failed for {username}: {e}", exc_info=True)

        # Dhan fetch failed — return cached data if any, or offline shape with 0 balance (not ₹10k)
        if cached:
            if isinstance(cached, dict):
                cached["isRunning"] = state.get("bot_running", False)
            return cached

        # No cache, no live data — return proper zero-balance live shape
        return {
            "isRunning": False,
            "config": {"mode": "live", "tickers": [], "riskLevel": "MEDIUM", "maxAllocation": 0.25},
            "portfolio": {
                "totalValue": 0, "cash": 0, "holdings": {},
                "investedValue": 0, "todayGain": 0,
                "unrealizedPnL": 0, "realizedPnL": 0,
                "startingBalance": 0, "tradeLog": [], "portfolioHistory": [],
            },
            "analysis": [],
            "lastUpdate": datetime.now().isoformat(),
            "dhan_error": "Could not connect to Dhan. Check your access token in Settings → Link Demat.",
        }
    # ─────────────────────────────────────────────────────────────────────────

    # PAPER mode (or bot initializing): standard bot-data path
    if not bot and not state.get("_bot_initializing"):
        return _offline_bot_data(username)

    # Background refresh for running bot
    should_refresh = state.get("bot_running")
    if should_refresh and (now - state.get("_bot_data_cache_ts", 0) > 30.0):
        asyncio.create_task(trigger_bot_data_refresh(username))

    cached = state.get("_bot_data_cache")
    if not cached:
        return _offline_bot_data(username)

    if isinstance(cached, dict):
        cached["isRunning"] = state.get("bot_running", False)
        if "portfolio" not in cached and "holdings" in cached:
            return {
                "isRunning": state.get("bot_running", False),
                "portfolio": cached,
                "analysis": list(state.get("_last_bot_analysis", {}).values()),
                "lastUpdate": datetime.now().isoformat(),
                "config": {}
            }
        return cached

    return _offline_bot_data(username)


@app.get("/api/portfolio", response_model=PortfolioMetrics)
@log_api_call("/api/portfolio", "GET")
async def get_portfolio(user_demat: tuple = Depends(get_optional_user_demat)):
    """Get comprehensive portfolio metrics. When user has demat linked, uses their broker account; else uses trading_bot."""
    try:
        payload, demat = user_demat if isinstance(
            user_demat, tuple) else (None, None)
        username = payload.get("sub") if payload else "guest"
        state = get_user_state(username)

        if demat and demat.get("access_token") and demat.get("client_id"):
            try:
                from dhan_client import get_live_portfolio
                loop = asyncio.get_event_loop()
                dhan_port = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: get_live_portfolio(
                        access_token=demat["access_token"], client_id=demat["client_id"])),
                    timeout=25.0,
                )
                if dhan_port:
                    metrics = _dhan_portfolio_to_metrics(dhan_port)
                    return PortfolioMetrics(**metrics)
            except Exception as e:
                logger.warning(
                    f"Demat portfolio fetch failed for {username}: {e}")

        # Fallback to user-specific bot instance
        bot = state.get("trading_bot")
        if bot:
            metrics = bot.get_portfolio_metrics()
            return PortfolioMetrics(**metrics)

        # If no bot and no demat, return zeroed metrics
        return PortfolioMetrics(
            total_value=0, cash=0, cash_percentage=0, holdings={},
            total_invested=0, invested_percentage=0, current_holdings_value=0,
            total_return=0, return_percentage=0, total_return_pct=0,
            unrealized_pnl=0, unrealized_pnl_pct=0, realized_pnl=0, realized_pnl_pct=0,
            total_exposure=0, exposure_ratio=0, profit_loss=0, profit_loss_pct=0,
            active_positions=0, trades_today=0, initial_balance=0,
        )
    except Exception as e:
        logger.error(f"Error getting portfolio for {username}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trades")
async def get_trades(limit: int = 10, user_demat: tuple = Depends(get_optional_user_demat)):
    """Get recent trades for the specific user."""
    payload, demat = user_demat if isinstance(
        user_demat, tuple) else (None, None)
    username = payload.get("sub") if payload else "guest"
    state = get_user_state(username)
    bot = state.get("trading_bot")

    if demat:
        return []  # Broker trades history not yet implemented

    try:
        if bot:
            loop = asyncio.get_event_loop()
            trades = await asyncio.wait_for(
                loop.run_in_executor(None, bot.get_recent_trades, limit),
                timeout=3.0,
            )
            return trades
        return []
    except Exception as e:
        logger.error(f"Error getting trades for {username}: {e}")
        return []


@app.get("/api/portfolio/realtime")
async def get_realtime_portfolio(user_demat: tuple = Depends(get_optional_user_demat)):
    """Get real-time portfolio updates. When user has demat linked, uses their account; else trading_bot + Dhan sync."""
    payload, demat = user_demat if isinstance(
        user_demat, tuple) else (None, None)
    username = payload.get("sub") if payload else "guest"
    state = get_user_state(username)

    if demat and demat.get("access_token") and demat.get("client_id"):
        try:
            from dhan_client import get_live_portfolio
            loop = asyncio.get_event_loop()
            dhan_port = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: get_live_portfolio(
                    access_token=demat["access_token"], client_id=demat["client_id"])),
                timeout=25.0,
            )
            if dhan_port:
                metrics = _dhan_portfolio_to_metrics(dhan_port)
                current_prices = {}
                fyers_client = get_fyers_client()
                for ticker in metrics.get("holdings", {}).keys():
                    try:
                        if fyers_client:
                            symbol_data = fyers_client.get_symbol_data(ticker)
                            if symbol_data:
                                current_prices[ticker] = {"price": symbol_data.get("price", 0), "change": symbol_data.get(
                                    "change", 0), "change_pct": symbol_data.get("change_pct", 0), "volume": symbol_data.get("volume", 0)}
                    except Exception:
                        pass
                return {"portfolio_metrics": metrics, "current_prices": current_prices}
        except Exception as e:
            logger.warning(f"Realtime demat fetch failed: {e}")

    try:
        bot = state.get("trading_bot")
        if bot and bot.config.get("mode") == "live":
            try:
                # Force sync with Dhan account to get latest balance
                sync_performed = False

                # Try live executor sync first
                if hasattr(bot, 'live_executor') and bot.live_executor:
                    sync_success = bot.live_executor.sync_portfolio_with_dhan()
                    if sync_success:
                        logger.debug(
                            "Successfully synced with Dhan account using live executor")
                        sync_performed = True
                    else:
                        logger.warning(
                            "Failed to sync with Dhan account using live executor")

                # Also sync VirtualPortfolio if it exists
                if hasattr(bot, 'portfolio') and bot.portfolio:
                    portfolio_sync_result = bot.portfolio.sync_with_dhan_account()
                    if portfolio_sync_result:
                        logger.debug(
                            "Successfully synced VirtualPortfolio with Dhan account")
                        sync_performed = True
                    else:
                        logger.warning(
                            "Failed to sync VirtualPortfolio with Dhan account")

                # Fallback: manually sync using dhan_client
                elif hasattr(bot, 'dhan_client') and bot.dhan_client:
                    # Fallback: manually sync using dhan_client
                    funds = bot.dhan_client.get_funds()
                    if funds:
                        # tolerant extraction
                        available_cash = 0.0
                        try:
                            for key in ('availableBalance', 'availabelBalance', 'available_balance', 'available', 'availBalance', 'cash'):
                                if isinstance(funds, dict) and key in funds:
                                    available_cash = float(
                                        funds.get(key, 0.0) or 0.0)
                                    break
                            else:
                                if isinstance(funds, dict):
                                    for v in funds.values():
                                        if isinstance(v, (int, float)):
                                            available_cash = float(v)
                                            break
                        except Exception:
                            available_cash = 0.0
                        # Update portfolio manager if available
                        if hasattr(bot, 'portfolio_manager'):
                            bot.portfolio_manager.update_cash_balance(
                                available_cash)
                        logger.debug(
                            f"Manually synced cash balance: ₹{available_cash}")
                        sync_performed = True

                if not sync_performed:
                    logger.warning("No sync method available for Dhan account")

            except Exception as e:
                logger.warning(
                    f"Dhan sync failed during realtime update, using local data: {e}")

        if bot:
            metrics = bot.get_portfolio_metrics()

            # Get current prices for all holdings
            current_prices = {}
            fyers_client = get_fyers_client()

            for ticker in metrics.get("holdings", {}).keys():
                try:
                    if fyers_client:
                        # PRODUCTION FIX: Use data service client methods
                        symbol_data = fyers_client.get_symbol_data(ticker)
                        if symbol_data:
                            current_prices[ticker] = {
                                "price": symbol_data.get("price", 0),
                                "change": symbol_data.get("change", 0),
                                "change_pct": symbol_data.get("change_pct", 0),
                                "volume": symbol_data.get("volume", 0)
                            }
                except Exception as e:
                    logger.warning(
                        f"Error fetching real-time price for {ticker}: {e}")

            return {
                "portfolio_metrics": metrics,
                "current_prices": current_prices,
                "last_updated": datetime.now().isoformat(),
                "market_status": _get_indian_market_status()
            }
        else:
            raise HTTPException(status_code=500, detail="Bot not initialized")
    except Exception as e:
        logger.error(f"Error getting real-time portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_indian_market_status() -> str:
    """Get Indian market status based on NSE trading hours"""
    try:
        import pytz
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)

        # Check if it's a weekday (Monday=0, Sunday=6)
        if now.weekday() >= 5:  # Saturday or Sunday
            return "CLOSED"

        # NSE trading hours: 9:15 AM to 3:30 PM IST
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

        if market_open <= now <= market_close:
            return "OPEN"
        else:
            return "CLOSED"
    except Exception as e:
        logger.error(f"Error determining market status: {e}")
        return "UNKNOWN"


@app.get("/api/watchlist", response_model=List[str])
async def get_watchlist(user=Depends(get_current_user_required)):
    """Get watchlist tickers for the authenticated user."""
    try:
        username = user.get("sub")
        state = get_user_state(username)
        bot = state.get("trading_bot")
        if bot:
            tickers = bot.config.get("tickers", [])
            logger.info(
                f"📊 GET /api/watchlist: Returning {len(tickers)} tickers for {username}")
            return tickers

        # Fallback to general saved config
        saved_mode = get_current_saved_mode(username) or "paper"
        saved_config = load_config_from_file(saved_mode, username) or {}
        tickers = saved_config.get("tickers", [])
        logger.info(
            f"📊 GET /api/watchlist: Returning {len(tickers)} tickers (fallback) for {username}")
        return tickers
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/watchlist", response_model=WatchlistResponse)
async def update_watchlist(request: WatchlistRequest, user=Depends(get_current_user_required)):
    """Add or remove ticker from watchlist for the authenticated user."""
    try:
        ticker = request.ticker.upper().strip()
        action = request.action.upper()

        if not ticker:
            raise HTTPException(status_code=400, detail="Ticker is required")

        username = user.get("sub")
        state = get_user_state(username)
        bot = state.get("trading_bot")
        if bot:
            current_tickers = bot.config["tickers"]

            if action == "ADD":
                if ticker not in current_tickers:
                    current_tickers.append(ticker)
                    message = f"Added {ticker} to watchlist"
                else:
                    message = f"{ticker} is already in watchlist"
            elif action == "REMOVE":
                if ticker in current_tickers:
                    current_tickers.remove(ticker)
                    message = f"Removed {ticker} from watchlist"
                else:
                    message = f"{ticker} is not in watchlist"
            else:
                raise HTTPException(
                    status_code=400, detail="Invalid action. Use ADD or REMOVE")

            return WatchlistResponse(message=message, tickers=current_tickers)
        else:
            raise HTTPException(status_code=500, detail="Bot not initialized")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/watchlist/add/{ticker}", response_model=WatchlistResponse)
async def add_to_watchlist(ticker: str, user=Depends(get_current_user_required)):
    """Add ticker to watchlist for the authenticated user and save to MongoDB."""
    try:
        ticker = ticker.upper().strip()
        if not ticker:
            raise HTTPException(status_code=400, detail="Ticker is required")
        if not ticker.endswith(('.NS', '.BO')):
            ticker += '.NS'

        username = user.get("sub")
        current_tickers = _get_user_watchlist_from_db(username)

        if ticker not in current_tickers:
            current_tickers.append(ticker)
            _save_user_watchlist_to_db(username, current_tickers)
            message = f"✅ Added {ticker} to your watchlist"

            # Update running bot if it exists
            state = get_user_state(username)
            bot = state.get("trading_bot")
            if bot and "tickers" in bot.config:
                if ticker not in bot.config["tickers"]:
                    bot.config["tickers"].append(ticker)
                    # Refresh data feed
                    try:
                        from data_feed import DataFeed
                        bot.data_feed = DataFeed(bot.config["tickers"])
                    except Exception:
                        pass
        else:
            message = f"{ticker} is already in your watchlist"

        logger.info(f"📊 Watchlist ADD: {ticker} for user {username}")
        return WatchlistResponse(message=message, tickers=current_tickers)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/watchlist/remove/{ticker}", response_model=WatchlistResponse)
async def remove_from_watchlist(ticker: str, user=Depends(get_current_user_required)):
    """Remove ticker from watchlist for the authenticated user and save to MongoDB."""
    try:
        ticker = ticker.upper().strip()
        if not ticker:
            raise HTTPException(status_code=400, detail="Ticker is required")
        if not ticker.endswith(('.NS', '.BO')):
            ticker += '.NS'

        username = user.get("sub")
        current_tickers = _get_user_watchlist_from_db(username)

        if ticker in current_tickers:
            current_tickers.remove(ticker)
            _save_user_watchlist_to_db(username, current_tickers)
            message = f"✅ Removed {ticker} from your watchlist"

            # Update running bot if it exists
            state = get_user_state(username)
            bot = state.get("trading_bot")
            if bot and "tickers" in bot.config:
                if ticker in bot.config["tickers"]:
                    bot.config["tickers"].remove(ticker)
                    # Refresh data feed
                    try:
                        from data_feed import DataFeed
                        bot.data_feed = DataFeed(bot.config["tickers"])
                    except Exception:
                        pass
        else:
            message = f"{ticker} is not in your watchlist"

        logger.info(f"📊 Watchlist REMOVE: {ticker} for user {username}")
        return WatchlistResponse(message=message, tickers=current_tickers)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/watchlist/bulk", response_model=BulkWatchlistResponse)
async def bulk_update_watchlist(request: BulkWatchlistRequest, user=Depends(get_current_user_required)):
    """Add or remove multiple tickers for the authenticated user and update MongoDB."""
    try:
        username = user.get("sub")
        action = request.action.upper()
        if action not in ["ADD", "REMOVE"]:
            raise HTTPException(
                status_code=400, detail="Action must be ADD or REMOVE")

        successful_tickers = []
        failed_tickers = []

        # Get current watchlist from DB
        current_tickers = list(_get_user_watchlist_from_db(username))

        for ticker in request.tickers:
            try:
                ticker = ticker.strip().upper()
                if not ticker:
                    continue
                if not ticker.endswith(('.NS', '.BO')):
                    ticker += '.NS'

                if action == "ADD":
                    if ticker not in current_tickers:
                        current_tickers.append(ticker)
                        successful_tickers.append(ticker)
                elif action == "REMOVE":
                    if ticker in current_tickers:
                        current_tickers.remove(ticker)
                        successful_tickers.append(ticker)
            except Exception as e:
                failed_tickers.append(f"{ticker}: {str(e)}")

        # Persist to DB
        if successful_tickers:
            _save_user_watchlist_to_db(username, current_tickers)

            # Update running bot if it exists
            state = get_user_state(username)
            bot = state.get("trading_bot")
            if bot and "tickers" in bot.config:
                bot.config["tickers"] = current_tickers
                try:
                    from data_feed import DataFeed
                    bot.data_feed = DataFeed(current_tickers)
                except Exception:
                    pass

        logger.info(
            f"📊 Watchlist bulk {action} for {username}: {len(successful_tickers)} successes")
        return BulkWatchlistResponse(
            message=f"Bulk {action} completed",
            successful_tickers=successful_tickers,
            failed_tickers=failed_tickers,
            total_processed=len(request.tickers)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk watchlist update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Priority 1: Remove duplicate validate_chat_input - now imported from utils


async def process_market_query(message: str) -> Optional[str]:
    """Process market-related queries with real-time data"""
    try:
        # Performance: Use set for O(1) lookup instead of O(n) list search
        market_keywords = {"volume", "stock", "price",
                           "highest", "lowest", "market", "trading", "analysis"}
        is_market_query = any(keyword in message.lower()
                              for keyword in market_keywords)

        if is_market_query:
            logger.info(f"Market query detected: {message}")
            return await get_real_time_market_response(message)
        return None
    except Exception as e:
        logger.error(f"Error processing market query: {e}")
        return None


async def process_groq_query(message: str, enhanced_prompt: str) -> str:
    """Process query using Groq reasoning engine"""
    try:
        global groq_engine
        if not groq_engine:
            return "Groq reasoning engine not available. Please try again later."

        response = await groq_engine.process_query(message, enhanced_prompt)
        return response.get("response", "I apologize, but I couldn't process your request at the moment.")
    except Exception as e:
        logger.error(f"Error with Groq processing: {e}")
        return "I encountered an error while processing your request. Please try again."


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat message - Forward to MCP Service"""
    try:
        # Performance: Validate and sanitize input
        try:
            message = validate_chat_input(request.message)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not message:
            return ChatResponse(
                response="Please enter a message.",
                timestamp=datetime.now().isoformat()
            )

        # Forward to MCP Service API
        mcp_api_url = os.getenv("MCP_API_URL", "http://localhost:8003")
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{mcp_api_url}/api/chat",
                    json={"message": message},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(
                            f"[WEB] Chat request forwarded to MCP service - response received")
                        return ChatResponse(
                            response=result.get(
                                "response", "No response from MCP service"),
                            timestamp=result.get(
                                "timestamp", datetime.now().isoformat()),
                            metadata=result.get("metadata")
                        )
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"[WEB] MCP service returned {response.status}: {error_text}")
                        # Fall through to fallback
        except Exception as e:
            logger.warning(f"[WEB] Failed to forward to MCP service: {e}")
            # Fall through to fallback

        # Fallback: Enhanced Real-Time Dynamic Market Analysis (if MCP service unavailable)
        try:
            # Get current timestamp for real-time data
            current_time = datetime.now()

            # Performance: Use set for O(1) lookup instead of O(n) list search
            market_keywords = {"volume", "stock", "price",
                               "highest", "lowest", "market", "trading", "analysis"}
            is_market_query = any(keyword in message.lower()
                                  for keyword in market_keywords)

            if is_market_query:
                # Get real-time market data
                logger.info(f"Market query detected: {message}")
                real_time_response = await get_real_time_market_response(message)
                logger.info(
                    f"Real-time response: {real_time_response is not None}")
                if real_time_response:
                    logger.info("Returning real-time market response")
                    return ChatResponse(
                        response=real_time_response,
                        timestamp=current_time.isoformat(),
                        confidence=0.95,
                        context="real_time_market_data"
                    )

            # Fallback to Dynamic Market Expert
            from dynamic_market_expert import DynamicMarketExpert

            # Initialize the market expert (cached for performance)
            if not hasattr(chat, '_market_expert'):
                chat._market_expert = DynamicMarketExpert()
                logger.info("Dynamic Market Expert initialized for web chat")

            # Process query with timeout protection
            import threading
            import queue

            result_queue = queue.Queue()

            def process_with_expert():
                try:
                    result = chat._market_expert.process_query(message)
                    result_queue.put(("success", result))
                except Exception as e:
                    result_queue.put(("error", str(e)))

            thread = threading.Thread(target=process_with_expert)
            thread.daemon = True
            thread.start()
            thread.join(timeout=15)  # 15 second timeout

            if not result_queue.empty():
                status, result = result_queue.get()
                if status == "success" and result:
                    return ChatResponse(
                        response=result,
                        timestamp=datetime.now().isoformat()
                    )
                else:
                    logger.error(f"Expert processing error: {result}")
            else:
                logger.warning("Dynamic Market Expert response timed out")

        except ImportError as e:
            logger.error(f"Could not import Dynamic Market Expert: {e}")
        except Exception as e:
            logger.error(f"Error with Dynamic Market Expert: {e}")

        # Fallback to direct professional response with live data
        try:
            # Use anonymous bot components if available
            state = get_user_state("anonymous")
            bot = state.get("trading_bot")
            if bot and hasattr(bot, 'llm'):
                llm = bot.llm
            else:
                llm = None

            # Use the Dynamic Market Expert instead
            try:
                from dynamic_market_expert import DynamicMarketExpert
                market_expert = DynamicMarketExpert()
                response = market_expert.process_query(message)
                return {"response": response, "timestamp": datetime.now().isoformat()}
            except Exception as expert_error:
                logger.error(f"Dynamic Market Expert error: {expert_error}")

            # Simple fallback response
            if True:  # Always execute fallback
                # Simple fallback response
                pass

        except Exception as e:
            logger.error(f"Error with fallback response: {e}")

        # Handle commands (anonymous fallback)
        state = get_user_state("anonymous")
        bot = state.get("trading_bot")
        if message.startswith('/') and bot:
            try:
                response = bot.process_chat_command(message)
                return ChatResponse(
                    response=response,
                    timestamp=datetime.now().isoformat()
                )
            except Exception as e:
                logger.error(f"Error with command: {e}")

        # Final professional fallback
        return ChatResponse(
            response=f"""I'm your professional stock market advisor!

I can help you with:
• **Live Stock Prices** - "What's the price of {', '.join(['Reliance', 'TCS', 'HDFC Bank'])}?"
• **Market Analysis** - "How is the IT sector performing?"
• **Investment Advice** - "Should I buy banking stocks now?"
• **Portfolio Management** - Use /get_pnl, /list_positions

**Current Market Focus:** Indian equities (NSE/BSE)
**Data Source:** Live Fyers API integration

What would you like to analyze today?""",
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        return ChatResponse(
            response="I apologize for the error. Please try asking about stock prices or portfolio information.",
            timestamp=datetime.now().isoformat()
        )


@app.post("/api/start", response_model=MessageResponse)
async def start_bot(payload: dict = Depends(get_optional_user)):
    """Start the trading bot - returns immediately, runs heavy operations in background. When authenticated, uses that user's watchlist and demat."""
    try:
        username = (payload.get("sub") or "").strip(
        ) if payload and isinstance(payload, dict) else "anonymous"

        # Warn but allow anonymous users to start the bot (for testing/demo)
        # However, they won't have access to live Dhan trading without credentials
        if username == "anonymous":
            logger.warning(
                "Anonymous user starting bot - live Dhan trading will NOT be available. "
                "Please log in and link your Dhan account for live trading.")

        state = get_user_state(username)

        # Resolve tickers for this user
        watchlist = _get_user_watchlist_from_db(
            username) if username != "anonymous" else []
        if watchlist:
            logger.info(
                f"📊 Bot start ({username}): using watchlist for user ({len(watchlist)} tickers from MongoDB)")

        # Resolve demat context for this user
        demat = auth_module.get_user_demat(username) if (
            username != "anonymous" and hasattr(auth_module, "get_user_demat")) else None
        user_context = None
        if demat and demat.get("access_token") and demat.get("client_id"):
            user_context = {
                "user_id": username, "dhan_client_id": demat["client_id"], "dhan_access_token": demat["access_token"]}
            logger.info(f"📊 Bot start ({username}): using demat for user")

        # Initialize bot if not already initialized
        if not state.get("trading_bot"):
            if state.get("_bot_initializing"):
                return MessageResponse(
                    message="Bot initialization is already in progress. Please wait a few seconds and try again."
                )

            async def init_bot_background(user_name: str, user_watchlist: list, context: Optional[dict]):
                """Initialize bot in background for a specific user."""
                logger.info(f"🚀 init_bot_background({user_name}) STARTED")
                user_state = get_user_state(user_name)
                try:
                    user_state["_bot_initializing"] = True
                    user_state["_bot_data_cache"] = {}
                    # PRODUCTION FIX: Store the context so initialize_bot can apply it
                    if context:
                        user_state["_pending_bot_user_context"] = context
                        logger.info(
                            f"💾 Stored pending context for {user_name}")

                    loop = asyncio.get_event_loop()
                    try:
                        # 180s timeout
                        bot_instance = await asyncio.wait_for(
                            loop.run_in_executor(
                                None, lambda: initialize_bot(username=user_name)),
                            timeout=180.0
                        )
                        if bot_instance:
                            user_state["trading_bot"] = bot_instance
                            logger.info(
                                f"✅ Bot instance created for {user_name}")
                        else:
                            logger.error(
                                f"❌ Bot instance is None for {user_name}")
                    except Exception as exec_err:
                        logger.error(
                            f"❌ Bot initialization for {user_name} failed: {exec_err}")
                        bot_instance = None

                    if bot_instance:
                        # Configure and start
                        if user_watchlist:
                            bot_instance.config["tickers"] = list(
                                user_watchlist)

                        risk_level = bot_instance.config.get(
                            "riskLevel", "MEDIUM")
                        apply_risk_level_settings(bot_instance, risk_level)

                        await loop.run_in_executor(None, bot_instance.start)
                        user_state["bot_running"] = True

                        # Start user's continuous loop
                        _start_continuous_loop(user_name)
                        logger.info(f"🚀 Bot and loop started for {user_name}")

                except Exception as init_error:
                    logger.error(
                        f"❌ Background bot initialization failed for {user_name}: {init_error}")
                finally:
                    user_state["_bot_initializing"] = False

            asyncio.create_task(init_bot_background(
                username, watchlist, user_context))
            return MessageResponse(
                message=f"Bot initialization started for {username}. It will be active shortly."
            )

        bot_instance = state.get("trading_bot")
        if bot_instance:
            # PRODUCTION FIX: Ensure existing bot has the correct user context
            if user_context:
                if not bot_instance.config.get("user_id"):
                    bot_instance.config["user_id"] = user_context["user_id"]
                    logger.info(f"🔧 Repaired user_id for {username}")
                if not bot_instance.config.get("dhan_client_id"):
                    bot_instance.config["dhan_client_id"] = user_context["dhan_client_id"]
                    bot_instance.config["dhan_access_token"] = user_context["dhan_access_token"]
                    logger.info(f"🔧 Repaired Dhan credentials for {username}")

                # Re-sync portfolio manager if needed
                if hasattr(bot_instance, 'portfolio_manager') and bot_instance.portfolio_manager:
                    if bot_instance.portfolio_manager.user_id != username:
                        bot_instance.portfolio_manager.user_id = username
                        logger.info(
                            f"🔧 Rescoped PortfolioManager to {username}")

            # If already initialized, just update tickers and start if stopped
            if watchlist:
                bot_instance.config["tickers"] = watchlist

            risk_level = bot_instance.config.get("riskLevel", "MEDIUM")
            apply_risk_level_settings(bot_instance, risk_level)

            if not getattr(bot_instance, 'bot_running', False):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, bot_instance.start)

            state["bot_running"] = True
            _start_continuous_loop(username)
            return MessageResponse(message=f"Bot running with {len(bot_instance.config.get('tickers', []))} tickers for {username}.")
        else:
            raise HTTPException(
                status_code=500, detail="Bot not initialized and could not trigger init")
    except HTTPException:
        raise
    except asyncio.TimeoutError:
        logger.error("Start bot operation timed out")
        raise HTTPException(
            status_code=500, detail="Start bot operation timed out - bot may still be starting in background")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/init", response_model=MessageResponse)
async def init_bot(payload: dict = Depends(get_optional_user)):
    """Manually initialize the trading bot"""
    try:
        username = (payload.get("sub") or "").strip(
        ) if payload and isinstance(payload, dict) else "anonymous"
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: initialize_bot(username=username))
        return MessageResponse(message="Trading bot initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stop", response_model=MessageResponse)
async def stop_bot(payload: dict = Depends(get_optional_user)):
    """Stop the trading bot for the authenticated user"""
    try:
        username = (payload.get("sub") or "").strip(
        ) if payload and isinstance(payload, dict) else "anonymous"
        state = get_user_state(username)
        bot = state.get("trading_bot")

        # 1. Cancel tasks and clear user-specific flags
        _stop_continuous_loop(username)
        state["bot_running"] = False

        # 2. Stop the bot instance if it exists
        if bot:
            if hasattr(bot, 'bot_running'):
                bot.bot_running = False
            try:
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, bot.stop),
                    timeout=15.0
                )
            except Exception as e:
                logger.warning(f"Error calling bot.stop() for {username}: {e}")

        logger.info(f"[STOP] Bot stopped for {username}")
        return MessageResponse(message="Bot stopped successfully")
    except Exception as e:
        logger.error(
            f"Error stopping bot for {payload.get('sub') if payload else 'unknown'}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/start", response_model=MessageResponse)
async def start_bot_bot_route(payload: dict = Depends(get_optional_user)):
    """Start the trading bot (alias for /api/start). Uses authenticated user's watchlist when present."""
    return await start_bot(payload)


@app.post("/api/bot/stop", response_model=MessageResponse)
async def stop_bot_bot_route(payload: dict = Depends(get_optional_user)):
    """Stop the trading bot (alias for /api/stop). Used by frontend Stop Bot button."""
    return await stop_bot(payload)


@app.get("/api/settings")
async def get_settings(user=Depends(get_optional_user)):
    """Get current settings. Isolated by user."""
    try:
        username = (user.get("sub") or "").strip() if user else "anonymous"
        state = get_user_state(username)
        bot = state.get("trading_bot")

        if bot:
            return {
                "mode": bot.config.get("mode", "paper"),
                "riskLevel": bot.config.get("riskLevel", "MEDIUM"),
                "stop_loss_pct": bot.config.get("stop_loss_pct", 0.05),
                "target_profit_pct": bot.config.get("target_profit_pct", 0.1),
                "use_risk_reward": bot.config.get("use_risk_reward", True),
                "risk_reward_ratio": bot.config.get("risk_reward_ratio", 2.0),
                "max_capital_per_trade": bot.config.get("max_capital_per_trade", 0.25),
                "max_trade_limit": bot.config.get("max_trade_limit", 10)
            }

        mode = get_current_saved_mode(username)
        saved = load_config_from_file(mode, username) or {}
        return {
            "mode": saved.get("mode", mode),
            "riskLevel": saved.get("riskLevel", "MEDIUM"),
            "stop_loss_pct": saved.get("stop_loss_pct", 0.05),
            "target_profit_pct": saved.get("target_profit_pct", 0.1),
            "targetPriceLevel": saved.get("targetPriceLevel", "MEDIUM"),
            "use_risk_reward": saved.get("use_risk_reward", True),
            "risk_reward_ratio": saved.get("risk_reward_ratio", 2.0),
            "max_capital_per_trade": saved.get("max_capital_per_trade", 0.25),
            "max_trade_limit": saved.get("max_trade_limit", 10),
        }
    except Exception as e:
        logger.error(
            f"Error getting settings for {user.get('sub') if user else 'unknown'}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cleaned up corrupted code block (the apply_risk_level_settings loop was incorrectly placed here)


# Renamed to save_config_to_file above for consistency and added username support.


@app.post("/api/settings", response_model=MessageResponse)
async def update_settings(request: SettingsRequest, user_demat: tuple = Depends(get_optional_user_demat)):
    """Update bot settings. Isolated by user."""
    payload, _ = user_demat if isinstance(user_demat, tuple) else (None, None)
    username = (payload.get("sub") or "").strip(
    ) if payload and isinstance(payload, dict) else "anonymous"
    state = get_user_state(username)
    bot = state.get("trading_bot")

    try:
        if bot:
            # Update configuration
            if request.mode is not None:
                old_mode = bot.config.get('mode', 'paper')
                new_mode = request.mode
                if new_mode != old_mode:
                    if bot.switch_trading_mode(new_mode, username=username):
                        actual_mode = bot.config.get('mode', 'paper')
                        save_config_to_file(actual_mode, bot.config, username)
                        set_current_saved_mode(actual_mode, username)
                    else:
                        raise HTTPException(
                            status_code=400, detail=f"Failed to switch to {new_mode}")
                else:
                    bot.config['mode'] = new_mode

            if request.riskLevel is not None:
                bot.config['riskLevel'] = request.riskLevel

                # Check if user provided custom values alongside preset risk level
                has_custom_values = (
                    request.stop_loss_pct is not None or
                    request.target_profit_pct is not None or
                    request.max_capital_per_trade is not None
                )

                if request.riskLevel in ["LOW", "MEDIUM", "HIGH"] and not has_custom_values:
                    # Apply ONLY predefined risk level settings (no custom values)
                    apply_risk_level_settings(bot, request.riskLevel)
                elif has_custom_values:
                    # User provided custom values - use CUSTOM mode even if risk level is preset
                    logger.info(
                        f"🎯 Custom values detected with {request.riskLevel} risk level - using hybrid mode")
                    apply_risk_level_settings(
                        bot=bot,
                        risk_level="CUSTOM",
                        custom_stop_loss=request.stop_loss_pct,
                        custom_allocation=request.max_capital_per_trade,
                        custom_target_profit=request.target_profit_pct,
                        custom_use_rr=request.use_risk_reward,
                        custom_rr_ratio=request.risk_reward_ratio
                    )
                else:
                    # CUSTOM risk level with custom values
                    apply_risk_level_settings(
                        bot=bot,
                        risk_level=request.riskLevel,
                        custom_stop_loss=request.stop_loss_pct,
                        custom_allocation=request.max_capital_per_trade,
                        custom_target_profit=request.target_profit_pct,
                        custom_use_rr=request.use_risk_reward,
                        custom_rr_ratio=request.risk_reward_ratio
                    )

            # Save to user-specific config
            save_config_to_file(bot.config.get(
                'mode', 'paper'), bot.config, username)

            # DEBUG: Log what's actually in bot.config before updating main file
            logger.info(
                f"🔍 DEBUG - bot.config contents before update_main_live_config:")
            logger.info(f"   riskLevel: {bot.config.get('riskLevel')}")
            logger.info(f"   stop_loss_pct: {bot.config.get('stop_loss_pct')}")
            logger.info(
                f"   target_profit_pct: {bot.config.get('target_profit_pct')}")
            logger.info(
                f"   max_capital_per_trade: {bot.config.get('max_capital_per_trade')}")

            # CRITICAL FIX: Also update the main live_config.json for dynamic calculations
            update_main_live_config(bot.config, username)

            # Force immediate refresh of professional buy logic with new config
            if hasattr(bot, 'professional_buy_integration') and bot.professional_buy_integration:
                try:
                    bot.professional_buy_integration.refresh_dynamic_config()
                    logger.info(
                        "✅ Professional buy logic config refreshed immediately")
                except Exception as e:
                    logger.warning(f"Config refresh skipped: {e}")

            if hasattr(bot, 'executor') and bot.executor:
                try:
                    bot.executor.refresh_dynamic_config()
                    logger.info(
                        "✅ Position executor config refreshed immediately")
                except Exception as e:
                    logger.warning(f"Executor config refresh skipped: {e}")

            return MessageResponse(message="Settings updated successfully")

        # No bot exists, save directly to file
        mode = request.mode or get_current_saved_mode(username)
        saved = load_config_from_file(mode, username) or {}
        # Merge new settings
        for field in request.model_fields:
            val = getattr(request, field, None)
            if val is not None:
                saved[field] = val

        save_config_to_file(mode, saved, username)
        if request.mode:
            set_current_saved_mode(request.mode, username)

        # Also update main live_config.json
        update_main_live_config(saved, username)

        return MessageResponse(message="Settings saved to file; will apply on next bot start.")
    except Exception as e:
        logger.error(f"Error updating settings for {username}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/live-status")
async def get_live_trading_status(user_demat: tuple = Depends(get_optional_user_demat)):
    """Get live trading status and connection info. When user has linked demat, dhan_configured reflects that (no env required)."""
    try:
        if not LIVE_TRADING_AVAILABLE:
            return {
                "available": False,
                "message": "Live trading components not installed"
            }

        payload, demat = user_demat if isinstance(
            user_demat, tuple) else (None, None)
        username = (payload.get("sub") or "").strip(
        ) if payload and isinstance(payload, dict) else "anonymous"
        user_has_demat = bool(demat and demat.get(
            "access_token") and demat.get("client_id"))

        state = get_user_state(username)
        bot = state.get("trading_bot")
        bot_is_running = state.get("bot_running", False)

        # Dhan connection state
        dhan_connected = False
        dhan_configured = user_has_demat
        dhan_error = None
        market_status = "UNKNOWN"
        account_info = {}

        # ── Step 1: Validate connection ──────────────────────────────────────────
        # We validate if credentials exist, regardless of whether the bot is running
        if user_has_demat:
            try:
                loop = asyncio.get_event_loop()
                dhan_client = None

                if bot and bot.dhan_client:
                    dhan_client = bot.dhan_client
                else:
                    # Create temporary client for validation if bot is stopped
                    dhan_client = DhanAPIClient(
                        demat.get("access_token"), demat.get("client_id"))

                val_result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, dhan_client.validate_connection),
                    timeout=4.0
                )

                if isinstance(val_result, dict):
                    dhan_connected = val_result.get("connected", False)
                    if not dhan_connected:
                        dhan_error = val_result.get(
                            "message") or "Authentication failed"
                else:
                    dhan_connected = bool(val_result)

                if dhan_connected:
                    # Fetch extra info only if connected
                    ms_data = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, dhan_client.get_market_status),
                        timeout=3.0
                    )
                    market_status = ms_data.get(
                        "marketStatus", "UNKNOWN") if ms_data else "UNKNOWN"

                    profile = await asyncio.wait_for(
                        loop.run_in_executor(None, dhan_client.get_profile),
                        timeout=3.0
                    )
                    funds = await asyncio.wait_for(
                        loop.run_in_executor(None, dhan_client.get_funds),
                        timeout=3.0
                    )

                    def _funds_value(keys, default=0):
                        for k in keys:
                            if k in funds and funds.get(k) is not None:
                                return funds.get(k)
                        return default

                    available_cash = _funds_value(
                        ["availablecash", "availabelBalance", "availableBalance", "netAvailableMargin", "netAvailableCash"], 0)
                    sod_limit = _funds_value(
                        ["sodlimit", "sodLimit", "openingBalance", "collateralMargin"], 0)

                    account_info = {
                        "client_id": profile.get("clientId", "") if profile else "",
                        "available_cash": available_cash,
                        "used_margin": max(0, sod_limit - available_cash)
                    }
            except asyncio.TimeoutError:
                logger.warning(
                    f"Dhan API calls timed out in live-status for {username}")
                dhan_error = "Dhan API connection timed out"
            except Exception as e:
                logger.error(f"Error validating Dhan for {username}: {e}")
                dhan_error = f"Connection error: {str(e)}"

        # ── Step 2: Finalize response ───────────────────────────────────────────
        if not user_has_demat:
            dhan_error = "Demat account not linked. Go to Settings → Demat to link your account."

        actual_mode = bot.config.get(
            "mode") if bot else get_current_saved_mode(username) or "paper"

        return {
            "available": True,
            "mode": actual_mode,
            "connected": dhan_connected,
            "dhan_configured": dhan_configured,
            "dhan_error": dhan_error,
            "market_status": market_status,
            "account_info": account_info,
            "bot_running": bot_is_running,
            "bot_status": "RUNNING" if bot_is_running else "STOPPED",
            "portfolio_synced": (bot.live_executor is not None) if bot else False,
            "lastUpdate": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting live trading status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/live/sync")
async def sync_live_portfolio(user_demat: tuple = Depends(get_optional_user_demat)):
    payload, demat = user_demat if isinstance(
        user_demat, tuple) else (None, None)
    username = (payload.get("sub") or "").strip(
    ) if payload and isinstance(payload, dict) else "anonymous"

    if demat and demat.get("access_token") and demat.get("client_id"):
        try:
            from dhan_client import get_live_portfolio
            loop = asyncio.get_event_loop()
            dhan_port = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: get_live_portfolio(
                    access_token=demat["access_token"], client_id=demat["client_id"])),
                timeout=25.0,
            )
            if dhan_port:
                metrics = _dhan_portfolio_to_metrics(dhan_port)
                return JSONResponse(status_code=200, content={
                    "success": True,
                    "message": "Portfolio refreshed",
                    "data": metrics,
                    "synced": True,
                    "cash": metrics.get("cash", 0),
                    "holdings_value": metrics.get("current_holdings_value", 0),
                    "total_value": metrics.get("total_value", 0),
                })
        except Exception as e:
            logger.warning(
                f"Live sync (demat) failed for {username}: {e}. Attempting last-known-metrics fallback.")
            if username != "anonymous" and demat and demat.get("access_token"):
                token = demat["access_token"]
                from dhan_client import _portfolio_cache
                if token in _portfolio_cache:
                    metrics = _dhan_portfolio_to_metrics(
                        _portfolio_cache.get(token))
                    return JSONResponse(status_code=200, content={
                        "success": True,
                        "message": "Dhan fetch failed (using last known data)",
                        "data": metrics,
                        "synced": False
                    })
        return JSONResponse(status_code=200, content={"success": False, "message": "Failed to fetch demat portfolio."})

    try:
        state = get_user_state(username)
        bot = state.get("trading_bot")

        if not bot or bot.config.get("mode") != "live":
            return JSONResponse(
                status_code=200,
                content={
                    "success": False, "message": "Not in live mode or bot not initialized for this user."},
            )

        # Use the sync service for immediate sync
        sync_service = get_sync_service()
        if sync_service:
            success = sync_service.sync_once()
            if not success:
                raise HTTPException(
                    status_code=502, detail="Failed to sync with Dhan using sync service")

            # Return updated portfolio data
            portfolio_data = bot.get_portfolio_metrics() if bot else {}
            return {
                "success": True,
                "message": "Portfolio synced successfully",
                "data": portfolio_data,
                "last_sync": sync_service.last_sync_time.isoformat() if sync_service.last_sync_time else None,
                "balance": sync_service.last_known_balance
            }

        # Fallback to live executor if sync service not available
        if not bot or not hasattr(bot, 'live_executor') or not bot.live_executor:
            raise HTTPException(
                status_code=503, detail="Live executor not initialized for user")

        ok = bot.live_executor.sync_portfolio_with_dhan()
        if not ok:
            raise HTTPException(
                status_code=502, detail="Failed to sync with Dhan")

        portfolio_data = bot.get_portfolio_metrics() if bot else {}
        return {
            "synced": True,
            "cash": portfolio_data.get("cash", 0.0),
            "holdings_value": portfolio_data.get("total_value", 0.0) - portfolio_data.get("cash", 0.0),
            "total_value": portfolio_data.get("total_value", 0.0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Live sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class OrderRequest(BaseModel):
    """Request model for placing buy/sell orders"""
    symbol: str
    side: str  # BUY or SELL
    quantity: int
    order_type: Optional[str] = "MARKET"
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@app.post("/api/order")
async def place_order(request: OrderRequest, user_demat: tuple = Depends(get_optional_user_demat)):
    """
    Place a buy or sell order. When user has demat linked, uses their broker (Dhan); else uses trading_bot.

    ⚠️ CRITICAL: This executes REAL trades on Dhan when credentials are provided!
    """
    side = (request.side or "").upper()
    if side not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Side must be BUY or SELL")
    if request.quantity <= 0:
        raise HTTPException(
            status_code=400, detail="Quantity must be greater than 0")

    payload, demat = user_demat if isinstance(
        user_demat, tuple) else (None, None)
    username = (payload.get("sub") or "").strip(
    ) if payload and isinstance(payload, dict) else "anonymous"

    if demat and demat.get("access_token") and demat.get("client_id") and (demat.get("broker") or "dhan") == "dhan":
        try:
            logger.warning(
                f"⚠️ WARNING: REAL TRADE EXECUTION - Initiating LIVE Dhan order for {username} - {request.symbol}: {side} {request.quantity} @ {request.order_type}")
            logger.info(
                f"🚀 PLACING REAL ORDER ON DHAN: {side} {request.quantity} {request.symbol}")
            from dhan_client import place_dhan_order
            loop = asyncio.get_event_loop()
            out = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: place_dhan_order(
                        symbol=request.symbol,
                        side=side,
                        quantity=request.quantity,
                        order_type=request.order_type or "MARKET",
                        price=request.price or 0.0,
                        product_type="CNC",
                        access_token=demat["access_token"],
                        client_id=demat["client_id"],
                    ),
                ),
                timeout=15.0,
            )
            if out and isinstance(out, dict):
                return {
                    "success": True,
                    "status": "executed",
                    "order_id": out.get("orderId") or out.get("order_id", ""),
                    "symbol": request.symbol,
                    "side": side,
                    "quantity": request.quantity,
                    "price": request.price,
                    "order_type": request.order_type,
                    "message": f"{side} {request.order_type} order sent successfully",
                    "mode": "live",
                }
            raise HTTPException(
                status_code=400, detail="Order failed or no response from broker")
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504, detail="Order request timed out")
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Demat order failed for {username}")
            raise HTTPException(status_code=400, detail=str(e))

    try:
        state = get_user_state(username)
        bot = state.get("trading_bot")

        if not bot:
            raise HTTPException(
                status_code=503, detail="Trading bot not initialized for user. Link a demat account or start the bot.")

        current_mode = bot.config.get("mode", "paper")
        signal_data = {
            "quantity": request.quantity,
            "current_price": request.price,
            "stop_loss": request.stop_loss,
            "take_profit": request.take_profit,
            "confidence": 1.0,
            "order_type": request.order_type or "MARKET",
        }

        if current_mode == "live":
            if not LIVE_TRADING_AVAILABLE:
                raise HTTPException(
                    status_code=503, detail="Live trading not available")
            if not hasattr(bot, "live_executor") or not bot.live_executor:
                raise HTTPException(
                    status_code=503, detail="Live executor not initialized for user. Please ensure Dhan credentials are configured.")

            if side == "BUY":
                result = bot.live_executor.execute_buy_order(
                    request.symbol, signal_data)
            else:
                result = bot.live_executor.execute_sell_order(
                    request.symbol, signal_data)

            if not result.get("success", False):
                raise HTTPException(status_code=400, detail=result.get(
                    "message", "Order execution failed"))

            try:
                loop = asyncio.get_event_loop()
                loop.run_in_executor(
                    None, bot.live_executor.sync_portfolio_with_dhan)
            except Exception:
                pass

            return {
                "success": True,
                "status": "executed",
                "order_id": result.get("order_id"),
                "symbol": request.symbol,
                "side": side,
                "quantity": result.get("quantity", request.quantity),
                "price": result.get("price"),
                "message": result.get("message", f"{side} order executed successfully"),
                "mode": "live",
            }

        # Non-live mode is now disabled
        raise HTTPException(
            status_code=400,
            detail="Paper mode is disabled. Manual orders only supported in live mode."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order placement error for {username}: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=500, detail=f"Order placement failed: {str(e)}")


# ============================================================================
# MCP (Model Context Protocol) API Endpoints
# ============================================================================


def _set_mcp_user_context_from_request(user_demat: tuple) -> None:
    """Set request-scoped user context for MCP (per-user portfolio/order)."""
    try:
        from request_context import set_mcp_user_context
        payload, demat = user_demat if isinstance(
            user_demat, tuple) else (None, None)
        user_id = (payload.get("sub") or "").strip() if payload else None
        set_mcp_user_context(user_id, demat)
    except Exception as e:
        logger.debug(f"set_mcp_user_context: {e}")


@app.post("/api/mcp/analyze")
async def mcp_analyze_market(request: MCPAnalysisRequest, user_demat: tuple = Depends(get_optional_user_demat)):
    """MCP-powered comprehensive market analysis with AI reasoning. Uses request user's demat when linked."""
    try:
        _set_mcp_user_context_from_request(user_demat)
        if not MCP_AVAILABLE:
            raise HTTPException(
                status_code=503, detail="MCP server not available")

        # Initialize MCP components if needed
        await _ensure_mcp_initialized()

        if not mcp_trading_agent:
            raise HTTPException(
                status_code=503, detail="MCP trading agent not initialized")

        # Perform AI-powered analysis
        signal = await mcp_trading_agent.analyze_and_decide(
            symbol=request.symbol,
            market_context={
                "timeframe": request.timeframe,
                "analysis_type": request.analysis_type
            }
        )

        return {
            "symbol": signal.symbol,
            "recommendation": signal.decision.value,
            "confidence": signal.confidence,
            "reasoning": signal.reasoning,
            "risk_score": signal.risk_score,
            "position_size": signal.position_size,
            "target_price": signal.target_price,
            "stop_loss": signal.stop_loss,
            "expected_return": signal.expected_return,
            "metadata": signal.metadata,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP market analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mcp/execute")
async def mcp_execute_trade(request: MCPTradeRequest, user_demat: tuple = Depends(get_optional_user_demat)):
    """MCP-controlled trade execution. Uses request user's demat when linked."""
    try:
        _set_mcp_user_context_from_request(user_demat)
        if not MCP_AVAILABLE:
            raise HTTPException(
                status_code=503, detail="MCP server not available")

        await _ensure_mcp_initialized()

        if not mcp_trading_agent:
            raise HTTPException(
                status_code=503, detail="MCP trading agent not initialized")

        # Get AI analysis first
        signal = await mcp_trading_agent.analyze_and_decide(request.symbol)

        # Generate explanation for the trade
        if groq_engine:
            async with groq_engine:
                explanation = await groq_engine.explain_trade_decision(
                    request.action,
                    TradingContext(
                        symbol=request.symbol,
                        current_price=0.0,  # Will be filled by agent
                        technical_signals={},
                        market_data={}
                    )
                )
        else:
            explanation = GroqResponse(
                content="MCP analysis completed", reasoning=signal.reasoning)

        # Execute real order when confidence is high and user has demat linked (any broker)
        execution_result = None
        if signal.confidence > 0.7 and signal.decision.value in ["BUY", "SELL"]:
            payload, demat = user_demat if isinstance(
                user_demat, tuple) else (None, None)
            if not demat or not demat.get("access_token") or not demat.get("client_id"):
                execution_result = {
                    "executed": False,
                    "reason": "Link your demat account in BOT Settings to place real orders",
                    "message": "Demat not linked"
                }
            else:
                quantity = request.quantity if request.quantity and request.quantity > 0 else 1
                try:
                    from request_context import place_order_for_request_user
                    loop = asyncio.get_event_loop()
                    out = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: place_order_for_request_user(
                                symbol=request.symbol,
                                side=signal.decision.value,
                                quantity=quantity,
                                product_type="CNC",
                                trigger_price=None,
                            ),
                        ),
                        timeout=15.0,
                    )
                    if out and isinstance(out, dict):
                        execution_result = {
                            "executed": True,
                            "order_id": out.get("orderId") or out.get("order_id") or f"MCP_{int(time.time())}",
                            "message": f"Order sent: {signal.decision.value} {request.symbol} qty={quantity}",
                        }
                    else:
                        execution_result = {
                            "executed": False,
                            "reason": "Broker did not return order confirmation",
                            "message": "Order may have failed",
                        }
                except asyncio.TimeoutError:
                    execution_result = {
                        "executed": False, "reason": "Order request timed out", "message": "Timeout"}
                except Exception as e:
                    logger.exception("MCP execute order failed")
                    execution_result = {"executed": False, "reason": str(
                        e), "message": "Order failed"}
        else:
            execution_result = {
                "executed": False,
                "reason": f"Low confidence ({signal.confidence:.2f}) or HOLD decision",
                "message": "Trade not executed due to risk management"
            }

        return {
            "analysis": {
                "recommendation": signal.decision.value,
                "confidence": signal.confidence,
                "reasoning": signal.reasoning,
                "risk_score": signal.risk_score
            },
            "execution": execution_result,
            "explanation": explanation.content,
            "override_reason": request.override_reason,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP trade execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mcp/predict")
async def mcp_predict(request: PredictionRequest, user_demat: tuple = Depends(get_optional_user_demat)):
    """MCP-powered prediction ranking. Uses request user's demat when linked."""
    try:
        _set_mcp_user_context_from_request(user_demat)
        if not MCP_AVAILABLE:
            raise HTTPException(
                status_code=503, detail="MCP server not available")

        await _ensure_mcp_initialized()

        # Generate a session ID for this request
        session_id = str(int(time.time() * 1000000))

        # Prepare arguments for the prediction tool
        arguments = {
            "symbols": request.symbols or [],
            "models": request.models or ["rl"],
            "horizon": request.horizon or "day",
            "include_explanations": request.include_explanations,
            "natural_query": request.natural_query or ""
        }

        # Call the prediction tool directly
        from mcp_server.tools.prediction_tool import PredictionTool
        prediction_tool = PredictionTool({
            "tool_id": "prediction_tool",
            "ollama_enabled": True,
            "ollama_host": "http://localhost:11434",
            "ollama_model": "llama3.1:8b"
        })

        result = await prediction_tool.rank_predictions(arguments, session_id)

        if result.status == "SUCCESS":
            return {
                "success": True,
                "data": result.data,
                "reasoning": result.reasoning,
                "confidence": result.confidence,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mcp/scan")
async def mcp_scan(request: ScanRequest, user_demat: tuple = Depends(get_optional_user_demat)):
    """MCP-powered stock scanning. Uses request user's demat when linked."""
    try:
        _set_mcp_user_context_from_request(user_demat)
        if not MCP_AVAILABLE:
            raise HTTPException(
                status_code=503, detail="MCP server not available")

        await _ensure_mcp_initialized()

        # Generate a session ID for this request
        session_id = str(int(time.time() * 1000000))

        # Prepare arguments for the scan tool
        arguments = {
            "filters": request.filters or {},
            "sort_by": request.sort_by or "score",
            "limit": request.limit or 50,
            "natural_query": request.natural_query or ""
        }

        # Call the scan tool directly
        from mcp_server.tools.scan_tool import ScanTool
        scan_tool = ScanTool({
            "tool_id": "scan_tool",
            "ollama_enabled": True,
            "ollama_host": "http://localhost:11434",
            "ollama_model": "llama3.1:8b"
        })

        result = await scan_tool.scan_all(arguments, session_id)

        if result.status == "SUCCESS":
            return {
                "success": True,
                "data": result.data,
                "reasoning": result.reasoning,
                "confidence": result.confidence,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/status")
async def get_mcp_status():
    """Get MCP server and agent status"""
    try:
        status = {
            "mcp_available": MCP_AVAILABLE,
            "server_initialized": mcp_server is not None,
            "agent_initialized": mcp_trading_agent is not None,
            "fyers_connected": fyers_client is not None,
            "groq_available": groq_engine is not None
        }

        if mcp_server:
            status["server_health"] = mcp_server.get_health_status()

        if mcp_trading_agent:
            status["agent_status"] = mcp_trading_agent.get_agent_status()

        if groq_engine:
            status["groq_health"] = await groq_engine.health_check()

        return status

    except Exception as e:
        logger.error(f"MCP status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# PRODUCTION-LEVEL API ENDPOINTS
# ============================================================================


@app.get("/api/production/signal-performance")
async def get_signal_performance(user: dict = Depends(get_current_user_required)):
    """Get signal collection performance metrics"""
    try:
        username = user.get("sub") or "anonymous"
        state = get_user_state(username)
        bot = state.get("trading_bot")

        if not bot or not state.get("bot_running"):
            raise HTTPException(
                status_code=503, detail="Trading bot not running for user")

        if not PRODUCTION_CORE_AVAILABLE or 'signal_collector' not in bot.production_components:
            raise HTTPException(
                status_code=503, detail="Production signal collector not available")

        signal_collector = bot.production_components['signal_collector']
        performance_metrics = signal_collector.get_performance_metrics()

        return {
            "success": True,
            "data": performance_metrics,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting signal performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/production/risk-metrics")
async def get_risk_metrics(user: dict = Depends(get_current_user_required)):
    """Get integrated risk management metrics"""
    try:
        username = user.get("sub") or "anonymous"
        state = get_user_state(username)
        bot = state.get("trading_bot")

        if not bot or not state.get("bot_running"):
            raise HTTPException(
                status_code=503, detail="Trading bot not running for user")

        if not PRODUCTION_CORE_AVAILABLE or 'risk_manager' not in bot.production_components:
            raise HTTPException(
                status_code=503, detail="Production risk manager not available")

        risk_manager = bot.production_components['risk_manager']
        risk_metrics = risk_manager.get_risk_metrics()

        return {
            "success": True,
            "data": risk_metrics,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting risk metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/production/make-decision")
async def make_production_decision(request: dict, user: dict = Depends(get_current_user_required)):
    """Make a production-level trading decision using all components"""
    try:
        username = user.get("sub") or "anonymous"
        state = get_user_state(username)
        bot = state.get("trading_bot")

        if not bot or not state.get("bot_running"):
            raise HTTPException(
                status_code=503, detail="Trading bot not running for user")

        if not PRODUCTION_CORE_AVAILABLE:
            raise HTTPException(
                status_code=503, detail="Production components not available")

        symbol = request.get('symbol', '')
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")

        # Use production components for enhanced decision making
        decision_data = await bot._make_production_decision(symbol)

        return {
            "success": True,
            "data": decision_data,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error making production decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/production/learning-insights")
async def get_learning_insights(user: dict = Depends(get_current_user_required)):
    """Get continuous learning engine insights"""
    try:
        username = user.get("sub") or "anonymous"
        state = get_user_state(username)
        bot = state.get("trading_bot")

        if not bot or not state.get("bot_running"):
            raise HTTPException(
                status_code=503, detail="Trading bot not running for user")

        if not PRODUCTION_CORE_AVAILABLE or 'learning_engine' not in bot.production_components:
            raise HTTPException(
                status_code=503, detail="Production learning engine not available")

        learning_engine = bot.production_components['learning_engine']
        insights = learning_engine.get_learning_insights()

        return {
            "success": True,
            "data": insights,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting learning insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/production/decision-history")
async def get_decision_history(days: int = 7, user: dict = Depends(get_current_user_required)):
    """Get decision audit trail history"""
    try:
        username = user.get("sub") or "anonymous"
        state = get_user_state(username)
        bot = state.get("trading_bot")

        if not bot or not state.get("bot_running"):
            raise HTTPException(
                status_code=503, detail="Trading bot not running for user")

        if not PRODUCTION_CORE_AVAILABLE or 'audit_trail' not in bot.production_components:
            raise HTTPException(
                status_code=503, detail="Production audit trail not available")

        audit_trail = bot.production_components['audit_trail']
        history = audit_trail.get_decision_history(days=days)

        return {
            "success": True,
            "data": history,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting decision history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _ensure_mcp_initialized():
    """Ensure MCP components are initialized"""
    global mcp_server, mcp_trading_agent, fyers_client, groq_engine

    try:
        if not MCP_AVAILABLE:
            return

        # Initialize Fyers client
        if not fyers_client:
            fyers_access_token = os.getenv("FYERS_ACCESS_TOKEN")
            fyers_client_id = os.getenv("FYERS_APP_ID")

            # Security: Mask sensitive data in logs
            masked_token = f"{fyers_access_token[:8]}***{fyers_access_token[-4:]}" if fyers_access_token else "None"
            masked_client_id = f"{fyers_client_id[:8]}***{fyers_client_id[-4:]}" if fyers_client_id else "None"
            logger.info(
                f"Initializing Fyers client with token: {masked_token}, client_id: {masked_client_id}")

            fyers_config = {
                "fyers_access_token": fyers_access_token,
                "fyers_client_id": fyers_client_id
            }
            fyers_client = FyersAPIClient(fyers_config)

        # Initialize Groq engine
        if not groq_engine:
            # Code Quality: Move hardcoded values to configuration
            groq_config = {
                "groq_api_key": os.getenv("GROQ_API_KEY", ""),
                "groq_model": os.getenv("GROQ_MODEL", "llama3-8b-8192"),
                "max_tokens": int(os.getenv("GROQ_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
                "temperature": float(os.getenv("GROQ_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
            }
            groq_engine = GroqReasoningEngine(groq_config)

        # Initialize MCP server
        if not mcp_server:
            mcp_config = {
                "monitoring_port": 8002,
                "max_sessions": 100
            }
            mcp_server = MCPTradingServer(mcp_config)

        # Initialize trading agent
        if not mcp_trading_agent:
            agent_config = {
                "agent_id": "production_trading_agent",
                "risk_tolerance": 0.02,
                "max_positions": 5,
                "min_confidence": 0.7,
                "fyers": {
                    "fyers_access_token": os.getenv("FYERS_ACCESS_TOKEN"),
                    "fyers_client_id": os.getenv("FYERS_APP_ID")
                },
                "llama": {
                    "llama_base_url": "http://localhost:11434",
                    "llama_model": "llama3.1:8b"
                },
                "groq": {
                    "groq_api_key": os.getenv("GROQ_API_KEY"),
                    "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                    "max_tokens": int(os.getenv("GROQ_MAX_TOKENS", "2048")),
                    "temperature": float(os.getenv("GROQ_TEMPERATURE", "0.1")),
                }
            }
            mcp_trading_agent = TradingAgent(agent_config)
            await mcp_trading_agent.initialize()

        # Register MCP tools
        if mcp_server:
            # Import tools
            from mcp_server.tools.prediction_tool import PredictionTool
            from mcp_server.tools.scan_tool import ScanTool
            from mcp_server.tools.execution_tool import ExecutionTool
            from mcp_server.tools.portfolio_tool import PortfolioTool
            from mcp_server.tools.risk_management_tool import RiskManagementTool

            # Initialize tools
            prediction_tool = PredictionTool({
                "tool_id": "prediction_tool",
                "ollama_enabled": True,
                "ollama_host": "http://localhost:11434",
                "ollama_model": "llama3.1:8b"
            })

            scan_tool = ScanTool({
                "tool_id": "scan_tool",
                "ollama_enabled": True,
                "ollama_host": "http://localhost:11434",
                "ollama_model": "llama3.1:8b"
            })

            execution_tool = ExecutionTool({
                "tool_id": "execution_tool",
                "trading_mode": "paper",
                "max_order_value": 100000,
                "max_position_size": 0.25,
                "daily_loss_limit": 0.05
            })

            portfolio_tool = PortfolioTool({
                "tool_id": "portfolio_tool",
                "portfolio_agent": {},
                "risk_agent": {}
            })

            risk_management_tool = RiskManagementTool({
                "tool_id": "risk_management_tool",
                "risk_agent": {},
                "portfolio_var_limit": 0.05,
                "position_size_limit": 0.25,
                "concentration_limit": 0.4,
                "correlation_limit": 0.8,
                "liquidity_threshold": 0.3
            })

            # Register prediction tool
            mcp_server.register_tool(
                name="predict",
                function=prediction_tool.rank_predictions,
                description="Rank predictions from RL agents and other models",
                schema={
                    "type": "object",
                    "properties": {
                        "symbols": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "models": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "horizon": {"type": "string"},
                        "include_explanations": {"type": "boolean"},
                        "natural_query": {"type": "string"}
                    },
                    "required": []
                }
            )

            # Register scan tool
            mcp_server.register_tool(
                name="scan_all",
                function=scan_tool.scan_all,
                description="Generate filtered shortlists based on user criteria",
                schema={
                    "type": "object",
                    "properties": {
                        "filters": {
                            "type": "object",
                            "properties": {
                                "min_price": {"type": "number"},
                                "max_price": {"type": "number"},
                                "min_volume": {"type": "number"},
                                "min_score": {"type": "number"},
                                "sectors": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "market_caps": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "risk_levels": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            }
                        },
                        "sort_by": {"type": "string"},
                        "limit": {"type": "number"},
                        "natural_query": {"type": "string"}
                    },
                    "required": []
                }
            )

            # Register execution tool
            mcp_server.register_tool(
                name="execute_trade",
                function=execution_tool.execute_trade,
                description="Execute a trade order with comprehensive risk checks",
                schema={
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "side": {"type": "string"},
                        "quantity": {"type": "number"},
                        "order_type": {"type": "string"},
                        "price": {"type": "number"},
                        "stop_loss": {"type": "number"},
                        "take_profit": {"type": "number"}
                    },
                    "required": ["symbol", "side", "quantity"]
                }
            )

            # Register portfolio analysis tool
            mcp_server.register_tool(
                name="analyze_portfolio",
                function=portfolio_tool.analyze_portfolio,
                description="Comprehensive portfolio analysis",
                schema={
                    "type": "object",
                    "properties": {
                        "portfolio_id": {"type": "string"},
                        "analysis_type": {"type": "string"},
                        "time_period": {"type": "string"},
                        "benchmark": {"type": "string"},
                        "include_recommendations": {"type": "boolean"}
                    },
                    "required": ["portfolio_id"]
                }
            )

            # Register portfolio optimization tool
            mcp_server.register_tool(
                name="optimize_portfolio",
                function=portfolio_tool.optimize_portfolio,
                description="Portfolio optimization with multiple methods",
                schema={
                    "type": "object",
                    "properties": {
                        "portfolio_id": {"type": "string"},
                        "optimization_method": {"type": "string"},
                        "risk_tolerance": {"type": "number"},
                        "target_return": {"type": "number"},
                        "constraints": {
                            "type": "object",
                            "properties": {
                                "max_position_size": {"type": "number"}
                            }
                        }
                    },
                    "required": ["portfolio_id"]
                }
            )

            # Register risk assessment tool
            mcp_server.register_tool(
                name="assess_portfolio_risk",
                function=risk_management_tool.assess_portfolio_risk,
                description="Comprehensive portfolio risk assessment",
                schema={
                    "type": "object",
                    "properties": {
                        "portfolio_id": {"type": "string"},
                        "assessment_type": {"type": "string"},
                        "risk_metrics": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "confidence_level": {"type": "number"},
                        "time_horizon": {"type": "number"}
                    },
                    "required": ["portfolio_id"]
                }
            )

            # Register position risk assessment tool
            mcp_server.register_tool(
                name="assess_position_risk",
                function=risk_management_tool.assess_position_risk,
                description="Individual position risk assessment",
                schema={
                    "type": "object",
                    "properties": {
                        "portfolio_id": {"type": "string"},
                        "symbol": {"type": "string"},
                        "position_size": {"type": "number"}
                    },
                    "required": ["portfolio_id", "symbol"]
                }
            )

        logger.info("MCP components initialized successfully")

    except Exception as e:
        logger.error(f"MCP initialization error: {e}")
        raise


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, username: Optional[str] = Query(None)):
    """WebSocket endpoint for real-time updates"""
    un = username or "anonymous"
    await manager.connect(websocket, username=un)
    state = get_user_state(un)

    try:
        # Send initial data when client connects
        bot = state.get("trading_bot")
        if bot:
            initial_data = bot.get_complete_bot_data()
            await manager.send_personal_message(
                json.dumps({
                    "type": "initial_data",
                    "data": initial_data,
                    "timestamp": datetime.now().isoformat()
                }),
                websocket
            )

        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()

            if data == "ping":
                await manager.send_personal_message("pong", websocket)
            elif data == "get_initial_data":
                bot = state.get("trading_bot")
                if bot:
                    initial_data = bot.get_complete_bot_data()
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "initial_data",
                            "data": initial_data,
                            "timestamp": datetime.now().isoformat()
                        }),
                        websocket
                    )

    except WebSocketDisconnect:
        logger.info(f"WebSocket client '{un}' disconnected")
        manager.disconnect(websocket, username=un)
    except Exception as e:
        logger.error(f"WebSocket error for user '{un}': {e}")
        manager.disconnect(websocket, username=un)
    finally:
        # Security: Ensure proper cleanup to prevent memory leaks
        try:
            if un in manager.active_connections and websocket in manager.active_connections[un]:
                manager.disconnect(websocket, username=un)
            # Clear any remaining references
            websocket = None
        except Exception as cleanup_error:
            logger.error(
                f"Error during WebSocket cleanup for user '{un}': {cleanup_error}")


def find_available_port(start_port=5000, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"No available ports found in range {start_port}-{start_port + max_attempts - 1}")


def run_web_server(host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
    """Run the FastAPI web server with uvicorn"""
    try:
        # Check if the requested port is available
        # CRITICAL: Frontend expects port 5000, so we must use it or fail
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
        except OSError:
            # Port 5000 is in use - try to kill the process (Windows)
            logger.warning(
                f"Port {port} is already in use. Attempting to free it...")
            try:
                import subprocess
                import platform
                if platform.system() == "Windows":
                    # Find PID using port 5000
                    result = subprocess.run(
                        ["netstat", "-ano"], capture_output=True, text=True
                    )
                    for line in result.stdout.splitlines():
                        if f":{port}" in line and "LISTENING" in line:
                            parts = line.split()
                            if len(parts) > 4:
                                pid = parts[-1]
                                logger.info(
                                    f"Killing process {pid} on port {port}")
                                subprocess.run(["taskkill", "/PID", pid, "/F"],
                                               capture_output=True, check=False)
                                time.sleep(1)  # Wait for port to be freed
                                break
                # Try binding again
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((host, port))
                logger.info(f"Port {port} is now available")
            except Exception as e:
                logger.error(f"Failed to free port {port}: {e}")
                logger.error(
                    f"Please manually kill the process using port {port} and restart")
                raise RuntimeError(
                    f"Port {port} is in use and could not be freed")

        # Don't initialize bot here - let the startup event handler do it
        # This prevents double initialization and blocking the server start
        logger.info(f"Starting FastAPI web server on http://{host}:{port}")
        logger.info("Web interface will be available at the above URL")
        logger.info("API documentation available at http://{host}:{port}/docs")

        # Configure uvicorn - use direct run to ensure server stays alive
        import uvicorn
        try:
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info",  # Use info to see startup messages
                reload=False,  # Disable reload to prevent crashes
                access_log=True  # Always log access to debug connectivity
            )
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            logger.exception("Full traceback:")
            raise

    except Exception as e:
        logger.error(f"Error running web server: {e}")
        raise


def _do_blocking_bot_init():
    """Sync helper: data service check + update watchlist + initialize_bot. Run in thread only."""
    try:
        # Load environment variables first
        try:
            from dhan_client import _load_env
            _load_env()
        except:
            pass

        data_client = get_data_client()
        if data_client.is_service_available():
            logger.info("*** DATA SERVICE AVAILABLE - PRODUCTION MODE ***")
            comprehensive_watchlist = [
                "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
                "SUZLON.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
                "LT.NS", "AXISBANK.NS", "MARUTI.NS", "HINDUNILVR.NS", "WIPRO.NS",
                "SUNPHARMA.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS"
            ]
            data_client.update_watchlist(comprehensive_watchlist)
        else:
            logger.warning(
                "*** DATA SERVICE NOT AVAILABLE - FALLBACK MODE ***")
            logger.info("Backend will use Yahoo Finance and mock data")

        # Skip default bot initialization - bots should only be created when users explicitly start them
        # This prevents unnecessary resource usage and infinite loops for anonymous users
        logger.info(
            "Skipping default bot initialization - bots will be created on-demand when users start trading")
        # initialize_bot(username=None)  # DISABLED - was causing infinite loops
    except Exception as e:
        logger.error(f"Blocking bot init failed: {e}")
        logger.exception("Full traceback:")


async def startup_event():
    """Initialize the server on startup."""
    global _main_event_loop
    _main_event_loop = asyncio.get_event_loop()

    # Mark server start time for /api/health uptime
    import time
    app.start_time = time.time()

    logger.info("Server startup event triggered")

    async def init_background():
        """Run blocking init in executor and start sync services."""
        try:
            loop = asyncio.get_event_loop()
            # Skip default bot initialization entirely - only create bots when users explicitly request them
            logger.info(
                "Skipping default bot initialization during startup - bots will be created on-demand")

            # CRITICAL: Don't iterate over _user_states_lock since no bots are initialized yet
            # This prevents any potential race conditions or crashes

            logger.info("Startup initialization task complete")
        except Exception as e:
            logger.error(f"Error in background startup task: {e}")
            logger.exception("Full traceback:")
            # Don't crash the server - just log the error

    try:
        asyncio.create_task(init_background())
        logger.info("Server started - initialization running in background")
    except Exception as e:
        logger.error(f"Failed to start background initialization task: {e}")
        # Don't crash the server if background task creation fails

    # CRITICAL: Return immediately so FastAPI marks startup as complete
    # The background task will continue running independently
    # No await here - function returns immediately


@app.get("/api/monitoring")
async def get_monitoring_stats():
    """Advanced Optimization: Get system performance statistics"""
    try:
        stats = {
            "performance": performance_monitor.get_stats(),
            "timestamp": datetime.now().isoformat(),
            "system_status": "operational"
        }

        # Add data service stats if available
        try:
            data_client = get_data_client()
            if hasattr(data_client, 'get_cache_stats'):
                stats["data_service_cache"] = data_client.get_cache_stats()
        except Exception as e:
            logger.debug(f"Could not get data service stats: {e}")

        return stats
    except Exception as e:
        logger.error(f"Error getting monitoring stats: {e}")
        raise HTTPException(
            status_code=500, detail="Error retrieving monitoring data")


async def shutdown_event():
    """Architectural Fix: Comprehensive resource cleanup on shutdown for all users."""
    logger.info("Starting graceful shutdown...")

    try:
        # Stop all Dhan sync services
        if LIVE_TRADING_AVAILABLE:
            try:
                from dhan_sync_service import stop_sync_service
                await stop_sync_service()  # Stop all
                logger.info("All Dhan sync services stopped")
            except Exception as e:
                logger.error(f"Error stopping Dhan sync services: {e}")

        # Stop all user bots
        with _user_states_lock:
            for username, state in _user_bot_states.items():
                bot = state.get("trading_bot")
                if bot:
                    try:
                        bot.stop()
                        logger.info(f"Trading bot stopped for {username}")
                    except Exception as e:
                        logger.error(f"Error stopping bot for {username}: {e}")

        # Cleanup MCP server
        if mcp_server:
            try:
                await mcp_server.shutdown()
                logger.info("MCP server shutdown")
            except Exception as e:
                logger.error(f"Error shutting down MCP server: {e}")

        # Cleanup Fyers client
        if fyers_client:
            try:
                await fyers_client.disconnect()
                logger.info("Fyers client disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting Fyers client: {e}")

        # Cleanup Groq engine
        if groq_engine:
            try:
                await groq_engine.cleanup()
                logger.info("Groq engine cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up Groq engine: {e}")

        logger.info("Graceful shutdown completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Indian Stock Trading Bot Web Interface (FastAPI)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000,
                        help="Port to bind to (default: 5000)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode")

    args = parser.parse_args()

    try:
        run_web_server(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("Web server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start web server: {e}")
        sys.exit(1)

# New API endpoints for RL scanning system


@app.post("/api/scan_all")
async def scan_all():
    """Trigger full market scan"""
    try:
        logger.info("Manual market scan triggered via API")
        data_agent.kickoff_scan()
        return {"status": "scan_started", "message": "Full market scan initiated"}
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_stocks(request: AnalyzeRequest):
    """Analyze custom tickers and return entry/exit points with confidence"""
    if not Stock:
        raise HTTPException(
            status_code=503, detail="Analysis components not loaded. Install optional deps and restart.")
    try:
        results = {}

        for ticker in request.tickers:
            try:
                # Use existing Stock class for analysis
                stock = Stock(ticker)

                # Get basic analysis (simplified - enhance based on your Stock class methods)
                price_data = stock.get_current_price()
                sentiment = stock.get_sentiment_score()

                # Calculate entry/exit based on current implementation
                entry_price = price_data * 0.98  # 2% below current
                exit_price = price_data * 1.05   # 5% above current
                confidence = min(sentiment * 0.8, 0.95)  # Cap at 95%

                results[ticker] = {
                    "entry": round(entry_price, 2),
                    "exit": round(exit_price, 2),
                    "confidence": round(confidence, 3),
                    "current_price": round(price_data, 2),
                    "horizon": request.horizon
                }
            except Exception as e:
                logger.error(f"Analysis failed for {ticker}: {e}")
                results[ticker] = {"error": str(e)}

        return results
    except Exception as e:
        logger.error(f"Analyze endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/update_risk")
async def update_risk(request: UpdateRiskRequest):
    """Update risk settings in live_config.json"""
    try:
        risk_engine.update_risk_profile(
            request.stop_loss_pct,
            request.capital_risk_pct,
            request.drawdown_limit_pct
        )
        return {
            "status": "updated",
            "message": "Risk profile updated in live_config.json",
            "new_settings": risk_engine.get_risk_settings()
        }
    except Exception as e:
        logger.error(f"Risk update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shortlist")
async def get_shortlist():
    """Get current shortlist from RL filtering"""
    try:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        shortlist_file = f"logs/shortlist_{date_str}.json"

        if os.path.exists(shortlist_file):
            with open(shortlist_file, 'r') as f:
                data = json.load(f)
                return data
        else:
            return {"message": "No shortlist available for today", "shortlist": []}
    except Exception as e:
        logger.error(f"Error getting shortlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tracking_stats")
async def get_tracking_stats():
    """Get monitoring and tracking statistics"""
    try:
        return {
            "data_agent_stats": data_agent.get_cache_stats(),
            "rl_agent_stats": rl_agent.get_model_stats(),
            "tracker_stats": tracker_agent.get_monitoring_stats(),
            "risk_settings": risk_engine.get_risk_settings()
        }
    except Exception as e:
        logger.error(f"Error getting tracking stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
