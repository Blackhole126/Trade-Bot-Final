from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Deque
from collections import deque

from .order_book import OrderBookSnapshot


@dataclass(frozen=True)
class OrderBookImbalance:
    """
    Represents Order Book Imbalance (OBI) at a specific timestamp.
    OBI = (bid_qty - ask_qty) / (bid_qty + ask_qty)
    Range: [-1, 1]

    Interpretation:
    - Positive (>0): More buy pressure (bids > asks)
    - Negative (<0): More sell pressure (asks > bids)
    - Zero (~0): Balanced book
    """
    timestamp: datetime
    symbol: str
    bid_qty: float
    ask_qty: float
    obi_value: float  # (bid - ask) / (bid + ask)

    @property
    def interpretation(self) -> str:
        """Human-readable interpretation of OBI value."""
        if self.obi_value > 0.3:
            return "Buy Pressure"
        elif self.obi_value < -0.3:
            return "Sell Pressure"
        return "Balanced"

    @property
    def strength(self) -> str:
        """Strength of imbalance."""
        abs_obi = abs(self.obi_value)
        if abs_obi > 0.7:
            return "VERY_STRONG"
        elif abs_obi > 0.5:
            return "STRONG"
        elif abs_obi > 0.3:
            return "MODERATE"
        return "WEAK"


class OBITracker:
    """
    Track Order Book Imbalance over time with EMA smoothing.

    The Exponential Moving Average (EMA) provides:
    - Smoother signal than raw OBI
    - Less noise for better decision making
    - Configurable responsiveness via alpha parameter

    Usage:
        tracker = OBITracker(alpha=0.3)
        for order_book in order_books:
            obi = tracker.update(order_book)
            print(f"OBI: {obi.obi_value:.3f} ({obi.interpretation})")
    """

    def __init__(self, alpha: float = 0.3):
        """
        Initialize OBI tracker.

        Args:
            alpha: EMA smoothing factor (0.0-1.0)
                   Higher = more responsive to recent changes
                   Lower = smoother, more lag
        """
        if not 0.0 < alpha <= 1.0:
            raise ValueError("Alpha must be between 0 and 1")

        self.alpha = alpha
        self.ema_obi: float = 0.0
        self.raw_obi: float = 0.0
        self._initialized = False

        # History for analysis (optional)
        self.history: Deque[OrderBookImbalance] = deque(maxlen=1000)

    def update(self, order_book: OrderBookSnapshot) -> OrderBookImbalance:
        """
        Update OBI with new order book snapshot.

        Args:
            order_book: Current order book snapshot

        Returns:
            OrderBookImbalance with EMA-smoothed value
        """
        # Calculate raw OBI from order book
        total_bid_qty = order_book.total_bid_qty
        total_ask_qty = order_book.total_ask_qty
        total_qty = total_bid_qty + total_ask_qty

        if total_qty == 0:
            raw_obi = 0.0
        else:
            raw_obi = (total_bid_qty - total_ask_qty) / total_qty

        self.raw_obi = raw_obi

        # Apply EMA smoothing
        if not self._initialized:
            # First value: initialize EMA to raw value
            self.ema_obi = raw_obi
            self._initialized = True
        else:
            # EMA formula: EMA_t = α × x_t + (1-α) × EMA_(t-1)
            self.ema_obi = self.alpha * raw_obi + \
                (1 - self.alpha) * self.ema_obi

        # Create immutable snapshot
        obi = OrderBookImbalance(
            timestamp=order_book.timestamp,
            symbol=order_book.symbol,
            bid_qty=total_bid_qty,
            ask_qty=total_ask_qty,
            obi_value=self.ema_obi
        )

        # Store in history
        self.history.append(obi)

        return obi

    def get_trend(self, lookback: int = 10) -> float:
        """
        Calculate OBI trend over recent history.

        Args:
            lookback: Number of samples to consider

        Returns:
            Slope of OBI trend (positive = increasing buy pressure)
        """
        if len(self.history) < 2:
            return 0.0

        # Get last N samples
        recent = list(self.history)[-lookback:]
        if len(recent) < 2:
            return 0.0

        # Simple linear regression slope
        n = len(recent)
        sum_x = sum(range(n))
        sum_y = sum(obi.obi_value for obi in recent)
        sum_xy = sum(i * obi.obi_value for i, obi in enumerate(recent))
        sum_x2 = sum(i * i for i in range(n))

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    def get_divergence(self) -> float:
        """
        Calculate divergence between raw and EMA OBI.
        Large divergence may signal regime change.

        Returns:
            Absolute difference between raw and EMA
        """
        return abs(self.raw_obi - self.ema_obi)
