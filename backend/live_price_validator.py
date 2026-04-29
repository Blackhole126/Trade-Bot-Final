"""
LIVE PRICE VALIDATOR - ENFORCES SINGLE SOURCE OF TRUTH
Ensures all current prices come from live Yahoo Finance API, not cached data
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, Optional, Tuple
import time

logger = logging.getLogger(__name__)

class LivePriceValidator:
    """
    Enforces live price fetching and validates data integrity
    """
    
    def __init__(self):
        self.max_cache_age_minutes = 15  # Cache expires after 15 minutes
    
    def get_live_price_data(self, symbol: str) -> Dict:
        """
        Get LIVE current price data directly from Yahoo Finance
        
        Returns:
            Dict with live price data and metadata
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get live info (current price, market status, etc.)
            info = ticker.info
            
            # Get latest trading day data
            hist = ticker.history(period="1d", interval="1m")
            
            if hist.empty:
                # Fallback to daily data
                hist = ticker.history(period="2d")
            
            if hist.empty:
                raise ValueError(f"No live data available for {symbol}")
            
            latest_price = float(hist['Close'].iloc[-1])
            latest_timestamp = hist.index[-1]
            
            # Extract key live data
            live_data = {
                'symbol': symbol,
                'current_price': latest_price,
                'price_timestamp': latest_timestamp.isoformat(),
                'price_source': 'yahoo_finance_live',
                'exchange': info.get('exchange', 'UNKNOWN'),
                'currency': info.get('currency', 'UNKNOWN'),
                'market_state': info.get('marketState', 'UNKNOWN'),
                'is_delayed': info.get('exchangeDataDelayedBy', 0) > 0,
                'delay_minutes': info.get('exchangeDataDelayedBy', 0),
                'regular_market_price': info.get('regularMarketPrice'),
                'regular_market_time': info.get('regularMarketTime'),
                'previous_close': info.get('previousClose'),
                'day_change': info.get('regularMarketChange'),
                'day_change_percent': info.get('regularMarketChangePercent'),
                'day_high': info.get('dayHigh'),
                'day_low': info.get('dayLow'),
                'volume': info.get('volume'),
                'fetch_timestamp': datetime.now().isoformat(),
                'data_freshness': 'LIVE'
            }
            
            # Validate price integrity
            validation = self._validate_price_integrity(live_data)
            live_data['validation'] = validation
            
            return live_data
            
        except Exception as e:
            logger.error(f"Failed to get live price for {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'price_source': 'FAILED',
                'fetch_timestamp': datetime.now().isoformat()
            }
    
    def _validate_price_integrity(self, live_data: Dict) -> Dict:
        """
        Validate price data integrity
        """
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }
        
        current_price = live_data.get('current_price')
        regular_price = live_data.get('regular_market_price')
        
        # Check if prices are reasonable
        if current_price and current_price <= 0:
            validation['errors'].append(f"Invalid current_price: {current_price}")
            validation['is_valid'] = False
        
        # Check price consistency
        if current_price and regular_price:
            price_diff_pct = abs(current_price - regular_price) / regular_price * 100
            if price_diff_pct > 5:  # More than 5% difference
                validation['warnings'].append(
                    f"Price inconsistency: current={current_price:.2f} vs regular={regular_price:.2f} "
                    f"({price_diff_pct:.2f}% difference)"
                )
        
        # Check data freshness
        if live_data.get('is_delayed'):
            delay = live_data.get('delay_minutes', 0)
            validation['warnings'].append(f"Data is delayed by {delay} minutes")
        
        # Check market state
        market_state = live_data.get('market_state', '').upper()
        if market_state not in ['REGULAR', 'PRE', 'POST']:
            validation['warnings'].append(f"Market state: {market_state}")
        
        return validation
    
    def enforce_live_price_in_prediction(self, prediction_data: Dict, symbol: str) -> Dict:
        """
        Enforce live price in prediction data and recalculate returns
        
        Args:
            prediction_data: Original prediction data
            symbol: Stock symbol
            
        Returns:
            Updated prediction data with live prices
        """
        # Get live price
        live_data = self.get_live_price_data(symbol)
        
        if 'error' in live_data:
            prediction_data['price_validation'] = {
                'status': 'FAILED',
                'error': live_data['error'],
                'warning': 'Using cached price - predictions may be inaccurate'
            }
            return prediction_data
        
        # Extract live price
        live_price = live_data['current_price']
        cached_price = prediction_data.get('current_price', 0)
        
        # Calculate price difference
        if cached_price > 0:
            price_diff_pct = ((live_price - cached_price) / cached_price) * 100
        else:
            price_diff_pct = 0
        
        # Update prediction with live price
        prediction_data['current_price'] = live_price
        prediction_data['price_metadata'] = {
            'price_source': live_data['price_source'],
            'price_timestamp': live_data['price_timestamp'],
            'exchange': live_data['exchange'],
            'currency': live_data['currency'],
            'is_delayed': live_data['is_delayed'],
            'delay_minutes': live_data.get('delay_minutes', 0),
            'market_state': live_data['market_state'],
            'data_freshness': live_data['data_freshness'],
            'validation': live_data['validation']
        }
        
        # Recalculate predicted returns with live price
        if 'predicted_price' in prediction_data:
            predicted_price = prediction_data['predicted_price']
            new_predicted_return = ((predicted_price - live_price) / live_price) * 100
            
            prediction_data['predicted_return'] = round(new_predicted_return, 2)
            prediction_data['price_correction'] = {
                'cached_price': cached_price,
                'live_price': live_price,
                'price_difference_pct': round(price_diff_pct, 2),
                'return_recalculated': True
            }
            logger.info(
                f"Live price applied for {symbol}: reference={live_price:.2f}, "
                f"predicted={predicted_price:.2f}, expected_return={new_predicted_return:.2f}%"
            )
            # Log significant price differences
            if abs(price_diff_pct) > 1:
                logger.warning(
                    f"Significant price difference for {symbol}: "
                    f"cached={cached_price:.2f} vs live={live_price:.2f} "
                    f"({price_diff_pct:+.2f}%)"
                )
        
        return prediction_data
    
    def validate_cached_data_freshness(self, cached_data: Dict, symbol: str) -> Dict:
        """
        Validate if cached data is fresh enough for trading decisions
        
        Returns:
            Dict with validation results
        """
        validation = {
            'is_fresh': False,
            'age_minutes': 0,
            'recommendation': 'REFRESH_REQUIRED',
            'warnings': []
        }
        
        try:
            # Check fetch timestamp
            fetch_time_str = cached_data.get('fetch_time') or cached_data.get('metadata', {}).get('fetch_timestamp')
            
            if not fetch_time_str:
                validation['warnings'].append("No fetch timestamp found in cached data")
                return validation
            
            fetch_time = pd.to_datetime(fetch_time_str)
            now = pd.Timestamp.now()
            
            # Calculate age
            age_delta = now - fetch_time
            age_minutes = age_delta.total_seconds() / 60
            
            validation['age_minutes'] = round(age_minutes, 1)
            
            # Check if fresh enough
            if age_minutes <= self.max_cache_age_minutes:
                validation['is_fresh'] = True
                validation['recommendation'] = 'CACHE_OK'
            elif age_minutes <= 60:  # 1 hour
                validation['recommendation'] = 'REFRESH_RECOMMENDED'
                validation['warnings'].append(f"Data is {age_minutes:.1f} minutes old")
            else:
                validation['recommendation'] = 'REFRESH_REQUIRED'
                validation['warnings'].append(f"Data is {age_minutes:.1f} minutes old - too stale for trading")
            
            # Check if market is open
            latest_price_date = None
            if 'price_history' in cached_data and cached_data['price_history']:
                latest_entry = cached_data['price_history'][-1]
                latest_price_date = pd.to_datetime(latest_entry.get('Date'))
            
            if latest_price_date:
                price_age_days = (now - latest_price_date).days
                if price_age_days > 1:
                    validation['warnings'].append(f"Latest price is {price_age_days} days old")
            
        except Exception as e:
            validation['warnings'].append(f"Error validating cache freshness: {e}")
        
        return validation

def create_live_price_endpoint():
    """
    Create a new API endpoint that ONLY returns live prices
    """
    endpoint_code = '''
@app.get("/live/price/{symbol}")
async def get_live_price(symbol: str):
    """Get LIVE current price - NO CACHE, ALWAYS FRESH"""
    validator = LivePriceValidator()
    live_data = validator.get_live_price_data(symbol)
    
    if 'error' in live_data:
        raise HTTPException(status_code=404, detail=live_data['error'])
    
    return {
        'symbol': symbol,
        'current_price': live_data['current_price'],
        'price_source': live_data['price_source'],
        'price_timestamp': live_data['price_timestamp'],
        'exchange': live_data['exchange'],
        'currency': live_data['currency'],
        'is_delayed': live_data['is_delayed'],
        'delay_minutes': live_data.get('delay_minutes', 0),
        'market_state': live_data['market_state'],
        'day_change': live_data.get('day_change'),
        'day_change_percent': live_data.get('day_change_percent'),
        'validation': live_data['validation'],
        'fetch_timestamp': live_data['fetch_timestamp']
    }
'''
    return endpoint_code