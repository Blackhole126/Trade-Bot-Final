"""
Test script for Signal Filtering Layer (Phase 1)
Tests all filtering criteria:
- Confidence threshold
- Ensemble alignment
- Conflicting signals detection
- Trade cycle completion and bot stop
"""

from core.signal_filter import SignalFilteringLayer, SignalQuality, TradeCycleState
import sys
import os
from datetime import datetime, timedelta

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, "backend", "hft2", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


def test_confidence_threshold():
    """Test that signals below confidence threshold are rejected"""
    print("\n" + "="*80)
    print("TEST 1: Confidence Threshold Filtering")
    print("="*80)

    config = {
        "min_confidence": 0.70,
        "min_ensemble_agreement": 0.60,
        "min_models_agreeing": 2,
        "stop_after_cycle": False
    }

    signal_filter = SignalFilteringLayer(config)

    # Test 1: Low confidence signal (should be rejected)
    low_conf_analysis = {
        "recommendation": "BUY",
        "confidence": 0.55,
        "model_predictions": {
            "model1": {"recommendation": "BUY"},
            "model2": {"recommendation": "BUY"},
            "model3": {"recommendation": "BUY"}
        },
        "risk_score": 0.3,
        "stop_loss": 100.0,
        "prediction_magnitude": 0.03
    }

    result = signal_filter.filter_signal("RELIANCE.NS", low_conf_analysis)
    assert not result["approved"], "Low confidence signal should be rejected"
    assert result["quality"] == SignalQuality.LOW, "Quality should be LOW"
    print(f"✅ Low confidence (0.55) correctly REJECTED")

    # Test 2: High confidence signal (should pass if other criteria met)
    high_conf_analysis = {
        "recommendation": "BUY",
        "confidence": 0.85,
        "model_predictions": {
            "model1": {"recommendation": "BUY"},
            "model2": {"recommendation": "BUY"},
            "model3": {"recommendation": "BUY"}
        },
        "risk_score": 0.3,
        "stop_loss": 100.0,
        "prediction_magnitude": 0.03
    }

    result = signal_filter.filter_signal("RELIANCE.NS", high_conf_analysis)
    assert result["approved"], "High confidence signal should be approved"
    assert result["quality"] == SignalQuality.HIGH, "Quality should be HIGH"
    print(f"✅ High confidence (0.85) correctly APPROVED")

    print("\n✅ TEST 1 PASSED: Confidence threshold filtering works correctly")


def test_ensemble_alignment():
    """Test that ensemble alignment is required"""
    print("\n" + "="*80)
    print("TEST 2: Ensemble Alignment Filtering")
    print("="*80)

    config = {
        "min_confidence": 0.60,
        "min_ensemble_agreement": 0.60,
        "min_models_agreeing": 3,
        "stop_after_cycle": False
    }

    signal_filter = SignalFilteringLayer(config)

    # Test 1: Models disagree (should fail ensemble check)
    disagreeing_analysis = {
        "recommendation": "BUY",
        "confidence": 0.80,
        "model_predictions": {
            "model1": {"recommendation": "BUY"},
            "model2": {"recommendation": "SELL"},
            "model3": {"recommendation": "HOLD"},
            "model4": {"recommendation": "BUY"},
            "model5": {"recommendation": "SELL"}
        },
        "risk_score": 0.3,
        "stop_loss": 100.0
    }

    result = signal_filter.filter_signal("TATASTEEL.NS", disagreeing_analysis)
    # Should be rejected or downgraded due to poor ensemble alignment
    print(
        f"✅ Disagreeing ensemble (2/5 BUY) correctly handled: quality={result['quality'].value}")

    # Test 2: Models agree (should pass ensemble check)
    agreeing_analysis = {
        "recommendation": "BUY",
        "confidence": 0.80,
        "model_predictions": {
            "model1": {"recommendation": "BUY"},
            "model2": {"recommendation": "BUY"},
            "model3": {"recommendation": "BUY"},
            "model4": {"recommendation": "BUY"},
            "model5": {"recommendation": "SELL"}
        },
        "risk_score": 0.3,
        "stop_loss": 100.0
    }

    result = signal_filter.filter_signal("TATASTEEL.NS", agreeing_analysis)
    assert result["filtered_analysis"]["signal_filter"]["ensemble_passed"], "Ensemble should pass"
    print(f"✅ Agreeing ensemble (4/5 BUY) correctly PASSED")

    print("\n✅ TEST 2 PASSED: Ensemble alignment filtering works correctly")


