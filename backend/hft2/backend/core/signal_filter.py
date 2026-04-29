"""
Phase 1 — Signal Filtering Layer (CRITICAL)
Filters Samruddhi predictions to only allow high-quality trades where:
- confidence > defined threshold
- multiple models agree (ensemble alignment)
- no conflicting recent signals
- bot stops after trade cycle completion
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class SignalQuality(Enum):
    """Signal quality levels"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    REJECT = "REJECT"


class TradeCycleState(Enum):
    """Trade cycle states"""
    IDLE = "IDLE"
    ANALYZING = "ANALYZING"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    TRADE_EXECUTED = "TRADE_EXECUTED"
    CYCLE_COMPLETE = "CYCLE_COMPLETE"


class SignalFilterConfig:
    """Configuration for signal filtering"""

    def __init__(self, config: Dict = None):
        config = config or {}

        # Confidence threshold
        self.min_confidence = config.get("min_confidence", 0.70)  # Default 70%

        # Ensemble alignment
        self.min_ensemble_agreement = config.get(
            "min_ensemble_agreement", 0.60)  # 60% of models must agree
        self.min_models_agreeing = config.get(
            "min_models_agreeing", 3)  # At least 3 models must agree

        # Signal conflict detection
        self.conflict_window_minutes = config.get(
            "conflict_window_minutes", 30)  # Check last 30 minutes
        self.max_conflicting_signals = config.get(
            "max_conflicting_signals", 1)  # Allow max 1 conflicting signal

        # Trade cycle control
        # Stop bot after trade cycle completes
        self.stop_after_cycle = config.get("stop_after_cycle", True)

        # Additional filters
        self.min_prediction_magnitude = config.get(
            "min_prediction_magnitude", 0.02)  # 2% minimum movement
        self.require_stop_loss = config.get("require_stop_loss", True)
        self.max_risk_score = config.get(
            "max_risk_score", 0.7)  # Max 70% risk score

        logger.info(f"SignalFilterConfig initialized: min_confidence={self.min_confidence}, "
                    f"min_ensemble_agreement={self.min_ensemble_agreement}, "
                    f"min_models_agreeing={self.min_models_agreeing}")


class RecentSignalTracker:
    """Track recent signals to detect conflicts"""

    def __init__(self, max_history: int = 100):
        self.signal_history: List[Dict] = []
        self.max_history = max_history

    def add_signal(self, symbol: str, recommendation: str, confidence: float,
                   timestamp: datetime, model_predictions: Dict = None):
        """Add a signal to history"""
        signal = {
            "symbol": symbol,
            "recommendation": recommendation,
            "confidence": confidence,
            "timestamp": timestamp,
            "model_predictions": model_predictions or {}
        }

        self.signal_history.append(signal)

        # Keep only recent history
        if len(self.signal_history) > self.max_history:
            self.signal_history = self.signal_history[-self.max_history:]

    def get_recent_signals(self, symbol: str, window_minutes: int = 30) -> List[Dict]:
        """Get recent signals for a symbol within time window"""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)

        return [
            s for s in self.signal_history
            if s["symbol"] == symbol and s["timestamp"] >= cutoff
        ]

    def count_conflicting_signals(self, symbol: str, recommendation: str,
                                  window_minutes: int = 30) -> int:
        """Count conflicting signals (opposite recommendations)"""
        recent_signals = self.get_recent_signals(symbol, window_minutes)

        conflicts = 0
        for signal in recent_signals:
            if signal["recommendation"] != recommendation:
                # Check if it's a truly conflicting signal (BUY vs SELL)
                if (recommendation == "BUY" and signal["recommendation"] == "SELL") or \
                   (recommendation == "SELL" and signal["recommendation"] == "BUY"):
                    conflicts += 1

        return conflicts


