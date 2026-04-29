"""
Backend Request Cache and Rate Limit Handler
Prevents duplicate external API calls and implements fail-fast on rate limits
"""

import time
import json
from typing import Dict, Any, Optional
from pathlib import Path

class BackendRequestCache:
    def __init__(self, cache_ttl: int = 300):  # 5 minutes default TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = cache_ttl
        self.rate_limit_tracker: Dict[str, float] = {}
        
    def get_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key from endpoint and parameters"""
        param_str = json.dumps(params, sort_keys=True)
        return f"{endpoint}:{hash(param_str)}"
    
    def is_cached(self, cache_key: str) -> bool:
        """Check if data is cached and not expired"""
        if cache_key not in self.cache:
            return False
            
        cached_data = self.cache[cache_key]
        age = time.time() - cached_data['timestamp']
        return age < self.cache_ttl
    
    def get_cached(self, cache_key: str) -> Optional[Any]:
        """Get cached data if available and not expired"""
        if self.is_cached(cache_key):
            print(f"[CACHE] Hit for {cache_key}")
            return self.cache[cache_key]['data']
        return None
    
    def set_cached(self, cache_key: str, data: Any) -> None:
        """Cache data with timestamp"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        print(f"[CACHE] Stored {cache_key}")
    
    def is_rate_limited(self, api_name: str) -> bool:
        """Check if API is currently rate limited"""
        if api_name in self.rate_limit_tracker:
            time_since_limit = time.time() - self.rate_limit_tracker[api_name]
            return time_since_limit < 60  # 1 minute cooldown
        return False
    
    def mark_rate_limited(self, api_name: str) -> None:
        """Mark API as rate limited"""
        self.rate_limit_tracker[api_name] = time.time()
        print(f"[RATE_LIMIT] {api_name} marked as rate limited")
    
    def clear_rate_limit(self, api_name: str) -> None:
        """Clear rate limit for API"""
        if api_name in self.rate_limit_tracker:
            del self.rate_limit_tracker[api_name]
            print(f"[RATE_LIMIT] {api_name} rate limit cleared")

# Global cache instance
backend_cache = BackendRequestCache()