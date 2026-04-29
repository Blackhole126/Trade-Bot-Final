"""
Liquidity-Aware Slippage Model

Replaces simple slippage with realistic volume-impact modeling.
Simulates partial fills and price drift across fill fragments.

Shadow-only. Deterministic. Auditable.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple, Deque
from collections import deque
import math


@dataclass(frozen=True)
class LiquidityEstimate:
    """Estimated market liquidity at current price level."""
    timestamp: datetime
    symbol: str
    bid_liquidity: float      # Estimated volume available at bid
    ask_liquidity: float      # Estimated volume available at ask
    spread_bps: float         # Current spread
    volatility: float         # Current volatility estimate

    @property
    def avg_liquidity(self) -> float:
        return (self.bid_liquidity + self.liquidity) / 2


@dataclass(frozen=True)
class SlippageComponent:
    """Individual slippage component for transparency."""
    base_slippage_bps: float      # Half spread (crossing cost)
    volume_impact_bps: float      # Order size vs liquidity
    volatility_adjustment_bps: float  # Volatility premium
    regime_multiplier: float      # Regime-based adjustment
    random_jitter_bps: float      # Microstructure noise (deterministic seed)

    @property
    def total_slippage_bps(self) -> float:
        """Calculate total slippage."""
        return (
            self.base_slippage_bps +
            self.volume_impact_bps +
            self.volatility_adjustment_bps
        ) * self.regime_multiplier + self.random_jitter_bps


@dataclass
class FillFragment:
    """
    Individual fill fragment for partial fill simulation.
    Multiple fragments comprise a complete order fill.
    """
    fragment_id: int
    fill_timestamp: datetime
    fill_price: float
    fill_quantity: float
    remaining_quantity: float  # Still to be filled
    slippage_bps: float
    liquidity_consumed: float  # How much liquidity this fragment consumed


class LiquidityAwareSlippageModel:
    """
    Advanced slippage model with liquidity awareness.

    Slippage Formula:
    slippage = f(volume_ratio, spread, volatility)

    Where:
    - volume_ratio = order_size / estimated_liquidity
    - spread = bid-ask spread (crossing cost)
    - volatility = price uncertainty premium

    Partial Fill Simulation:
    - Large orders split into chunks
    - Each chunk consumes liquidity
    - Price drifts as liquidity consumed
    - Deterministic (seeded randomness)
    """

    # Model parameters (configurable)
    DEFAULT_LIQUIDITY_ESTIMATE = 10000  # Shares
    VOLUME_IMPACT_EXPONENT = 1.5  # Non-linear impact
    VOLATILITY_SENSITIVITY = 0.5
    RANDOM_SEED = 42  # For deterministic jitter

    def __init__(
        self,
        default_liquidity: float = None,
        volume_impact_exp: float = None,
        vol_sensitivity: float = None
    ):
        """
        Initialize liquidity-aware slippage model.

        Args:
            default_liquidity: Default liquidity estimate if not provided
            volume_impact_exp: Exponent for volume impact (non-linearity)
            vol_sensitivity: Sensitivity to volatility changes
        """
        self.default_liquidity = default_liquidity or self.DEFAULT_LIQUIDITY_ESTIMATE
        self.volume_impact_exp = volume_impact_exp or self.VOLUME_IMPACT_EXPONENT
        self.vol_sensitivity = vol_sensitivity or self.VOLATILITY_SENSITIVITY

        # State tracking
        self._liquidity_history: Deque[LiquidityEstimate] = deque(maxlen=100)

    def estimate_liquidity(
        self,
        symbol: str,
        timestamp: datetime,
        bid_qty: float,
        ask_qty: float,
        spread_bps: float,
        volatility: float
    ) -> LiquidityEstimate:
        """
        Estimate market liquidity from order book.

        Args:
            symbol: Trading symbol
            timestamp: Current time
            bid_qty: Total bid quantity
            ask_qty: Total ask quantity
            spread_bps: Spread in basis points
            volatility: Current volatility estimate

        Returns:
            LiquidityEstimate object
        """
        # Simple estimate: use visible book depth
        # In production, would use historical volume profiles
        est = LiquidityEstimate(
            timestamp=timestamp,
            symbol=symbol,
            bid_liquidity=bid_qty,
            ask_liquidity=ask_qty,
            spread_bps=spread_bps,
            volatility=volatility
        )

        self._liquidity_history.append(est)
        return est

    def calculate_slippage_components(
        self,
        order_size: float,
        spread_bps: float,
        volatility: float,
        liquidity: Optional[float] = None,
        regime_multiplier: float = 1.0,
        deterministic_seed: int = 0
    ) -> SlippageComponent:
        """
        Calculate detailed slippage components with ZERO RANDOMNESS.

        DETERMINISTIC FORMULA:
        slippage_bps = (base_spread + volume_impact + volatility_adjustment) * regime_multiplier

        Where:
        - base_spread = spread_bps / 2.0 (crossing cost)
        - volume_impact = k * volume_ratio^exponent
        - volatility_adjustment = normalized_vol * sensitivity

        Same inputs ALWAYS produce same output. NO EXCEPTIONS.

        Args:
            order_size: Order quantity
            spread_bps: Current spread
            volatility: Current volatility
            liquidity: Available liquidity (uses default if None)
            regime_multiplier: Regime adjustment
            deterministic_seed: For reproducibility (NOT randomness)

        Returns:
            SlippageComponent with breakdown
        """
        effective_liquidity = liquidity or self.default_liquidity

        # 1. Base slippage: half the spread (crossing cost) - DETERMINISTIC
        base_slippage_bps = spread_bps / 2.0

        # 2. Volume impact: non-linear function of order size vs liquidity - DETERMINISTIC
        volume_ratio = order_size / max(effective_liquidity, 1.0)
        volume_impact_bps = (
            volume_ratio ** self.volume_impact_exp) * 10.0  # Scale factor

        # Cap volume impact at reasonable level (50 bps max) - DETERMINISTIC
        volume_impact_bps = min(volume_impact_bps, 50.0)

        # 3. Volatility adjustment: higher vol = more adverse selection risk - DETERMINISTIC
        normalized_vol = volatility / 0.015  # Normalize to typical 1.5% daily vol
        volatility_adjustment_bps = normalized_vol * self.vol_sensitivity * 2.0

        # 4. NO RANDOM JITTER - removed for determinism
        # Instead use microstructure noise based on order properties (deterministic)
        # This creates consistent "noise" pattern based on order characteristics
        microstructure_noise_bps = (
            (order_size % 100) / 100.0) * 0.5  # 0-0.5 bps based on qty

        return SlippageComponent(
            base_slippage_bps=base_slippage_bps,
            volume_impact_bps=volume_impact_bps,
            volatility_adjustment_bps=volatility_adjustment_bps,
            regime_multiplier=regime_multiplier,
            # Actually deterministic based on order_size
            random_jitter_bps=microstructure_noise_bps
        )

    def simulate_partial_fills(
        self,
        order_size: float,
        side: str,
        base_price: float,
        spread_bps: float,
        volatility: float,
        liquidity: Optional[float] = None,
        regime_multiplier: float = 1.0,
        max_fragments: int = 5
    ) -> List[FillFragment]:
        """
        Simulate partial fills for large orders.

        Large orders consume liquidity progressively, causing price drift.

        Args:
            order_size: Total order quantity
            side: BUY or SELL
            base_price: Starting price (mid or best)
            spread_bps: Current spread
            volatility: Current volatility
            liquidity: Available liquidity at best price
            regime_multiplier: Regime adjustment
            max_fragments: Maximum number of fill fragments

        Returns:
            List of FillFragment objects
        """
        effective_liquidity = liquidity or self.default_liquidity

        # Determine optimal fragment size
        # Rule: Don't consume more than 20% of liquidity per fragment
        max_fragment_size = effective_liquidity * 0.2
        num_fragments = min(max_fragments, math.ceil(
            order_size / max_fragment_size))

        fragment_size = order_size / num_fragments

        fragments = []
        remaining_qty = order_size
        current_price = base_price
        timestamp = datetime.now()

        for i in range(num_fragments):
            # Calculate fill quantity for this fragment
            fill_qty = min(fragment_size, remaining_qty)

            # Calculate slippage for this fragment
            slippage_components = self.calculate_slippage_components(
                order_size=fill_qty,
                spread_bps=spread_bps,
                volatility=volatility,
                liquidity=effective_liquidity,
                regime_multiplier=regime_multiplier,
                deterministic_seed=i  # Different seed per fragment
            )

            slippage_bps = slippage_components.total_slippage_bps

            # Apply slippage to get fill price
            if side == "BUY":
                fill_price = current_price * (1 + slippage_bps / 10000.0)
            else:
                fill_price = current_price * (1 - slippage_bps / 10000.0)

            # Create fragment
            fragment = FillFragment(
                fragment_id=i,
                fill_timestamp=timestamp,
                fill_price=fill_price,
                fill_quantity=fill_qty,
                remaining_quantity=remaining_qty - fill_qty,
                slippage_bps=slippage_bps,
                liquidity_consumed=fill_qty
            )

            fragments.append(fragment)

            # Update for next fragment
            remaining_qty -= fill_qty
            effective_liquidity -= fill_qty  # Consume liquidity

            # Price drift: as liquidity consumed, worse prices available
            if effective_liquidity > 0:
                drift_factor = 1 + \
                    (order_size - remaining_qty) / order_size * 0.001
                current_price *= drift_factor

        return fragments

    def calculate_vwap(self, fragments: List[FillFragment]) -> float:
        """
        Calculate volume-weighted average price from fill fragments.

        Args:
            fragments: List of fill fragments

        Returns:
            VWAP price
        """
        if not fragments:
            return 0.0

        total_value = sum(f.fill_price * f.fill_quantity for f in fragments)
        total_volume = sum(f.fill_quantity for f in fragments)

        if total_volume == 0:
            return 0.0

        return total_value / total_volume

    def estimate_market_impact(
        self,
        order_size: float,
        side: str,
        liquidity: float,
        spread_bps: float,
        volatility: float
    ) -> Tuple[float, float]:
        """
        Estimate permanent and temporary market impact.

        Permanent impact: Price doesn't fully revert after trade
        Temporary impact: Short-term price pressure that reverts

        Args:
            order_size: Order quantity
            side: BUY or SELL
            liquidity: Market liquidity
            spread_bps: Spread
            volatility: Volatility

        Returns:
            (permanent_impact_bps, temporary_impact_bps)
        """
        volume_ratio = order_size / max(liquidity, 1)

        # Permanent impact: ~40% of total impact (academic studies)
        permanent_impact_bps = (volume_ratio ** 1.0) * 5  # Linear

        # Temporary impact: ~60% of total impact
        temporary_impact_bps = (volume_ratio ** 1.5) * 8  # Non-linear

        return permanent_impact_bps, temporary_impact_bps


__all__ = [
    'LiquidityEstimate',
    'SlippageComponent',
    'FillFragment',
    'LiquidityAwareSlippageModel'
]
