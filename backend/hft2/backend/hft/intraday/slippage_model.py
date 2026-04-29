from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
from enum import Enum


class RegimeType(Enum):
    """Market regime types for regime-aware slippage"""
    RANGING = "RANGING"
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    EXTREME_VOLATILITY = "EXTREME_VOLATILITY"


@dataclass(frozen=True)
class SlippageEstimate:
    """
    Comprehensive slippage estimate with multiple components.
    All values in basis points (bps) for consistency.
    """
    timestamp: datetime
    symbol: str
    trade_size: int
    side: str  # 'BUY' or 'SELL'

    # Slippage components (all in bps)
    base_slippage_bps: float        # Base slippage from spread
    volatility_adjustment: float    # Additional slippage from volatility
    volume_impact: float            # Impact from order size vs market volume
    regime_multiplier: float        # Multiplier based on market regime

    # Total impact
    total_slippage_bps: float       # Final slippage in bps
    estimated_cost: float           # Absolute cost in currency units

    # Confidence
    confidence_score: float         # 0.0 to 1.0

    @property
    def explanation(self) -> str:
        """Human-readable explanation"""
        return (
            f"Total slippage: {self.total_slippage_bps:.2f}bps (" +
            f"base={self.base_slippage_bps:.1f}, " +
            f"vol_adj={self.volatility_adjustment:.1f}, " +
            f"vol_impact={self.volume_impact:.1f}) × " +
            f"regime_mult={self.regime_multiplier:.2f}"
        )


