"""
Signal Filter Integration Example
Shows how to use the Signal Filtering Layer with Samruddhi predictions
"""

from core.signal_filter import get_signal_filter, SignalQuality
from datetime import datetime


def example_basic_usage():
    """Basic example of using the signal filter"""
    print("="*80)
    print("EXAMPLE 1: Basic Signal Filtering")
    print("="*80)

    # Configuration
    config = {
        "min_confidence": 0.70,
        "min_ensemble_agreement": 0.60,
        "min_models_agreeing": 3,
        "conflict_window_minutes": 30,
        "max_conflicting_signals": 1,
        "stop_after_cycle": True
    }

    # Get signal filter instance
    signal_filter = get_signal_filter(config)

    # Example: Samruddhi prediction
    samruddhi_prediction = {
        "symbol": "RELIANCE.NS",
        "recommendation": "BUY",
        "confidence": 0.82,
        "current_price": 2450.00,
        "target_price": 2520.00,
        "stop_loss": 2400.00,
        "risk_score": 0.35,
        "prediction_magnitude": 0.028,
        "model_predictions": {
            "lightgbm": {"recommendation": "BUY", "confidence": 0.85},
            "xgboost": {"recommendation": "BUY", "confidence": 0.78},
            "random_forest": {"recommendation": "BUY", "confidence": 0.80},
            "dqn": {"recommendation": "BUY", "confidence": 0.86}
        }
    }

    # Filter the signal
    result = signal_filter.filter_signal(
        samruddhi_prediction["symbol"],
        samruddhi_prediction
    )

    # Check if approved
    if result["approved"]:
        print(f"✅ Signal APPROVED!")
        print(f"   Quality: {result['quality'].value}")
        print(f"   Recommendation: {samruddhi_prediction['recommendation']}")
        print(f"   Confidence: {samruddhi_prediction['confidence']:.1%}")
        print(f"   Models agreeing: 4/4")
        print(f"   → Ready for execution")

        # Record trade execution
        signal_filter.record_trade_execution(
            samruddhi_prediction["symbol"],
            samruddhi_prediction["recommendation"],
            success=True
        )

        # Complete cycle (will stop bot if stop_after_cycle=True)
        should_stop = signal_filter.complete_trade_cycle()
        print(f"   Trade cycle complete, should_stop={should_stop}")
    else:
        print(f"❌ Signal REJECTED!")
        print(f"   Quality: {result['quality'].value}")
        print(f"   Reasons: {result['reasons']}")


def example_ensemble_disagreement():
    """Example where models disagree"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Ensemble Disagreement")
    print("="*80)

    config = {
        "min_confidence": 0.70,
        "min_ensemble_agreement": 0.60,
        "min_models_agreeing": 3,
        "stop_after_cycle": False
    }

    signal_filter = get_signal_filter(config)

    # Models disagree
    prediction = {
        "symbol": "TATASTEEL.NS",
        "recommendation": "BUY",
        "confidence": 0.75,
        "current_price": 145.50,
        "target_price": 152.00,
        "stop_loss": 142.00,
        "risk_score": 0.40,
        "model_predictions": {
            "lightgbm": {"recommendation": "BUY"},
            "xgboost": {"recommendation": "SELL"},  # Disagrees
            "random_forest": {"recommendation": "HOLD"},  # Neutral
            "dqn": {"recommendation": "BUY"}
        }
    }

    result = signal_filter.filter_signal(prediction["symbol"], prediction)

    print(f"Signal: {prediction['recommendation']} {prediction['symbol']}")
    print(f"Confidence: {prediction['confidence']:.1%}")
    print(f"Model predictions: BUY=2, SELL=1, HOLD=1")
    print(f"Result: quality={result['quality'].value}")

    if not result["approved"]:
        print(f"❌ Rejected - Ensemble alignment insufficient")
        print(f"   Only 2/4 models agree (need 3)")
    else:
        print(f"✅ Approved despite some disagreement")


def example_conflicting_signals():
    """Example with conflicting recent signals"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Conflicting Signals Detection")
    print("="*80)

    from datetime import timedelta

    config = {
        "min_confidence": 0.70,
        "conflict_window_minutes": 30,
        "max_conflicting_signals": 1,
        "stop_after_cycle": False
    }

    signal_filter = get_signal_filter(config)

    # Simulate recent SELL signal
    signal_filter.signal_tracker.add_signal(
        "INFY.NS",
        "SELL",
        0.80,
        datetime.now() - timedelta(minutes=10),
        {"model1": {"recommendation": "SELL"}}
    )
    print(f"10 min ago: SELL signal for INFY.NS")

    # Now generate BUY signal
    prediction = {
        "symbol": "INFY.NS",
        "recommendation": "BUY",
        "confidence": 0.85,
        "current_price": 1520.00,
        "target_price": 1580.00,
        "stop_loss": 1500.00,
        "risk_score": 0.30,
        "model_predictions": {
            "lightgbm": {"recommendation": "BUY"},
            "xgboost": {"recommendation": "BUY"},
            "random_forest": {"recommendation": "BUY"}
        }
    }

    result = signal_filter.filter_signal(prediction["symbol"], prediction)

    conflicts = result["filtered_analysis"]["signal_filter"]["conflict_count"]
    print(
        f"Now: BUY signal for INFY.NS (confidence={prediction['confidence']:.1%})")
    print(f"Conflicts detected: {conflicts}")

    if conflicts > config["max_conflicting_signals"]:
        print(f"❌ REJECTED - Too many conflicting signals")
        print(f"   Recent SELL conflicts with new BUY")
    else:
        print(f"✅ APPROVED - Within conflict tolerance")