class SignalFilteringLayer:
    """
    Main signal filtering layer that validates Samruddhi predictions
    before allowing trade execution.
    """

    def __init__(self, config: Dict = None):
        self.config = SignalFilterConfig(config)
        self.signal_tracker = RecentSignalTracker()
        self.trade_cycle_state = TradeCycleState.IDLE
        self.cycle_trade_executed = False

        logger.info("SignalFilteringLayer initialized")

    def filter_signal(self, symbol: str, analysis: Dict) -> Dict:
        """
        Filter a trading signal through all validation layers.

        Returns:
            Dict with filtering results:
            - approved: bool
            - quality: SignalQuality
            - reasons: List[str]
            - filtered_analysis: Dict (original analysis with filter metadata)
        """
        reasons = []
        quality = SignalQuality.HIGH

        # Extract key metrics from analysis
        recommendation = analysis.get("recommendation", "HOLD").upper()
        confidence = float(analysis.get("confidence", 0.0))
        model_predictions = analysis.get("model_predictions", {})
        risk_score = float(analysis.get("risk_score", 0.5))
        stop_loss = analysis.get("stop_loss")
        prediction_magnitude = abs(
            float(analysis.get("prediction_magnitude", 0.0)))

        logger.info(f"Filtering signal for {symbol}: rec={recommendation}, "
                    f"confidence={confidence:.3f}, models={len(model_predictions)}")

        # Skip filtering for HOLD recommendations
        if recommendation == "HOLD":
            return {
                "approved": False,
                "quality": SignalQuality.LOW,
                "reasons": ["HOLD recommendation - no trade needed"],
                "filtered_analysis": analysis
            }

        # ── Filter 1: Confidence Threshold ─────────────────────────────────
        if confidence < self.config.min_confidence:
            reasons.append(
                f"Confidence {confidence:.3f} below threshold {self.config.min_confidence}")
            quality = SignalQuality.LOW

        # ── Filter 2: Ensemble Alignment ──────────────────────────────────
        ensemble_passed, ensemble_reason = self._check_ensemble_alignment(
            model_predictions, recommendation
        )

        if not ensemble_passed:
            reasons.append(ensemble_reason)
            if quality == SignalQuality.HIGH:
                quality = SignalQuality.MEDIUM

        # ── Filter 3: Conflicting Recent Signals ──────────────────────────
        conflicts = self.signal_tracker.count_conflicting_signals(
            symbol, recommendation, self.config.conflict_window_minutes
        )

        if conflicts > self.config.max_conflicting_signals:
            reasons.append(
                f"Too many conflicting signals ({conflicts}) in last "
                f"{self.config.conflict_window_minutes} minutes")
            quality = SignalQuality.REJECT

        # ── Filter 4: Risk Score Validation ───────────────────────────────
        if risk_score > self.config.max_risk_score:
            reasons.append(
                f"Risk score {risk_score:.3f} exceeds maximum {self.config.max_risk_score}")
            quality = SignalQuality.REJECT

        # ── Filter 5: Stop Loss Required ──────────────────────────────────
        if self.config.require_stop_loss and not stop_loss:
            reasons.append("Stop loss not provided")
            quality = SignalQuality.LOW

        # ── Filter 6: Prediction Magnitude ────────────────────────────────
        if prediction_magnitude > 0 and prediction_magnitude < self.config.min_prediction_magnitude:
            reasons.append(
                f"Prediction magnitude {prediction_magnitude:.4f} too small "
                f"(min: {self.config.min_prediction_magnitude})")
            quality = SignalQuality.MEDIUM

        # ── Final Decision ────────────────────────────────────────────────
        approved = (quality != SignalQuality.REJECT and
                    confidence >= self.config.min_confidence and
                    ensemble_passed and
                    conflicts <= self.config.max_conflicting_signals)

        # Track this signal regardless of approval
        self.signal_tracker.add_signal(
            symbol, recommendation, confidence, datetime.now(), model_predictions
        )

        # Add filter metadata to analysis
        filtered_analysis = analysis.copy()
        filtered_analysis["signal_filter"] = {
            "approved": approved,
            "quality": quality.value,
            "reasons": reasons,
            "confidence_passed": confidence >= self.config.min_confidence,
            "ensemble_passed": ensemble_passed,
            "conflict_count": conflicts,
            "timestamp": datetime.now().isoformat()
        }

        if approved:
            logger.info(f"✅ Signal APPROVED for {symbol}: {recommendation} "
                        f"(confidence={confidence:.3f}, quality={quality.value})")
        else:
            logger.info(f"❌ Signal REJECTED for {symbol}: {recommendation} "
                        f"(confidence={confidence:.3f}, quality={quality.value}) - "
                        f"Reasons: {reasons}")

        return {
            "approved": approved,
            "quality": quality,
            "reasons": reasons,
            "filtered_analysis": filtered_analysis
        }

    def _check_ensemble_alignment(self, model_predictions: Dict,
                                  recommendation: str) -> Tuple[bool, str]:
        """
        Check if multiple models agree on the recommendation.

        Returns:
            (passed: bool, reason: str)
        """
        if not model_predictions:
            return False, "No model predictions available for ensemble check"

        # Count model predictions by direction
        buy_count = 0
        sell_count = 0
        hold_count = 0
        total_models = len(model_predictions)

        for model_name, pred_data in model_predictions.items():
            if isinstance(pred_data, dict):
                pred_rec = pred_data.get("recommendation", "HOLD").upper()
            else:
                # Assume it's a prediction value
                if pred_data > 0.02:
                    pred_rec = "BUY"
                elif pred_data < -0.02:
                    pred_rec = "SELL"
                else:
                    pred_rec = "HOLD"

            if pred_rec == "BUY":
                buy_count += 1
            elif pred_rec == "SELL":
                sell_count += 1
            else:
                hold_count += 1

        # Check if enough models agree
        if recommendation == "BUY":
            agreeing_models = buy_count
        elif recommendation == "SELL":
            agreeing_models = sell_count
        else:
            agreeing_models = hold_count

        agreement_ratio = agreeing_models / total_models if total_models > 0 else 0

        # Both ratio and absolute count must meet thresholds
        ratio_passed = agreement_ratio >= self.config.min_ensemble_agreement
        count_passed = agreeing_models >= self.config.min_models_agreeing

        if ratio_passed and count_passed:
            return True, f"Ensemble aligned: {agreeing_models}/{total_models} models agree ({agreement_ratio:.1%})"
        else:
            return False, (
                f"Insufficient ensemble alignment: {agreeing_models}/{total_models} models agree "
                f"({agreement_ratio:.1%}, need {self.config.min_ensemble_agreement:.0%} ratio "
                f"and {self.config.min_models_agreeing} models)"
            )

    def record_trade_execution(self, symbol: str, side: str, success: bool):
        """Record that a trade was executed"""
        self.cycle_trade_executed = True
        self.trade_cycle_state = TradeCycleState.TRADE_EXECUTED

        logger.info(
            f"Trade execution recorded: {side} {symbol} - {'SUCCESS' if success else 'FAILED'}")

    def complete_trade_cycle(self) -> bool:
        """
        Complete the trade cycle and determine if bot should stop.

        Returns:
            should_stop: bool - whether the bot should stop after this cycle
        """
        self.trade_cycle_state = TradeCycleState.CYCLE_COMPLETE

        if self.config.stop_after_cycle:
            logger.info(
                "Trade cycle complete - bot will stop (stop_after_cycle=True)")
            return True
        else:
            logger.info(
                "Trade cycle complete - bot will continue (stop_after_cycle=False)")
            self.trade_cycle_state = TradeCycleState.IDLE
            self.cycle_trade_executed = False
            return False

    def start_new_cycle(self):
        """Start a new trade cycle"""
        self.trade_cycle_state = TradeCycleState.ANALYZING
        self.cycle_trade_executed = False
        logger.info("New trade cycle started")

    def get_cycle_state(self) -> Dict:
        """Get current trade cycle state"""
        return {
            "state": self.trade_cycle_state.value,
            "trade_executed": self.cycle_trade_executed,
            "stop_after_cycle": self.config.stop_after_cycle
        }

    def get_filter_stats(self) -> Dict:
        """Get filtering statistics"""
        total_signals = len(self.signal_tracker.signal_history)

        # Count by recommendation
        buy_signals = sum(1 for s in self.signal_tracker.signal_history
                          if s["recommendation"] == "BUY")
        sell_signals = sum(1 for s in self.signal_tracker.signal_history
                           if s["recommendation"] == "SELL")

        return {
            "total_signals_tracked": total_signals,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "current_cycle_state": self.trade_cycle_state.value,
            "config": {
                "min_confidence": self.config.min_confidence,
                "min_ensemble_agreement": self.config.min_ensemble_agreement,
                "min_models_agreeing": self.config.min_models_agreeing,
                "conflict_window_minutes": self.config.conflict_window_minutes,
                "stop_after_cycle": self.config.stop_after_cycle
            }
        }


# Global instance for the application
_signal_filter = None


def get_signal_filter(config: Dict = None) -> SignalFilteringLayer:
    """Get or create the global signal filtering layer instance"""
    global _signal_filter
    if _signal_filter is None:
        _signal_filter = SignalFilteringLayer(config)
    return _signal_filter


def reset_signal_filter():
    """Reset the global signal filter (useful for testing)"""
    global _signal_filter
    _signal_filter = None
