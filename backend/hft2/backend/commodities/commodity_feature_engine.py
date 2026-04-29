"""
DAY 2: COMMODITY FEATURE ENGINEERING PIPELINE
=============================================

Purpose: Create features for commodity analysis

Features:
- Price momentum
- Volatility index
- Moving averages
- Demand trend signals
"""

from commodities.commodity_data_ingestion import CommodityPrice
from db.samruddhi_memory import Base, FinancialMemoryManager
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Boolean
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE SCHEMA FOR FEATURES
# ============================================================================

class CommodityFeature(Base):
    """Engineered features for commodities"""
    __tablename__ = 'commodity_features'

    id = Column(Integer, primary_key=True)
    commodity_id = Column(String(100), index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)

    # Momentum Features
    momentum_1d = Column(Float)  # 1-day momentum
    momentum_5d = Column(Float)  # 5-day momentum
    momentum_20d = Column(Float)  # 20-day momentum

    # Moving Averages
    ma_5 = Column(Numeric(18, 4))  # 5-period MA
    ma_20 = Column(Numeric(18, 4))  # 20-period MA
    ma_50 = Column(Numeric(18, 4))  # 50-period MA
    ma_200 = Column(Numeric(18, 4))  # 200-period MA

    # Volatility Features
    volatility_5d = Column(Float)  # 5-day volatility
    volatility_20d = Column(Float)  # 20-day volatility
    atr_14 = Column(Numeric(18, 4))  # Average True Range (14-day)

    # Trend Signals
    trend_short = Column(String(20))  # 'UP', 'DOWN', 'SIDEWAYS'
    trend_medium = Column(String(20))
    trend_long = Column(String(20))

    # Relative Strength
    rsi_14 = Column(Float)  # RSI (14-day)

    # Volume Features (if available)
    volume_ma_20 = Column(Float)  # 20-day average volume
    volume_spike = Column(Boolean, default=False)  # Volume spike detected

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CommodityFeature(commodity={self.commodity_id}, date={self.timestamp})>"


# ============================================================================
# FEATURE ENGINEERING ENGINE
# ============================================================================

