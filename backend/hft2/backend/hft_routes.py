#!/usr/bin/env python3
"""
HFT API Endpoints - Control and monitoring for BHIV HFT system
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

hft_router = APIRouter(prefix="/api/hft", tags=["HFT"])


@hft_router.get("/status")
async def get_hft_status(user=Depends(get_optional_user)):
    """Get HFT system status for authenticated user"""
    try:
        username = (user.get("sub") or "").strip() if user else "anonymous"
        state = get_user_state(username)
        
        hft_manager = state.get("hft_manager")
        
        if not hft_manager:
            return {
                "enabled": False,
                "initialized": False,
                "message": "HFT system not initialized"
            }
        
        # Get detailed status from HFT Manager
        status = hft_manager.get_status()
        
        # Add pipeline metrics if available
        if hft_manager.pipeline:
            status["pipeline"] = {
                "tick_buffer_size": hft_manager.pipeline.tick_buffer.size() if hasattr(hft_manager.pipeline.tick_buffer, 'size') else 0,
                "last_regime": hft_manager.pipeline.simulator.current_regime.value if hasattr(hft_manager.pipeline.simulator, 'current_regime') else "UNKNOWN",
                "karma_score": hft_manager.pipeline.simulator.get_karma_score() if hasattr(hft_manager.pipeline.simulator, 'get_karma_score') else 0.0
            }
        
        return status
        
    except Exception as e:
        logger.error(f"HFT status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@hft_router.post("/enable")
async def enable_hft(user=Depends(get_optional_user)):
    """Enable HFT intraday trading"""
    try:
        username = (user.get("sub") or "").strip() if user else "anonymous"
        state = get_user_state(username)
        
        hft_manager = state.get("hft_manager")
        
        if not hft_manager:
            # Initialize HFT manager
            from hft_manager import HFTManager
            bot = state.get("trading_bot")
            if bot:
                config = bot.config
                hft_manager = HFTManager(config=config, username=username)
                state["hft_manager"] = hft_manager
        
        if hft_manager:
            hft_manager.enable()
            return {"success": True, "message": "HFT enabled"}
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize HFT")
            
    except Exception as e:
        logger.error(f"HFT enable error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@hft_router.post("/disable")
async def disable_hft(user=Depends(get_optional_user)):
    """Disable HFT intraday trading"""
    try:
        username = (user.get("sub") or "").strip() if user else "anonymous"
        state = get_user_state(username)
        
        hft_manager = state.get("hft_manager")
        
        if hft_manager:
            hft_manager.disable()
            return {"success": True, "message": "HFT disabled"}
        else:
            return {"success": True, "message": "HFT already disabled"}
            
    except Exception as e:
        logger.error(f"HFT disable error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@hft_router.post("/mode")
async def set_hft_mode(mode: str, user=Depends(get_optional_user)):
    """Set HFT mode (shadow, live, hybrid)"""
    try:
        username = (user.get("sub") or "").strip() if user else "anonymous"
        state = get_user_state(username)
        
        hft_manager = state.get("hft_manager")
        
        if not hft_manager:
            raise HTTPException(status_code=400, detail="HFT not initialized")
        
        if mode not in ["shadow", "live", "hybrid"]:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}. Must be shadow, live, or hybrid")
        
        hft_manager.set_mode(mode)
        return {"success": True, "mode": mode}
        
    except Exception as e:
        logger.error(f"HFT mode error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@hft_router.get("/metrics")
async def get_hft_metrics(user=Depends(get_optional_user)):
    """Get HFT performance metrics"""
    try:
        username = (user.get("sub") or "").strip() if user else "anonymous"
        state = get_user_state(username)
        
        hft_manager = state.get("hft_manager")
        
        if not hft_manager:
            return {
                "signals_generated": 0,
                "shadow_orders": 0,
                "karma_score": 0.0
            }
        
        return {
            "signals_generated": hft_manager.signals_generated,
            "shadow_orders_filled": hft_manager.shadow_orders_filled,
            "last_signal_time": hft_manager.last_signal_time.isoformat() if hft_manager.last_signal_time else None,
            "uptime_seconds": (datetime.now() - hft_manager.last_signal_time).total_seconds() if hft_manager.last_signal_time else 0
        }
        
    except Exception as e:
        logger.error(f"HFT metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Import dependencies
from web_backend import get_user_state, get_optional_user
import logging
