"""
MCP-Style API Server for Stock Prediction - FastAPI Version
Exposes REST endpoints for ML predictions with dynamic risk parameters
OPEN ACCESS - No authentication required, with rate limiting and input validation
"""

import sys
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hft2", "data", "trading.db")



# Force unbuffered output so prints appear immediately in Render logs
# Use env var approach only — replacing sys.stdout/stderr with os.fdopen crashes on Render's piped subprocess
os.environ['PYTHONUNBUFFERED'] = '1'

from hft2.backend.db.knowledge_ingestor import KnowledgeIngestor
from hft2.backend.db.samruddhi_memory import FinancialMemoryManager
from pydantic import BaseModel
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
from datetime import datetime
import json
import psutil
import threading
import uuid
import time
import asyncio
import requests

import json

def log_to_db(endpoint: str, request_data: dict, response: dict):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO api_logs (
                endpoint,
                request_data,
                response_data,
                success,
                error,
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            endpoint,
            json.dumps(request_data),
            json.dumps(response),
            int(response.get("success", False)),
            response.get("error"),
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        # ❗ DO NOT break main API flow
        logger.error(f"API LOGGING FAILED: {e}", exc_info=True)

# === Knowledge System Init ===
try:
    memory_manager = FinancialMemoryManager()
    knowledge_ingestor = KnowledgeIngestor(memory_manager)

    print("✅ Knowledge system initialized")
except Exception as e:
    print("❌ Knowledge system init failed:", e)
    knowledge_ingestor = None
    memory_manager = None

from core.mcp_adapter import MCPAdapter
# JWT authentication removed - open access API
from rate_limiter import check_rate_limit, get_rate_limit_status
from validators import (
    validate_symbols, validate_horizon, validate_horizons_list,
    validate_risk_parameters, sanitize_input, validate_confidence
)
import config
from config import LOGS_DIR
from live_price_validator import LivePriceValidator

# Logging setup with automatic rotation
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            str(LOGS_DIR / 'api_server.log'),  # Cross-platform path handling
            maxBytes=10*1024*1024,  # 10 MB per file (prevents huge log files)
            backupCount=5,           # Keep 5 backup files (max 60 MB total)
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description=config.API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)
# =========================
# PORTFOLIO STORAGE (PHASE 5)
# =========================
portfolio_data = {
    "holdings": [],
    "total_value": 0,
    "total_gain": 0,
    "total_gain_percent": 0
}

@app.get("/portfolio")
def get_portfolio():
    return portfolio_data

from pydantic import BaseModel
from typing import List

class PortfolioUpdate(BaseModel):
    holdings: list
    total_value: float
    total_gain: float
    total_gain_percent: float