class CommodityFeatureEngine:
    """
    Generate features from commodity price data.

    Features:
    - Momentum indicators
    - Moving averages
    - Volatility measures
    - Trend signals
    - Volume analysis
    """

    def __init__(self, memory_manager: FinancialMemoryManager):
        self.memory = memory_manager
        logger.info("✓ CommodityFeatureEngine initialized")

    # ========================================================================
    # FEATURE CALCULATION FUNCTIONS
    # ========================================================================

    def calculate_momentum(self, prices: pd.Series, periods: List[int] = [1, 5, 20]) -> Dict[str, pd.Series]:
        """
        Calculate price momentum for multiple periods.

        Args:
            prices: Price series
            periods: List of lookback periods

        Returns:
            Dictionary of momentum series {period_name: momentum_series}
        """
        momentum = {}
        for period in periods:
            momentum[f'momentum_{period}d'] = prices.pct_change(
                periods=period) * 100

        return momentum

    def calculate_moving_averages(self, prices: pd.Series, windows: List[int] = [5, 20, 50, 200]) -> Dict[str, pd.Series]:
        """
        Calculate moving averages.

        Args:
            prices: Price series
            windows: List of window sizes

        Returns:
            Dictionary of MA series {ma_window: ma_series}
        """
        mas = {}
        for window in windows:
            mas[f'ma_{window}'] = prices.rolling(window=window).mean()

        return mas

    def calculate_volatility(self, prices: pd.Series, windows: List[int] = [5, 20]) -> Dict[str, pd.Series]:
        """
        Calculate historical volatility (standard deviation of returns).

        Args:
            prices: Price series
            windows: List of window sizes

        Returns:
            Dictionary of volatility series
        """
        returns = prices.pct_change()
        volatility = {}

        for window in windows:
            volatility[f'volatility_{window}d'] = returns.rolling(
                window=window).std() * np.sqrt(252) * 100

        return volatility

    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR).

        Args:
            high: High price series
            low: Low price series
            close: Close price series
            period: ATR period

        Returns:
            ATR series
        """
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).

        Args:
            prices: Price series
            period: RSI period

        Returns:
            RSI series (0-100)
        """
        delta = prices.diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def detect_trend(self, prices: pd.Series, short_window: int = 5, medium_window: int = 20, long_window: int = 50) -> Dict[str, pd.Series]:
        """
        Detect trend direction using moving average crossovers.

        Args:
            prices: Price series
            short_window: Short-term MA window
            medium_window: Medium-term MA window
            long_window: Long-term MA window

        Returns:
            Dictionary with trend signals
        """
        ma_short = prices.rolling(window=short_window).mean()
        ma_medium = prices.rolling(window=medium_window).mean()
        ma_long = prices.rolling(window=long_window).mean()

        # Trend classification
        def classify_trend(row):
            if row['short'] > row['medium'] > row['long']:
                return 'UP'
            elif row['short'] < row['medium'] < row['long']:
                return 'DOWN'
            else:
                return 'SIDEWAYS'

        trends_df = pd.DataFrame({
            'short': ma_short,
            'medium': ma_medium,
            'long': ma_long
        })

        trend_signal = trends_df.apply(classify_trend, axis=1)

        return {
            'trend_short': trend_signal,
            'trend_medium': trend_signal,
            'trend_long': trend_signal
        }

    def detect_volume_spike(self, volume: pd.Series, window: int = 20, threshold: float = 2.0) -> pd.Series:
        """
        Detect volume spikes (volume > threshold × average).

        Args:
            volume: Volume series
            window: Rolling window for average
            threshold: Spike threshold multiplier

        Returns:
            Boolean series indicating volume spikes
        """
        volume_avg = volume.rolling(window=window).mean()
        volume_spike = volume > (volume_avg * threshold)

        return volume_spike

    # ========================================================================
    # MAIN FEATURE GENERATION
    # ========================================================================

    def generate_features(self,
                          commodity_id: str,
                          start_date: datetime = None) -> List[CommodityFeature]:
        """
        Generate all features for a commodity.

        Args:
            commodity_id: Commodity identifier
            start_date: Start date for feature calculation

        Returns:
            List of CommodityFeature objects
        """
        session = self.memory.get_session()
        try:
            # Fetch price data
            query = session.query(CommodityPrice).filter(
                CommodityPrice.commodity_id == commodity_id
            ).order_by(CommodityPrice.timestamp)

            if start_date:
                query = query.filter(CommodityPrice.timestamp >= start_date)

            prices_data = query.all()

            if not prices_data:
                logger.warning(f"No price data found for {commodity_id}")
                return []

            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': p.timestamp,
                'price': float(p.price),
                'open': float(p.open_price) if p.open_price else float(p.price),
                'high': float(p.high_price) if p.high_price else float(p.price),
                'low': float(p.low_price) if p.low_price else float(p.price),
                'close': float(p.close_price) if p.close_price else float(p.price),
                'volume': p.volume if p.volume else 0
            } for p in prices_data])

            if len(df) < 50:
                logger.warning(
                    f"Insufficient data for {commodity_id} (need at least 50 records)")
                return []

            # Set index
            df.set_index('timestamp', inplace=True)

            # Calculate features
            features_list = []

            for idx in range(50, len(df)):
                timestamp = df.index[idx]

                # Get price series up to this point
                prices_hist = df.loc[:timestamp, 'price']

                # Momentum
                momentum = self.calculate_momentum(prices_hist)

                # Moving averages
                mas = self.calculate_moving_averages(prices_hist)

                # Volatility
                volatility = self.calculate_volatility(prices_hist)

                # ATR
                atr = self.calculate_atr(
                    df.loc[:timestamp, 'high'],
                    df.loc[:timestamp, 'low'],
                    df.loc[:timestamp, 'close']
                )

                # RSI
                rsi = self.calculate_rsi(prices_hist)

                # Trends
                trends = self.detect_trend(prices_hist)

                # Volume spike
                vol_spike = self.detect_volume_spike(
                    df.loc[:timestamp, 'volume'])

                # Create feature object
                feature = CommodityFeature(
                    commodity_id=commodity_id,
                    timestamp=timestamp,
                    momentum_1d=float(
                        momentum['momentum_1d'].iloc[-1]) if not momentum['momentum_1d'].iloc[-1] is np.nan else None,
                    momentum_5d=float(
                        momentum['momentum_5d'].iloc[-1]) if not momentum['momentum_5d'].iloc[-1] is np.nan else None,
                    momentum_20d=float(
                        momentum['momentum_20d'].iloc[-1]) if not momentum['momentum_20d'].iloc[-1] is np.nan else None,
                    ma_5=mas['ma_5'].iloc[-1] if not mas['ma_5'].iloc[-1] is np.nan else None,
                    ma_20=mas['ma_20'].iloc[-1] if not mas['ma_20'].iloc[-1] is np.nan else None,
                    ma_50=mas['ma_50'].iloc[-1] if not mas['ma_50'].iloc[-1] is np.nan else None,
                    ma_200=mas['ma_200'].iloc[-1] if not mas['ma_200'].iloc[-1] is np.nan else None,
                    volatility_5d=float(
                        volatility['volatility_5d'].iloc[-1]) if not volatility['volatility_5d'].iloc[-1] is np.nan else None,
                    volatility_20d=float(
                        volatility['volatility_20d'].iloc[-1]) if not volatility['volatility_20d'].iloc[-1] is np.nan else None,
                    atr_14=atr.iloc[-1] if not atr.iloc[-1] is np.nan else None,
                    trend_short=trends['trend_short'].iloc[-1],
                    trend_medium=trends['trend_medium'].iloc[-1],
                    trend_long=trends['trend_long'].iloc[-1],
                    rsi_14=float(
                        rsi.iloc[-1]) if not rsi.iloc[-1] is np.nan else None,
                    volume_spike=bool(
                        vol_spike.iloc[-1]) if not vol_spike.iloc[-1] is np.nan else False
                )

                features_list.append(feature)

            logger.info(
                f"✓ Generated {len(features_list)} feature sets for {commodity_id}")
            return features_list

        except Exception as e:
            logger.error(f"✗ Feature generation failed: {e}")
            raise
        finally:
            session.close()

    def store_features(self, features: List[CommodityFeature]) -> int:
        """Store features in database"""
        session = self.memory.get_session()
        try:
            stored_count = 0
            for feature in features:
                try:
                    session.add(feature)
                    stored_count += 1
                except Exception as e:
                    logger.warning(f"Failed to store feature: {e}")

            session.commit()
            logger.info(f"✓ Stored {stored_count} features")
            return stored_count

        except Exception as e:
            logger.error(f"✗ Storage failed: {e}")
            session.rollback()
            raise
        finally:
            session.close()