class RegimeAwareSlippageModel:
    """
    Regime-aware slippage model for realistic fill simulation.

    Components:
    1. Base slippage: Half the bid-ask spread (cost of crossing spread)
    2. Volatility adjustment: Additional slippage during high volatility
    3. Volume impact: Price impact based on order size relative to market volume
    4. Regime multiplier: Adjusts all components based on market state

    Indian Market Considerations:
    - Accounts for lower liquidity in mid-cap stocks
    - Higher slippage during market open/close
    - Increased slippage during news events (captured via volatility)
    """

    # Regime multipliers - increase slippage in volatile/trending markets
    REGIME_MULTIPLIERS: Dict[RegimeType, float] = {
        RegimeType.RANGING: 1.0,      # Normal conditions
        RegimeType.TRENDING_UP: 1.3,  # Higher slippage in trends
        RegimeType.TRENDING_DOWN: 1.3,
        RegimeType.HIGH_VOLATILITY: 2.0,  # Double slippage
        RegimeType.EXTREME_VOLATILITY: 3.5  # Extreme caution
    }

    def __init__(
        self,
        default_avg_volume: int = 10000,
        volume_impact_factor: float = 0.0001,
        volatility_sensitivity: float = 0.5
    ):
        """
        Args:
            default_avg_volume: Default average volume if not provided
            volume_impact_factor: How much order size impacts price
            volatility_sensitivity: Sensitivity to volatility changes
        """
        self.default_avg_volume = default_avg_volume
        self.volume_impact_factor = volume_impact_factor
        self.volatility_sensitivity = volatility_sensitivity
        self.current_regime = RegimeType.RANGING

    def update_regime(self, regime: RegimeType):
        """Update current market regime"""
        self.current_regime = regime

    def estimate_slippage(
        self,
        timestamp: datetime,
        symbol: str,
        order_size: int,
        side: str,
        spread_bps: float,
        current_volatility: float,
        avg_volume: Optional[int] = None,
        limit_price: Optional[float] = None
    ) -> SlippageEstimate:
        """
        Estimate comprehensive slippage for a hypothetical order.

        Args:
            timestamp: Order timestamp
            symbol: Trading symbol
            order_size: Order quantity
            side: 'BUY' or 'SELL'
            spread_bps: Current bid-ask spread in basis points
            current_volatility: Current volatility (e.g., from GARCH/ATR)
            avg_volume: Average daily volume (uses default if None)
            limit_price: Limit price for absolute cost calculation

        Returns:
            SlippageEstimate with detailed breakdown
        """
        # Use provided volume or default
        effective_avg_volume = avg_volume or self.default_avg_volume

        # 1. Base slippage: half the spread (crossing cost)
        base_slippage_bps = spread_bps / 2.0

        # 2. Volatility adjustment: higher vol = more adverse selection
        # Normalize volatility (assume typical vol ~0.01-0.02)
        normalized_vol = current_volatility / 0.015
        volatility_adjustment = normalized_vol * self.volatility_sensitivity * 1.0

        # 3. Volume impact: larger orders move the market more
        volume_ratio = order_size / max(1, effective_avg_volume)
        volume_impact = min(
            volume_ratio * self.volume_impact_factor * 100, 5.0)  # Cap at 5 bps

        # 4. Regime multiplier
        regime_multiplier = self.REGIME_MULTIPLIERS.get(
            self.current_regime, 1.0)

        # Calculate total slippage
        base_component = (base_slippage_bps +
                          volatility_adjustment + volume_impact)
        total_slippage_bps = base_component * regime_multiplier

        # Calculate absolute cost
        reference_price = limit_price if limit_price else 100.0  # Default if no price
        estimated_cost = (total_slippage_bps / 10000) * \
            reference_price * order_size

        # Confidence score (lower in extreme regimes)
        confidence_scores = {
            RegimeType.RANGING: 0.9,
            RegimeType.TRENDING_UP: 0.8,
            RegimeType.TRENDING_DOWN: 0.8,
            RegimeType.HIGH_VOLATILITY: 0.6,
            RegimeType.EXTREME_VOLATILITY: 0.4
        }
        confidence_score = confidence_scores.get(self.current_regime, 0.7)

        return SlippageEstimate(
            timestamp=timestamp,
            symbol=symbol,
            trade_size=order_size,
            side=side,
            base_slippage_bps=base_slippage_bps,
            volatility_adjustment=volatility_adjustment,
            volume_impact=volume_impact,
            regime_multiplier=regime_multiplier,
            total_slippage_bps=total_slippage_bps,
            estimated_cost=estimated_cost,
            confidence_score=confidence_score
        )

    def estimate_market_order_slippage(
        self,
        timestamp: datetime,
        symbol: str,
        order_size: int,
        side: str,
        spread_bps: float,
        current_volatility: float,
        avg_volume: Optional[int] = None
    ) -> SlippageEstimate:
        """
        Specialized estimator for market orders (guaranteed fill, worse slippage).
        Applies additional penalty for immediate execution.
        """
        # Get base estimate
        estimate = self.estimate_slippage(
            timestamp=timestamp,
            symbol=symbol,
            order_size=order_size,
            side=side,
            spread_bps=spread_bps,
            current_volatility=current_volatility,
            avg_volume=avg_volume
        )

        # Market orders pay full spread + urgency penalty
        urgency_penalty_bps = 0.5  # Additional 0.5 bps for immediacy

        # Recalculate with urgency penalty
        adjusted_base = estimate.base_slippage_bps + urgency_penalty_bps
        adjusted_total = (adjusted_base + estimate.volatility_adjustment +
                          estimate.volume_impact) * estimate.regime_multiplier

        # Create new estimate with adjustments
        return SlippageEstimate(
            timestamp=estimate.timestamp,
            symbol=estimate.symbol,
            trade_size=estimate.trade_size,
            side=estimate.side,
            base_slippage_bps=adjusted_base,
            volatility_adjustment=estimate.volatility_adjustment,
            volume_impact=estimate.volume_impact,
            regime_multiplier=estimate.regime_multiplier,
            total_slippage_bps=adjusted_total,
            estimated_cost=(adjusted_total / 10000) *
            100.0 * order_size,  # Approximate
            confidence_score=estimate.confidence_score
        )
