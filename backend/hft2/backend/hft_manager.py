#!/usr/bin/env python3
"""
HFT Manager - Integrates BHIV HFT Pipeline with main trading bot system
Provides unified interface for HFT intraday trading, shadow execution, and risk management
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HFTSignal:
    """HFT trading signal with metadata"""
    symbol: str
    timestamp: datetime
    action: str  # BUY, SELL, HOLD
    confidence: float
    spread_bps: float
    market_regime: str
    volatility: float
    karma_score: float
    reason: str


class HFTManager:
    """
    Main manager for HFT intraday trading system.
    Wires together: HFTPipeline + Main Bot + Risk Management + Execution
    """

    def __init__(self, config: Dict[str, Any], username: str = "anonymous"):
        """
        Initialize HFT Manager

        Args:
            config: Bot configuration dictionary
            username: User identifier for isolation
        """
        self.config = config
        self.username = username
        self.enabled = config.get("hft_enabled", False)
        self.mode = config.get("hft_mode", "shadow")  # shadow, live, hybrid

        logger.info(f"🚀 HFT Manager initialized for {username}")
        logger.info(f"   Mode: {self.mode}, Enabled: {self.enabled}")

        # Lazy initialization - will be created when first needed
        self._pipeline = None
        self._initialized = False

        # Performance tracking
        self.signals_generated = 0
        self.shadow_orders_filled = 0
        self.last_signal_time: Optional[datetime] = None

    @property
    def pipeline(self):
        """Lazy load HFT Pipeline"""
        if not self._pipeline and self.enabled:
            try:
                from backend.hft.pipeline import HFTPipeline
                from backend.hft.config import default_config

                # Configure pipeline based on bot settings
                hft_config = self._build_hft_config()
                self._pipeline = HFTPipeline(config=hft_config)

                logger.info(f"✅ HFT Pipeline initialized for {self.username}")
                self._initialized = True
            except Exception as e:
                logger.error(f"❌ Failed to initialize HFT Pipeline: {e}")
                self.enabled = False

        return self._pipeline

    def _build_hft_config(self):
        """Build HFT config from bot settings"""
        try:
            from backend.hft.config import HFTConfig

            # Get HFT-specific settings from bot config
            risk_config = {
                # 2% default
                'max_daily_loss': self.config.get("hft_max_daily_loss", 0.02),
                # 10% default
                'max_position_size': self.config.get("hft_max_position", 0.10),
                'enable_shadow': self.mode in ["shadow", "hybrid"],
                'enable_live': self.mode == "live",
            }

            strategy_config = {
                'spread_ema_alpha': self.config.get("hft_spread_alpha", 0.1),
                'momentum_window_ticks': self.config.get("hft_momentum_window", 50),
                'regime_detection_window': self.config.get("hft_regime_window", 100),
            }

            return HFTConfig(
                symbol="",  # Will be set per-symbol
                risk=risk_config,
                strategy=strategy_config,
                execution_mode=self.mode
            )
        except Exception as e:
            logger.warning(f"Using default HFT config: {e}")
            from backend.hft.config import default_config
            return default_config

    def process_tick(self, symbol: str, tick_data: Dict[str, Any]) -> Optional[HFTSignal]:
        """
        Process real-time tick data through HFT pipeline

        Args:
            symbol: Stock symbol (e.g., RELIANCE.NS)
            tick_data: Tick data with bid, ask, price, volume, timestamp

        Returns:
            HFTSignal if conditions met, None otherwise
        """
        if not self.enabled or not self.pipeline:
            return None

        try:
            # Convert tick data to HFT Tick format
            from backend.hft.tick_engine import Tick

            tick = Tick(
                symbol=symbol.replace(".NS", "").replace(".BO", ""),
                price=tick_data.get('price', 0.0),
                bid=tick_data.get('bid', 0.0),
                ask=tick_data.get('ask', 0.0),
                volume=tick_data.get('volume', 0),
                timestamp=datetime.fromisoformat(
                    tick_data['timestamp']) if 'timestamp' in tick_data else datetime.now()
            )

            # Process through pipeline
            self.pipeline.process_tick(tick)

            # Check if we should generate signal
            signal = self._generate_signal(symbol, tick)

            if signal:
                self.signals_generated += 1
                self.last_signal_time = datetime.now()

            return signal

        except Exception as e:
            logger.error(f"HFT tick processing error for {symbol}: {e}")
            return None

    def _generate_signal(self, symbol: str, tick: 'Tick') -> Optional[HFTSignal]:
        """Generate trading signal from HFT pipeline state"""
        try:
            # Get current feature vector
            features = self._extract_features(tick)

            if not features:
                return None

            # Determine action based on features
            action, confidence, reason = self._analyze_features(features)

            if action == "HOLD" or confidence < 0.6:
                return None  # Only return signals with sufficient confidence

            # Get karma score from simulator
            karma_score = self.pipeline.simulator.get_karma_score() if hasattr(
                self.pipeline.simulator, 'get_karma_score') else 0.0

            return HFTSignal(
                symbol=symbol,
                timestamp=datetime.now(),
                action=action,
                confidence=confidence,
                spread_bps=features.spread_bps,
                market_regime=features.current_regime,
                volatility=features.volatility_garch,
                karma_score=karma_score,
                reason=reason
            )

        except Exception as e:
            logger.error(f"Signal generation error: {e}")
            return None

    def _extract_features(self, tick: 'Tick') -> Optional[Any]:
        """Extract feature vector from pipeline"""
        try:
            # Access latest feature vector from pipeline
            # This assumes pipeline stores last computed features
            if hasattr(self.pipeline, 'last_features'):
                return self.pipeline.last_features

            # Fallback: construct from trackers
            from backend.hft.feature_pipeline import FeatureVector

            spread_metrics = self.pipeline.spread_tracker.get_latest()
            momentum_event = self.pipeline.momentum_tracker.get_latest()
            regime = self.pipeline.regime_detector.get_latest()

            return FeatureVector(
                timestamp=tick.timestamp,
                symbol=tick.symbol,
                spread_bps=spread_metrics.spread_relative if spread_metrics else 0.0,
                obi_value=0.0,  # Placeholder
                volume_delta=0.0,  # Placeholder
                micro_momentum_bps=momentum_event.velocity_bps_per_sec if momentum_event else 0.0,
                volatility_garch=0.0,  # Placeholder
                current_regime=regime.regime.value if regime else "UNKNOWN"
            )
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return None

    def _analyze_features(self, features: Any) -> Tuple[str, float, str]:
        """
        Analyze feature vector to generate trading decision

        Returns:
            Tuple of (action, confidence, reason)
        """
        try:
            # Simple rule-based logic for now (can be enhanced with ML)
            action = "HOLD"
            confidence = 0.0
            reasons = []

            # Spread analysis
            if features.spread_bps > 50:  # Wide spread
                reasons.append(f"Wide spread: {features.spread_bps:.1f} bps")
            elif features.spread_bps < 10:  # Tight spread
                reasons.append(f"Tight spread: {features.spread_bps:.1f} bps")

            # Momentum analysis
            if abs(features.micro_momentum_bps) > 100:  # Strong momentum
                if features.micro_momentum_bps > 0:
                    action = "BUY"
                    confidence = min(
                        abs(features.micro_momentum_bps) / 200, 0.95)
                    reasons.append(
                        f"Strong upward momentum: {features.micro_momentum_bps:.1f} bps/s")
                else:
                    action = "SELL"
                    confidence = min(
                        abs(features.micro_momentum_bps) / 200, 0.95)
                    reasons.append(
                        f"Strong downward momentum: {features.micro_momentum_bps:.1f} bps/s")

            # Regime filtering
            if features.current_regime == "RANGING":
                confidence *= 0.7  # Reduce confidence in ranging market
                reasons.append(f"Ranging regime detected")
            elif features.current_regime == "TRENDING_UP" and action == "BUY":
                confidence = min(confidence * 1.2, 0.95)  # Boost confidence
                reasons.append(f"Trending up regime confirms BUY")

            # Volatility check
            if features.volatility_garch > 0.5:  # High volatility
                confidence *= 0.8  # Reduce position size in high vol
                reasons.append(
                    f"High volatility: {features.volatility_garch:.2f}")

            reason = "; ".join(reasons) if reasons else "No clear signal"

            return action, confidence, reason

        except Exception as e:
            logger.error(f"Feature analysis error: {e}")
            return "HOLD", 0.0, f"Analysis error: {e}"

    def execute_shadow_order(self, signal: HFTSignal, quantity: int) -> Dict[str, Any]:
        """
        Execute shadow order through HFT pipeline

        Args:
            signal: HFT signal to execute
            quantity: Number of shares

        Returns:
            Execution result dictionary
        """
        if not self.enabled or not self.pipeline:
            return {"success": False, "message": "HFT not enabled"}

        try:
            from backend.hft.shadow_execution import ShadowOrder, Side

            # Convert signal to shadow order
            side = Side.BUY if signal.action == "BUY" else Side.SELL

            order = ShadowOrder(
                symbol=signal.symbol.replace(".NS", "").replace(".BO", ""),
                side=side,
                quantity=quantity,
                limit_price=None,  # Market order
                trigger_reason=f"HFT Signal: {signal.reason}"
            )

            # Route through pipeline
            self.pipeline.submit_shadow_order(order)

            self.shadow_orders_filled += 1

            return {
                "success": True,
                "order_id": order.order_id,
                "symbol": signal.symbol,
                "side": signal.action,
                "quantity": quantity,
                "shadow": True,
                "karma_logged": True
            }

        except Exception as e:
            logger.error(f"Shadow order execution error: {e}")
            return {"success": False, "message": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get HFT system status"""
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "initialized": self._initialized,
            "signals_generated": self.signals_generated,
            "shadow_orders_filled": self.shadow_orders_filled,
            "last_signal_time": self.last_signal_time.isoformat() if self.last_signal_time else None,
            "pipeline_ready": self.pipeline is not None
        }

    def enable(self):
        """Enable HFT trading"""
        self.enabled = True
        logger.info(f"✅ HFT enabled for {self.username}")

    def disable(self):
        """Disable HFT trading"""
        self.enabled = False
        logger.info(f"⏹ HFT disabled for {self.username}")

    def set_mode(self, mode: str):
        """Set HFT mode (shadow, live, hybrid)"""
        if mode in ["shadow", "live", "hybrid"]:
            self.mode = mode
            logger.info(f"🔄 HFT mode set to: {mode}")
        else:
            logger.warning(f"Invalid HFT mode: {mode}")
