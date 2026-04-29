from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Optional
from enum import Enum

from .order_book import OrderBookSnapshot, OrderBookLevel


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class QueueEstimate:
    """
    Estimated queue position at bid/ask price level.
    Provides probabilistic fill priority assessment.
    """
    timestamp: datetime
    symbol: str
    side: Side
    price_level: float

    # Queue metrics
    volume_ahead: float      # Total volume currently ahead of us
    orders_ahead: int        # Estimated number of orders ahead
    our_position_rank: int   # Estimated rank in queue (1 = front)

    # Fill probability
    fill_probability: float  # [0.0, 1.0] - likelihood of fill
    estimated_wait_volume: float  # Volume needed to fill our order

    @property
    def interpretation(self) -> str:
        """Human-readable interpretation"""
        if self.fill_probability > 0.8:
            return "High fill probability - near front of queue"
        elif self.fill_probability > 0.5:
            return "Moderate fill probability - middle of queue"
        elif self.fill_probability > 0.2:
            return "Low fill probability - back of queue"
        else:
            return "Very low fill probability - unlikely to fill soon"


class QueuePositionEstimator:
    """
    Estimate queue position at bid/ask price level.
    Uses approximate logic based on visible book depth.

    Methodology:
    - Count visible volume at and better than our price level
    - Estimate number of orders based on average order size
    - Calculate fill probability based on queue position
    - Provide conservative (pessimistic) estimates for safety
    """

    def __init__(self, avg_order_size: int = 100):
        """
        Args:
            avg_order_size: Average order size for estimating order count
        """
        self.avg_order_size = avg_order_size

    def estimate_position(
        self,
        order_book: OrderBookSnapshot,
        our_order_qty: int,
        side: Side,
        limit_price: float
    ) -> QueueEstimate:
        """
        Estimate queue position for a hypothetical order at given price level.

        Args:
            order_book: Current order book snapshot
            our_order_qty: Our order quantity
            side: Buy or Sell
            limit_price: Our limit price

        Returns:
            QueueEstimate with fill probability and position metrics
        """
        if side == Side.BUY:
            return self._estimate_buy_position(order_book, our_order_qty, limit_price)
        else:
            return self._estimate_sell_position(order_book, our_order_qty, limit_price)

    def _estimate_buy_position(
        self,
        order_book: OrderBookSnapshot,
        our_order_qty: int,
        limit_price: float
    ) -> QueueEstimate:
        """
        Estimate queue position for buy order.
        Buy orders queue at bid prices (lower is better for seller).
        """
        volume_ahead = 0
        orders_ahead = 0

        # Count volume at better or equal bid prices
        for level in order_book.bids:
            if level.price >= limit_price:
                volume_ahead += level.qty
                orders_ahead += max(1, level.order_count)
            else:
                break  # Bids are sorted descending

        # Subtract our order from volume at this level (we're at the back)
        volume_at_level = sum(
            l.qty for l in order_book.bids if l.price == limit_price)
        our_position_in_level = volume_at_level  # We're at the back of this level

        # Total volume ahead includes all better prices + same price ahead of us
        total_volume_ahead = volume_ahead - our_order_qty + our_position_in_level

        # Estimate wait volume (volume that needs to trade to fill us)
        estimated_wait_volume = total_volume_ahead

        # Calculate fill probability based on queue position
        total_liquidity = order_book.total_ask_qty
        if total_liquidity > 0:
            # Probability decreases as we go deeper in queue
            fill_probability = min(
                1.0, total_liquidity / max(1, total_volume_ahead))
        else:
            fill_probability = 0.0

        # Estimate rank in queue
        our_position_rank = max(
            1, int(total_volume_ahead / self.avg_order_size) + 1)

        return QueueEstimate(
            timestamp=order_book.timestamp,
            symbol=order_book.symbol,
            side=Side.BUY,
            price_level=limit_price,
            volume_ahead=total_volume_ahead,
            orders_ahead=orders_ahead,
            our_position_rank=our_position_rank,
            fill_probability=fill_probability,
            estimated_wait_volume=estimated_wait_volume
        )

    def _estimate_sell_position(
        self,
        order_book: OrderBookSnapshot,
        our_order_qty: int,
        limit_price: float
    ) -> QueueEstimate:
        """
        Estimate queue position for sell order.
        Sell orders queue at ask prices (higher is better for buyer).
        """
        volume_ahead = 0
        orders_ahead = 0

        # Count volume at better or equal ask prices
        for level in order_book.asks:
            if level.price <= limit_price:
                volume_ahead += level.qty
                orders_ahead += max(1, level.order_count)
            else:
                break  # Asks are sorted ascending

        # Subtract our order from volume at this level (we're at the back)
        volume_at_level = sum(
            l.qty for l in order_book.asks if l.price == limit_price)
        our_position_in_level = volume_at_level  # We're at the back of this level

        # Total volume ahead includes all better prices + same price ahead of us
        total_volume_ahead = volume_ahead - our_order_qty + our_position_in_level

        # Estimate wait volume
        estimated_wait_volume = total_volume_ahead

        # Calculate fill probability
        total_liquidity = order_book.total_bid_qty
        if total_liquidity > 0:
            fill_probability = min(
                1.0, total_liquidity / max(1, total_volume_ahead))
        else:
            fill_probability = 0.0

        # Estimate rank in queue
        our_position_rank = max(
            1, int(total_volume_ahead / self.avg_order_size) + 1)

        return QueueEstimate(
            timestamp=order_book.timestamp,
            symbol=order_book.symbol,
            side=Side.SELL,
            price_level=limit_price,
            volume_ahead=total_volume_ahead,
            orders_ahead=orders_ahead,
            our_position_rank=our_position_rank,
            fill_probability=fill_probability,
            estimated_wait_volume=estimated_wait_volume
        )
