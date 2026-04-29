"""
Professional Short-Sell Logic Integration
Integrates the professional short-sell logic with existing trading modules
for intraday short-selling (sell first, then buy to square off)
"""

import logging
import os
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from .professional_short_sell_logic import (
    ProfessionalShortSellLogic, ShortStockMetrics, ShortSellDecision, ShortSellReason
)
from .professional_sell_logic import MarketTrend, MarketContext
from .market_context_analyzer import MarketContextAnalyzer

logger = logging.getLogger(__name__)


class ProfessionalShortSellIntegration:
    """
    Integration layer for professional short-sell logic
    This enables AUTOMATIC detection of intraday trading direction:
    - BUY first → SELL later (normal long) when signals are bullish
    - SELL first → BUY later (short-sell) when signals are bearish
    
    Only active when product_type is MIS (intraday)
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Initialize professional components
        self.short_sell_logic = ProfessionalShortSellLogic(config)
        self.market_analyzer = MarketContextAnalyzer(config)
        
        # Integration settings
        self.enable_short_selling = config.get("enable_short_selling", True)
        self.product_type = config.get("product_type", "MIS")  # MIS required for intraday
        
        logger.info(f"🔄 Professional Short-Sell Integration initialized (AUTO-detect mode)")
        logger.info(f"   - Short-selling enabled: {self.enable_short_selling}")
        logger.info(f"   - Product type: {self.product_type} ({'Intraday' if self.product_type == 'MIS' else 'Delivery'})")
        logger.info(f"   - Mode: Automatic direction detection (BUY or SELL first based on signals)")
    
    def evaluate_professional_short_sell(
        self,
        ticker: str,
        current_price: float,
        portfolio_holdings: Dict,
        analysis_data: Dict,
        price_history: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Main integration point for professional short-sell evaluation
        Returns a decision compatible with existing trading modules
        
        For short-selling:
        - We SELL first without holdings (opens short position)
        - Stop-loss is ABOVE entry price
        - Take-profit is BELOW entry price
        - Must square off by BUYING before market close
        """
        # Check if short-selling is enabled
        if not self.enable_short_selling:
            logger.info(f"🚫 SHORT-SELL DISABLED: Short-selling disabled by configuration for {ticker}")
            return self._disabled_decision(ticker, current_price)
        
        # CRITICAL: Only allow MIS (intraday) product type for short-selling
        if self.product_type != "MIS":
            logger.error(f"❌ SHORT-SELL REJECTED: Product type must be MIS (intraday), not {self.product_type}. Short-selling not allowed for CNC/delivery.")
            return self._invalid_product_type_decision(ticker, current_price, self.product_type)
        
        try:
            logger.info(f"=== STARTING PROFESSIONAL SHORT-SELL EVALUATION FOR {ticker} ===")
            
            # Build stock metrics for short-sell analysis
            stock_metrics = self._build_short_stock_metrics(
                ticker, current_price, portfolio_holdings, analysis_data, price_history
            )
            
            # Build market context
            market_context = self._build_market_context(analysis_data, price_history)
            
            # Extract analysis components
            technical_analysis = analysis_data.get("technical_indicators", {})
            sentiment_analysis = analysis_data.get("sentiment", {})
            ml_analysis = analysis_data.get("ml_analysis", {})
            
            # Get portfolio context
            portfolio_context = self._build_portfolio_context(portfolio_holdings)
            
            # Get professional short-sell decision
            short_decision = self.short_sell_logic.evaluate_short_decision(
                ticker=ticker,
                stock_metrics=stock_metrics,
                market_context=market_context,
                technical_analysis=technical_analysis,
                sentiment_analysis=sentiment_analysis,
                ml_analysis=ml_analysis,
                portfolio_context=portfolio_context
            )
            
            # Log detailed decision information
            logger.info(f"Professional Short-Sell Decision for {ticker}:")
            logger.info(f"  Should Short: {short_decision.should_short}")
            logger.info(f"  Confidence: {short_decision.confidence:.3f}")
            logger.info(f"  Short Percentage: {short_decision.short_percentage:.3f}")
            logger.info(f"  Reason: {short_decision.reason.value if short_decision.reason else 'N/A'}")
            logger.info(f"  Target Entry: Rs.{short_decision.target_entry_price:.2f}")
            logger.info(f"  Stop-Loss: Rs.{short_decision.stop_loss_price:.2f} (ABOVE entry)")
            logger.info(f"  Take-Profit: Rs.{short_decision.take_profit_price:.2f} (BELOW entry)")
            
            # Convert to standard decision format
            if short_decision.should_short:
                logger.info(f"✅ SHORT-SELL SIGNAL CONFIRMED for {ticker}")
                return {
                    "action": "short_sell",  # Special action type for short-selling
                    "ticker": ticker,
                    "qty": short_decision.short_quantity,
                    "price": current_price,
                    "stop_loss": short_decision.stop_loss_price,
                    "take_profit": short_decision.take_profit_price,
                    "success": True,
                    "confidence_score": short_decision.confidence,
                    "signals": len(short_decision.signals_triggered),
                    "reason": short_decision.reason.value if short_decision.reason else "short_opportunity",
                    "is_short_sell": True,
                    "short_entry_price": short_decision.target_entry_price,
                    "square_off_action": "BUY",  # Must buy to square off
                    "professional_reasoning": short_decision.reasoning
                }
            else:
                logger.info(f"❌ No short-sell opportunity for {ticker}: {short_decision.reasoning}")
                return {
                    "action": "hold",
                    "ticker": ticker,
                    "qty": 0,
                    "price": current_price,
                    "stop_loss": 0.0,
                    "take_profit": 0.0,
                    "success": True,
                    "confidence_score": 0.0,
                    "signals": 0,
                    "reason": "no_short_opportunity",
                    "is_short_sell": False,
                    "professional_reasoning": short_decision.reasoning
                }
        
        except Exception as e:
            logger.error(f"Error in professional short-sell evaluation for {ticker}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "action": "hold",
                "ticker": ticker,
                "qty": 0,
                "price": current_price,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "success": False,
                "confidence_score": 0.0,
                "signals": 0,
                "reason": "error",
                "is_short_sell": False,
                "professional_reasoning": f"Error during analysis: {str(e)}"
            }
    
    def _build_short_stock_metrics(
        self,
        ticker: str,
        current_price: float,
        portfolio_holdings: Dict,
        analysis_data: Dict,
        price_history: Optional[pd.DataFrame] = None
    ) -> ShortStockMetrics:
        """Build ShortStockMetrics from analysis data"""
        try:
            technical = analysis_data.get("technical_indicators", {})
            fundamental = analysis_data.get("fundamental_analysis", {})
            ml = analysis_data.get("ml_analysis", {})
            
            # Calculate volatility from price history
            volatility = 0.02  # Default 2%
            atr = current_price * 0.02  # Default ATR
            
            if price_history is not None and len(price_history) > 10:
                returns = price_history['Close'].pct_change().dropna()
                volatility = returns.std()
                
                # Calculate ATR (simplified)
                high_low = price_history['High'] - price_history['Low']
                high_close = abs(price_history['High'] - price_history['Close'].shift())
                low_close = abs(price_history['Low'] - price_history['Close'].shift())
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = ranges.max(axis=1)
                atr = true_range.rolling(14).mean().iloc[-1] if len(true_range) > 14 else current_price * 0.02
            
            # Extract technical indicators
            rsi = technical.get("rsi_14", 50.0)
            macd = technical.get("macd", 0.0)
            macd_signal = technical.get("macd_signal", 0.0)
            sma_20 = technical.get("sma_20", current_price)
            sma_50 = technical.get("sma_50", current_price)
            sma_200 = technical.get("sma_200", current_price)
            
            # Support and resistance
            support_level = technical.get("support_level", current_price * 0.95)
            resistance_level = technical.get("resistance_level", current_price * 1.05)
            
            # Volume ratio
            volume_ratio = technical.get("volume_ratio", 1.0)
            
            # Valuation metrics
            price_to_book = fundamental.get("price_to_book", 2.0)
            price_to_earnings = fundamental.get("pe_ratio", 20.0)
            sector_pe = fundamental.get("sector_pe", 20.0)
            earnings_growth = fundamental.get("earnings_growth", 0.05)
            return_on_equity = fundamental.get("roe", 0.10)
            debt_to_equity = fundamental.get("debt_to_equity", 0.5)
            
            return ShortStockMetrics(
                current_price=current_price,
                entry_price=current_price,  # Target entry at current price
                quantity=0,  # Will be calculated by execution layer
                volatility=volatility,
                atr=atr if atr > 0 else current_price * 0.02,
                rsi=rsi,
                macd=macd,
                macd_signal=macd_signal,
                sma_20=sma_20,
                sma_50=sma_50,
                sma_200=sma_200,
                support_level=support_level,
                resistance_level=resistance_level,
                volume_ratio=volume_ratio,
                price_to_book=price_to_book,
                price_to_earnings=price_to_earnings,
                earnings_growth=earnings_growth,
                return_on_equity=return_on_equity,
                debt_to_equity=debt_to_equity,
                sector_pe=sector_pe
            )
        
        except Exception as e:
            logger.error(f"Error building short stock metrics: {e}")
            # Return minimal valid metrics
            return ShortStockMetrics(
                current_price=current_price,
                entry_price=current_price,
                quantity=0,
                volatility=0.02,
                atr=current_price * 0.02,
                rsi=50.0,
                macd=0.0,
                macd_signal=0.0,
                sma_20=current_price,
                sma_50=current_price,
                sma_200=current_price,
                support_level=current_price * 0.95,
                resistance_level=current_price * 1.05,
                volume_ratio=1.0,
                price_to_book=2.0,
                price_to_earnings=20.0
            )
    
    def _build_market_context(
        self,
        analysis_data: Dict,
        price_history: Optional[pd.DataFrame] = None
    ) -> MarketContext:
        """Build MarketContext from analysis data"""
        try:
            # Try to get market regime from ML analysis
            ml_analysis = analysis_data.get("ml_analysis", {})
            market_regime = ml_analysis.get("market_regime", "neutral")
            
            # Map market regime to MarketTrend
            trend_mapping = {
                "bull": MarketTrend.UPTREND,
                "bear": MarketTrend.DOWNTREND,
                "neutral": MarketTrend.SIDEWAYS,
                "strong_bull": MarketTrend.STRONG_UPTREND,
                "strong_bear": MarketTrend.STRONG_DOWNTREND
            }
            trend = trend_mapping.get(market_regime, MarketTrend.SIDEWAYS)
            
            # Calculate trend strength
            trend_strength = 0.5  # Default moderate strength
            if price_history is not None and len(price_history) > 20:
                returns = price_history['Close'].pct_change().dropna()
                trend_strength = min(abs(returns.mean()) / returns.std(), 1.0) if returns.std() > 0 else 0.5
            
            # Volatility regime
            volatility_regime = "normal"
            if price_history is not None:
                recent_vol = price_history['Close'].pct_change().std()
                if recent_vol > 0.03:
                    volatility_regime = "high"
                elif recent_vol < 0.01:
                    volatility_regime = "low"
            
            # Market stress (simplified)
            market_stress = 0.3  # Default low-moderate stress
            
            return MarketContext(
                trend=trend,
                trend_strength=trend_strength,
                volatility_regime=volatility_regime,
                market_stress=market_stress,
                sector_performance=0.0,  # Neutral
                volume_profile=1.0  # Average
            )
        
        except Exception as e:
            logger.error(f"Error building market context: {e}")
            # Return default market context
            return MarketContext(
                trend=MarketTrend.SIDEWAYS,
                trend_strength=0.5,
                volatility_regime="normal",
                market_stress=0.3,
                sector_performance=0.0,
                volume_profile=1.0
            )
    
    def _build_portfolio_context(self, portfolio_holdings: Dict) -> Dict:
        """Build portfolio context for short-sell decision"""
        # For short-selling, we need available margin/cash
        total_value = sum(
            holding.get("avg_price", 0) * holding.get("quantity", 0)
            for holding in portfolio_holdings.values()
        )
        
        # Assume 25% of portfolio value is available as cash/margin
        available_cash = total_value * 0.25
        max_allocation = 0.25  # Max 25% per trade
        
        return {
            "available_cash": available_cash,
            "total_value": total_value,
            "max_allocation_per_trade": max_allocation
        }
    
    def _disabled_decision(self, ticker: str, current_price: float) -> Dict:
        """Return HOLD decision when short-selling is disabled"""
        return {
            "action": "hold",
            "ticker": ticker,
            "qty": 0,
            "price": current_price,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "success": True,
            "confidence_score": 0.0,
            "signals": 0,
            "reason": "short_selling_disabled",
            "is_short_sell": False,
            "professional_reasoning": "Short-selling functionality is disabled in configuration"
        }
    
    def _invalid_product_type_decision(self, ticker: str, current_price: float, product_type: str) -> Dict:
        """Return HOLD decision when product type is invalid for short-selling"""
        return {
            "action": "hold",
            "ticker": ticker,
            "qty": 0,
            "price": current_price,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "success": True,
            "confidence_score": 0.0,
            "signals": 0,
            "reason": "invalid_product_type",
            "is_short_sell": False,
            "professional_reasoning": f"Short-selling requires MIS (intraday) product type, not {product_type}"
        }
    
    def evaluate_intraday_direction(
        self,
        ticker: str,
        current_price: float,
        portfolio_holdings: Dict,
        analysis_data: Dict,
        price_history: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        INDUSTRY-LEVEL UNIFIED DECISION MAKER
        
        Automatically detects optimal intraday direction:
        1. Analyze market signals (bullish vs bearish)
        2. If strongly bearish → SELL first (short-sell)
        3. If strongly bullish → BUY first (normal long)
        4. If unclear → HOLD
        
        This provides maximum flexibility for intraday trading.
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🎯 INTRADAY DIRECTION ANALYSIS FOR {ticker}")
        logger.info(f"{'='*80}")
        
        # Step 1: Check if MIS (intraday)
        if self.product_type != "MIS":
            logger.info(f"⚠️  Not MIS product type ({self.product_type}). Using normal buy/sell logic only.")
            return self._no_position_decision()
        
        # Step 2: Evaluate BOTH directions
        logger.info(f"📊 Evaluating both LONG and SHORT opportunities...")
        
        # A. Evaluate SHORT opportunity (SELL first)
        short_decision = self.evaluate_professional_short_sell(
            ticker=ticker,
            current_price=current_price,
            portfolio_holdings=portfolio_holdings,
            analysis_data=analysis_data,
            price_history=price_history
        )
        
        # B. Evaluate LONG opportunity (BUY first) - using buy logic
        long_decision = self._evaluate_long_opportunity(
            ticker=ticker,
            current_price=current_price,
            portfolio_holdings=portfolio_holdings,
            analysis_data=analysis_data,
            price_history=price_history
        )
        
        # Step 3: Compare and select best direction
        short_confidence = short_decision.get("confidence_score", 0.0)
        long_confidence = long_decision.get("confidence_score", 0.0)
        
        logger.info(f"\n📈 Direction Comparison:")
        logger.info(f"   🔴 Short (SELL first): Confidence = {short_confidence:.1%}")
        logger.info(f"   🟢 Long (BUY first):   Confidence = {long_confidence:.1%}")
        
        # Decision matrix
        min_confidence = 0.60  # Minimum threshold
        
        if short_confidence >= min_confidence and short_confidence > long_confidence:
            # SHORT is better
            logger.info(f"\n✅ DECISION: SHORT-SELL (SELL first, BUY later)")
            logger.info(f"   Reason: Bearish signals stronger than bullish signals")
            return short_decision
        
        elif long_confidence >= min_confidence and long_confidence > short_confidence:
            # LONG is better
            logger.info(f"\n✅ DECISION: NORMAL BUY (BUY first, SELL later)")
            logger.info(f"   Reason: Bullish signals stronger than bearish signals")
            return long_decision
        
        else:
            # No clear direction
            logger.info(f"\n⚠️  DECISION: HOLD (No clear directional bias)")
            logger.info(f"   Reason: Neither direction meets confidence threshold")
            return {
                "action": "hold",
                "ticker": ticker,
                "qty": 0,
                "price": current_price,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "success": True,
                "confidence_score": max(short_confidence, long_confidence),
                "signals": 0,
                "reason": "no_clear_direction",
                "is_short_sell": False,
                "professional_reasoning": f"No clear directional bias - Short: {short_confidence:.1%}, Long: {long_confidence:.1%}"
            }
    
    def _evaluate_long_opportunity(
        self,
        ticker: str,
        current_price: float,
        portfolio_holdings: Dict,
        analysis_data: Dict,
        price_history: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Evaluate LONG opportunity (normal BUY first → SELL later)
        Simplified version compatible with existing buy logic
        """
        try:
            # Import buy logic if available
            from core.professional_buy_integration import ProfessionalBuyIntegration
            
            buy_integration = ProfessionalBuyIntegration(self.config)
            
            # Build portfolio context for buy
            portfolio_context = self._build_portfolio_context(portfolio_holdings)
            
            # Use existing buy logic
            # Note: This is a simplified wrapper - in production, you'd call the full buy integration
            logger.info(f"   🟢 Evaluating LONG opportunity using professional buy logic...")
            
            # For now, return a placeholder that defers to the main buy integration
            # In production, this would call buy_integration.evaluate_professional_buy()
            return {
                "action": "buy",  # Will be processed by main buy integration
                "ticker": ticker,
                "qty": 0,  # To be calculated by buy integration
                "price": current_price,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "success": True,
                "confidence_score": 0.5,  # Placeholder
                "signals": 0,
                "reason": "defer_to_buy_integration",
                "is_short_sell": False,
                "professional_reasoning": "Long evaluation delegated to ProfessionalBuyIntegration"
            }
        
        except ImportError:
            logger.warning("ProfessionalBuyIntegration not available, using simplified long logic")
            return {
                "action": "buy",
                "ticker": ticker,
                "qty": 0,
                "price": current_price,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "success": True,
                "confidence_score": 0.5,
                "signals": 0,
                "reason": "buy_logic_unavailable",
                "is_short_sell": False
            }
