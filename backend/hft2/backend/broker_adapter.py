"""
Universal broker adapter: one interface for all demat brokers.
Register adapters per broker (Dhan, Zerodha, etc.); portfolio and order calls dispatch by user's broker.
"""
import logging
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

# Type aliases for adapter functions
GetPortfolioFn = Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]
PlaceOrderFn = Callable[..., Optional[Dict[str, Any]]]

_registry: Dict[str, Dict[str, Any]] = {}  # broker_id -> { "get_portfolio": fn, "place_order": fn }


def register_broker(
    broker_id: str,
    get_portfolio: GetPortfolioFn,
    place_order: PlaceOrderFn,
) -> None:
    """Register a broker adapter. broker_id is stored per user (e.g. 'dhan', 'zerodha')."""
    _registry[broker_id.lower().strip()] = {
        "get_portfolio": get_portfolio,
        "place_order": place_order,
    }
    logger.info("Registered broker adapter: %s", broker_id)


def get_portfolio(creds: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get live portfolio for the given credentials. creds must have broker, client_id, access_token."""
    broker = (creds.get("broker") or "dhan").lower().strip()
    adapter = _registry.get(broker)
    if not adapter:
        logger.warning("No adapter for broker: %s", broker)
        return None
    try:
        return adapter["get_portfolio"](creds)
    except Exception as e:
        logger.warning("Broker get_portfolio failed for %s: %s", broker, e)
        return None


def place_order(
    creds: Dict[str, Any],
    symbol: str,
    side: str,
    quantity: int,
    product_type: str = "CNC",
    trigger_price: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Place order for the given credentials. Works for any registered broker."""
    broker = (creds.get("broker") or "dhan").lower().strip()
    adapter = _registry.get(broker)
    if not adapter:
        logger.warning("No adapter for broker: %s", broker)
        return None
    try:
        return adapter["place_order"](
            creds=creds,
            symbol=symbol,
            side=side.upper(),
            quantity=quantity,
            product_type=product_type,
            trigger_price=trigger_price,
        )
    except Exception as e:
        logger.warning("Broker place_order failed for %s: %s", broker, e)
        return None


def _dhan_get_portfolio(creds: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from dhan_client import get_live_portfolio
    return get_live_portfolio(
        access_token=creds.get("access_token"),
        client_id=creds.get("client_id"),
    )


def _dhan_place_order(
    creds: Dict[str, Any],
    symbol: str,
    side: str,
    quantity: int,
    product_type: str = "CNC",
    trigger_price: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    from dhan_client import place_order_market
    return place_order_market(
        symbol=symbol,
        side=side.upper(),
        quantity=quantity,
        product_type=product_type,
        trigger_price=trigger_price,
        access_token=creds.get("access_token"),
        client_id=creds.get("client_id"),
    )


# Register Dhan by default. To add another broker (e.g. Zerodha):
# 1. Implement _zerodha_get_portfolio(creds) -> portfolio dict and _zerodha_place_order(creds, symbol, side, quantity, ...) -> order result.
# 2. register_broker("zerodha", _zerodha_get_portfolio, _zerodha_place_order)
# 3. Store broker="zerodha" in user demat credentials. No other backend changes needed.
register_broker("dhan", _dhan_get_portfolio, _dhan_place_order)