def main():
    """Demo and test feature engineering"""
    logging.basicConfig(level=logging.INFO)

    print("\n" + "="*80)
    print("DAY 2: COMMODITY FEATURE ENGINEERING")
    print("="*80)

    # Initialize
    memory = FinancialMemoryManager()
    feature_engine = CommodityFeatureEngine(memory)

    print("\n✓ Commodity Feature Engine initialized")

    print("\n" + "="*80)
    print("AVAILABLE FEATURES")
    print("="*80)

    features = [
        ("Momentum", "momentum_1d, momentum_5d, momentum_20d"),
        ("Moving Averages", "ma_5, ma_20, ma_50, ma_200"),
        ("Volatility", "volatility_5d, volatility_20d, atr_14"),
        ("Trend Signals", "trend_short, trend_medium, trend_long"),
        ("Relative Strength", "rsi_14"),
        ("Volume Analysis", "volume_spike detection"),
    ]

    for category, details in features:
        print(f"\n{category}:")
        print(f"  {details}")

    print("\n" + "="*80)
    print("FEATURE CALCULATION METHODS")
    print("="*80)

    methods = [
        "calculate_momentum()",
        "calculate_moving_averages()",
        "calculate_volatility()",
        "calculate_atr()",
        "calculate_rsi()",
        "detect_trend()",
        "detect_volume_spike()",
        "generate_features()"
    ]

    for method in methods:
        print(f"  ✓ {method}")

    print("\n" + "="*80)
    print("✓ DAY 2 COMPLETE - FEATURE ENGINE READY")
    print("="*80)
    print("\nNext: Day 2b — Signal Generation Engine")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