def example_trade_cycle_flow():
    """Example showing complete trade cycle flow"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Complete Trade Cycle Flow")
    print("="*80)

    config = {
        "min_confidence": 0.70,
        "stop_after_cycle": True
    }

    signal_filter = get_signal_filter(config)

    # Step 1: Start new cycle
    print("Step 1: Starting new trade cycle")
    signal_filter.start_new_cycle()
    print(f"   State: {signal_filter.get_cycle_state()['state']}")

    # Step 2: Analyze signals
    print("\nStep 2: Analyzing signals")
    prediction = {
        "symbol": "HDFCBANK.NS",
        "recommendation": "BUY",
        "confidence": 0.88,
        "current_price": 1650.00,
        "target_price": 1720.00,
        "stop_loss": 1620.00,
        "risk_score": 0.25,
        "model_predictions": {
            "lightgbm": {"recommendation": "BUY"},
            "xgboost": {"recommendation": "BUY"},
            "random_forest": {"recommendation": "BUY"},
            "dqn": {"recommendation": "BUY"}
        }
    }

    result = signal_filter.filter_signal(prediction["symbol"], prediction)
    print(f"   Signal filtered: approved={result['approved']}")

    # Step 3: Execute trade
    if result["approved"]:
        print("\nStep 3: Executing trade")
        signal_filter.record_trade_execution(
            prediction["symbol"],
            prediction["recommendation"],
            success=True
        )
        print(f"   State: {signal_filter.get_cycle_state()['state']}")
        print(
            f"   Trade executed: {signal_filter.get_cycle_state()['trade_executed']}")

    # Step 4: Complete cycle
    print("\nStep 4: Completing trade cycle")
    should_stop = signal_filter.complete_trade_cycle()
    print(f"   State: {signal_filter.get_cycle_state()['state']}")
    print(f"   Should stop bot: {should_stop}")

    if should_stop:
        print("   🛑 Bot will stop after this cycle")


def example_filter_statistics():
    """Example showing how to get filter statistics"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Filter Statistics")
    print("="*80)

    config = {
        "min_confidence": 0.70,
        "stop_after_cycle": False
    }

    signal_filter = get_signal_filter(config)

    # Simulate several signals
    symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFC.NS", "ICICI.NS"]
    for i, symbol in enumerate(symbols):
        prediction = {
            "symbol": symbol,
            "recommendation": "BUY" if i % 2 == 0 else "SELL",
            "confidence": 0.75 + (i * 0.05),
            "current_price": 1000.00,
            "target_price": 1050.00,
            "stop_loss": 980.00,
            "risk_score": 0.30,
            "model_predictions": {
                "model1": {"recommendation": "BUY" if i % 2 == 0 else "SELL"}
            }
        }
        signal_filter.filter_signal(symbol, prediction)

    # Get statistics
    stats = signal_filter.get_filter_stats()

    print("Signal Filter Statistics:")
    print(f"  Total signals tracked: {stats['total_signals_tracked']}")
    print(f"  Buy signals: {stats['buy_signals']}")
    print(f"  Sell signals: {stats['sell_signals']}")
    print(f"  Current cycle state: {stats['current_cycle_state']}")
    print(f"\nConfiguration:")
    print(f"  Min confidence: {stats['config']['min_confidence']:.0%}")
    print(
        f"  Min ensemble agreement: {stats['config']['min_ensemble_agreement']:.0%}")
    print(f"  Min models agreeing: {stats['config']['min_models_agreeing']}")
    print(
        f"  Conflict window: {stats['config']['conflict_window_minutes']} min")
    print(f"  Stop after cycle: {stats['config']['stop_after_cycle']}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("SIGNAL FILTERING LAYER - USAGE EXAMPLES")
    print("="*80 + "\n")

    example_basic_usage()
    example_ensemble_disagreement()
    example_conflicting_signals()
    example_trade_cycle_flow()
    example_filter_statistics()

    print("\n" + "="*80)
    print("✅ All examples completed successfully!")
    print("="*80)
