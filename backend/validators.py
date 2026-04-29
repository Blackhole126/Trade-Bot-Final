"""
Input Validation Module
Validates and sanitizes user inputs to prevent security vulnerabilities
Works with FastAPI Pydantic models and direct validation
"""

import re
from typing import List, Dict, Any
import logging

from config import MAX_SYMBOLS_PER_REQUEST, MAX_SCAN_SYMBOLS

logger = logging.getLogger(__name__)


def validate_symbol(symbol: str) -> bool:
    """Validate stock symbol format"""
    if not symbol:
        return False
    
    # Allow up to 20 characters for symbols like JSWSTEEL.NS, TATAMOTORS.BO, etc.
    pattern = r'^[A-Z0-9\.\-]{1,20}$'
    return bool(re.match(pattern, symbol.upper()))


def validate_symbols(symbols: List[str], max_count: int = MAX_SYMBOLS_PER_REQUEST) -> dict:
    """Validate a list of stock symbols"""
    if not symbols:
        return {'valid': False, 'error': 'No symbols provided'}
    
    if not isinstance(symbols, list):
        return {'valid': False, 'error': 'Symbols must be a list'}
    
    if len(symbols) > max_count:
        return {'valid': False, 'error': f'Too many symbols. Maximum allowed: {max_count}'}
    
    invalid_symbols = []
    for symbol in symbols:
        if not validate_symbol(symbol):
            invalid_symbols.append(symbol)
    
    if invalid_symbols:
        return {
            'valid': False,
            'error': f'Invalid symbols: {", ".join(invalid_symbols)}'
        }
    
    return {'valid': True}


def validate_horizon(horizon: str) -> bool:
    """Validate prediction horizon"""
    valid_horizons = ['intraday', 'short', 'long']
    return horizon.lower() in valid_horizons


def validate_confidence(confidence: float) -> bool:
    """Validate confidence value"""
    try:
        conf = float(confidence)
        return 0.0 <= conf <= 1.0
    except (ValueError, TypeError):
        return False


def validate_horizons_list(horizons: List[str]) -> dict:
    """Validate a list of horizons"""
    if not horizons:
        return {'valid': False, 'error': 'No horizons provided'}
    
    if not isinstance(horizons, list):
        return {'valid': False, 'error': 'Horizons must be a list'}
    
    invalid_horizons = []
    for horizon in horizons:
        if not validate_horizon(horizon):
            invalid_horizons.append(horizon)
    
    if invalid_horizons:
        return {
            'valid': False,
            'error': f'Invalid horizons: {", ".join(invalid_horizons)}. Valid: intraday, short, long'
        }
    
    return {'valid': True}


def sanitize_input(data: Dict[str, Any], max_depth: int = 3, _current_depth: int = 0) -> Dict[str, Any]:
    """
    Recursively sanitize input data
    Handles: strings, lists, integers, floats, booleans, nested dicts
    Prevents: injection attacks, DoS, overflow, deep nesting
    """
    # Prevent infinite recursion / deep nesting attacks
    if _current_depth > max_depth:
        logger.warning(f"Input nesting too deep (>{max_depth}), truncating")
        return {}
    
    sanitized = {}
    
    for key, value in data.items():
        # Sanitize dictionary key
        if not isinstance(key, str) or len(key) > 100:
            logger.warning(f"Skipping invalid key: {key}")
            continue
        
        # Sanitize value based on type
        if isinstance(value, str):
            # String sanitization
            value = value.replace('\x00', '')  # Remove null bytes
            value = value.strip()              # Remove whitespace
            value = value[:1000]               # Limit length
            
        elif isinstance(value, list):
            # List sanitization
            if len(value) > 100:               # Limit list size
                logger.warning(f"List too large ({len(value)}), truncating to 100")
                value = value[:100]
            
            # Sanitize each item in list
            sanitized_list = []
            for item in value:
                if isinstance(item, str):
                    item = item.replace('\x00', '').strip()
                    item = item[:100]          # Limit string length in lists
                    sanitized_list.append(item)
                elif isinstance(item, (int, float)):
                    # Validate numeric items in lists
                    if isinstance(item, float):
                        if item != item or abs(item) > 1e15:  # NaN or too large
                            item = 0.0
                    elif isinstance(item, int):
                        if abs(item) > 1e9:
                            item = int(1e9) if item > 0 else int(-1e9)
                    sanitized_list.append(item)
                elif isinstance(item, bool):
                    sanitized_list.append(item)
                elif isinstance(item, dict):
                    # Nested dict in list
                    sanitized_list.append(sanitize_input(item, max_depth, _current_depth + 1))
            
            value = sanitized_list
            
        elif isinstance(value, dict):
            # Recursive sanitization for nested dicts
            value = sanitize_input(value, max_depth, _current_depth + 1)
            
        elif isinstance(value, float):
            # Float sanitization
            if value != value:  # NaN check
                logger.warning(f"NaN value detected for key {key}, replacing with 0.0")
                value = 0.0
            elif abs(value) > 1e15:  # Extremely large values
                logger.warning(f"Float too large ({value}) for key {key}, capping")
                value = 1e15 if value > 0 else -1e15
                
        elif isinstance(value, int):
            # Integer sanitization
            if abs(value) > 1e9:  # 1 billion max
                logger.warning(f"Integer too large ({value}) for key {key}, capping")
                value = int(1e9) if value > 0 else int(-1e9)
        
        elif isinstance(value, bool):
            # Boolean is safe, pass through
            pass
        
        elif value is None:
            # None is safe, pass through
            pass
        
        else:
            # Unknown type - skip for security
            logger.warning(f"Unknown type {type(value).__name__} for key {key}, skipping")
            continue
        
        sanitized[key] = value
    
    return sanitized


def validate_risk_parameters(stop_loss_pct: float = None, 
                            capital_risk_pct: float = None,
                            drawdown_limit_pct: float = None) -> dict:
    """Validate risk parameter values"""
    errors = []
    
    if stop_loss_pct is not None:
        try:
            sl = float(stop_loss_pct)
            if not (0.1 <= sl <= 50.0):
                errors.append('stop_loss_pct must be between 0.1 and 50.0')
        except (ValueError, TypeError):
            errors.append('stop_loss_pct must be a number')
    
    if capital_risk_pct is not None:
        try:
            cr = float(capital_risk_pct)
            if not (0.1 <= cr <= 100.0):
                errors.append('capital_risk_pct must be between 0.1 and 100.0')
        except (ValueError, TypeError):
            errors.append('capital_risk_pct must be a number')
    
    if drawdown_limit_pct is not None:
        try:
            dl = float(drawdown_limit_pct)
            if not (0.1 <= dl <= 100.0):
                errors.append('drawdown_limit_pct must be between 0.1 and 100.0')
        except (ValueError, TypeError):
            errors.append('drawdown_limit_pct must be a number')
    
    if errors:
        return {'valid': False, 'error': '; '.join(errors)}
    
    return {'valid': True}
