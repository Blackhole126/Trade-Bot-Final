"""
COMPLETE DESTRUCTIVE TEST RUNNER
=================================

Runs all 4 phases of stress testing:
1. Functional Core Testing (20+ attempts per function)
2. Stress & Edge Case Testing
3. Financial Correctness Testing (30+ trade cycles)
4. UI Stability Testing

Generates comprehensive report with all failures, warnings, and fixes needed.
"""

import sys
import json
from datetime import datetime
from pathlib import Path


def run_all_phases():
    """Run all test phases sequentially"""

    print("\n" + "="*80)
    print("COMPLETE DESTRUCTIVE TEST SUITE")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*80)

    results = {
        'phase_1': None,
        'phase_2': None,
        'phase_3': None,
        'phase_4': None,
        'overall_success': False
    }

    # Import test modules
    try:
        import stress_test_destructive as phase1
        import stress_test_phase2 as phase2
        import stress_test_phase3 as phase3
        import stress_test_phase4 as phase4
    except ImportError as e:
        print(f"\nERROR: Failed to import test modules: {e}")
        print("Make sure all test files are in the same directory")
        return results

    # Run Phase 1
    print("\n" + "="*80)
    print("RUNNING PHASE 1: FUNCTIONAL CORE TESTING")
    print("="*80)
    try:
        phase1.run_phase_1()
        results['phase_1'] = {
            'total': phase1.results.total_tests,
            'passed': phase1.results.passed_tests,
            'failed': phase1.results.failed_tests,
            'errors': phase1.results.errors,
            'warnings': phase1.results.warnings
        }
        print(
            f"\n✓ Phase 1 Complete: {phase1.results.passed_tests}/{phase1.results.total_tests} passed")
    except Exception as e:
        print(f"\n✗ Phase 1 FAILED: {e}")
        results['phase_1'] = {'error': str(e)}

    # Run Phase 2
    print("\n" + "="*80)
    print("RUNNING PHASE 2: STRESS & EDGE CASE TESTING")
    print("="*80)
    try:
        phase2.run_phase_2()
        results['phase_2'] = {
            'total': phase2.results.total_tests,
            'passed': phase2.results.passed_tests,
            'failed': phase2.results.failed_tests,
            'edge_cases_caught': phase2.results.edge_cases_caught,
            'validations_passed': phase2.results.validations_passed,
            'errors': phase2.results.errors
        }
        print(
            f"\n✓ Phase 2 Complete: {phase2.results.passed_tests}/{phase2.results.total_tests} passed")
    except Exception as e:
        print(f"\n✗ Phase 2 FAILED: {e}")
        results['phase_2'] = {'error': str(e)}

    # Run Phase 3
    print("\n" + "="*80)
    print("RUNNING PHASE 3: FINANCIAL CORRECTNESS TESTING")
    print("="*80)
    try:
        phase3.run_phase_3()
        results['phase_3'] = {
            'total_trades': phase3.results.total_trades,
            'valid_trades': phase3.results.valid_trades,
            'invalid_trades': phase3.results.invalid_trades,
            'pnl_discrepancies': len(phase3.results.pnl_discrepancies),
            'calculation_errors': phase3.results.calculation_errors,
            'pnl_discrepancies_details': phase3.results.pnl_discrepancies
        }
        print(
            f"\n✓ Phase 3 Complete: {phase3.results.valid_trades}/{phase3.results.total_trades} valid")
    except Exception as e:
        print(f"\n✗ Phase 3 FAILED: {e}")
        results['phase_3'] = {'error': str(e)}

    # Run Phase 4
    print("\n" + "="*80)
    print("RUNNING PHASE 4: UI STABILITY TESTING")
    print("="*80)
    try:
        phase4.run_phase_4()
        results['phase_4'] = {
            'total': phase4.results.total_tests,
            'passed': phase4.results.passed_tests,
            'failed': phase4.results.failed_tests,
            'console_errors': len(phase4.results.console_errors),
            'blank_components': len(phase4.results.blank_components),
            'hanging_loaders': len(phase4.results.hanging_loaders),
            'errors_detail': phase4.results.console_errors + phase4.results.blank_components + phase4.results.hanging_loaders
        }
        print(
            f"\n✓ Phase 4 Complete: {phase4.results.passed_tests}/{phase4.results.total_tests} passed")
    except Exception as e:
        print(f"\n✗ Phase 4 FAILED: {e}")
        results['phase_4'] = {'error': str(e)}

    # Calculate overall success
    all_phases_passed = all([
        results.get('phase_1', {}).get('failed', 0) == 0,
        results.get('phase_2', {}).get('failed', 0) == 0,
        results.get('phase_3', {}).get('invalid_trades', 999) == 0,
        results.get('phase_4', {}).get('failed', 0) == 0
    ])

    results['overall_success'] = all_phases_passed

    # Generate final report
    print("\n" + "="*80)
    print("FINAL COMPREHENSIVE REPORT")
    print("="*80)

    print("\nPHASE RESULTS:")
    print("-" * 80)

    if 'phase_1' in results and 'error' not in results['phase_1']:
        p1 = results['phase_1']
        success_rate = p1['passed']/p1['total']*100 if p1['total'] > 0 else 0
        print(
            f"Phase 1 (Functional): {p1['passed']}/{p1['total']} ({success_rate:.1f}%) - {'✓ PASS' if p1['failed'] == 0 else '✗ FAIL'}")

    if 'phase_2' in results and 'error' not in results['phase_2']:
        p2 = results['phase_2']
        success_rate = p2['passed']/p2['total']*100 if p2['total'] > 0 else 0
        print(
            f"Phase 2 (Stress): {p2['passed']}/{p2['total']} ({success_rate:.1f}%) - {'✓ PASS' if p2['failed'] == 0 else '✗ FAIL'}")

    if 'phase_3' in results and 'error' not in results['phase_3']:
        p3 = results['phase_3']
        success_rate = p3['valid_trades']/p3['total_trades'] * \
            100 if p3['total_trades'] > 0 else 0
        print(
            f"Phase 3 (Financial): {p3['valid_trades']}/{p3['total_trades']} ({success_rate:.1f}%) - {'✓ PASS' if p3['invalid_trades'] == 0 else '✗ FAIL'}")

    if 'phase_4' in results and 'error' not in results['phase_4']:
        p4 = results['phase_4']
        success_rate = p4['passed']/p4['total']*100 if p4['total'] > 0 else 0
        print(
            f"Phase 4 (UI): {p4['passed']}/{p4['total']} ({success_rate:.1f}%) - {'✓ PASS' if p4['failed'] == 0 else '✗ FAIL'}")

    print("-" * 80)
    print(
        f"\nOVERALL RESULT: {'✓ ALL TESTS PASSED' if all_phases_passed else '✗ TESTS FAILED'}\n")

    # Save comprehensive report
    report = {
        'timestamp': datetime.now().isoformat(),
        'overall_success': all_phases_passed,
        'phases': results
    }

    report_path = Path("destructive_test_comprehensive_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Comprehensive report saved to: {report_path}")
    print("="*80)

    return results


if __name__ == "__main__":
    print("\n" + "="*80)
    print("DESTRUCTIVE TESTING - COMPLETE STRESS & RESILIENCE SPRINT")
    print("="*80)
    print("\nThis will run ALL 4 phases of destructive testing:")
    print("  Phase 1: Functional Core Testing (20+ attempts)")
    print("  Phase 2: Stress & Edge Case Testing")
    print("  Phase 3: Financial Correctness Testing (30+ trades)")
    print("  Phase 4: UI Stability Testing")
    print("\nWARNING: This may take 10-30 minutes to complete.")
    print("The system WILL be stressed to its limits.\n")
    print("="*80)

    response = input("\nContinue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Testing cancelled.")
        sys.exit(0)

    print("\nStarting tests...\n")

    try:
        results = run_all_phases()

        if results.get('overall_success', False):
            print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
            print("System is resilient under stress!")
            sys.exit(0)
        else:
            print("\n✗✗✗ TESTS FAILED ✗✗✗")
            print("System has fragilities that need fixing!")
            print("\nReview the comprehensive report for details.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTesting failed with critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
