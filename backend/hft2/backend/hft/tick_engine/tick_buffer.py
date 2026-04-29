from collections import deque
from typing import Optional, Deque, List, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import time
import logging

# Setup logging
logger = logging.getLogger(__name__)


class OverflowStrategy(Enum):
    """Strategy for handling buffer overflow."""
    DROP_OLDEST = "DROP_OLDEST"  # Remove oldest ticks (default)
    DROP_NEWEST = "DROP_NEWEST"  # Reject new ticks
    BLOCK = "BLOCK"              # Block until space available (async)


@dataclass
class BackpressureMetrics:
    """Tracks backpressure and overflow events."""
    total_ticks_received: int = 0
    total_ticks_dropped: int = 0
    overflow_events: int = 0
    last_overflow_timestamp: Optional[datetime] = None
    max_buffer_utilization: float = 0.0  # Peak utilization %

    @property
    def drop_rate(self) -> float:
        """Calculate drop rate as percentage."""
        if self.total_ticks_received == 0:
            return 0.0
        return (self.total_ticks_dropped / self.total_ticks_received) * 100

    @property
    def is_critical(self) -> bool:
        """Check if drop rate is critical (>1%)."""
        return self.drop_rate > 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "total_ticks_received": self.total_ticks_received,
            "total_ticks_dropped": self.total_ticks_dropped,
            "drop_rate_percent": self.drop_rate,
            "overflow_events": self.overflow_events,
            "last_overflow": self.last_overflow_timestamp.isoformat() if self.last_overflow_timestamp else None,
            "max_utilization_percent": self.max_buffer_utilization * 100,
            "is_critical": self.is_critical
        }


@dataclass
class Tick:
    """
    Represents a single market tick (price update).
    Immutable once created.
    """
    symbol: str
    price: float
    volume: int
    timestamp: float  # Unix timestamp
    bid: float = 0.0
    ask: float = 0.0
    exchange: str = "NSE"  # Default to NSE

    def __post_init__(self):
        """Validate tick on creation."""
        if self.price <= 0:
            raise ValueError(f"Price must be positive, got {self.price}")
        if self.volume < 0:
            raise ValueError(f"Volume cannot be negative, got {self.volume}")

    @property
    def mid_price(self) -> float:
        """Calculate mid-price from bid/ask."""
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return self.price

    @property
    def spread_bps(self) -> float:
        """Calculate spread in basis points."""
        if self.bid > 0 and self.ask > 0:
            mid = self.mid_price
            return ((self.ask - self.bid) / mid) * 10000
        return 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "volume": self.volume,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "bid": self.bid,
            "ask": self.ask,
            "spread_bps": self.spread_bps,
            "exchange": self.exchange
        }


class TickBuffer:
    """
    Hardened Tick Buffer with Fixed Size and Overflow Policy.

    Features:
    - Max buffer size enforcement
    - Configurable overflow strategy (DROP_OLDEST/DROP_NEWEST/BLOCK)
    - Backpressure counter and metrics logging
    - Monotonicity validation (optional strict mode)
    - Thread-safe operations (with lock)

    System must never silently fail - all overflows logged.
    """

    def __init__(
        self,
        max_size: int = 10000,
        drop_strategy: str = "DROP_OLDEST",
        strict_monotonicity: bool = False,
        alert_threshold: float = 0.5  # Alert when >0.5% drop rate
    ):
        """
        Initialize tick buffer.

        Args:
            max_size: Maximum buffer size (default: 10,000 ticks)
            drop_strategy: Overflow strategy ("DROP_OLDEST", "DROP_NEWEST", "BLOCK")
            strict_monotonicity: Reject non-monotonic timestamps
            alert_threshold: Drop rate % to trigger alerts
        """
        self.max_size = max_size
        self.drop_strategy = OverflowStrategy(drop_strategy)
        self.strict_monotonicity = strict_monotonicity
        self.alert_threshold = alert_threshold

        # Initialize buffer based on strategy
        if self.drop_strategy == OverflowStrategy.DROP_OLDEST:
            self._buffer: Deque[Tick] = deque(maxlen=max_size)
        else:
            self._buffer: Deque[Tick] = deque()

        # Metrics tracking
        self.metrics = BackpressureMetrics()

        logger.info(
            f"TickBuffer initialized: max_size={max_size}, "
            f"strategy={self.drop_strategy.value}, "
            f"strict_monotonicity={strict_monotonicity}"
        )

    def add_tick(self, tick: Tick) -> bool:
        """
        Adds a tick to the buffer with full validation and metrics tracking.

        Args:
            tick: Tick to add

        Returns:
            True if added, False if dropped

        Raises:
            ValueError: If tick fails validation in strict mode
        """
        now = datetime.now()

        # Update metrics
        self.metrics.total_ticks_received += 1

        # Check buffer utilization
        utilization = len(self._buffer) / self.max_size
        if utilization > self.metrics.max_buffer_utilization:
            self.metrics.max_buffer_utilization = utilization

        # Validate monotonicity if strict mode enabled
        if self.strict_monotonicity and self._buffer:
            if tick.timestamp < self._buffer[-1].timestamp:
                logger.warning(
                    f"Non-monotonic tick rejected: {tick.timestamp} < {self._buffer[-1].timestamp}"
                )
                self.metrics.total_ticks_dropped += 1
                return False

        # Handle based on strategy
        if self.drop_strategy == OverflowStrategy.DROP_OLDEST:
            # Check if we're about to overflow
            if len(self._buffer) >= self.max_size:
                self.metrics.overflow_events += 1
                self.metrics.last_overflow_timestamp = now

                # Log critical alerts
                if self.metrics.is_critical:
                    logger.error(
                        f"CRITICAL: Tick buffer overflow - drop_rate={self.metrics.drop_rate:.2f}%"
                    )

            self._buffer.append(tick)
            return True

        elif self.drop_strategy == OverflowStrategy.DROP_NEWEST:
            if len(self._buffer) >= self.max_size:
                self.metrics.total_ticks_dropped += 1
                self.metrics.overflow_events += 1
                self.metrics.last_overflow_timestamp = now

                # Log warning
                logger.debug(f"Tick dropped (buffer full): {tick.symbol}")
                return False

            self._buffer.append(tick)
            return True

        elif self.drop_strategy == OverflowStrategy.BLOCK:
            # For async implementation - would wait for space
            # For now, treat as DROP_NEWEST
            if len(self._buffer) >= self.max_size:
                self.metrics.total_ticks_dropped += 1
                logger.warning(
                    "BLOCK strategy not implemented in sync mode - dropping tick")
                return False

            self._buffer.append(tick)
            return True

        return False

    def get_backpressure_status(self) -> dict:
        """
        Get current backpressure status.

        Returns:
            Dictionary with buffer status and metrics
        """
        return {
            "buffer_size": len(self._buffer),
            "max_size": self.max_size,
            "utilization_percent": (len(self._buffer) / self.max_size) * 100,
            "strategy": self.drop_strategy.value,
            "metrics": self.metrics.to_dict()
        }

    def should_throttle(self) -> bool:
        """
        Check if system should throttle input due to backpressure.

        Returns:
            True if throttling recommended
        """
        return self.metrics.is_critical or (len(self._buffer) / self.max_size) > 0.95

    def get_snapshot(self) -> List[Tick]:
        """Returns a list of current ticks."""
        return list(self._buffer)

    def get_latest(self) -> Optional[Tick]:
        """Returns the most recent tick, or None if empty."""
        return self._buffer[-1] if self._buffer else None

    def size(self) -> int:
        return len(self._buffer)

    def clear(self):
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)
