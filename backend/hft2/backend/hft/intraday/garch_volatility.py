from dataclasses import dataclass
from datetime import datetime
from typing import List, Deque, Optional
from collections import deque
import math


@dataclass(frozen=True)
class GarchOutput:
    """
    GARCH(1,1) volatility estimate output.
    """
    timestamp: datetime
    returns_sq: float               # Squared return (shock)
    conditional_variance: float     # σ²_t (conditional variance)
    annualized_volatility: float    # sqrt(variance) * sqrt(252) * 100 (%)

    @property
    def daily_volatility(self) -> float:
        """Daily volatility in percent"""
        return math.sqrt(self.conditional_variance) * 100


class GarchVolatility:
    """
    Real-time GARCH(1,1) volatility estimator using pre-fitted parameters.

    Model:
    σ²_t = ω + α × ε²_(t-1) + β × σ²_(t-1)

    Where:
    - ω (omega): Constant term (long-run average variance component)
    - α (alpha): ARCH term (news impact - last period's shock)
    - β (beta): GARCH term (persistence - last period's variance)
    - α + β < 1 for stationarity (typically α + β ≈ 0.95-0.99)

    Typical Parameters (daily equity):
    - ω = 0.000002
    - α = 0.08  (8% of last shock)
    - β = 0.91  (91% persistence)

    Usage:
        garch = GarchVolatility(omega=0.000002, alpha=0.08, beta=0.91)
        for return in returns:
            output = garch.update(timestamp, return)
            print(f"Volatility: {output.annualized_volatility:.2f}%")
    """

    # Default GARCH(1,1) parameters for Indian equities (daily)
    DEFAULT_OMEGA = 0.000002  # Constant term
    DEFAULT_ALPHA = 0.08      # ARCH term (news impact)
    DEFAULT_BETA = 0.91       # GARCH term (persistence)

    def __init__(
        self,
        omega: float = DEFAULT_OMEGA,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        long_term_variance: Optional[float] = None,
        window: int = 100
    ):
        """
        Initialize GARCH model.

        Args:
            omega: Constant term in variance equation
            alpha: ARCH term coefficient (news impact)
            beta: GARCH term coefficient (persistence)
            long_term_variance: Initial variance estimate (uses sample if None)
            window: Number of returns to store for initialization
        """
        # Validate stationarity condition
        if alpha + beta >= 1.0:
            raise ValueError(
                f"GARCH stationarity violated: alpha({alpha}) + beta({beta}) >= 1.0")

        self.omega = omega
        self.alpha = alpha
        self.beta = beta
        self.window = window

        # Storage for returns (for computing initial variance)
        self.returns: Deque[float] = deque(maxlen=window)

        # State variables
        self._last_variance = long_term_variance if long_term_variance else None
        self._last_return_sq = 0.0
        self._initialized = long_term_variance is not None

    def update(self, timestamp: datetime, current_return: float) -> GarchOutput:
        """
        Update GARCH estimate with new return.

        Args:
            timestamp: Observation timestamp
            current_return: Return in decimal (e.g., 0.01 for 1%)

        Returns:
            GarchOutput with updated volatility estimate
        """
        # Store return
        self.returns.append(current_return)

        # Square of current return (shock)
        return_sq = current_return ** 2
        self._last_return_sq = return_sq

        # Initialize variance if not done
        if not self._initialized and len(self.returns) >= self.window:
            # Use sample variance as initial estimate
            returns_list = list(self.returns)
            mean_return = sum(returns_list) / len(returns_list)
            sample_variance = sum(
                (r - mean_return) ** 2 for r in returns_list) / (len(returns_list) - 1)
            self._last_variance = sample_variance
            self._initialized = True
        elif not self._initialized:
            # Not enough data yet - use unconditional variance
            self._last_variance = self.omega / (1 - self.alpha - self.beta)

        # GARCH(1,1) update formula
        # σ²_t = ω + α × ε²_(t-1) + β × σ²_(t-1)
        new_variance = (
            self.omega +
            self.alpha * self._last_return_sq +
            self.beta * self._last_variance
        )

        # Ensure non-negative variance
        new_variance = max(new_variance, 0.0)
        self._last_variance = new_variance

        # Annualize: sqrt(variance) * sqrt(252) * 100 (to percent)
        annualized_vol = math.sqrt(new_variance) * math.sqrt(252) * 100

        return GarchOutput(
            timestamp=timestamp,
            returns_sq=return_sq,
            conditional_variance=new_variance,
            annualized_volatility=annualized_vol
        )

    @property
    def current_volatility(self) -> Optional[float]:
        """Current annualized volatility (if initialized)"""
        if not self._initialized:
            return None
        return math.sqrt(self._last_variance) * math.sqrt(252) * 100

    @property
    def unconditional_variance(self) -> float:
        """
        Long-run unconditional variance (ω / (1 - α - β)).
        Volatility reverts to this mean over time.
        """
        return self.omega / (1 - self.alpha - self.beta)
