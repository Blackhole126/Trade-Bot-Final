"""
Multi-Source Data Provider with Intelligent Fallback
Provides robust data fetching with automatic fallback between multiple free data sources
Priority: Fyers -> Dhan -> Alpha Vantage -> CoinGecko -> Yahoo Finance (with rate limiting)
"""

import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Rate limit configuration
RATE_LIMITS = {
    'yahoo': {'calls': 60, 'window': 3600, 'cooldown': 3600},  # 60 calls per hour, 1h cooldown
    'alpha_vantage': {'calls': 5, 'window': 60, 'cooldown': 60},  # 5 calls per minute
    'coingecko': {'calls': 10, 'window': 60, 'cooldown': 300},  # 10 calls per minute, 5m cooldown
    'finnhub': {'calls': 30, 'window': 60, 'cooldown': 60},  # 30 calls per minute
}

# Cache file paths
RATE_LIMIT_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'data', 'rate_limit_cache.json')
DATA_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'data', 'data_cache.json')


class CircuitBreaker:
    """Circuit breaker pattern to prevent cascading failures"""
    
    def __init__(self, failure_threshold=5, recovery_time=300):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time  # seconds
        self.failures = 0
        self.last_failure_time = 0
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
    def record_success(self):
        self.failures = 0
        self.state = 'CLOSED'
        
    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"Circuit breaker OPENED after {self.failures} failures")
            
    def can_proceed(self) -> bool:
        if self.state == 'CLOSED':
            return True
        elif self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_time:
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker HALF_OPEN - testing")
                return True
            return False
        else:  # HALF_OPEN
            return True
            
    def reset(self):
        self.failures = 0
        self.last_failure_time = 0
        self.state = 'CLOSED'


