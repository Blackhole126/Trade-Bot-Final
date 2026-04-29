from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Deque
from collections import deque


@dataclass(frozen=True)
class Candle:
    """
    OHLC candle for intraday volatility calculation.
    """
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float

    @property
    def range(self) -> float:
        """Candle range (high - low)"""
        return self.high - self.low


@dataclass(frozen=True)
class AtrOutput:
    """
    Average True Range output.
    """
    timestamp: datetime
    true_range: float           # Current true range
    atr_value: float            # Smoothed ATR value

    @property
    def atr_percent(self) -> float:
        """ATR as percentage of price"""
        if self.true_range == 0:
            return 0.0
        return (self.atr_value / self.true_range) * 100


class IntradayATR:
    """
    Calculates Average True Range (ATR) on streaming candle data.

    True Range = max(
        high - low,
        |high - prev_close|,
        |low - prev_close|
    )

    ATR uses Wilder's smoothing method:
    ATR_t = ((ATR_(t-1) × (n-1)) + TR_t) / n

    Usage:
        atr = IntradayATR(period=14)
        for candle in candles:
            output = atr.update(candle)
            print(f"ATR: {output.atr_value:.2f}")
    """

    def __init__(self, period: int = 14):
        """
        Initialize ATR calculator.

        Args:
            period: Number of periods for ATR calculation (default: 14)
        """
        self.period = period
        self._prev_close: Optional[float] = None
        self._atr: Optional[float] = None
        self._true_ranges: Deque[float] = deque(maxlen=period)
        self._initialized = False

    def update(self, candle: Candle) -> AtrOutput:
        """
        Update ATR with a new completed candle.

        Args:
            candle: Completed candle

        Returns:
            AtrOutput with updated ATR value
        """
        # Calculate True Range
        if self._prev_close is None:
            # First candle: TR = high - low
            true_range = candle.high - candle.low
        else:
            # Subsequent candles: TR = max(H-L, |H-prevC|, |L-prevC|)
            tr1 = candle.high - candle.low
            tr2 = abs(candle.high - self._prev_close)
            tr3 = abs(candle.low - self._prev_close)
            true_range = max(tr1, tr2, tr3)

        # Store true range
        self._true_ranges.append(true_range)

        # Calculate ATR using Wilder's smoothing
        if not self._initialized:
            if len(self._true_ranges) >= self.period:
                # Initialize with simple average of first 'period' true ranges
                self._atr = sum(self._true_ranges) / self.period
                self._initialized = True
            else:
                # Not enough data yet
                self._atr = true_range
        else:
            # Wilder's smoothing: ATR_t = ((ATR_(t-1) × (n-1)) + TR_t) / n
            self._atr = ((self._atr * (self.period - 1)) +
                         true_range) / self.period

        # Update previous close
        self._prev_close = candle.close

        return AtrOutput(
            timestamp=candle.timestamp,
            true_range=true_range,
            atr_value=self._atr if self._atr else true_range
        )

    @property
    def current_atr(self) -> Optional[float]:
        """Current ATR value (if initialized)"""
        return self._atr
