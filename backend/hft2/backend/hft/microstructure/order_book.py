from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import hashlib


@dataclass(frozen=True)
class OrderBookLevel:
    """
    Represents a single price level in the order book.
    """
    price: float
    qty: int
    # Number of orders at this level (for queue position estimation)
    order_count: int = 0

    @property
    def value(self) -> float:
        """Total value at this level"""
        return self.price * self.qty


@dataclass(frozen=True)
class OrderBookSnapshot:
    """
    Represents a snapshot of the order book at a specific point in time.
    Contains top 5 levels on each side with derived metrics.
    """
    timestamp: datetime
    symbol: str
    bids: List[OrderBookLevel]  # Top 5 bid levels (highest first)
    asks: List[OrderBookLevel]  # Top 5 ask levels (lowest first)

    @property
    def total_bid_qty(self) -> float:
        """Total bid quantity across all levels"""
        return sum(level.qty for level in self.bids)

    @property
    def total_ask_qty(self) -> float:
        """Total ask quantity across all levels"""
        return sum(level.qty for level in self.asks)

    @property
    def spread_bps(self) -> float:
        """Bid-ask spread in basis points"""
        if not self.bids or not self.asks:
            return 0.0
        mid_price = (self.bids[0].price + self.asks[0].price) / 2
        return ((self.asks[0].price - self.bids[0].price) / mid_price) * 10000

    @property
    def mid_price(self) -> float:
        """Simple mid-price"""
        if not self.bids or not self.asks:
            return 0.0
        return (self.bids[0].price + self.asks[0].price) / 2

    @property
    def weighted_mid(self) -> float:
        """
        Volume-weighted mid-price.
        Gives more weight to the side with less liquidity.
        """
        if not self.bids or not self.asks:
            return 0.0

        bid_qty = self.total_bid_qty
        ask_qty = self.total_ask_qty
        total_qty = bid_qty + ask_qty

        if total_qty == 0:
            return 0.0

        # Weight towards the side with less liquidity
        bid_weight = ask_qty / total_qty
        ask_weight = bid_qty / total_qty

        return (self.bids[0].price * bid_weight) + (self.asks[0].price * ask_weight)

    @property
    def best_bid(self) -> float:
        """Best bid price (highest bid)"""
        return self.bids[0].price if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        """Best ask price (lowest ask)"""
        return self.asks[0].price if self.asks else 0.0

    @property
    def imbalance_ratio(self) -> float:
        """
        Order book imbalance ratio.
        Positive = more buy pressure, Negative = more sell pressure.
        Range: [-1, 1]
        """
        total_qty = self.total_bid_qty + self.total_ask_qty
        if total_qty == 0:
            return 0.0
        return (self.total_bid_qty - self.total_ask_qty) / total_qty

    @property
    def feature_hash(self) -> str:
        """Generate deterministic hash for audit trail"""
        data_str = (
            f"{self.timestamp.isoformat()}|"
            f"{self.symbol}|"
            f"{','.join(f'{l.price}:{l.qty}' for l in self.bids)}|"
            f"{','.join(f'{l.price}:{l.qty}' for l in self.asks)}"
        )
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
