"""
Simple Demo: Watch the Fallback Mechanism in Action

This script demonstrates how the system automatically switches between
data sources when Yahoo Finance is rate limited or unavailable.
"""

import sys
import os
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from multi_source_data_provider import get_data_provider

def demo_basic_fallback():
    """Show basic fallback mechanism"""
    print("\n" + "="*70)
    print("DEMO: Automatic Fallback Between Data Sources")
    print("="*70)
    
    provider = get_data_provider()
    
    # Test with different tickers to show different paths through fallback chain
    test_cases = [
        ("RELIANCE.NS", "Indian stock - should use Fyers"),
        ("AAPL", "US stock - may need Alpha Vantage"),
        ("INVALID.STOCK", "Invalid ticker - will fail all sources"),
    ]
    
    for ticker, description in test_cases:
        print(f"\nTest: {ticker} ({description})")
        print("-" * 70)
        
        start = time.time()
        df = provider.get_stock_data(ticker, period="1d")
        elapsed = time.time() - start
        
        if df is not None and not df.empty:
            price_col = 'Close' if 'Close' in df.columns else 'close'
            price = df.iloc[-1].get(price_col, 0)
            print(f"✅ SUCCESS in {elapsed:.2f}s")
            print(f"   Price: {price:.2f}")
            print(f"   Data shape: {df.shape}")
        else:
            print(f"❌ FAILED after {elapsed:.2f}s - All sources exhausted")
            
    # Show which sources were used
    print("\n" + "="*70)
    print("Source Status After Tests:")
    print("="*70)
    status = provider.get_status_report()
    for source, info in status.items():
        state = info['circuit_breaker_state']
        available = "✓ Available" if info['can_proceed'] else "✗ Unavailable"
        failures = info['failures']
        print(f"{source:20} | {state:10} | {available:15} | Failures: {failures}")


def demo_rate_limit_scenario():
    """Simulate what happens when Yahoo Finance is rate limited"""
    print("\n" + "="*70)
    print("DEMO: Rate Limit Protection in Action")
    print("="*70)
    
    provider = get_data_provider()
    
    print("\nScenario: Multiple rapid requests (simulating rate limit)")
    print("-" * 70)
    
    # Make several requests to trigger rate limiting
    for i in range(3):
        print(f"\nRequest {i+1}:")
        result = provider.get_stock_data("TEST.NS", period="1d")
        
        if result is None:
            print(f"  Request failed (expected for invalid ticker)")
            
        # Show circuit breaker state
        cb_state = provider.circuit_breakers['yahoo'].state
        failures = provider.circuit_breakers['yahoo'].failures
        print(f"  Yahoo circuit breaker: {cb_state} ({failures} failures)")
    
    print("\n" + "-"*70)
    print("After multiple failures:")
    cb_state = provider.circuit_breakers['yahoo'].state
    can_proceed = provider.circuit_breakers['yahoo'].can_proceed()
    
    if cb_state == 'OPEN':
        print(f"✓ Circuit breaker OPEN - protecting system from cascading failures")
        print(f"  Will auto-recover in ~5 minutes")
    else:
        print(f"Circuit breaker: {cb_state}, Can proceed: {can_proceed}")


def demo_cache_benefit():
    """Show caching performance benefit"""
    print("\n" + "="*70)
    print("DEMO: Caching Performance Benefits")
    print("="*70)
    
    provider = get_data_provider()
    ticker = "RELIANCE.NS"
    
    print(f"\nFetching same ticker multiple times:")
    print("-" * 70)
    
    times = []
    for i in range(3):
        start = time.time()
        df = provider.get_stock_data(ticker, period="1d")
        elapsed = time.time() - start
        times.append(elapsed)
        
        cache_status = "CACHED" if i > 0 else "FRESH"
        print(f"Request {i+1} ({cache_status:6}): {elapsed:.4f}s")
    
    if len(times) > 1:
        speedup = times[0] / max(times[1], 0.001)
        print(f"\nCache performance:")
        print(f"  First request (fresh): {times[0]:.4f}s")
        print(f"  Average cached:        {sum(times[1:])/len(times[1:]):.4f}s")
        print(f"  Speedup:               {speedup:.1f}x faster")


def demo_graceful_failure():
    """Show how system handles complete failure gracefully"""
    print("\n" + "="*70)
    print("DEMO: Graceful Failure Handling (No Crashes!)")
    print("="*70)
    
    provider = get_data_provider()
    
    print("\nTesting with completely invalid ticker:")
    print("-" * 70)
    
    # This should fail all sources but NOT crash
    try:
        result = provider.get_stock_data("NOTAREALSTOCK.XYZ", period="1d")
        
        if result is None:
            print("✓ System handled failure gracefully")
            print("  - No exception thrown")
            print("  - Returned None instead of crashing")
            print("  - Bot can continue operating")
        else:
            print("? Unexpected success - ticker may have been corrected")
            
    except Exception as e:
        print(f"✗ Unexpected exception: {e}")
        print("  System should not throw exceptions!")


def main():
    """Run all demonstrations"""
    print("\n" + "="*70)
    print("MULTI-SOURCE DATA PROVIDER - LIVE DEMONSTRATION")
    print("="*70)
    print("\nThis demonstrates how the system prevents crashes by:")
    print("  1. Automatically switching between data sources")
    print("  2. Protecting against rate limits with circuit breakers")
    print("  3. Caching data to reduce API calls")
    print("  4. Handling failures gracefully (no crashes)")
    print("="*70)
    
    try:
        # Run demos
        demo_basic_fallback()
        demo_rate_limit_scenario()
        demo_cache_benefit()
        demo_graceful_failure()
        
        # Final summary
        print("\n" + "="*70)
        print("DEMONSTRATION COMPLETE")
        print("="*70)
        
        provider = get_data_provider()
        status = provider.get_status_report()
        
        healthy = sum(1 for s in status.values() if s['can_proceed'])
        total = len(status)
        
        print(f"\nSystem Health: {healthy}/{total} sources available")
        
        if healthy >= 4:
            print("Status: EXCELLENT - Multiple redundant sources active")
        elif healthy >= 2:
            print("Status: GOOD - Sufficient sources for operation")
        else:
            print("Status: DEGRADED - Limited sources available")
            
        print("\nKey Takeaways:")
        print("  ✓ System never crashes - always graceful")
        print("  ✓ Automatic fallback when sources fail")
        print("  ✓ Rate limits tracked and respected")
        print("  ✓ Caching improves performance")
        print("  ✓ Circuit breakers prevent cascading failures")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