class RateLimitTracker:
    """Track rate limits across all data sources"""
    
    def __init__(self):
        self.cache = self._load_cache()
        
    def _load_cache(self) -> Dict:
        """Load rate limit cache from disk"""
        try:
            if os.path.exists(RATE_LIMIT_CACHE_FILE):
                with open(RATE_LIMIT_CACHE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load rate limit cache: {e}")
        return {}
        
    def _save_cache(self):
        """Save rate limit cache to disk"""
        try:
            os.makedirs(os.path.dirname(RATE_LIMIT_CACHE_FILE), exist_ok=True)
            with open(RATE_LIMIT_CACHE_FILE, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save rate limit cache: {e}")
            
    def is_rate_limited(self, source: str, ticker: str) -> bool:
        """Check if a source is rate limited for a specific ticker"""
        key = f"{source}:{ticker}"
        if key not in self.cache:
            return False
            
        last_limit = self.cache[key]
        cooldown = RATE_LIMITS.get(source, {}).get('cooldown', 3600)
        
        if time.time() - last_limit < cooldown:
            remaining = int(cooldown - (time.time() - last_limit))
            logger.warning(f"{source} rate limited for {ticker} - retry in {remaining//60}m")
            return True
            
        # Cache expired, remove it
        del self.cache[key]
        self._save_cache()
        return False
        
    def record_rate_limit(self, source: str, ticker: str):
        """Record a rate limit event"""
        key = f"{source}:{ticker}"
        self.cache[key] = time.time()
        self._save_cache()
        logger.warning(f"Rate limit triggered for {ticker} on {source}")
        
    def clear_cache(self, source: str = None):
        """Clear rate limit cache for a specific source or all"""
        if source:
            self.cache = {k: v for k, v in self.cache.items() if not k.startswith(f"{source}:")}
        else:
            self.cache = {}
        self._save_cache()


class MultiSourceDataProvider:
    """
    Intelligent multi-source data provider with automatic fallback
    Priority chain: Fyers -> Dhan -> Alpha Vantage -> CoinGecko -> Yahoo Finance
    """
    
    def __init__(self):
        self.rate_limit_tracker = RateLimitTracker()
        self.circuit_breakers = {
            'fyers': CircuitBreaker(failure_threshold=5, recovery_time=300),
            'dhan': CircuitBreaker(failure_threshold=5, recovery_time=300),
            'alpha_vantage': CircuitBreaker(failure_threshold=3, recovery_time=60),
            'coingecko': CircuitBreaker(failure_threshold=3, recovery_time=300),
            'yahoo': CircuitBreaker(failure_threshold=3, recovery_time=3600),
        }
        self.data_cache = self._load_data_cache()
        
    def _load_data_cache(self) -> Dict:
        """Load recent data cache to avoid repeated API calls"""
        try:
            if os.path.exists(DATA_CACHE_FILE):
                with open(DATA_CACHE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load data cache: {e}")
        return {}
        
    def _save_data_cache(self):
        """Save data cache to disk"""
        try:
            os.makedirs(os.path.dirname(DATA_CACHE_FILE), exist_ok=True)
            # Clean old entries (older than 1 hour)
            current_time = time.time()
            self.data_cache = {
                k: v for k, v in self.data_cache.items()
                if current_time - v.get('timestamp', 0) < 3600
            }
            with open(DATA_CACHE_FILE, 'w') as f:
                json.dump(self.data_cache, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save data cache: {e}")
            
    def get_cached_data(self, ticker: str, max_age_seconds: int = 300) -> Optional[pd.DataFrame]:
        """Get cached data if it's fresh enough"""
        if ticker in self.data_cache:
            cached = self.data_cache[ticker]
            age = time.time() - cached.get('timestamp', 0)
            if age < max_age_seconds:
                logger.debug(f"Using cached data for {ticker} (age: {int(age)}s)")
                try:
                    df = pd.DataFrame(cached['data'])
                    df.index = pd.to_datetime(df['timestamp'])
                    return df
                except Exception as e:
                    logger.debug(f"Failed to parse cached data: {e}")
        return None
        
    def cache_data(self, ticker: str, df: pd.DataFrame):
        """Cache data for future use"""
        try:
            data_dict = df.reset_index().to_dict('records')
            self.data_cache[ticker] = {
                'timestamp': time.time(),
                'data': data_dict
            }
            self._save_data_cache()
        except Exception as e:
            logger.debug(f"Failed to cache data: {e}")
    
    def get_stock_data(self, ticker: str, period: str = "1d", 
                      fyers_client=None, dhan_client=None) -> Optional[pd.DataFrame]:
        """
        Get stock data with intelligent fallback through all sources
        
        Args:
            ticker: Stock symbol (e.g., 'RELIANCE.NS', 'TATAMOTORS.NS')
            period: Time period ('1d', '5d', '1mo', etc.)
            fyers_client: Optional Fyers client instance
            dhan_client: Optional Dhan client instance
            
        Returns:
            pandas DataFrame with OHLCV data, or None if all sources fail
        """
        # Normalize ticker format
        if ticker.startswith('$'):
            ticker = ticker[1:] + '.NS'
        elif '.' not in ticker and not ticker.isdigit():
            ticker = ticker + '.NS'
            
        # Check cache first
        cached = self.get_cached_data(ticker, max_age_seconds=300 if period == "1d" else 3600)
        if cached is not None:
            return cached
        
        # Try each source in priority order
        sources = [
            ('fyers', self._try_fyers, [ticker, fyers_client]),
            ('dhan', self._try_dhan, [ticker, dhan_client]),
            ('alpha_vantage', self._try_alpha_vantage, [ticker]),
            ('coingecko', self._try_coingecko, [ticker]),
            ('yahoo', self._try_yahoo, [ticker, period]),
        ]
        
        last_error = None
        
        for source_name, method, args in sources:
            # Check circuit breaker
            cb = self.circuit_breakers[source_name]
            if not cb.can_proceed():
                logger.warning(f"Skipping {source_name} - circuit breaker OPEN")
                continue
                
            # Check rate limits
            if self.rate_limit_tracker.is_rate_limited(source_name, ticker):
                continue
                
            try:
                logger.debug(f"Trying {source_name} for {ticker}...")
                result = method(*args)
                
                if result is not None and not result.empty:
                    logger.info(f"Successfully fetched data from {source_name} for {ticker}")
                    cb.record_success()
                    
                    # Cache the successful result
                    self.cache_data(ticker, result)
                    
                    return result
                else:
                    logger.debug(f"{source_name} returned no data for {ticker}")
                    
            except Exception as e:
                error_msg = str(e)
                last_error = e
                
                # Handle rate limits specifically
                if "Too Many Requests" in error_msg or "rate limit" in error_msg.lower():
                    self.rate_limit_tracker.record_rate_limit(source_name, ticker)
                    cb.record_failure()
                else:
                    logger.warning(f"{source_name} failed for {ticker}: {e}")
                    cb.record_failure()
                    
        # All sources failed
        logger.error(f"All data sources failed for {ticker} (last error: {last_error})")
        return None
        
    def _try_fyers(self, ticker: str, fyers_client) -> Optional[pd.DataFrame]:
        """Try fetching from Fyers API"""
        if not fyers_client:
            logger.debug("Fyers client not available")
            return None
            
        try:
            # Get quotes from Fyers
            quotes = fyers_client.quotes({"symbols": [ticker]})
            if quotes and 'quotes' in quotes and ticker in quotes['quotes']:
                quote = quotes['quotes'][ticker]
                price_data = {
                    'timestamp': datetime.now(),
                    'open': quote.get('open', 0),
                    'high': quote.get('high', 0),
                    'low': quote.get('low', 0),
                    'close': quote.get('ltp', 0),
                    'volume': quote.get('volume', 0)
                }
                df = pd.DataFrame([price_data])
                df.set_index('timestamp', inplace=True)
                return df
        except Exception as e:
            logger.debug(f"Fyers fetch failed: {e}")
            
        return None
        
    def _try_dhan(self, ticker: str, dhan_client) -> Optional[pd.DataFrame]:
        """Try fetching from Dhan API"""
        if not dhan_client:
            logger.debug("Dhan client not available")
            return None
            
        try:
            # Convert ticker to Dhan format
            if '.NS' in ticker:
                symbol = ticker.replace('.NS', '')
                exchange = 'NSE'
            elif '.BO' in ticker:
                symbol = ticker.replace('.BO', '')
                exchange = 'BSE'
            else:
                symbol = ticker
                exchange = 'NSE'
                
            # Fetch from Dhan
            # Note: Adjust based on actual Dhan API methods
            ltp = dhan_client.fetch_ltp(symbol, exchange)
            if ltp and ltp > 0:
                price_data = {
                    'timestamp': datetime.now(),
                    'open': ltp,
                    'high': ltp,
                    'low': ltp,
                    'close': ltp,
                    'volume': 0
                }
                df = pd.DataFrame([price_data])
                df.set_index('timestamp', inplace=True)
                return df
        except Exception as e:
            logger.debug(f"Dhan fetch failed: {e}")
            
        return None
        
    def _try_alpha_vantage(self, ticker: str) -> Optional[pd.DataFrame]:
        """Try fetching from Alpha Vantage API"""
        api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            logger.debug("Alpha Vantage API key not configured")
            return None
            
        try:
            # Remove .NS suffix for Alpha Vantage
            symbol = ticker.replace('.NS', '').replace('.BO', '')
            
            # Try different endpoints
            endpoints = [
                f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}",
                f"https://alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
            ]
            
            for url in endpoints:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check for rate limit message
                    if "Note" in data and "rate limit" in str(data.get("Note", "")).lower():
                        raise Exception("Alpha Vantage rate limit exceeded")
                        
                    if "Global Quote" in data and data["Global Quote"]:
                        quote = data["Global Quote"]
                        price_data = {
                            'timestamp': datetime.now(),
                            'open': float(quote.get('02. open', 0)),
                            'high': float(quote.get('03. high', 0)),
                            'low': float(quote.get('04. low', 0)),
                            'close': float(quote.get('05. price', 0)),
                            'volume': int(quote.get('06. volume', 0))
                        }
                        df = pd.DataFrame([price_data])
                        df.set_index('timestamp', inplace=True)
                        return df
                        
        except Exception as e:
            logger.debug(f"Alpha Vantage fetch failed: {e}")
            
        return None
        
    def _try_coingecko(self, ticker: str) -> Optional[pd.DataFrame]:
        """Try fetching from CoinGecko API (for crypto-related stocks/ETFs)"""
        try:
            # CoinGecko is primarily for crypto, but can be used for some ETFs
            # This is a fallback for very specific cases
            symbol = ticker.replace('.NS', '').replace('.BO', '').lower()
            
            # Try to find matching coin
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd&include_24hr_vol=true"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if symbol in data:
                    coin_data = data[symbol]
                    price = coin_data.get('usd', 0)
                    volume = coin_data.get('usd_24h_vol', 0)
                    
                    if price > 0:
                        price_data = {
                            'timestamp': datetime.now(),
                            'Open': price,
                            'High': price,
                            'Low': price,
                            'Close': price,
                            'Volume': volume
                        }
                        df = pd.DataFrame([price_data])
                        df.set_index('timestamp', inplace=True)
                        return df
                        
        except Exception as e:
            logger.debug(f"CoinGecko fetch failed: {e}")
            
        return None
        
    def _try_yahoo(self, ticker: str, period: str) -> Optional[pd.DataFrame]:
        """Try fetching from Yahoo Finance (last resort due to rate limits)"""
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            
            if not df.empty:
                return df
            else:
                logger.debug(f"Yahoo Finance returned empty data for {ticker}")
                
        except Exception as e:
            error_msg = str(e)
            if "Too Many Requests" in error_msg or "rate limited" in error_msg.lower():
                raise  # Re-raise to trigger rate limit handling
            else:
                logger.debug(f"Yahoo Finance failed: {e}")
                
        return None
        
    def get_live_prices(self, tickers: List[str], 
                       fyers_client=None, dhan_client=None) -> Dict[str, Dict[str, Any]]:
        """
        Get live prices for multiple tickers with automatic fallback
        
        Args:
            tickers: List of ticker symbols
            fyers_client: Optional Fyers client
            dhan_client: Optional Dhan client
            
        Returns:
            Dictionary of ticker -> price data
        """
        results = {}
        
        for ticker in tickers:
            try:
                df = self.get_stock_data(
                    ticker=ticker,
                    period="1d",
                    fyers_client=fyers_client,
                    dhan_client=dhan_client
                )
                
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    results[ticker] = {
                        'price': float(latest['Close']),
                        'volume': float(latest.get('Volume', 0)),
                        'open': float(latest.get('Open', 0)),
                        'high': float(latest.get('High', 0)),
                        'low': float(latest.get('Low', 0)),
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    logger.warning(f"No data available for {ticker}")
                    results[ticker] = {'error': 'No data available'}
                    
            except Exception as e:
                logger.error(f"Error fetching {ticker}: {e}")
                results[ticker] = {'error': str(e)}
                
        return results
        
    def reset_all_circuit_breakers(self):
        """Reset all circuit breakers (useful for testing or manual recovery)"""
        for cb in self.circuit_breakers.values():
            cb.reset()
        logger.info("All circuit breakers reset")
        
    def get_status_report(self) -> Dict[str, Any]:
        """Get current status of all data sources"""
        status = {}
        for source_name, cb in self.circuit_breakers.items():
            status[source_name] = {
                'circuit_breaker_state': cb.state,
                'failures': cb.failures,
                'can_proceed': cb.can_proceed()
            }
        return status


# Global instance for reuse
_data_provider_instance: Optional[MultiSourceDataProvider] = None


def get_data_provider() -> MultiSourceDataProvider:
    """Get or create global data provider instance"""
    global _data_provider_instance
    if _data_provider_instance is None:
        _data_provider_instance = MultiSourceDataProvider()
    return _data_provider_instance


# Convenience functions for backward compatibility
def get_stock_data_fallback(ticker: str, period: str = "1d",
                           fyers_client=None, dhan_client=None) -> Optional[pd.DataFrame]:
    """
    Backward compatible function for get_stock_data_fyers_or_yf
    Uses new multi-source provider internally
    """
    provider = get_data_provider()
    return provider.get_stock_data(ticker, period, fyers_client, dhan_client)


def get_live_prices_multi(tickers: List[str],
                         fyers_client=None, dhan_client=None) -> Dict[str, Dict[str, Any]]:
    """
    Get live prices for multiple tickers with automatic fallback
    """
    provider = get_data_provider()
    return provider.get_live_prices(tickers, fyers_client, dhan_client)