@app.post("/portfolio/update")
def update_portfolio(data: dict):
    request_id = f"portfolio_{int(time.time())}_{str(uuid.uuid4())[:6]}"

    try:
        portfolio_id = data.get("portfolio_id", "seed")
        holdings = data.get("holdings", [])

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # wipe old
        cursor.execute("DELETE FROM portfolio WHERE portfolio_id = ?", (portfolio_id,))

        # insert new
        for h in holdings:
           cursor.execute("""
INSERT INTO portfolio (
    portfolio_id,
    symbol,
    shares,
    avg_price,
    current_price,
    request_id
) VALUES (?, ?, ?, ?, ?, ?)
""", (
    portfolio_id,
    h["symbol"],
    h["shares"],
    h["avgPrice"],
    h.get("currentPrice", h.get("avgPrice")),
    request_id
))

        conn.commit()
        conn.close()

        print(f"✅ SAVED {len(holdings)} holdings")

        response = {
            "success": True,
            "data": {
                "portfolio_id": portfolio_id,
                "count": len(holdings)
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        # 🔥 STRICT: logging must succeed
        try:
            log_to_db('/portfolio/update', data, response)
        except Exception as log_err:
            raise HTTPException(
                status_code=500,
                detail=f"Logging failed: {str(log_err)}"
            )

        return response

    except Exception as e:
        print("❌ SAVE ERROR:", e)

        response = {
            "success": False,
            "data": {},
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        # 🔥 Try logging error (but don’t crash again)
        try:
            log_to_db('/portfolio/update', data, response)
        except:
            pass

        return response

@app.get("/portfolio/{portfolio_id}")
def get_portfolio(portfolio_id: str):
    request_id = f"portfolio_get_{int(time.time())}_{str(uuid.uuid4())[:6]}"

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT symbol, shares, avg_price, current_price
            FROM portfolio
            WHERE portfolio_id = ?
        """, (portfolio_id,))

        rows = cursor.fetchall()

        holdings = []
        total_value = 0

        for row in rows:
            value = row[1] * row[3]
            total_value += value

            holdings.append({
                "symbol": row[0],
                "shares": row[1],
                "avgPrice": row[2],
                "currentPrice": row[3],
                "value": value
            })

        conn.close()

        # ✅ CONTRACT RESPONSE
        response = {
            "success": True,
            "data": {
                "portfolio_id": portfolio_id,
                "holdings": holdings,
                "total_value": total_value,
                "count": len(holdings)
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        # 🔥 PHASE 3 LOGGING
        log_to_db('/portfolio/get', {"portfolio_id": portfolio_id}, response)

        return response

    except Exception as e:
        print("❌ ERROR:", e)

        response = {
            "success": False,
            "data": {},
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        # 🔥 LOG FAILURE
        try:
            log_to_db('/portfolio/get', {"portfolio_id": portfolio_id}, response)
        except:
            pass

        return response

# CORS middleware
# Build CORS origins list
if config.CORS_ALLOW_ALL:
    # Allow all origins (useful for debugging)
    cors_origins = ["*"]
    allow_credentials = False  # Cannot use credentials with wildcard
    logger.warning("CORS: Allowing all origins (CORS_ALLOW_ALL=true)")
else:
    cors_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://trade-bot-frontend-halb.onrender.com",
        "https://trade-bot-dashboard-llb8.onrender.com",
        "https://trade-bot-dashboard-c9x3.onrender.com",
        "https://trade-bot-api.onrender.com",
        *config.CORS_ORIGINS_EXTRA,
    ]
    # Remove duplicates while preserving order
    cors_origins = list(dict.fromkeys(cors_origins))
    allow_credentials = True
    logger.info(f"CORS: Allowing origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight for 1 hour
)



# Initialize MCP Adapter
try:
    mcp_adapter = MCPAdapter()
    logger.info("MCP Adapter initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize MCP Adapter: {e}", exc_info=True)
    raise

# Initialize Live Price Validator
price_validator = LivePriceValidator()

# HFT: use cloned hft2 backend for real demat when HFT2_BACKEND_URL is set; else use in-repo stubs
HFT2_BACKEND_URL = os.environ.get("HFT2_BACKEND_URL", "http://127.0.0.1:5000").rstrip("/")  # e.g. http://127.0.0.1:5002
app.state.mcp_adapter = mcp_adapter

if HFT2_BACKEND_URL:
    # Real trades: proxy /api/* (except predictions & status) to hft2. Predictions stay here (vetting).
    from fastapi import Response


    @app.get("/api/predictions")
    async def hft_predictions(request: Request, symbols: str = "RELIANCE.NS", horizon: str = "intraday"):
        adapter = getattr(request.app.state, "mcp_adapter", None)
        if not adapter:
            return {"predictions": [], "message": "Vetting agent not available"}
        try:
            symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()] or ["RELIANCE.NS"]
            return adapter.predict(symbols=symbol_list, horizon=horizon)
        except Exception as e:
            logger.exception("HFT predictions from vetting agent failed")
            raise HTTPException(status_code=500, detail=str(e))
        
    @app.get("/api/health")
    def health_check():
        return {"status": "ok"}

    @app.get("/api/status")
    async def hft_status():
        return {"status": "healthy", "isRunning": False, "timestamp": datetime.now().isoformat()}

    async def _proxy_to_hft2(request: Request, path: str) -> Response:
        url = f"{HFT2_BACKEND_URL}/api/{path}"
        if request.url.query:
            url += "?" + request.url.query
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
        body = await request.body()
        try:
            resp = await asyncio.to_thread(
                requests.request,
                request.method,
                url,
                headers=headers,
                data=body if body else None,
                timeout=30,
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers={k: v for k, v in resp.headers.items() if k.lower() not in ("content-encoding", "transfer-encoding")},
            )
        except requests.Timeout:
            logger.error(f"HFT2 proxy timeout for /api/{path}")
            raise HTTPException(status_code=504, detail="HFT2 backend timeout")
        except requests.ConnectionError:
            logger.error(f"HFT2 connection error for /api/{path}")
            raise HTTPException(status_code=503, detail="HFT2 service unavailable")
        except requests.RequestException as e:
            logger.warning("HFT2 proxy error: %s", e)
            raise HTTPException(status_code=502, detail=f"HFT2 backend unreachable: {e}")

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def hft2_proxy(request: Request, path: str):
        if path in ("predictions", "status") or path.startswith("predictions") or path.startswith("status"):
            raise HTTPException(status_code=404, detail="Use direct /api/predictions or /api/status")
        return await _proxy_to_hft2(request, path)

    logger.info("HFT Bot: proxying to hft2 at %s (predictions from vetting)", HFT2_BACKEND_URL)
else:
    from hft.routes import hft_router
    app.include_router(hft_router, prefix="/api", tags=["HFT Bot"])
    logger.info("HFT Bot routes registered at /api/* (in-repo stubs)")

# API request logging — use LOGS_DIR from config (resolves to /tmp/logs on Render)
API_LOG_PATH = LOGS_DIR / 'api_requests.jsonl'
SECURITY_LOG_PATH = LOGS_DIR / 'security.jsonl'

# Async predict: in-memory job store (job_id -> { status, result?, error?, created_at })
_predict_jobs: Dict[str, Dict[str, Any]] = {}
_predict_jobs_lock = threading.Lock()
JOB_EXPIRE_SECONDS = 3600  # 1 hour




def _run_predict_job(job_id: str, data: dict) -> None:
    try:
        with _predict_jobs_lock:
            _predict_jobs[job_id]["status"] = "running"
        logger.info(f"Async predict job {job_id} started (symbols=%s, horizon=%s)", data.get("symbols"), data.get("horizon"))
        
        # Validate MCP adapter availability before running
        if 'mcp_adapter' not in globals() or mcp_adapter is None:
            raise RuntimeError("MCP Adapter not initialized. Please restart the server.")
        
        result = mcp_adapter.predict(
            symbols=data["symbols"],
            horizon=data["horizon"],
            risk_profile=data.get("risk_profile"),
            stop_loss_pct=data.get("stop_loss_pct"),
            capital_risk_pct=data.get("capital_risk_pct"),
            drawdown_limit_pct=data.get("drawdown_limit_pct"),
        )
        with _predict_jobs_lock:
            _predict_jobs[job_id]["status"] = "completed"
            _predict_jobs[job_id]["result"] = result
        logger.info(f"Async predict job {job_id} completed successfully")
    except Exception as e:
        logger.exception(f"Async predict job {job_id} failed")
        with _predict_jobs_lock:
            _predict_jobs[job_id]["status"] = "failed"
            _predict_jobs[job_id]["error"] = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Async predict job {job_id} marked failed: {e}")


def _prune_old_jobs() -> None:
    now = time.time()
    with _predict_jobs_lock:
        expired = [jid for jid, j in _predict_jobs.items() if (now - j.get("created_at", 0)) > JOB_EXPIRE_SECONDS]
        for jid in expired:
            del _predict_jobs[jid]


# ==================== Pydantic Models ====================
# JWT authentication removed - no login models needed

class PredictRequest(BaseModel):
    symbols: List[str] = Field(default=["AAPL"], min_length=1, max_length=50, examples=[["AAPL", "GOOGL", "TCS.NS"]])
    horizon: str = Field(default="intraday", examples=["intraday", "short", "long"])
    risk_profile: Optional[str] = Field(default="moderate", examples=["low", "moderate", "high"])
    stop_loss_pct: Optional[float] = Field(default=2.0, ge=0.1, le=50.0)
    capital_risk_pct: Optional[float] = Field(default=1.0, ge=0.1, le=100.0)
    drawdown_limit_pct: Optional[float] = Field(default=5.0, ge=0.1, le=100.0)
    news_data: Optional[List[Dict[str, Any]]] = []
    
    @field_validator('symbols', mode='after')
    @classmethod
    def validate_symbols_not_empty(cls, v):
        """Ensure symbols list is not empty and normalize to uppercase"""
        if not v or len(v) == 0:
            raise ValueError('At least one symbol must be provided')
        return [s.upper().strip() for s in v]
    
    @field_validator('horizon', mode='after')
    @classmethod
    def validate_horizon_value(cls, v):
        """Validate horizon is one of the allowed values"""
        valid_horizons = ['intraday', 'short', 'long']
        if v.lower() not in valid_horizons:
            raise ValueError(f'Invalid horizon. Valid options: {", ".join(valid_horizons)}')
        return v.lower()
    
    @field_validator('risk_profile', mode='after')
    @classmethod
    def validate_risk_profile_value(cls, v):
        """Validate risk profile if provided"""
        if v is not None:
            valid_profiles = ['low', 'moderate', 'high']
            if v.lower() not in valid_profiles:
                raise ValueError(f'Invalid risk_profile. Valid options: {", ".join(valid_profiles)}')
            return v.lower()
        return v


class ScanAllRequest(BaseModel):
    symbols: List[str] = Field(default=["AAPL", "GOOGL", "MSFT"], min_length=1, max_length=100, examples=[["AAPL", "GOOGL", "MSFT", "TCS.NS"]])
    horizon: str = Field(default="intraday", examples=["intraday", "short", "long"])
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    stop_loss_pct: Optional[float] = Field(default=2.0, ge=0.1, le=50.0)
    capital_risk_pct: Optional[float] = Field(default=1.0, ge=0.1, le=100.0)
    
    @field_validator('symbols', mode='after')
    @classmethod
    def validate_symbols_list(cls, v):
        """Ensure symbols list is not empty and normalize"""
        if not v or len(v) == 0:
            raise ValueError('At least one symbol must be provided')
        return [s.upper().strip() for s in v]
    
    @field_validator('horizon', mode='after')
    @classmethod
    def validate_horizon_value(cls, v):
        """Validate horizon is one of the allowed values"""
        valid_horizons = ['intraday', 'short', 'long']
        if v.lower() not in valid_horizons:
            raise ValueError(f'Invalid horizon. Valid options: {", ".join(valid_horizons)}')
        return v.lower()


class AnalyzeRequest(BaseModel):
    symbol: str = Field(default="AAPL", min_length=1, max_length=20, examples=["AAPL", "TCS.NS", "RELIANCE.NS"])
    horizons: List[str] = Field(default=["intraday"], min_length=1, max_length=3, examples=[["intraday"], ["intraday", "short", "long"]])
    stop_loss_pct: float = Field(default=2.0, ge=0.1, le=50.0)
    capital_risk_pct: float = Field(default=1.0, ge=0.1, le=100.0)
    drawdown_limit_pct: float = Field(default=5.0, ge=0.1, le=100.0)
    
    @field_validator('symbol', mode='after')
    @classmethod
    def validate_symbol_format(cls, v):
        """Normalize symbol to uppercase and validate not empty"""
        if not v.strip():
            raise ValueError('Symbol cannot be empty')
        return v.upper().strip()
    
    @field_validator('horizons', mode='after')
    @classmethod
    def validate_horizons_list(cls, v):
        """Validate each horizon and normalize"""
        if not v or len(v) == 0:
            raise ValueError('At least one horizon must be provided')
        valid_horizons = ['intraday', 'short', 'long']
        for h in v:
            if h.lower() not in valid_horizons:
                raise ValueError(f'Invalid horizon: {h}. Valid options: {", ".join(valid_horizons)}')
        return [h.lower() for h in v]


class FeedbackRequest(BaseModel):
    symbol: str = Field(default="AAPL", min_length=1, max_length=20, examples=["AAPL", "TCS.NS"])
    predicted_action: str = Field(default="LONG", examples=["LONG", "SHORT", "HOLD"])
    user_feedback: str = Field(default="correct", examples=["correct", "incorrect"])
    actual_return: Optional[float] = Field(default=2.5, ge=-100.0, le=1000.0, examples=[2.5, -1.2, 5.0])
    
    @field_validator('symbol', mode='after')
    @classmethod
    def validate_symbol_format(cls, v):
        """Normalize symbol to uppercase"""
        return v.upper().strip()
    
    @field_validator('predicted_action', mode='after')
    @classmethod
    def validate_and_uppercase_action(cls, v):
        """Validate and normalize predicted action"""
        valid_actions = ['LONG', 'SHORT', 'HOLD']
        if v.upper() not in valid_actions:
            raise ValueError(f'Invalid predicted_action. Valid options: {", ".join(valid_actions)}')
        return v.upper()
    
    @field_validator('user_feedback', mode='after')
    @classmethod
    def validate_and_lowercase_feedback(cls, v):
        """Validate and normalize user feedback"""
        valid_feedback = ['correct', 'incorrect']
        if v.lower() not in valid_feedback:
            raise ValueError(f'Invalid user_feedback. Valid options: {", ".join(valid_feedback)}')
        return v.lower()
    
    @field_validator('actual_return', mode='after')
    @classmethod
    def validate_return_range(cls, v):
        """Validate actual return is within reasonable range"""
        if v is not None:
            # Check for NaN or Inf
            if v != v:  # NaN check
                raise ValueError('actual_return cannot be NaN')
            if abs(v) == float('inf'):
                raise ValueError('actual_return cannot be infinite')
        return v


class TrainRLRequest(BaseModel):
    symbol: str = Field(default="AAPL", min_length=1, max_length=20, examples=["AAPL", "TCS.NS", "GOOGL"])
    horizon: str = Field(default="intraday", examples=["intraday", "short", "long"])
    n_episodes: int = Field(default=10, ge=10, le=100)
    force_retrain: bool = False
    
    @field_validator('symbol', mode='after')
    @classmethod
    def validate_symbol_format(cls, v):
        """Normalize symbol to uppercase"""
        return v.upper().strip()
    
    @field_validator('horizon', mode='after')
    @classmethod
    def validate_horizon_value(cls, v):
        """Validate horizon is one of the allowed values"""
        valid_horizons = ['intraday', 'short', 'long']
        if v.lower() not in valid_horizons:
            raise ValueError(f'Invalid horizon. Valid options: {", ".join(valid_horizons)}')
        return v.lower()


class FetchDataRequest(BaseModel):
    symbols: List[str] = Field(default=["AAPL"], min_length=1, max_length=100, examples=[["AAPL", "GOOGL", "TCS.NS"]])
    period: str = Field(default="2y", examples=["1mo", "6mo", "1y", "2y"])
    include_features: bool = False
    refresh: bool = False
    
    @field_validator('symbols', mode='after')
    @classmethod
    def validate_symbols_list(cls, v):
        """Ensure symbols list is not empty and normalize"""
        if not v or len(v) == 0:
            raise ValueError('At least one symbol must be provided')
        return [s.upper().strip() for s in v]
    
    @field_validator('period', mode='after')
    @classmethod
    def validate_period_value(cls, v):
        """Validate period is one of the allowed values"""
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
        if v not in valid_periods:
            raise ValueError(f'Invalid period. Valid options: {", ".join(valid_periods)}')
        return v


# ==================== Utility Functions ====================

def log_api_request(endpoint: str, request_data: Dict, response_data: Dict, status_code: int):
    """Log API request and response with detailed information"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'endpoint': endpoint,
        'method': 'POST',
        'request': request_data,
        'response_summary': {
            'status_code': status_code,
            'has_predictions': 'predictions' in response_data,
            'prediction_count': response_data.get('metadata', {}).get('count', 0) if 'metadata' in response_data else 0
        },
        'status_code': status_code
    }
    
    API_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(API_LOG_PATH, 'a') as f:
        f.write(json.dumps(log_entry, default=str) + '\n')


def log_security_event(request: Request, event_type: str, details: Dict):
    """Log security-related events"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'client_ip': request.client.host if request.client else 'unknown',
        'endpoint': request.url.path,
        'details': details
    }
    
    SECURITY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(SECURITY_LOG_PATH, 'a') as f:
        f.write(json.dumps(log_entry, default=str) + '\n')


# ==================== Exception Handlers ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            'error': str(exc),
            'type': type(exc).__name__
        }
    )


# ==================== API Routes ====================

@app.get("/")
async def index():
    """API information"""
    return {
        'name': 'Stock Prediction MCP API',
        'version': '4.0',
        'description': 'MCP-style REST API with open access, rate limiting, and validation',
        'authentication': 'DISABLED - Open access to all endpoints',
        'auth_status': 'disabled',
        'endpoints': {
            '/': 'GET - API information',
            '/auth/status': 'GET - Check rate limit status',
            '/tools/health': 'GET - System health',
            '/tools/predict': 'POST - Generate predictions (NO AUTH)',
            '/tools/predict/async': 'POST - Start prediction, returns job_id; poll /tools/predict/result/{job_id}',
            '/tools/predict/result/{job_id}': 'GET - Get async prediction result (202=running, 200=done)',
            '/tools/scan_all': 'POST - Scan and rank symbols (NO AUTH)',
            '/tools/analyze': 'POST - Analyze with risk parameters (NO AUTH)',
            '/tools/feedback': 'POST - Provide feedback (NO AUTH)',
            '/tools/train_rl': 'POST - Train RL agent (NO AUTH)',
            '/tools/fetch_data': 'POST - Fetch batch data (NO AUTH)',
            '/live/price/{symbol}': 'GET - Get live current price (NO AUTH)',
            '/data/transparency/{symbol}': 'GET - Data source transparency (NO AUTH)'
        },
        'rate_limits': {
            'per_minute': config.RATE_LIMIT_PER_MINUTE,
            'per_hour': config.RATE_LIMIT_PER_HOUR
        },
        'documentation': {
            'swagger_ui': '/docs',
            'redoc': '/redoc'
        }
    }


@app.get("/auth/status")
async def auth_status(request: Request):
    """Get rate limit status for current IP"""
    try:
        status = get_rate_limit_status(request=request)
        return status
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/health")
async def health_check():
    """System health and resource usage"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('.')
        
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_usage_percent': cpu_percent,
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'memory_percent': memory.percent,
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'disk_used_gb': round(disk.used / (1024**3), 2),
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'disk_percent': disk.percent
            },
            'models': {
                'available': True,
                'total_trained': len(list(Path('models').glob('*.pkl')))
            }
        }
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail={'status': 'error', 'message': str(e)})


