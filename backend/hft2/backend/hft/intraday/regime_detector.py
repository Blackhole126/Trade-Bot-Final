from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import List, Optional
import math


class RegimeType(Enum):
    """
    Market regime classification for regime-aware trading.
    """
    TRENDING_UP = "TRENDING_UP"           # Strong upward trend
    TRENDING_DOWN = "TRENDING_DOWN"       # Strong downward trend
    RANGING = "RANGING"                   # Sideways/mean-reverting
    HIGH_VOLATILITY = "HIGH_VOLATILITY"   # High volatility (any direction)
    EXTREME_VOLATILITY = "EXTREME_VOLATILITY"  # Extreme moves - halt trading
    UNKNOWN = "UNKNOWN"                   # Insufficient data


@dataclass(frozen=True)
class MarketRegime:
    """
    Classified market regime at a specific timestamp.
    """
    timestamp: datetime
    symbol: str
    regime: RegimeType
    confidence: float               # [0.0, 1.0] classification confidence
    basis_explanation: str          # Human-readable explanation

    @property
    def should_halt_trading(self) -> bool:
        """Check if regime suggests halting trading"""
        return self.regime == RegimeType.EXTREME_VOLATILITY

    @property
    def is_trending(self) -> bool:
        """Check if market is trending"""
        return self.regime in [RegimeType.TRENDING_UP, RegimeType.TRENDING_DOWN]

    @property
    def is_ranging(self) -> bool:
        """Check if market is ranging"""
        return self.regime == RegimeType.RANGING


class RegimeDetector:
    """
    Deterministic regime classifier based on technical thresholds.
    No ML, purely rule-based with explainable logic.

    Classification Logic:
    1. Check volatility first (HIGH_VOL, EXTREME_VOL override trends)
    2. Check trend strength (slope of price movement)
    3. Default to RANGING if no strong signal

    Usage:
        detector = RegimeDetector()
        for tick in ticks:
            regime = detector.update(timestamp, tick.price, volatility, lookback_prices)
            print(f"Regime: {regime.regime.value} ({regime.confidence:.0%})")
    """

    # Thresholds (configurable)
    VOLATILITY_HIGH_THRESHOLD = 0.015      # 1.5% daily vol
    VOLATILITY_EXTREME_THRESHOLD = 0.03    # 3% daily vol
    TREND_STRENGTH_THRESHOLD = 0.02        # 2% move over lookback
    RANGE_BOUNDARY = 0.005                 # 0.5% for ranging detection

    def __init__(self, lookback_period: int = 20):
        """
        Initialize regime detector.

        Args:
            lookback_period: Number of periods for trend calculation
        """
        self.lookback_period = lookback_period
        self._price_history: List[float] = []
        self._last_regime: Optional[MarketRegime] = None

    def update(
        self,
        timestamp: datetime,
        symbol: str,
        price: float,
        volatility: float,
        lookback_prices: Optional[List[float]] = None
    ) -> MarketRegime:
        """
        Classify market regime based on current conditions.

        Args:
            timestamp: Current timestamp
            symbol: Trading symbol
            price: Current price
            volatility: Current volatility estimate (from GARCH/ATR)
            lookback_prices: Historical prices for trend calc (optional)

        Returns:
            MarketRegime with classification and explanation
        """
        # Update price history
        self._price_history.append(price)
        if len(self._price_history) > self.lookback_period * 2:
            self._price_history.pop(0)

        # Use provided lookback or internal history
        prices = lookback_prices if lookback_prices else self._price_history

        # 1. Check volatility first (highest priority)
        if volatility >= self.VOLATILITY_EXTREME_THRESHOLD:
            return MarketRegime(
                timestamp=timestamp,
                symbol=symbol,
                regime=RegimeType.EXTREME_VOLATILITY,
                confidence=min(
                    volatility / self.VOLATILITY_EXTREME_THRESHOLD, 1.0),
                basis_explanation=f"Extreme volatility: {volatility:.2%} (threshold: {self.VOLATILITY_EXTREME_THRESHOLD:.2%})"
            )

        if volatility >= self.VOLATILITY_HIGH_THRESHOLD:
            return MarketRegime(
                timestamp=timestamp,
                symbol=symbol,
                regime=RegimeType.HIGH_VOLATILITY,
                confidence=min(
                    volatility / self.VOLATILITY_HIGH_THRESHOLD, 1.0),
                basis_explanation=f"High volatility: {volatility:.2%} (threshold: {self.VOLATILITY_HIGH_THRESHOLD:.2%})"
            )

        # 2. Check trend strength
        if len(prices) >= self.lookback_period:
            trend_slope = self._calculate_trend_slope(
                prices[-self.lookback_period:])

            if abs(trend_slope) >= self.TREND_STRENGTH_THRESHOLD:
                if trend_slope > 0:
                    return MarketRegime(
                        timestamp=timestamp,
                        symbol=symbol,
                        regime=RegimeType.TRENDING_UP,
                        confidence=min(abs(trend_slope) /
                                       self.TREND_STRENGTH_THRESHOLD, 0.9),
                        basis_explanation=f"Strong uptrend: slope {trend_slope:.2%} over {self.lookback_period} periods"
                    )
                else:
                    return MarketRegime(
                        timestamp=timestamp,
                        symbol=symbol,
                        regime=RegimeType.TRENDING_DOWN,
                        confidence=min(abs(trend_slope) /
                                       self.TREND_STRENGTH_THRESHOLD, 0.9),
                        basis_explanation=f"Strong downtrend: slope {trend_slope:.2%} over {self.lookback_period} periods"
                    )

        # 3. Default: RANGING
        return MarketRegime(
            timestamp=timestamp,
            symbol=symbol,
            regime=RegimeType.RANGING,
            confidence=0.8,
            basis_explanation="Low volatility, no clear trend - range-bound market"
        )

    def _calculate_trend_slope(self, prices: List[float]) -> float:
        """
        Calculate trend slope using linear regression.

        Args:
            prices: List of prices (oldest to newest)

        Returns:
            Slope as percentage change from start to end
        """
        if len(prices) < 2:
            return 0.0

        # Simple slope: (end - start) / start
        start_price = prices[0]
        end_price = prices[-1]

        if start_price == 0:
            return 0.0

        slope = (end_price - start_price) / start_price
        return slope

    @property
    def current_regime(self) -> Optional[MarketRegime]:
        """Last classified regime"""
        return self._last_regime
