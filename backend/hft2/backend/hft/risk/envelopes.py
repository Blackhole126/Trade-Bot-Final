from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Deque
from collections import deque
from enum import Enum


class RiskStopReason(Enum):
    """Reasons for risk gate rejection."""
    MAX_TRADES_MINUTE = "MAX_TRADES_PER_MINUTE"
    MAX_LOSS_MINUTE = "MAX_LOSS_PER_MINUTE"
    POSITION_SIZE_CAP = "POSITION_SIZE_EXCEEDED"
    GROSS_EXPOSURE_LIMIT = "GROSS_EXPOSURE_EXCEEDED"
    MAX_DRAWDOWN_SESSION = "MAX_DRAWDOWN_REACHED"
    EXTREME_VOLATILITY = "EXTREME_VOLATILITY_REGIME"
    SHADOW_MODE_ONLY = "SHADOW_MODE_NO_LIVE_TRADING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RiskConstraints:
    """
    Hard risk limits that cannot be exceeded.
    All limits are enforced per-symbol unless noted.
    """
    max_trades_per_minute: int          # Max trades per minute (any symbol)
    max_loss_per_minute: float          # Max loss per minute (₹)
    max_position_size: float            # Max position size (shares)
    max_gross_exposure: float           # Max total exposure (₹)
    max_drawdown_session: float         # Max session drawdown (₹)

    @property
    def summary(self) -> str:
        """Human-readable summary of constraints."""
        return (
            f"Max {self.max_trades_per_minute} trades/min | "
            f"Max loss ₹{self.max_loss_per_minute}/min | "
            f"Max position {self.max_position_size:.0f} shares | "
            f"Max exposure ₹{self.max_gross_exposure:,.0f}"
        )


@dataclass
class RiskState:
    """
    Tracks current usage of risk limits.
    Reset every minute for per-minute limits.
    """
    trades_this_minute: Dict[str, int]  # Per-symbol trade count
    loss_this_minute: float              # Total loss this minute
    current_positions: Dict[str, float]  # Per-symbol position size
    gross_exposure: float                # Total exposure
    session_pnl: float                   # Session PnL (realized)
    peak_session_pnl: float              # Peak PnL this session (for drawdown)
    last_reset_time: datetime            # Last reset time

    def __init__(self):
        self.trades_this_minute = {}
        self.loss_this_minute = 0.0
        self.current_positions = {}
        self.gross_exposure = 0.0
        self.session_pnl = 0.0
        self.peak_session_pnl = 0.0
        self.last_reset_time = datetime.now()

    @property
    def current_drawdown(self) -> float:
        """Current drawdown from peak PnL."""
        return max(0.0, self.peak_session_pnl - self.session_pnl)


class RiskEnvelopes:
    """
    Dynamic risk constraints that adapt to intraday conditions.
    Enforces hard limits on trading activity.

    Usage:
        envelopes = RiskEnvelopes(constraints)
        allowed, reason = envelopes.check_envelope(order, current_exposure)
        if allowed:
            # Execute trade
            envelopes.record_trade(order, pnl_impact)
        else:
            # Reject trade with reason
    """

    def __init__(self, constraints: RiskConstraints):
        """
        Initialize risk envelopes.

        Args:
            constraints: Risk constraint limits
        """
        self.constraints = constraints
        self.state = RiskState()

    def check_envelope(
        self,
        symbol: str,
        order_quantity: float,
        order_value: float,
        current_exposure: float
    ) -> Tuple[bool, Optional[RiskStopReason]]:
        """
        Check all risk envelopes for a proposed order.

        Args:
            symbol: Trading symbol
            order_quantity: Order quantity
            order_value: Estimated order value (₹)
            current_exposure: Current gross exposure

        Returns:
            (allowed, reason) - True if trade allowed, False with reason
        """
        now = datetime.now()

        # Reset per-minute counters if needed
        if (now - self.state.last_reset_time).total_seconds() >= 60:
            self._reset_minute_counters(now)

        # 1. Max trades per minute
        symbol_trades = self.state.trades_this_minute.get(symbol, 0)
        if symbol_trades >= self.constraints.max_trades_per_minute:
            return False, RiskStopReason.MAX_TRADES_MINUTE

        # 2. Max loss per minute
        if self.state.loss_this_minute >= self.constraints.max_loss_per_minute:
            return False, RiskStopReason.MAX_LOSS_MINUTE

        # 3. Position size cap
        current_position = self.state.current_positions.get(symbol, 0.0)
        if abs(current_position) + order_quantity > self.constraints.max_position_size:
            return False, RiskStopReason.POSITION_SIZE_CAP

        # 4. Gross exposure limit
        if current_exposure + order_value > self.constraints.max_gross_exposure:
            return False, RiskStopReason.GROSS_EXPOSURE_LIMIT

        # 5. Max drawdown session
        if self.state.current_drawdown >= self.constraints.max_drawdown_session:
            return False, RiskStopReason.MAX_DRAWDOWN_SESSION

        # All checks passed
        return True, None

    def record_trade(self, symbol: str, quantity: float, pnl_impact: float, order_value: float):
        """
        Update risk state after trade execution.

        Args:
            symbol: Trading symbol
            quantity: Trade quantity
            pnl_impact: PnL impact (positive=profit, negative=loss)
            order_value: Order value (₹)
        """
        # Update trade count
        self.state.trades_this_minute[symbol] = self.state.trades_this_minute.get(
            symbol, 0) + 1

        # Update position
        current_pos = self.state.current_positions.get(symbol, 0.0)
        self.state.current_positions[symbol] = current_pos + quantity

        # Update gross exposure
        self.state.gross_exposure += order_value

        # Update PnL
        self.state.session_pnl += pnl_impact

        # Update peak PnL
        if self.state.session_pnl > self.state.peak_session_pnl:
            self.state.peak_session_pnl = self.state.session_pnl

        # Update loss if trade was losing
        if pnl_impact < 0:
            self.state.loss_this_minute += abs(pnl_impact)

    def _reset_minute_counters(self, now: datetime):
        """Reset per-minute counters."""
        self.state.trades_this_minute.clear()
        self.state.loss_this_minute = 0.0
        self.state.last_reset_time = now
