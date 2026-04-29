"""
Stress Test Runner - Starts backend with test-friendly settings and runs all tests
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path


def start_backend():
    """Start backend with increased rate limits for testing"""
    print("\n" + "="*80)
    print("STARTING BACKEND WITH TEST SETTINGS")
    print("="*80)

    # Set environment variables for testing
    env = os.environ.copy()
    env['RATE_LIMIT_PER_MINUTE'] = '1000'
    env['RATE_LIMIT_PER_HOUR'] = '10000'

    # Start backend process
    backend_path = Path(__file__).parent / 'api_server.py'
    process = subprocess.Popen(
        [sys.executable, str(backend_path)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for server to start (watch for startup message)
    print("Waiting for backend to start...")
    started = False
    for _ in range(30):  # Wait up to 30 seconds
        line = process.stderr.readline()
        if 'Uvicorn running' in line or 'Application startup complete' in line:
            started = True
            print("✓ Backend started successfully")
            break
        elif line:
            print(line.strip())
        time.sleep(0.5)

    if not started:
        print("✗ Backend failed to start")
        return None

    time.sleep(2)  # Give it a moment to fully initialize
    return process


def stop_backend(process):
    """Stop the backend process"""
    print("\nStopping backend...")
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
            print("✓ Backend stopped")
        except:
            process.kill()
            print("✓ Backend killed")


def run_tests():
    """Run all stress tests"""
    print("\n" + "="*80)
    print("RUNNING STRESS TESTS")
    print("="*80)

    # Import and run tests
    import stress_test_destructive as phase1

    print("\nRunning Phase 1...")
    phase1.results.start_time = phase1.datetime.now()
    phase1.run_phase_1()
    phase1.results.end_time = phase1.datetime.now()

    success = phase1.results.summary()

    # Save results
    import json
    with open("stress_test_results.json", "w") as f:
        json.dump({
            'summary': {
                'total': phase1.results.total_tests,
                'passed': phase1.results.passed_tests,
                'failed': phase1.results.failed_tests,
                'success_rate': phase1.results.passed_tests/phase1.results.total_tests*100 if phase1.results.total_tests > 0 else 0,
            },
            'errors': phase1.results.errors,
            'warnings': phase1.results.warnings
        }, f, indent=2)

    print(f"\nResults saved to stress_test_results.json")

    return success


if __name__ == "__main__":
    print("\n" + "="*80)
    print("STRESS TEST RUNNER")
    print("="*80)
    print("\nThis will:")
    print("  1. Start backend with increased rate limits (1000/min)")
    print("  2. Run Phase 1 functional tests")
    print("  3. Stop backend")
    print("\nStarting tests...\n")
    print("="*80)

    backend_process = None
    try:
        # Start backend
        backend_process = start_backend()

        if not backend_process:
            print("\n✗ Failed to start backend")
            sys.exit(1)

        # Run tests
        success = run_tests()

        print("\n" + "="*80)
        if success:
            print("✓ PHASE 1 TESTS PASSED")
        else:
            print("✗ PHASE 1 TESTS FAILED")
        print("="*80)

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTests failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Always stop backend
        if backend_process:
            stop_backend(backend_process)
