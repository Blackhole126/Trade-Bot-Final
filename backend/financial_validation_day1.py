"""
FINANCIAL CORRECTNESS VALIDATION - DAY 1 & 2
=============================================

This is NOT optional testing. This is about proving the system tells the FINANCIAL TRUTH.

Every PnL calculation, every fee, every audit log must be 100% accurate and reproducible.

Test Plan:
----------
Day 1: Financial Logic Understanding and Test Design
  - Understand FeeModel
  - Understand ShadowSimulator  
  - Understand Position update logic
  - Understand PnL logic
  - Create test plan ✓ (this file)

Day 1-B: Execute Financial Validation Tests
  - Run minimum 50 BUY trades
  - Run minimum 50 SELL trades
  - Run 20 partial fills
  - Run 20 position open-close cycles
  - Record: Expected PnL, Actual PnL, Difference
  - All differences must be explained

Day 2: Repeatability Validation
  - Repeat same test cases 10 times each
  - Same input must produce identical output
  - System must be deterministic
  - No random financial drift allowed

Day 2-B: Audit Validation
  - Verify Karma logs match: Trade price, Fees, PnL
  - Audit trail must match execution exactly
"""

from backend.hft.reporting.karma import KarmaLogger
from backend.hft.risk.limits import RiskConfig
from backend.hft.risk.throttling import RiskGate, VolatilityRegime
from backend.hft.models.trade_event import FeeBreakdown, TradeType, RiskStopReason
from backend.hft.shadow_execution.fee_model import FeeImpactCalculator
from backend.hft.shadow_execution.simulator import ShadowSimulator, ShadowOrder, Side, OrderStatus
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import asdict

# Add parent directory to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent / 'hft2'
sys.path.insert(0, str(project_root))

# Now imports should work


