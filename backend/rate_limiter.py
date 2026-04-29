"""
Rate Limiting Module for FastAPI
Implements rate limiting to prevent API abuse using FastAPI dependencies

MULTI-PROCESS CONSIDERATION:
=============================
This rate limiter uses in-memory storage (Python dictionary) which is 
NOT shared across multiple processes.

CURRENT DEPLOYMENT: Single Process (Works Perfectly)
- Command: python api_server.py
- Workers: 1 (default)
- Status: Rate limiting works correctly ✓

MULTI-PROCESS DEPLOYMENT: Requires Upgrade
If you scale to multiple processes (--workers > 1) or multiple instances,
each process will have separate rate limit counters.

Example with 4 workers:
- Limit: 10 requests/minute
- Client can make: 40 requests (10 to each worker)
- Expected: Block after 10
- Actual: All 40 allowed ✗

SOLUTIONS FOR MULTI-PROCESS (when scaling):
1. External Rate Limiting (RECOMMENDED)
   - Use Nginx limit_req module
   - Use API Gateway (AWS, Azure, GCP)
   - No code changes needed
   
2. Redis Backend (CODE CHANGE)
   - Shared storage across all processes
   - Fast, reliable, industry standard
   - Requires: Redis server + redis-py package
   
3. Single Process with Async (CURRENT - SUFFICIENT)
   - FastAPI's async nature is very efficient
   - One process can handle thousands of concurrent requests
   - No multi-process needed for most workloads

For 95% of use cases, single-process FastAPI is sufficient and efficient.
Consider scaling only if you have >1000 concurrent users.
"""

from datetime import datetime, timedelta
from collections import defaultdict
import logging
from typing import Optional

from fastapi import Request, HTTPException, status

from config import RATE_LIMIT_PER_MINUTE, RATE_LIMIT_PER_HOUR

logger = logging.getLogger(__name__)

# In-memory storage for rate limiting
# NOTE: This is per-process storage. See module docstring for multi-process considerations.
request_counts = defaultdict(lambda: {'minute': [], 'hour': []})


def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0]
    return request.client.host if request.client else 'unknown'


async def check_rate_limit(request: Request) -> str:
    """
    FastAPI dependency to check rate limits
    Usage: client_ip = Depends(check_rate_limit)
    """
    client_ip = get_client_ip(request)
    current_time = datetime.now()
    
    minute_ago = current_time - timedelta(minutes=1)
    hour_ago = current_time - timedelta(hours=1)
    
    # Clean up old requests
    request_counts[client_ip]['minute'] = [
        t for t in request_counts[client_ip]['minute'] if t > minute_ago
    ]
    request_counts[client_ip]['hour'] = [
        t for t in request_counts[client_ip]['hour'] if t > hour_ago
    ]
    
    minute_count = len(request_counts[client_ip]['minute'])
    hour_count = len(request_counts[client_ip]['hour'])
    
    # Check minute limit
    if minute_count >= RATE_LIMIT_PER_MINUTE:
        logger.warning(f"Rate limit exceeded (minute) for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                'error': 'Rate limit exceeded',
                'message': f'Maximum {RATE_LIMIT_PER_MINUTE} requests per minute allowed',
                'retry_after': 60
            }
        )
    
    # Check hour limit
    if hour_count >= RATE_LIMIT_PER_HOUR:
        logger.warning(f"Rate limit exceeded (hour) for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                'error': 'Rate limit exceeded',
                'message': f'Maximum {RATE_LIMIT_PER_HOUR} requests per hour allowed',
                'retry_after': 3600
            }
        )
    
    # Record this request
    request_counts[client_ip]['minute'].append(current_time)
    request_counts[client_ip]['hour'].append(current_time)
    
    # Periodic bulk cleanup: Remove all stale IPs every 100 requests
    # This prevents memory from growing indefinitely with many unique IPs
    if len(request_counts) > 100:  # Only if we have many IPs
        total_requests = sum(len(data['hour']) for data in request_counts.values())
        if total_requests % 100 == 0:
            cleanup_time = current_time - timedelta(hours=2)
            ips_to_remove = [
                ip for ip, data in list(request_counts.items())
                if not data['hour'] or all(t < cleanup_time for t in data['hour'])
            ]
            
            for ip in ips_to_remove[:500]:  # Limit to 500 removals per cleanup
                del request_counts[ip]
            
            if ips_to_remove:
                logger.info(f"Rate limiter cleanup: Removed {len(ips_to_remove[:500])} stale IPs. "
                           f"Active IPs: {len(request_counts)}")
    
    return client_ip


def get_rate_limit_status(client_ip: Optional[str] = None, request: Optional[Request] = None) -> dict:
    """Get current rate limit status for a client"""
    if client_ip is None and request is not None:
        client_ip = get_client_ip(request)
    elif client_ip is None:
        return {'error': 'No client IP provided'}
    
    current_time = datetime.now()
    minute_ago = current_time - timedelta(minutes=1)
    hour_ago = current_time - timedelta(hours=1)
    
    minute_requests = len([t for t in request_counts[client_ip]['minute'] if t > minute_ago])
    hour_requests = len([t for t in request_counts[client_ip]['hour'] if t > hour_ago])
    
    return {
        'client_ip': client_ip,
        'requests_last_minute': minute_requests,
        'requests_last_hour': hour_requests,
        'limit_per_minute': RATE_LIMIT_PER_MINUTE,
        'limit_per_hour': RATE_LIMIT_PER_HOUR,
        'remaining_minute': max(0, RATE_LIMIT_PER_MINUTE - minute_requests),
        'remaining_hour': max(0, RATE_LIMIT_PER_HOUR - hour_requests)
    }