@app.post("/tools/predict")
async def predict(
    request: Request,
    predict_data: PredictRequest,
    client_ip: str = Depends(check_rate_limit)
):
    """Generate predictions for symbols (CONTRACT ENFORCED)"""

    try:
        # -----------------------------
        # 1. INPUT + VALIDATION
        # -----------------------------
        data = predict_data.dict()
        data = sanitize_input(data)

        validation = validate_symbols(data['symbols'])
        if not validation['valid']:
            raise HTTPException(status_code=400, detail=validation['error'])

        if not validate_horizon(data['horizon']):
            raise HTTPException(
                status_code=400,
                detail='Invalid horizon. Valid options: intraday, short, long'
            )

        risk_validation = validate_risk_parameters(
            data.get('stop_loss_pct'),
            data.get('capital_risk_pct'),
            data.get('drawdown_limit_pct')
        )
        if not risk_validation['valid']:
            raise HTTPException(status_code=400, detail=risk_validation['error'])

        # -----------------------------
        # 2. MODEL CALL
        # -----------------------------
        result = mcp_adapter.predict(
            symbols=data['symbols'],
            horizon=data['horizon'],
            risk_profile=data.get('risk_profile'),
            stop_loss_pct=data.get('stop_loss_pct'),
            capital_risk_pct=data.get('capital_risk_pct'),
            drawdown_limit_pct=data.get('drawdown_limit_pct'),
            news_data=data.get('news_data', [])
        )

        # -----------------------------
        # 3. SAFE EXTRACTION
        # -----------------------------
        predictions = result.get("predictions", []) if isinstance(result, dict) else []

        has_errors = any(
            isinstance(p, dict) and p.get("status") == "error"
            for p in predictions
        )

        # -----------------------------
        # 4. CONTRACT RESPONSE
        # -----------------------------
        request_id = f"predict_{int(time.time())}_{str(uuid.uuid4())[:6]}"

        response = {
            "success": not has_errors,
            "data": {
                "predictions": predictions
            },
            "error": "Prediction failed for one or more symbols" if has_errors else None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        # -----------------------------
        # 5. DB WRITE (STRICT MODE)
        # -----------------------------
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            for p in response["data"]["predictions"]:
                cursor.execute("""
                INSERT INTO predictions (
                    symbol, status, current_price,
                    predicted_price, predicted_return,
                    action, confidence, timestamp, request_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p.get("symbol"),
                    p.get("status"),
                    p.get("current_price"),
                    p.get("predicted_price"),
                    p.get("predicted_return"),
                    p.get("action"),
                    p.get("confidence"),
                    datetime.utcnow().isoformat(),
                    request_id
                ))

            conn.commit()
            conn.close()

        except Exception as db_error:
            logger.error(f"Prediction DB insert failed: {db_error}", exc_info=True)

            error_response = {
                "success": False,
                "data": {},
                "error": "Database write failed. Predictions not saved.",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id
            }

            log_api_request('/tools/predict', data, error_response, 500)
            log_to_db('/tools/predict', data, error_response)

            return JSONResponse(status_code=500, content=error_response)

        # -----------------------------
        # 6. SUCCESS RESPONSE
        # -----------------------------
        log_api_request('/tools/predict', data, response, 200)
        log_to_db('/tools/predict', data, response)

        return JSONResponse(status_code=200, content=response)

    # -----------------------------
    # 7. HANDLED HTTP ERRORS
    # -----------------------------
    except HTTPException as http_err:
        request_id = f"predict_{int(time.time())}_{str(uuid.uuid4())[:6]}"

        error_response = {
            "success": False,
            "data": {},
            "error": http_err.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        log_api_request('/tools/predict', data, error_response, http_err.status_code)

        return JSONResponse(status_code=http_err.status_code, content=error_response)

    # -----------------------------
    # 8. UNEXPECTED ERRORS
    # -----------------------------
    except Exception as e:
        logger.error(f"Predict error: {e}", exc_info=True)

        request_id = f"predict_{int(time.time())}_{str(uuid.uuid4())[:6]}"

        error_response = {
            "success": False,
            "data": {},
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        log_api_request('/tools/predict', data, error_response, 500)

        return JSONResponse(status_code=500, content=error_response)
    

@app.post("/tools/predict/async")
async def predict_async(
    request: Request,
    predict_data: PredictRequest,
    client_ip: str = Depends(check_rate_limit)
):
    """Start prediction in background; returns job_id immediat*ely. Poll GET /tools/predict/result/{job_id} for result."""
    try:
        data = predict_data.dict()
        data = sanitize_input(data)
        validation = validate_symbols(data['symbols'])
        if not validation['valid']:
            raise HTTPException(status_code=400, detail=validation['error'])
        if not validate_horizon(data['horizon']):
            raise HTTPException(status_code=400, detail='Invalid horizon. Valid options: intraday, short, long')
        risk_validation = validate_risk_parameters(
            data.get('stop_loss_pct'), data.get('capital_risk_pct'), data.get('drawdown_limit_pct')
        )
        if not risk_validation['valid']:
            raise HTTPException(status_code=400, detail=risk_validation['error'])

        _prune_old_jobs()
        job_id = str(uuid.uuid4())
        with _predict_jobs_lock:
            _predict_jobs[job_id] = {
                "status": "pending",
                "result": None,
                "error": None,
                "created_at": time.time(),
            }
        thread = threading.Thread(target=_run_predict_job, args=(job_id, data), daemon=True)
        thread.start()
        return {
            "job_id": job_id,
            "status": "accepted",
            "message": f"Poll GET /tools/predict/result/{job_id} for result (may take 2–10 minutes).",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Predict async error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/predict/result/{job_id}")
async def predict_result(job_id: str):
    """Get status and result of an async prediction job. Returns 202 while running, 200 with result when done."""
    _prune_old_jobs()
    with _predict_jobs_lock:
        job = _predict_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    status = job["status"]
    if status == "pending" or status == "running":
        return JSONResponse(status_code=202, content={"job_id": job_id, "status": status})
    if status == "completed":
        return job["result"]
    if status == "failed":
        return JSONResponse(
            status_code=200,
            content={"status": "failed", "job_id": job_id, "error": job.get("error", "Unknown error")},
        )
    return JSONResponse(status_code=202, content={"job_id": job_id, "status": status})


@app.post("/tools/scan_all")
async def scan_all(
    request: Request,
    scan_data: ScanAllRequest,
    client_ip: str = Depends(check_rate_limit)
):
    """Scan and rank multiple symbols (NO AUTH REQUIRED)"""
    try:
        data = scan_data.dict()
        data = sanitize_input(data)
        
        validation = validate_symbols(data['symbols'], config.MAX_SCAN_SYMBOLS)
        if not validation['valid']:
            raise HTTPException(status_code=400, detail=validation['error'])
        
        if not validate_horizon(data['horizon']):
            raise HTTPException(status_code=400, detail='Invalid horizon. Valid options: intraday, short, long')
        
        if not validate_confidence(data['min_confidence']):
            raise HTTPException(status_code=400, detail='min_confidence must be between 0.0 and 1.0')
        
        result = mcp_adapter.scan_all(
            symbols=data['symbols'],
            horizon=data['horizon'],
            min_confidence=data['min_confidence'],
            stop_loss_pct=data.get('stop_loss_pct'),
            capital_risk_pct=data.get('capital_risk_pct')
        )
        
        log_api_request('/tools/scan_all', data, result, 200)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scan error: {e}", exc_info=True)
        error_response = {'error': str(e)}
        log_api_request('/tools/scan_all', scan_data.dict(), error_response, 500)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/analyze")
async def analyze(
    request: Request,
    analyze_data: AnalyzeRequest,
    client_ip: str = Depends(check_rate_limit)
):
    """Analyze custom tickers with risk parameters (NO AUTH REQUIRED)"""
    try:
        data = analyze_data.dict()
        data = sanitize_input(data)
        
        validation = validate_symbols([data['symbol']])
        if not validation['valid']:
            raise HTTPException(status_code=400, detail=validation['error'])
        
        horizons_validation = validate_horizons_list(data['horizons'])
        if not horizons_validation['valid']:
            raise HTTPException(status_code=400, detail=horizons_validation['error'])
        
        risk_validation = validate_risk_parameters(
            data['stop_loss_pct'], 
            data['capital_risk_pct'], 
            data['drawdown_limit_pct']
        )
        if not risk_validation['valid']:
            raise HTTPException(status_code=400, detail=risk_validation['error'])
        
        result = mcp_adapter.analyze(
            symbol=data['symbol'],
            horizons=data['horizons'],
            stop_loss_pct=data['stop_loss_pct'],
            capital_risk_pct=data['capital_risk_pct'],
            drawdown_limit_pct=data['drawdown_limit_pct']
        )
        
        log_api_request('/tools/analyze', data, result, 200)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        error_response = {'error': str(e)}
        log_api_request('/tools/analyze', analyze_data.dict(), error_response, 500)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/feedback")
async def feedback(
    request: Request,
    feedback_data: FeedbackRequest,
    client_ip: str = Depends(check_rate_limit)
):
    """Submit feedback (CONTRACT ENFORCED)"""

    data = feedback_data.dict()
    data = sanitize_input(data)

    request_id = f"feedback_{int(time.time())}_{str(uuid.uuid4())[:6]}"

    try:
        # -----------------------------
        # 1. BASIC VALIDATION (ADAPT IF YOUR FIELDS DIFFER)
        # -----------------------------
        symbol = data.get("symbol")
        predicted_action = data.get("predicted_action")
        user_feedback = data.get("user_feedback")
        actual_return = data.get("actual_return")

        if not symbol or not predicted_action or user_feedback is None:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # -----------------------------
        # 2. PROCESS (IF YOU HAVE EXISTING LOGIC, KEEP IT)
        # -----------------------------
        # If you already call a service, keep it here:
        # result = mcp_adapter.process_feedback(...)
        # For now we just echo minimal processed result:
        result = {
            "symbol": symbol,
            "predicted_action": predicted_action,
            "user_feedback": user_feedback,
            "actual_return": actual_return
        }

        # Determine error state (if your processor returns error, adapt here)
        has_error = False
        error_msg = None

        # -----------------------------
        # 3. CONTRACT RESPONSE (BUILD FIRST)
        # -----------------------------
        response = {
            "success": not has_error,
            "data": result if not has_error else {},
            "error": error_msg,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        # -----------------------------
        # 4. DB WRITE (STRICT MODE)
        # -----------------------------
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("""
    INSERT INTO feedback (
        symbol,
        predicted_action,
        user_feedback,
        actual_return,
        timestamp,
        request_id
    ) VALUES (?, ?, ?, ?, ?, ?)
""", (
    symbol,
    predicted_action,
    user_feedback,
    actual_return,
    datetime.utcnow().isoformat(),
    request_id
))

            conn.commit()
            conn.close()

        except Exception as db_error:
            logger.error(f"Feedback DB insert failed: {db_error}", exc_info=True)

            raise HTTPException(
                status_code=500,
                detail="Database write failed. Feedback not saved."
            )

        # -----------------------------
        # 5. LOG ONLY AFTER SUCCESS
        # -----------------------------
        log_api_request('/tools/feedback', data, response, 200)
        log_to_db('/tools/feedback', data, response)
        return response

    # -----------------------------
    # 6. HANDLED HTTP ERRORS
    # -----------------------------
    except HTTPException as http_err:
        error_response = {
            "success": False,
            "data": {},
            "error": http_err.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        log_api_request('/tools/feedback', data, error_response, http_err.status_code)

        return JSONResponse(status_code=http_err.status_code, content=error_response)

    # -----------------------------
    # 7. UNEXPECTED ERRORS
    # -----------------------------
    except Exception as e:
        logger.error(f"Feedback error: {e}", exc_info=True)

        error_response = {
            "success": False,
            "data": {},
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        log_api_request('/tools/feedback', data, error_response, 500)

        return JSONResponse(status_code=500, content=error_response)

@app.post("/tools/train_rl")
async def train_rl(
    request: Request,
    train_data: TrainRLRequest,
    client_ip: str = Depends(check_rate_limit)
):
    """Train RL agent and return reward statistics (NO AUTH REQUIRED)"""
    try:
        data = train_data.dict()
        data = sanitize_input(data)
        
        validation = validate_symbols([data['symbol']])
        if not validation['valid']:
            raise HTTPException(status_code=400, detail=validation['error'])
        
        if not validate_horizon(data['horizon']):
            raise HTTPException(status_code=400, detail='Invalid horizon. Valid options: intraday, short, long')
        
        try:
            n_episodes = int(data['n_episodes'])
            if not (10 <= n_episodes <= 100):
                raise HTTPException(status_code=400, detail='n_episodes must be between 10 and 100')
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail='n_episodes must be an integer')
        
        result = mcp_adapter.train_rl(
            symbol=data['symbol'],
            horizon=data['horizon'],
            n_episodes=n_episodes,
            force_retrain=data['force_retrain']
        )
        
        log_api_request('/tools/train_rl', data, result, 200)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RL training error: {e}", exc_info=True)
        error_response = {'error': str(e)}
        log_api_request('/tools/train_rl', train_data.dict(), error_response, 500)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/live/price/{symbol}")
async def get_live_price(symbol: str):
    """Get LIVE current price - NO CACHE, ALWAYS FRESH"""
    try:
        live_data = price_validator.get_live_price_data(symbol)
        
        if 'error' in live_data:
            raise HTTPException(status_code=404, detail=live_data['error'])
        
        return {
            'symbol': symbol,
            'current_price': live_data['current_price'],
            'price_source': live_data['price_source'],
            'price_timestamp': live_data['price_timestamp'],
            'exchange': live_data['exchange'],
            'currency': live_data['currency'],
            'is_delayed': live_data['is_delayed'],
            'delay_minutes': live_data.get('delay_minutes', 0),
            'market_state': live_data['market_state'],
            'day_change': live_data.get('day_change'),
            'day_change_percent': live_data.get('day_change_percent'),
            'validation': live_data['validation'],
            'fetch_timestamp': live_data['fetch_timestamp']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Live price error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data/transparency/{symbol}")
async def get_data_transparency(symbol: str):
    """Get complete data source transparency for a symbol"""
    try:
        # Get live price data
        live_data = price_validator.get_live_price_data(symbol)
        
        # Load cached data if available
        cached_info = {}
        try:
            import json
            from pathlib import Path
            cache_path = Path(f"data/cache/{symbol}_all_data.json")
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    cached_data = json.load(f)
                
                cached_info = {
                    'cache_exists': True,
                    'cache_fetch_time': cached_data.get('fetch_time'),
                    'cache_data_source': cached_data.get('metadata', {}).get('data_source', 'unknown'),
                    'cached_price': cached_data.get('info', {}).get('currentPrice'),
                    'cache_age_hours': 0
                }
                
                # Calculate cache age
                if cached_info['cache_fetch_time']:
                    import pandas as pd
                    cache_time = pd.to_datetime(cached_info['cache_fetch_time'])
                    now = pd.Timestamp.now()
                    age_hours = (now - cache_time).total_seconds() / 3600
                    cached_info['cache_age_hours'] = round(age_hours, 2)
            else:
                cached_info = {'cache_exists': False}
        except Exception as e:
            cached_info = {'cache_error': str(e)}
        
        # Calculate price differences
        price_comparison = {}
        if 'error' not in live_data and cached_info.get('cached_price'):
            live_price = live_data['current_price']
            cached_price = cached_info['cached_price']
            
            if cached_price > 0:
                diff_pct = ((live_price - cached_price) / cached_price) * 100
                price_comparison = {
                    'live_price': live_price,
                    'cached_price': cached_price,
                    'difference_pct': round(diff_pct, 4),
                    'significant_difference': abs(diff_pct) > 0.5
                }
        
        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'live_data': live_data,
            'cached_data': cached_info,
            'price_comparison': price_comparison,
            'data_integrity': {
                'single_source_of_truth': 'yahoo_finance_live',
                'cache_policy': 'Live prices always override cached prices',
                'prediction_policy': 'Returns calculated using live prices only',
                'transparency_level': 'FULL'
            }
        }
        
    except Exception as e:
        logger.error(f"Data transparency error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/fetch_data")
async def fetch_data(
    request: Request,
    fetch_data_req: FetchDataRequest,
    client_ip: str = Depends(check_rate_limit)
):
    """Fetch batch data for symbols (NO AUTH REQUIRED)"""
    try:
        data = fetch_data_req.dict()
        data = sanitize_input(data)
        
        validation = validate_symbols(data['symbols'], config.MAX_SCAN_SYMBOLS)
        if not validation['valid']:
            raise HTTPException(status_code=400, detail=validation['error'])
        
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
        if data['period'] not in valid_periods:
            raise HTTPException(status_code=400, detail=f'Invalid period. Valid options: {", ".join(valid_periods)}')
        
        result = mcp_adapter.fetch_data(
            symbols=data['symbols'],
            period=data['period'],
            include_features=data['include_features'],
            refresh=data['refresh']
        )
        
        log_api_request('/tools/fetch_data', data, result, 200)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fetch data error: {e}", exc_info=True)
        error_response = {'error': str(e)}
        log_api_request('/tools/fetch_data', fetch_data_req.dict(), error_response, 500)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Main ====================

if __name__ == '__main__':
    import uvicorn
    
    print("\n" + "="*80)
    print(" " * 20 + "MCP API SERVER STARTING")
    print("="*80)
    print("\nSECURITY FEATURES:")
    print("  [ ] JWT Authentication: DISABLED (Open Access)")
    print(f"  [X] Rate Limiting ({config.RATE_LIMIT_PER_MINUTE}/min, {config.RATE_LIMIT_PER_HOUR}/hour)")
    print("  [X] Input Validation")
    print("  [X] Comprehensive Logging")
    print("\nFRAMEWORK:")
    print("  [X] FastAPI (Modern, Fast, Async)")
    print("  [X] Automatic OpenAPI Documentation")
    print("  [X] Pydantic Data Validation")
    print("\nENDPOINTS (ALL OPEN ACCESS - NO AUTH):")
    print("  GET  /                - API information")
    print("  GET  /auth/status     - Rate limit status")
    print("  GET  /tools/health    - System health")
    print("  POST /tools/predict   - Generate predictions")
    print("  POST /tools/scan_all  - Scan and rank symbols")
    print("  POST /tools/analyze   - Analyze with risk parameters")
    print("  POST /tools/feedback  - Human feedback")
    print("  POST /tools/train_rl  - Train RL agent")
    print("  POST /tools/fetch_data - Fetch batch data")
    print("\nDOCUMENTATION:")
    # Show accessible URLs (not 0.0.0.0 which is not accessible in browsers)
    accessible_host = "127.0.0.1" if config.UVICORN_HOST == "0.0.0.0" else config.UVICORN_HOST
    print(f"  Swagger UI: http://{accessible_host}:{config.UVICORN_PORT}/docs")
    print(f"  ReDoc: http://{accessible_host}:{config.UVICORN_PORT}/redoc")
    print("\nACCESS MODE:")
    print("  Status: OPEN ACCESS")
    print("  Authentication: None required")
    print("  All endpoints available without login")
    print(f"\n>>> SERVER ACCESSIBLE AT: http://{accessible_host}:{config.UVICORN_PORT} <<<")
    print(f">>> OPEN IN BROWSER: http://localhost:{config.UVICORN_PORT}/docs <<<")
    print("="*80 + "\n")
    
    # Security warning for debug mode
    if config.DEBUG_MODE:
        print("!" * 80)
        print(" WARNING: DEBUG MODE IS ENABLED ".center(80, "!"))
        print("!" * 80)
        print(" Debug mode exposes sensitive information!".center(80))
        print(" NEVER use debug mode in production deployments!".center(80))
        print(" Set DEBUG_MODE=False in .env for production".center(80))
        print("!" * 80 + "\n")
        import time
        time.sleep(2)  # Force admin to see warning
    
    uvicorn.run(
        "api_server:app",
        host=config.UVICORN_HOST,
        port=config.UVICORN_PORT,
        reload=config.DEBUG_MODE,
        log_level="info"
    )

@app.post("/knowledge/ingest")
async def ingest_knowledge(req: dict):
    request_id = f"knowledge_ingest_{int(time.time())}_{str(uuid.uuid4())[:6]}"

    try:
        knowledge_ingestor.insert_manual({
            "concept": req.get("text", ""),
            "category": "GENERAL",
            "title": req.get("text", ""),
            "explanation": req.get("text", ""),
            "confidence_level": 0.8
        })

        response = {
            "success": True,
            "data": {
                "message": "Knowledge ingested"
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        log_to_db('/knowledge/ingest', req, response)

        return response

    except Exception as e:
        response = {
            "success": False,
            "data": {},
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        try:
            log_to_db('/knowledge/ingest', req, response)
        except:
            pass

        return response


@app.get("/knowledge/retrieve")
def retrieve_knowledge(query: str = ""):
    request_id = f"knowledge_retrieve_{int(time.time())}_{str(uuid.uuid4())[:6]}"

    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory system not initialized")

    try:
        results = memory_manager.get_knowledge(concept=query)

        response = {
            "success": True,
            "data": {
                "count": len(results),
                "results": [
                    {
                        "concept": r.concept,
                        "title": r.title,
                        "explanation": r.explanation
                    }
                    for r in results
                ]
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        log_to_db('/knowledge/retrieve', {"query": query}, response)

        return response

    except Exception as e:
        print("❌ RETRIEVE ERROR:", e)

        response = {
            "success": False,
            "data": {},
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

        try:
            log_to_db('/knowledge/retrieve', {"query": query}, response)
        except:
            pass

        return response
    
@app.post("/news/ingest")
def ingest_news(data: dict):
    try:
        request_id = f"news_{int(time.time())}_{str(uuid.uuid4())[:6]}"

        # -------------------------
        # 1. VALIDATION
        # -------------------------
        required = ["news_id", "title", "content", "source", "timestamp"]
        for field in required:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing field: {field}")

        metadata = data.get("metadata", {})
        category = metadata.get("category", "general")
        region = metadata.get("region", "global")

        # -------------------------
        # 2. SIMPLE NLP LOGIC
        # -------------------------
        text = data["content"].lower()

        if "profit" in text or "growth" in text:
            sentiment = "positive"
        elif "loss" in text or "decline" in text:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        impact_score = round(min(len(text) / 1000, 1), 2)

        tags = []
        if "stock" in text:
            tags.append("market")
        if "policy" in text:
            tags.append("policy")

        # -------------------------
        # 3. DB WRITE
        # -------------------------
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO news (
            news_id, title, content, source, timestamp,
            category, region, sentiment, impact_score, tags, request_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["news_id"],
            data["title"],
            data["content"],
            data["source"],
            data["timestamp"],
            category,
            region,
            sentiment,
            impact_score,
            ",".join(tags),
            request_id
        ))

        conn.commit()
        conn.close()

        # -------------------------
        # 4. RESPONSE
        # -------------------------
        return {
            "success": True,
            "data": {
                "sentiment": sentiment,
                "impact_score": impact_score,
                "tags": tags
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }

    except HTTPException as e:
        return {
            "success": False,
            "data": {},
            "error": e.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": f"news_error_{int(time.time())}"
        }

    except Exception as e:
        return {
            "success": False,
            "data": {},
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": f"news_error_{int(time.time())}"
        }
    
@app.get("/news/{news_id}")
def get_news(news_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM news WHERE news_id = ?", (news_id,))
    row = cursor.fetchone()

    conn.close()

    if not row:
        return {"success": False, "error": "Not found"}

    columns = [desc[0] for desc in cursor.description]
    data = dict(zip(columns, row))

    return {"success": True, "data": data}