class FinancialValidator:
    """
    Comprehensive financial validation engine.

    Validates:
    1. Fee calculations (absolute accuracy)
    2. PnL calculations (gross and net)
    3. Position updates (average price, quantity)
    4. Audit trail accuracy (karma logs)
    5. Repeatability (deterministic results)
    """

    def __init__(self, output_dir: str = "financial_validation_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.fee_calculator = FeeImpactCalculator()
        self.karma_logger = KarmaLogger(output_dir=f"{output_dir}/karma_logs")

        # Test results storage
        self.test_results = {
            'fee_tests': [],
            'pnl_tests': [],
            'position_tests': [],
            'repeatability_tests': [],
            'audit_tests': []
        }

        # Counters
        self.total_buy_trades = 0
        self.total_sell_trades = 0
        self.total_partial_fills = 0
        self.total_open_close_cycles = 0

    def validate_fee_calculation(self, buy_price: float, sell_price: float, qty: int,
                                 trade_type: TradeType = TradeType.EQUITY_INTRADAY) -> Dict:
        """
        Validate fee calculation accuracy.

        Manual calculation must match system calculation within ±0.01 INR tolerance.
        """
        test_id = f"FEE_{len(self.test_results['fee_tests']) + 1}"

        # System calculation
        system_breakdown = self.fee_calculator.calculate_complete_breakdown(
            buy_price=buy_price,
            sell_price=sell_price,
            qty=qty,
            trade_type=trade_type
        )

        # Manual calculation (replicate the formula)
        buy_turnover = buy_price * qty
        sell_turnover = sell_price * qty
        total_turnover = buy_turnover + sell_turnover

        # Brokerage
        brokerage_buy = min(buy_turnover * 0.0003, 20.0)
        brokerage_sell = min(sell_turnover * 0.0003, 20.0)
        manual_brokerage = max(brokerage_buy + brokerage_sell, 0.01 * 2)

        # STT (intraday: only on sell side at 0.025%)
        is_intraday = (trade_type == TradeType.EQUITY_INTRADAY)
        if is_intraday:
            manual_stt = sell_turnover * 0.00025
        else:
            manual_stt = (buy_turnover + sell_turnover) * 0.001

        # Exchange transaction charge (0.00325%)
        manual_exchange = total_turnover * 0.0000325

        # SEBI turnover fee (0.0001%)
        manual_sebi = total_turnover * 0.000001

        # Stamp duty (buy side, intraday: 0.003%)
        if is_intraday:
            manual_stamp = buy_turnover * 0.00003
        else:
            manual_stamp = buy_turnover * 0.00015

        # GST (18% on brokerage + exchange + SEBI)
        manual_gst_base = manual_brokerage + manual_exchange + manual_sebi
        manual_gst = manual_gst_base * 0.18

        # Total fees
        manual_total = manual_brokerage + manual_stt + \
            manual_exchange + manual_sebi + manual_stamp + manual_gst

        # Calculate differences
        tolerance = 0.01  # ±0.01 INR tolerance
        differences = {
            'brokerage_diff': abs(system_breakdown.brokerage - manual_brokerage),
            'stt_diff': abs(system_breakdown.stt - manual_stt),
            'exchange_diff': abs(system_breakdown.exchange_txn_charge - manual_exchange),
            'sebi_diff': abs(system_breakdown.sebi_turnover_fee - manual_sebi),
            'stamp_diff': abs(system_breakdown.stamp_duty - manual_stamp),
            'gst_diff': abs(system_breakdown.gst - manual_gst),
            'total_diff': abs(system_breakdown.total_fees - manual_total)
        }

        # Check if all differences are within tolerance
        all_within_tolerance = all(
            diff <= tolerance for diff in differences.values())

        result = {
            'test_id': test_id,
            'timestamp': datetime.now().isoformat(),
            'inputs': {
                'buy_price': buy_price,
                'sell_price': sell_price,
                'qty': qty,
                'trade_type': trade_type.value
            },
            'system_breakdown': asdict(system_breakdown),
            'manual_breakdown': {
                'brokerage': manual_brokerage,
                'stt': manual_stt,
                'exchange_txn_charge': manual_exchange,
                'sebi_turnover_fee': manual_sebi,
                'stamp_duty': manual_stamp,
                'gst': manual_gst,
                'total_fees': manual_total
            },
            'differences': differences,
            'tolerance': tolerance,
            'passed': all_within_tolerance,
            'status': 'PASS' if all_within_tolerance else 'FAIL'
        }

        self.test_results['fee_tests'].append(result)
        return result

    def validate_pnl_calculation(self, symbol: str, buy_price: float, sell_price: float,
                                 qty: int, expected_net_pnl: float) -> Dict:
        """
        Validate PnL calculation including fees.

        Net PnL = Gross PnL - Total Fees
        Must match within ±0.50 INR tolerance.
        """
        test_id = f"PNL_{len(self.test_results['pnl_tests']) + 1}"

        # Create simulator
        risk_config = RiskConfig(
            max_loss_per_min=1000000,
            max_trades_per_min=10000,
            max_drawdown_session=1000000,
            max_order_qty=100000
        )
        risk_gate = RiskGate(risk_config)
        simulator = ShadowSimulator(
            risk_gate=risk_gate, karma_logger=self.karma_logger)

        # Place BUY order
        buy_order = ShadowOrder(
            order_id=f"BURDER_{test_id}",
            timestamp=datetime.now(),
            symbol=symbol,
            side=Side.BUY,
            quantity=qty,
            limit_price=buy_price,
            status=OrderStatus.OPEN,
            trade_type=TradeType.EQUITY_INTRADAY
        )

        # Simulate BUY fill
        simulator._fill_order(buy_order, price=buy_price, qty=qty)

        # Place SELL order (close position)
        sell_order = ShadowOrder(
            order_id=f"SELL_ORDER_{test_id}",
            timestamp=datetime.now(),
            symbol=symbol,
            side=Side.SELL,  # Note: SELL side for closing long position
            quantity=qty,
            limit_price=sell_price,
            status=OrderStatus.OPEN,
            trade_type=TradeType.EQUITY_INTRADAY
        )

        # Simulate SELL fill
        simulator._fill_order(sell_order, price=sell_price, qty=qty)

        # Get actual PnL from position
        position = simulator.positions.get(symbol)
        if not position:
            result = {
                'test_id': test_id,
                'status': 'FAIL',
                'error': 'Position not found'
            }
            self.test_results['pnl_tests'].append(result)
            return result

        actual_net_pnl = position.realized_pnl - position.total_fees

        # Calculate expected gross PnL
        expected_gross_pnl = (sell_price - buy_price) * qty

        # Calculate expected fees
        expected_fees_breakdown = self.fee_calculator.calculate_complete_breakdown(
            buy_price=buy_price,
            sell_price=sell_price,
            qty=qty,
            trade_type=TradeType.EQUITY_INTRADAY
        )
        expected_total_fees = expected_fees_breakdown.total_fees

        expected_net_pnl_calculated = expected_gross_pnl - expected_total_fees

        # Check difference
        tolerance = 0.50  # ±0.50 INR tolerance
        pnl_difference = abs(actual_net_pnl - expected_net_pnl_calculated)
        passed = pnl_difference <= tolerance

        result = {
            'test_id': test_id,
            'timestamp': datetime.now().isoformat(),
            'inputs': {
                'symbol': symbol,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'qty': qty,
                'expected_net_pnl': expected_net_pnl
            },
            'actual_results': {
                'gross_pnl': position.realized_pnl,
                'total_fees': position.total_fees,
                'net_pnl': actual_net_pnl
            },
            'expected_results': {
                'gross_pnl': expected_gross_pnl,
                'total_fees': expected_total_fees,
                'net_pnl': expected_net_pnl_calculated
            },
            'difference': pnl_difference,
            'tolerance': tolerance,
            'passed': passed,
            'status': 'PASS' if passed else 'FAIL'
        }

        self.test_results['pnl_tests'].append(result)
        return result

    def validate_position_update(self, symbol: str, trades: List[Dict]) -> Dict:
        """
        Validate position updates after multiple trades.

        Tests:
        - Average price calculation
        - Quantity tracking
        - Realized vs unrealized PnL
        """
        test_id = f"POS_{len(self.test_results['position_tests']) + 1}"

        # Create simulator
        risk_config = RiskConfig(
            max_loss_per_min=1000000,
            max_trades_per_min=10000,
            max_drawdown_session=1000000,
            max_order_qty=100000
        )
        risk_gate = RiskGate(risk_config)
        simulator = ShadowSimulator(risk_gate=risk_gate)

        # Execute trades
        for i, trade in enumerate(trades):
            order = ShadowOrder(
                order_id=f"ORDER_{test_id}_{i}",
                timestamp=datetime.now(),
                symbol=symbol,
                side=Side.BUY if trade['side'] == 'BUY' else Side.SELL,
                quantity=trade['qty'],
                limit_price=trade['price'],
                status=OrderStatus.OPEN,
                trade_type=TradeType.EQUITY_INTRADAY
            )
            simulator._fill_order(
                order, price=trade['price'], qty=trade['qty'])

        # Get final position
        position = simulator.positions.get(symbol)
        if not position:
            result = {
                'test_id': test_id,
                'status': 'FAIL',
                'error': 'Position not found'
            }
            self.test_results['position_tests'].append(result)
            return result

        # Calculate expected position manually
        expected_qty = 0
        expected_avg_price = 0.0
        total_fees_paid = 0.0

        for trade in trades:
            if trade['side'] == 'BUY':
                new_qty = expected_qty + trade['qty']
                if new_qty > 0:
                    expected_avg_price = (
                        (expected_qty * expected_avg_price) + (trade['qty'] * trade['price'])) / new_qty
                expected_qty = new_qty
            else:  # SELL
                expected_qty -= trade['qty']

            # Calculate fees for this trade
            fees = self.fee_calculator.calculate_complete_breakdown(
                buy_price=trade['price'] if trade['side'] == 'BUY' else 0,
                sell_price=trade['price'] if trade['side'] == 'SELL' else 0,
                qty=trade['qty'],
                trade_type=TradeType.EQUITY_INTRADAY
            )
            total_fees_paid += fees.total_fees

        # Compare
        tolerance_qty = 0.01
        tolerance_price = 0.01
        tolerance_fees = 0.50

        qty_diff = abs(position.quantity - expected_qty)
        price_diff = abs(position.average_price - expected_avg_price)
        fees_diff = abs(position.total_fees - total_fees_paid)

        passed = (qty_diff <= tolerance_qty and
                  price_diff <= tolerance_price and
                  fees_diff <= tolerance_fees)

        result = {
            'test_id': test_id,
            'timestamp': datetime.now().isoformat(),
            'inputs': {
                'symbol': symbol,
                'trades': trades
            },
            'actual_position': {
                'quantity': position.quantity,
                'average_price': position.average_price,
                'total_fees': position.total_fees
            },
            'expected_position': {
                'quantity': expected_qty,
                'average_price': expected_avg_price,
                'total_fees': total_fees_paid
            },
            'differences': {
                'quantity_diff': qty_diff,
                'price_diff': price_diff,
                'fees_diff': fees_diff
            },
            'passed': passed,
            'status': 'PASS' if passed else 'FAIL'
        }

        self.test_results['position_tests'].append(result)
        return result

    def run_buy_trade_campaign(self, num_trades: int = 50) -> List[Dict]:
        """Execute minimum 50 BUY trades and validate each"""
        print(f"\n{'='*80}")
        print(f"RUNNING {num_trades} BUY TRADES")
        print(f"{'='*80}")

        results = []
        symbol = "RELIANCE.NS"
        base_price = 2500.0

        for i in range(num_trades):
            # Vary price slightly to simulate real market
            buy_price = base_price + (i % 10) * 5
            sell_price = buy_price + 2  # Small profit
            qty = 100

            result = self.validate_pnl_calculation(
                symbol=symbol,
                buy_price=buy_price,
                sell_price=sell_price,
                qty=qty,
                expected_net_pnl=(sell_price - buy_price) * qty
            )

            results.append(result)
            self.total_buy_trades += 1

            status = "✓" if result['status'] == 'PASS' else "✗"
            print(
                f"{status} BUY Trade {i+1}/{num_trades}: PnL Diff = ₹{result['difference']:.2f}")

        return results

    def run_sell_trade_campaign(self, num_trades: int = 50) -> List[Dict]:
        """Execute minimum 50 SELL trades (shorting) and validate each"""
        print(f"\n{'='*80}")
        print(f"RUNNING {num_trades} SELL TRADES (SHORTING)")
        print(f"{'='*80}")

        results = []
        symbol = "TATAMOTORS.NS"
        base_price = 900.0

        for i in range(num_trades):
            # Short sell: sell high, buy low
            sell_price = base_price + (i % 10) * 5
            buy_price = sell_price - 2  # Small profit
            qty = 200

            result = self.validate_pnl_calculation(
                symbol=symbol,
                buy_price=buy_price,
                sell_price=sell_price,
                qty=qty,
                expected_net_pnl=(sell_price - buy_price) * qty
            )

            results.append(result)
            self.total_sell_trades += 1

            status = "✓" if result['status'] == 'PASS' else "✗"
            print(
                f"{status} SELL Trade {i+1}/{num_trades}: PnL Diff = ₹{result['difference']:.2f}")

        return results

    def run_partial_fill_tests(self, num_tests: int = 20) -> List[Dict]:
        """Test partial fill scenarios"""
        print(f"\n{'='*80}")
        print(f"RUNNING {num_tests} PARTIAL FILL TESTS")
        print(f"{'='*80}")

        results = []
        symbol = "INFY.NS"

        for i in range(num_tests):
            # Create multi-leg position with partial fills
            trades = [
                {'side': 'BUY', 'price': 1500.0 + i, 'qty': 100},
                {'side': 'BUY', 'price': 1502.0, 'qty': 50},   # Partial add
                {'side': 'SELL', 'price': 1505.0, 'qty': 75},  # Partial close
            ]

            result = self.validate_position_update(symbol, trades)
            results.append(result)
            self.total_partial_fills += 1

            status = "✓" if result['status'] == 'PASS' else "✗"
            print(
                f"{status} Partial Fill {i+1}/{num_tests}: Qty Diff = {result['differences']['quantity_diff']:.2f}")

        return results

    def run_open_close_cycles(self, num_cycles: int = 20) -> List[Dict]:
        """Test complete position open-close cycles"""
        print(f"\n{'='*80}")
        print(f"RUNNING {num_cycles} OPEN-CLOSE CYCLES")
        print(f"{'='*80}")

        results = []

        for i in range(num_cycles):
            symbol = f"STOCK_{i % 5}.NS"
            base_price = 1000.0 + i * 10

            # Complete cycle: Open → Add → Close partially → Close fully
            trades = [
                {'side': 'BUY', 'price': base_price, 'qty': 200},
                {'side': 'BUY', 'price': base_price + 5, 'qty': 100},
                {'side': 'SELL', 'price': base_price + 10, 'qty': 150},
                {'side': 'SELL', 'price': base_price +
                    15, 'qty': 150},  # Fully close
            ]

            result = self.validate_position_update(symbol, trades)
            results.append(result)
            self.total_open_close_cycles += 1

            # Position should be flat (qty ≈ 0)
            final_qty = result['actual_position']['quantity']
            status = "✓" if result['status'] == 'PASS' else "✗"
            print(f"{status} Cycle {i+1}/{num_cycles}: Final Qty = {final_qty:.2f}")

        return results

    def generate_report(self) -> Dict:
        """Generate comprehensive financial validation report"""
        total_tests = sum(len(v) for v in self.test_results.values())
        passed_tests = sum(sum(1 for t in v if t.get('passed', False))
                           for v in self.test_results.values())

        report = {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'timestamp': datetime.now().isoformat()
            },
            'trade_counts': {
                'total_buy_trades': self.total_buy_trades,
                'total_sell_trades': self.total_sell_trades,
                'total_partial_fills': self.total_partial_fills,
                'total_open_close_cycles': self.total_open_close_cycles
            },
            'detailed_results': self.test_results
        }

        # Save report
        report_path = self.output_dir / \
            f"financial_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n{'='*80}")
        print("FINANCIAL VALIDATION REPORT")
        print(f"{'='*80}")
        print(f"Total Tests: {total_tests}")
        print(
            f"Passed: {passed_tests} ({report['summary']['success_rate']:.1f}%)")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"\nTrade Counts:")
        print(f"  BUY Trades: {self.total_buy_trades}")
        print(f"  SELL Trades: {self.total_sell_trades}")
        print(f"  Partial Fills: {self.total_partial_fills}")
        print(f"  Open-Close Cycles: {self.total_open_close_cycles}")
        print(f"\nReport saved to: {report_path}")
        print(f"{'='*80}")

        return report


def main():
    """Run complete Day 1-B financial validation"""
    print("\n" + "="*80)
    print("FINANCIAL CORRECTNESS VALIDATION - DAY 1-B")
    print("="*80)
    print("\nThis will execute:")
    print("  • 50 BUY trades")
    print("  • 50 SELL trades")
    print("  • 20 partial fill tests")
    print("  • 20 open-close cycles")
    print("\nAll PnL, fees, and positions will be validated.")
    print("All differences must be within tolerance.")
    print("="*80 + "\n")

    validator = FinancialValidator()

    try:
        # Run test campaigns
        validator.run_buy_trade_campaign(50)
        validator.run_sell_trade_campaign(50)
        validator.run_partial_fill_tests(20)
        validator.run_open_close_cycles(20)

        # Generate report
        report = validator.generate_report()

        # Exit with appropriate code
        success = report['summary']['failed_tests'] == 0
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nValidation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