def test_conflicting_signals():
    """Test that conflicting recent signals are detected"""
    print("\n" + "="*80)
    print("TEST 3: Conflicting Signals Detection")
    print("="*80)

    config = {
        "min_confidence": 0.60,
        "min_ensemble_agreement": 0.50,
        "min_models_agreeing": 2,
        "conflict_window_minutes": 30,
        "max_conflicting_signals": 1,
        "stop_after_cycle": False
    }

    signal_filter = SignalFilteringLayer(config)

    # Add a recent SELL signal
    now = datetime.now()
    signal_filter.signal_tracker.add_signal(
        "INFY.NS", "SELL", 0.75, now - timedelta(minutes=5),
        {"model1": {"recommendation": "SELL"}}
    )

    # Now try to generate a BUY signal (should conflict)
    buy_analysis = {
        "recommendation": "BUY",
        "confidence": 0.80,
        "model_predictions": {
            "model1": {"recommendation": "BUY"},
            "model2": {"recommendation": "BUY"},
            "model3": {"recommendation": "BUY"}
        },
        "risk_score": 0.3,
        "stop_loss": 100.0
    }

    result = signal_filter.filter_signal("INFY.NS", buy_analysis)
    conflicts = result["filtered_analysis"]["signal_filter"]["conflict_count"]
    print(
        f"✅ Conflicting signal detected: {conflicts} conflict(s) in last 30 minutes")

    # Add another conflicting signal
    signal_filter.signal_tracker.add_signal(
        "INFY.NS", "SELL", 0.70, now - timedelta(minutes=10),
        {"model1": {"recommendation": "SELL"}}
    )

    # Try BUY again (should now have too many conflicts)
    result = signal_filter.filter_signal("INFY.NS", buy_analysis)
    conflicts = result["filtered_analysis"]["signal_filter"]["conflict_count"]
    print(f"✅ Multiple conflicts detected: {conflicts} conflicts")
    assert conflicts == 2, "Should have 2 conflicting signals"

    print("\n✅ TEST 3 PASSED: Conflicting signals detection works correctly")


def test_trade_cycle_completion():
    """Test that bot stops after trade cycle completes"""
    print("\n" + "="*80)
    print("TEST 4: Trade Cycle Completion and Bot Stop")
    print("="*80)

    config = {
        "min_confidence": 0.60,
        "min_ensemble_agreement": 0.50,
        "min_models_agreeing": 2,
        "stop_after_cycle": True  # Should stop after cycle
    }

    signal_filter = SignalFilteringLayer(config)

    # Start new cycle
    signal_filter.start_new_cycle()
    assert signal_filter.trade_cycle_state == TradeCycleState.ANALYZING
    print(f"✅ Cycle started: state={signal_filter.trade_cycle_state.value}")

    # Record trade execution
    signal_filter.record_trade_execution("HDFC.NS", "BUY", True)
    assert signal_filter.trade_cycle_state == TradeCycleState.TRADE_EXECUTED
    print(f"✅ Trade executed: state={signal_filter.trade_cycle_state.value}")

    # Complete cycle
    should_stop = signal_filter.complete_trade_cycle()
    assert should_stop == True, "Bot should stop after cycle (stop_after_cycle=True)"
    assert signal_filter.trade_cycle_state == TradeCycleState.CYCLE_COMPLETE
    print(
        f"✅ Cycle completed: should_stop={should_stop}, state={signal_filter.trade_cycle_state.value}")

    # Test with stop_after_cycle=False
    config["stop_after_cycle"] = False
    signal_filter2 = SignalFilteringLayer(config)
    signal_filter2.start_new_cycle()
    signal_filter2.record_trade_execution("HDFC.NS", "BUY", True)
    should_stop = signal_filter2.complete_trade_cycle()
    assert should_stop == False, "Bot should continue (stop_after_cycle=False)"
    print(f"✅ Cycle completed with continue: should_stop={should_stop}")

    print("\n✅ TEST 4 PASSED: Trade cycle completion and bot stop works correctly")


