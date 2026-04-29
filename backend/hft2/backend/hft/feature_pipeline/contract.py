from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
import hashlib


@dataclass(frozen=True)
class FeatureVector:
    """
    Complete HFT feature vector - deterministic and explainable.
    Read-only data contract between Intraday Features and downstream ML/RL models.
    Strictly contains features. NO signals, NO execution paths.

    All features computed at a single timestamp for reproducibility.
    """
    # Identity
    timestamp: datetime
    symbol: str

    # Microstructure Features
    spread_bps: float                  # Bid-ask spread in basis points
    obi_value: float                   # Order book imbalance [-1, 1]
    volume_delta: float                # Buy vol - Sell vol (last N ticks)
    micro_momentum_bps: float          # Price velocity (bps per second)

    # Volatility Features
    volatility_garch: float            # GARCH(1,1) estimate (annualized)
    volatility_atr: float              # Average True Range (absolute)
    # Realized vol (5-min window, annualized)
    volatility_realized: float

    # Regime Features
    current_regime: str                # TRENDING_UP, RANGING, etc.
    regime_confidence: float           # [0, 1] classification confidence

    # Fee Impact
    estimated_fee_impact_bps: float    # STT + GST + Stamp duty in bps

    # Determinism Check
    feature_hash: str                  # SHA256 for reproducibility

    @property
    def explanation(self) -> str:
        """
        Human-readable feature summary.
        Financial language, NOT technical jargon.
        """
        return (
            f"Spread: {self.spread_bps:.2f}bps | "
            f"OBI: {self.obi_value:.3f} | "
            f"Vol Δ: {self.volume_delta:+.1f} | "
            f"Momentum: {self.micro_momentum_bps:+.2f}bps/s | "
            f"Regime: {self.current_regime}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "features": {
                "spread_bps": self.spread_bps,
                "obi_value": self.obi_value,
                "volume_delta": self.volume_delta,
                "micro_momentum_bps": self.micro_momentum_bps,
                "volatility_garch": self.volatility_garch,
                "volatility_atr": self.volatility_atr,
                "volatility_realized": self.volatility_realized,
                "current_regime": self.current_regime,
                "regime_confidence": self.regime_confidence,
                "estimated_fee_impact_bps": self.estimated_fee_impact_bps
            },
            "feature_hash": self.feature_hash,
            "explanation": self.explanation
        }

    @classmethod
    def compute_hash(cls, features_dict: Dict[str, Any]) -> str:
        """
        Generate deterministic hash for feature vector.
        Ensures reproducibility and tamper detection.
        """
        # Sort keys for determinism
        sorted_items = sorted(features_dict.items())
        data_str = "|".join(f"{k}={v}" for k, v in sorted_items)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
