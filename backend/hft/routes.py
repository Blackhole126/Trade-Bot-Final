"""
HFT Bot API routes - integrated into main backend.
Unified server: vetting agent at /tools/*, HFT Bot at /api/*.
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, List, Any
from datetime import datetime, timedelta
import random

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

hft_router = APIRouter()

# When Start Bot is used without HFT2_BACKEND_URL, optionally start hft2 processes (web_backend, fyers) so logs show in Render.
_hft2_processes: List[subprocess.Popen] = []
_hft2_stream_threads: List[Any] = []  # keep refs so threads don't get GC'd
# HFT2_BACKEND_DIR: optional env override on Render. If relative, resolved from backend dir (not cwd).
_backend_dir = (Path(__file__).resolve().parent.parent)  # .../backend
_default_hft2_dir = (_backend_dir / "hft2" / "backend").resolve()
_env_hft2 = os.environ.get("HFT2_BACKEND_DIR")
if _env_hft2:
    _p = Path(_env_hft2)
    if _p.is_absolute():
        _hft2_backend_dir = _p.resolve()
    else:
        # "backend/hft2/backend": strip leading "backend/" and resolve rest under _backend_dir -> .../backend/hft2/backend
        _parts = _p.parts
        if _parts and _parts[0] == "backend":
            _hft2_backend_dir = (_backend_dir / Path(*_parts[1:])).resolve()
        else:
            _hft2_backend_dir = (_backend_dir / _p).resolve()
else:
    _hft2_backend_dir = _default_hft2_dir
# Render: try fallbacks when path missing (e.g. root=backend so _backend_dir=.../src, path .../src/hft2/backend missing; try .../src/backend/hft2/backend)
if not _hft2_backend_dir.is_dir():
    for _candidate in (
        _backend_dir / "backend" / "hft2" / "backend",  # root=backend: .../src/backend/hft2/backend
        _backend_dir.parent / "backend" / "hft2" / "backend" if _backend_dir.parent else Path(),
        _backend_dir.parent / "hft2" / "backend" if _backend_dir.parent else Path(),
    ):
        if _candidate and _candidate.resolve().is_dir():
            _hft2_backend_dir = _candidate.resolve()
            break


# ---------- Pydantic models ----------
class BotConfig(BaseModel):
    model_config = {"populate_by_name": True}
    mode: str
    risk_level: str = Field(alias="riskLevel")
    max_allocation: float = Field(alias="maxAllocation")
    stop_loss: Optional[float] = Field(None, alias="stopLoss")


class ChatMessage(BaseModel):
    message: str


class OrderRequest(BaseModel):
    symbol: str
    side: str  # BUY | SELL
    quantity: int
    order_type: str = "MARKET"
    price: Optional[float] = None


# ---------- In-memory state (unified with main backend; no second process) ----------
bot_state = {
    "isRunning": False,
    "config": {
        "mode": "paper",
        "tickers": ["RELIANCE.NS", "TCS.NS", "INFY.NS"],
        "riskLevel": "MEDIUM",
        "maxAllocation": 0.25,
        "stopLoss": 0.05,
    },
    "portfolio": {
        "totalValue": 1050000,
        "cash": 850000,
        "startingBalance": 1000000,
        "holdings": {
            "RELIANCE.NS": {
                "symbol": "RELIANCE.NS",
                "quantity": 50,
                "avgPrice": 2500,
                "currentPrice": 2600,
                "lastAction": "BUY",
            },
            "TCS.NS": {
                "symbol": "TCS.NS",
                "quantity": 100,
                "avgPrice": 3200,
                "currentPrice": 3300,
                "lastAction": "BUY",
            },
        },
        "tradeLog": [
            {
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "symbol": "RELIANCE.NS",
                "action": "BUY",
                "quantity": 50,
                "price": 2500,
                "total": 125000,
            },
            {
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "symbol": "TCS.NS",
                "action": "BUY",
                "quantity": 100,
                "price": 3200,
                "total": 320000,
            },
        ],
    },
    "chatMessages": [],
}

# After cold start (e.g. Render), use live mode if env is set so Dhan is fetched without re-saving Settings.
if os.environ.get("HFT_DEFAULT_MODE", "").strip().lower() == "live":
    bot_state["config"]["mode"] = "live"


# ---------- Health & status ----------
@hft_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@hft_router.get("/status")
async def status():
    return {
        "status": "healthy",
        "isRunning": bot_state["isRunning"],
        "timestamp": datetime.now().isoformat(),
    }


# ---------- Dhan live (optional; uses env only - works on Render when DHAN_ACCESS_TOKEN set) ----------
_last_dhan_error: Optional[str] = None


def _get_dhan_live_portfolio():
    """When mode is live and env has Dhan credentials, return real portfolio; else None."""
    global _last_dhan_error
    try:
        import dhan_live
        if not getattr(dhan_live, "get_dhan_token", None) or not dhan_live.get_dhan_token():
            _last_dhan_error = None
            return None
        out = dhan_live.get_live_portfolio()
        if out is not None:
            _last_dhan_error = None
        return out
    except Exception as e:
        _last_dhan_error = str(e)
        logger.warning("dhan_live get_live_portfolio failed: %s", e)
        return None


# ---------- Bot data & portfolio ----------
def _hft_portfolio():
    """Paper: empty. Live: use Dhan from env if available (single-backend / Render)."""
    if bot_state.get("config", {}).get("mode") == "live":
        live = _get_dhan_live_portfolio()
        if live is not None:
            return live
    return {
        "totalValue": 0,
        "cash": 0,
        "startingBalance": 0,
        "holdings": {},
        "tradeLog": [],
    }


@hft_router.get("/bot-data")
async def get_bot_data():
    portfolio = _hft_portfolio()
    mode = bot_state.get("config", {}).get("mode", "paper")
    payload = {
        **bot_state,
        "isRunning": bot_state["isRunning"],
        "portfolio": portfolio,
    }
    if mode == "live" and _last_dhan_error and (not portfolio or portfolio.get("totalValue", 0) == 0):
        payload["dhan_error"] = _last_dhan_error
    return payload


@hft_router.get("/portfolio")
async def get_portfolio():
    return _hft_portfolio()


@hft_router.get("/trades")
async def get_trades(limit: int = 10):
    return []


# ---------- Watchlist ----------
@hft_router.get("/watchlist")
async def get_watchlist():
    return {"tickers": bot_state["config"]["tickers"]}


@hft_router.post("/watchlist/add/{ticker}")
async def add_to_watchlist(ticker: str):
    ticker = ticker.upper().strip()
    if ticker not in bot_state["config"]["tickers"]:
        bot_state["config"]["tickers"].append(ticker)
    return {"status": "success", "message": f"Added {ticker}", "tickers": bot_state["config"]["tickers"]}


@hft_router.delete("/watchlist/remove/{ticker}")
async def remove_from_watchlist(ticker: str):
    ticker = ticker.upper().strip()
    if ticker in bot_state["config"]["tickers"]:
        bot_state["config"]["tickers"].remove(ticker)
    return {"status": "success", "message": f"Removed {ticker}", "tickers": bot_state["config"]["tickers"]}


class WatchlistBulkBody(BaseModel):
    tickers: List[str]
    action: str = "ADD"


@hft_router.post("/watchlist/bulk")
async def watchlist_bulk(body: WatchlistBulkBody):
    for t in (x.upper().strip() for x in body.tickers):
        if body.action.upper() == "ADD" and t not in bot_state["config"]["tickers"]:
            bot_state["config"]["tickers"].append(t)
        elif body.action.upper() == "REMOVE" and t in bot_state["config"]["tickers"]:
            bot_state["config"]["tickers"].remove(t)
    return {"status": "success", "tickers": bot_state["config"]["tickers"]}


# ---------- Bot control ----------
def _pipe_subprocess_log(name: str, pipe: Any, _process: subprocess.Popen) -> None:
    """Read subprocess stdout/stderr line by line and log with prefix so Render shows HFT2 output."""
    import threading
    try:
        for line in iter(pipe.readline, ""):
            if not line:
                break
            line = line.rstrip()
            if line:
                logger.info("[%s] %s", name, line)
    except Exception as e:
        logger.warning("[%s] pipe read error: %s", name, e)
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def _start_hft2_stack() -> None:
    """Start fyers_data_service and web_backend (uses testindia); pipe their output to backend logs for Render."""
    global _hft2_processes, _hft2_stream_threads
    _hft2_stream_threads.clear()
    if not _hft2_backend_dir.is_dir():
        logger.warning("HFT2 backend dir not found at %s - Start Bot will not run testindia/web_backend", _hft2_backend_dir)
        return
    if _hft2_processes:
        logger.info("HFT2 processes already running (%s), skipping", len(_hft2_processes))
        return
    env = os.environ.copy()
    # Use Render/env Fyers credentials as-is; set FYERS_ALLOW_MOCK=true only if you want mock data
    env["PYTHONUNBUFFERED"] = "1"
    cwd = str(_hft2_backend_dir)
    logger.info("HFT2 Start Bot: starting stack at %s", cwd)
    try:
        import threading
        # Fyers data service (port 8002) - pipe output so it appears in Render logs
        p1 = subprocess.Popen(
            [sys.executable, "-u", "fyers_data_service.py", "--port", "8002"],
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        _hft2_processes.append(p1)
        t1 = threading.Thread(target=_pipe_subprocess_log, args=("fyers", p1.stdout, p1), daemon=True)
        t1.start()
        _hft2_stream_threads.append(t1)
        logger.info("Started fyers_data_service (PID %s) - output will stream to logs", p1.pid)
        # Web backend (port 5000) - imports testindia.py; bind 0.0.0.0 so health check reaches it
        p2 = subprocess.Popen(
            [sys.executable, "-u", "web_backend.py", "--host", "0.0.0.0", "--port", "5000"],
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        _hft2_processes.append(p2)
        t2 = threading.Thread(target=_pipe_subprocess_log, args=("web_backend", p2.stdout, p2), daemon=True)
        t2.start()
        _hft2_stream_threads.append(t2)
        logger.info("Started web_backend (PID %s) - testindia/output will stream to logs", p2.pid)
    except Exception as e:
        logger.exception("Failed to start HFT2 stack: %s", e)


def _stop_hft2_stack() -> None:
    """Terminate started hft2 subprocesses."""
    global _hft2_processes
    for p in _hft2_processes:
        try:
            p.terminate()
            p.wait(timeout=10)
        except Exception as e:
            logger.warning("Error stopping HFT2 process %s: %s", p.pid, e)
            try:
                p.kill()
            except Exception:
                pass
    _hft2_processes.clear()
    logger.info("HFT2 stack stopped")


async def _hft2_sync_watchlist_and_predict() -> None:
    """After HFT2 stack starts: wait for web_backend, sync watchlist, trigger predict so Render logs show activity."""
    import requests
    await asyncio.sleep(15)  # web_backend can be slow (initialize_bot, heavy imports)
    base = "http://127.0.0.1:5000"
    for _ in range(30):  # up to 60s more
        try:
            r = requests.get(f"{base}/api/health", timeout=5)
            if r.status_code == 200:
                break
        except Exception:
            pass
        await asyncio.sleep(2)
    else:
        logger.warning("HFT2 web_backend did not become ready in time; check [web_backend] logs above for startup errors")
        return
    tickers = list(bot_state.get("config", {}).get("tickers") or [])
    if not tickers:
        logger.info("HFT2 sync: no watchlist tickers")
        return
    logger.info("HFT2 syncing watchlist and triggering predict for %s", tickers)
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: requests.post(f"{base}/api/watchlist/bulk", json={"tickers": tickers, "action": "ADD"}, timeout=15),
        )
        await loop.run_in_executor(
            None,
            lambda: requests.post(f"{base}/api/mcp/predict", json={"symbols": tickers}, timeout=180),
        )
        logger.info("HFT2 watchlist synced and predict triggered for %s", tickers)
    except Exception as e:
        logger.warning("HFT2 sync/predict failed: %s", e)


@hft_router.post("/bot/start")
async def start_bot():
    logger.info("Start Bot requested (HFT2_BACKEND_URL=%s)", "set" if os.environ.get("HFT2_BACKEND_URL") else "not set")
    if not os.environ.get("HFT2_BACKEND_URL"):
        _start_hft2_stack()
        asyncio.create_task(_hft2_sync_watchlist_and_predict())
    bot_state["isRunning"] = True
    logger.info("HFT Bot started (isRunning=True)")
    return {"status": "success", "message": "Bot started", "isRunning": True}


@hft_router.post("/bot/stop")
async def stop_bot():
    _stop_hft2_stack()
    bot_state["isRunning"] = False
    logger.info("HFT Bot stopped")
    return {"status": "success", "message": "Bot stopped", "isRunning": False}


# ---------- Settings ----------
@hft_router.get("/settings")
async def get_settings():
    return bot_state["config"]


@hft_router.post("/settings")
async def update_settings(config: BotConfig):
    bot_state["config"]["mode"] = config.mode
    bot_state["config"]["riskLevel"] = config.risk_level
    bot_state["config"]["maxAllocation"] = config.max_allocation
    if config.stop_loss is not None:
        bot_state["config"]["stopLoss"] = config.stop_loss
    return {"status": "success", "message": "Settings updated"}


# ---------- Chat ----------
@hft_router.post("/chat")
async def chat(message: ChatMessage):
    user_msg = {"role": "user", "content": message.message, "timestamp": datetime.now().isoformat()}
    bot_state["chatMessages"].append(user_msg)

    response_content = "I'm the HFT trading assistant. How can I help you today?"
    if "pnl" in message.message.lower() or "profit" in message.message.lower():
        total = bot_state["portfolio"]["totalValue"]
        start = bot_state["portfolio"]["startingBalance"]
        pnl = total - start
        pnl_pct = (pnl / start) * 100 if start else 0
        response_content = f"Current P&L: ₹{pnl:,.2f} ({pnl_pct:.2f}%)\nTotal Portfolio Value: ₹{total:,.2f}"
    elif "position" in message.message.lower():
        n = len(bot_state["portfolio"]["holdings"])
        response_content = f"You have {n} active positions.\n"
        for sym, h in bot_state["portfolio"]["holdings"].items():
            pnl = (h.get("currentPrice", h["avgPrice"]) - h["avgPrice"]) * h["quantity"]
            response_content += f"- {sym}: {h['quantity']} shares, P&L: ₹{pnl:,.2f}\n"

    assistant_msg = {"role": "assistant", "content": response_content, "timestamp": datetime.now().isoformat()}
    bot_state["chatMessages"].append(assistant_msg)
    return {"response": response_content, "messages": bot_state["chatMessages"]}


# ---------- Live status & sync ----------
@hft_router.get("/live-status")
async def get_live_status():
    mode = bot_state["config"]["mode"]
    dhan_configured = False
    if mode == "live":
        try:
            import dhan_live
            dhan_configured = bool(getattr(dhan_live, "get_dhan_token", None) and dhan_live.get_dhan_token())
        except Exception:
            pass
    return {
        "connected": bot_state["isRunning"],
        "mode": mode,
        "lastUpdate": datetime.now().isoformat(),
        "dhan_configured": dhan_configured,
        "dhan_error": _last_dhan_error if (mode == "live" and _last_dhan_error) else None,
    }


@hft_router.post("/live/sync")
async def sync_live_portfolio():
    return {"status": "success", "message": "Portfolio sync (paper mode)"}


# ---------- MCP (stubs; real execution would plug broker here) ----------
@hft_router.post("/mcp/analyze")
async def mcp_analyze(symbol: str):
    return {
        "symbol": symbol.upper(),
        "analysis": {"trend": "bullish", "strength": random.uniform(0.6, 0.9), "recommendation": "BUY"},
        "timestamp": datetime.now().isoformat(),
    }


@hft_router.post("/mcp/execute")
async def mcp_execute(request: Request, body: dict):
    # Stub: paper order logged; for live demat, wire to broker client here
    symbol = (body.get("symbol") or "").upper()
    side = (body.get("side") or "BUY").upper()
    qty = int(body.get("quantity", 0))
    return {
        "status": "success",
        "message": f"Paper order: {side} {qty} {symbol} (configure broker for live execution)",
        "order_id": f"paper-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    }


@hft_router.post("/mcp/chat")
async def mcp_chat(body: dict):
    msg = (body.get("message") or "").strip()
    return {"response": f"MCP chat received: {msg[:100]}", "timestamp": datetime.now().isoformat()}


@hft_router.get("/mcp/status")
async def mcp_status():
    return {"mcp_available": True, "server_initialized": True}


# ---------- Predictions from vetting agent (Market Scan backend) ----------
@hft_router.get("/predictions")
async def get_predictions(request: Request, symbols: str = "RELIANCE.NS", horizon: str = "intraday"):
    """Fetch predictions from the vetting agent (same backend). HFT Bot can show these."""
    adapter = getattr(request.app.state, "mcp_adapter", None)
    if not adapter:
        return {"predictions": [], "message": "Vetting agent not available"}
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            symbol_list = ["RELIANCE.NS"]
        result = adapter.predict(symbols=symbol_list, horizon=horizon)
        return result
    except Exception as e:
        logger.exception("HFT predictions from vetting agent failed")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Order (buy/sell) stub for demat/live ----------
@hft_router.post("/order")
async def place_order(order: OrderRequest):
    # Paper: append to tradeLog; live would call broker
    ts = datetime.now().isoformat()
    total = order.quantity * (order.price or 0)
    entry = {
        "timestamp": ts,
        "symbol": order.symbol.upper(),
        "action": order.side.upper(),
        "quantity": order.quantity,
        "price": order.price or 0,
        "total": total,
    }
    bot_state["portfolio"]["tradeLog"].insert(0, entry)
    return {"status": "success", "order_id": f"paper-{ts}", "message": "Order placed (paper)"}


# ---------- Production stubs ----------
@hft_router.get("/production/signal-performance")
async def signal_performance():
    return {"signals": [], "message": "Stub"}


@hft_router.get("/production/risk-metrics")
async def risk_metrics():
    return {"metrics": {}, "message": "Stub"}


@hft_router.post("/production/make-decision")
async def make_decision(body: dict):
    return {"decision": "HOLD", "symbol": body.get("symbol", ""), "message": "Stub"}


@hft_router.get("/production/learning-insights")
async def learning_insights():
    return {"insights": [], "message": "Stub"}


@hft_router.get("/production/decision-history")
async def decision_history(days: int = 7):
    return {"history": [], "days": days}
