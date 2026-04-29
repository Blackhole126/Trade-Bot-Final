"""
Request-scoped user context for MCP and bot flows.
When set (e.g. by web_backend before calling MCP), portfolio/order tools use this user's demat.
"""
import contextvars
from typing import Optional, Dict, Any

# Context var: when set, holds {"user_id": str, "demat": {"client_id", "access_token", "broker"}}
_mcp_user_context: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "mcp_user_context", default=None
)


def set_mcp_user_context(user_id: Optional[str], demat: Optional[Dict[str, Any]]) -> None:
    """Set the current request's user context (call from web_backend before MCP)."""
    if user_id and demat and demat.get("access_token") and demat.get("client_id"):
        _mcp_user_context.set({"user_id": user_id, "demat": demat})
    else:
        _mcp_user_context.set(None)


def get_mcp_user_context() -> Optional[Dict[str, Any]]:
    """Return current request user context or None."""
    return _mcp_user_context.get()


def get_portfolio_for_request_user() -> Optional[Dict[str, Any]]:
    """Return live portfolio for the request user if context is set; uses universal broker adapter."""
    ctx = get_mcp_user_context()
    if not ctx or not ctx.get("demat"):
        return None
    demat = ctx["demat"]
    if not demat.get("access_token") or not demat.get("client_id"):
        return None
    try:
        from broker_adapter import get_portfolio as broker_get_portfolio
        return broker_get_portfolio(demat)
    except Exception:
        return None


def place_order_for_request_user(
    symbol: str, side: str, quantity: int,
    product_type: str = "CNC", trigger_price: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Place order for the request user if context is set; uses universal broker adapter (any registered broker)."""
    ctx = get_mcp_user_context()
    if not ctx or not ctx.get("demat"):
        return None
    demat = ctx["demat"]
    if not demat.get("access_token") or not demat.get("client_id"):
        return None
    try:
        from broker_adapter import place_order as broker_place_order
        return broker_place_order(
            demat,
            symbol=symbol,
            side=side,
            quantity=quantity,
            product_type=product_type,
            trigger_price=trigger_price,
        )
    except Exception:
        return None