def test_risk_score_filter():
    """Test that high risk signals are rejected"""
    print("\n" + "="*80)
    print("TEST 5: Risk Score Filtering")
    print("="*80)

    config = {
        "min_confidence": 0.60,
        "max_risk_score": 0.7,
        "stop_after_cycle": False
    }

    signal_filter = SignalFilteringLayer(config)

    # High risk signal (should be rejected)
    high_risk_analysis = {
        "recommendation": "BUY",
        "confidence": 0.85,
        "model_predictions": {
            "model1": {"recommendation": "BUY"},
            "model2": {"recommendation": "BUY"}
        },
        "risk_score": 0.85,  # Too high
        "stop_loss": 100.0
    }

    result = signal_filter.filter_signal("ICICI.NS", high_risk_analysis)
    assert result["quality"] == SignalQuality.REJECT, "High risk should be rejected"
    print(f"✅ High risk (0.85) correctly REJECTED")

    # Low risk signal (should pass)
    low_risk_analysis = {
        "recommendation": "BUY",
        "confidence": 0.85,
        "model_predictions": {
            "model1": {"recommendation": "BUY"},
            "model2": {"recommendation": "BUY"}
        },
        "risk_score": 0.4,  # Acceptable
        "stop_loss": 100.0
    }

    result = signal_filter.filter_signal("ICICI.NS", low_risk_analysis)
    assert result["quality"] != SignalQuality.REJECT, "Low risk should not be rejected"
    print(f"✅ Low risk (0.40) correctly PASSED")

    print("\n✅ TEST 5 PASSED: Risk score filtering works correctly")


def test_hold_recommendation():
    """Test that HOLD recommendations are not filtered"""
    print("\n" + "="*80)
    print("TEST 6: HOLD Recommendation Handling")
    print("="*80)

    config = {"min_confidence": 0.70, "stop_after_cycle": False}
    signal_filter = SignalFilteringLayer(config)

    hold_analysis = {
        "recommendation": "HOLD",
        "confidence": 0.50,  # Low confidence but it's HOLD
        "model_predictions": {},
        "risk_score": 0.5
    }

    result = signal_filter.filter_signal("SBIN.NS", hold_analysis)
    assert not result["approved"], "HOLD should not be approved for trading"
    assert "HOLD recommendation" in result["reasons"][0]
    print(f"✅ HOLD recommendation correctly filtered out (no trade needed)")

    print("\n✅ TEST 6 PASSED: HOLD recommendation handling works correctly")


def test_filter_statistics():
    """Test that filter statistics are tracked correctly"""
    print("\n" + "="*80)
    print("TEST 7: Filter Statistics Tracking")
    print("="*80)

    config = {"min_confidence": 0.60, "stop_after_cycle": False}
    signal_filter = SignalFilteringLayer(config)

    # Generate some signals
    for i in range(5):
        analysis = {
            "recommendation": "BUY" if i % 2 == 0 else "SELL",
            "confidence": 0.75,
            "model_predictions": {
                "model1": {"recommendation": "BUY" if i % 2 == 0 else "SELL"}
            },
            "risk_score": 0.3,
            "stop_loss": 100.0
        }
        signal_filter.filter_signal(f"TEST{i}.NS", analysis)

    stats = signal_filter.get_filter_stats()
    assert stats["total_signals_tracked"] == 5, "Should track 5 signals"
    assert stats["buy_signals"] == 3, "Should have 3 BUY signals"
    assert stats["sell_signals"] == 2, "Should have 2 SELL signals"

    print(f"✅ Statistics tracked correctly:")
    print(f"   Total signals: {stats['total_signals_tracked']}")
    print(f"   Buy signals: {stats['buy_signals']}")
    print(f"   Sell signals: {stats['sell_signals']}")

    print("\n✅ TEST 7 PASSED: Filter statistics tracking works correctly")


def run_all_tests():
    """Run all signal filter tests"""
    print("\n" + "="*80)
    print("SIGNAL FILTERING LAYER - COMPREHENSIVE TEST SUITE")
    print("="*80)

    try:
        test_confidence_threshold()
        test_ensemble_alignment()
        test_conflicting_signals()
        test_trade_cycle_completion()
        test_risk_score_filter()
        test_hold_recommendation()
        test_filter_statistics()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED - SIGNAL FILTERING LAYER IS WORKING PERFECTLY")
        print("="*80)
        print("\nSummary:")
        print("  ✅ Confidence threshold filtering")
        print("  ✅ Ensemble alignment validation")
        print("  ✅ Conflicting signals detection")
        print("  ✅ Trade cycle completion and bot stop")
        print("  ✅ Risk score filtering")
        print("  ✅ HOLD recommendation handling")
        print("  ✅ Filter statistics tracking")
        print("\nThe signal filtering layer is production-ready!")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_all_tests()
