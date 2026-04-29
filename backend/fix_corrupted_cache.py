#!/usr/bin/env python3
"""
Fix corrupted cache data that causes datetime calculation errors
"""

import os
import json
from pathlib import Path
import shutil

def fix_corrupted_cache():
    """Remove corrupted cache files that cause datetime errors"""
    
    backend_dir = Path(__file__).parent
    cache_dir = backend_dir / "data" / "cache"
    features_dir = backend_dir / "data" / "features"
    
    print("FIXING CORRUPTED CACHE DATA")
    print("=" * 50)
    
    # List of symbols with known datetime issues
    corrupted_symbols = ["TCS.NS"]
    
    # Check for corrupted data by looking for invalid date ranges
    if cache_dir.exists():
        for cache_file in cache_dir.glob("*_all_data.json"):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                # Check if price_summary has invalid dates
                price_summary = data.get('price_summary', {})
                start_date = price_summary.get('start_date', '')
                end_date = price_summary.get('end_date', '')
                
                # If dates are just numbers (like "0", "494"), it's corrupted
                if (start_date.isdigit() or end_date.isdigit() or 
                    start_date == "0" or end_date == "494"):
                    
                    symbol = cache_file.stem.replace('_all_data', '')
                    corrupted_symbols.append(symbol)
                    print(f"[ERROR] Found corrupted cache: {symbol}")
                    print(f"   Invalid date range: {start_date} to {end_date}")
                    
            except Exception as e:
                print(f"[WARNING] Error checking {cache_file}: {e}")
    
    # Remove corrupted cache files
    removed_count = 0
    for symbol in set(corrupted_symbols):  # Remove duplicates
        
        # Remove cache files
        cache_file = cache_dir / f"{symbol}_all_data.json"
        if cache_file.exists():
            cache_file.unlink()
            print(f"[REMOVED] Corrupted cache: {cache_file.name}")
            removed_count += 1
        
        # Remove feature files (they depend on cache)
        feature_file = features_dir / f"{symbol}_features.json"
        if feature_file.exists():
            feature_file.unlink()
            print(f"[REMOVED] Dependent features: {feature_file.name}")
            removed_count += 1
    
    print("\n[SUCCESS] CACHE CLEANUP COMPLETE")
    print(f"   Removed {removed_count} corrupted files")
    print(f"   Affected symbols: {', '.join(set(corrupted_symbols))}")
    print("\n[NEXT STEPS]:")
    print("   1. Restart the backend server")
    print("   2. Use 'Force Refresh' button in frontend")
    print("   3. Fresh data will be fetched from Yahoo Finance")
    
    return removed_count

if __name__ == "__main__":
    fix_corrupted_cache()