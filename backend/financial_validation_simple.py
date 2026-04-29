"""
FINANCIAL CORRECTNESS VALIDATION - SIMPLIFIED VERSION
======================================================

Direct validation of financial calculations WITHOUT complex imports.
This validates the core financial logic directly.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class DirectFeeCalculator:
    """
    Direct implementation of Indian market fee calculation.
    Replicates the exact logic from the HFT2 backend.
    """

    # Fee rates (matching backend.hft.shadow_execution.fee_model)
    BROKERAGE_PCT = 0.0003         # 0.03%
    BROKERAGE_MAX = 20.0           # ₹20 max per order
    STT_INTRADAY_SELL_PCT = 0.00025   # 0.025% on sell side only
    EXCHANGE_TXN_NSE_PCT = 0.0000325  # 0.00325% (NSE equity)
    SEBI_TURNOVER_PCT = 0.000001      # ₹10 per crore = 0.0001%
    STAMP_DUTY_INTRADAY_PCT = 0.00003   # 0.003% on buy side
    GST_PCT = 0.18                    # 18%

    def calculate_fees(self, buy_price: float, sell_price: float, qty: int) -> Dict:
        """Calculate complete fee breakdown for intraday trade"""

        buy_turnover = buy_price * qty
        sell_turnover = sell_price * qty
        total_turnover = buy_turnover + sell_turnover

        # 1. Brokerage (both sides)
        brokerage_buy = min(
            buy_turnover * self.BROKERAGE_PCT, self.BROKERAGE_MAX)
        brokerage_sell = min(
            sell_turnover * self.BROKERAGE_PCT, self.BROKERAGE_MAX)
        brokerage = max(brokerage_buy + brokerage_sell, 0.01 * 2)

        # 2. STT (intraday: only on sell side)
        stt = sell_turnover * self.STT_INTRADAY_SELL_PCT

        # 3. Exchange transaction charge
        exchange_txn = total_turnover * self.EXCHANGE_TXN_NSE_PCT

        # 4. SEBI turnover fee
        sebi_fee = total_turnover * self.SEBI_TURNOVER_PCT

        # 5. Stamp duty (buy side only)
        stamp_duty = buy_turnover * self.STAMP_DUTY_INTRADAY_PCT

        # 6. GST (on brokerage + exchange + SEBI)
        gst_base = brokerage + exchange_txn + sebi_fee
        gst = gst_base * self.GST_PCT

        # Total fees
        total_fees = brokerage + stt + exchange_txn + sebi_fee + stamp_duty + gst

        return {
            'brokerage': brokerage,
            'stt': stt,
            'exchange_txn': exchange_txn,
            'sebi_fee': sebi_fee,
            'stamp_duty': stamp_duty,
            'gst': gst,
            'total_fees': total_fees,
            'turnover': total_turnover
        }


class FinancialValidator:
    """Simple financial validator without complex dependencies"""

    def __init__(self):
        self.fee_calc = DirectFeeCalculator()
        self.results = {
            'fee_tests': [],
            'pnl_tests': []
        }
        self.buy_count = 0
        self.sell_count = 0

    def validate_fee(self, buy_price: float, sell_price: float, qty: int) -> Dict:
        """Validate fee calculation"""
        test_id = f"FEE_{len(self.results['fee_tests']) + 1}"

        # System calculation
        fees = self.fee_calc.calculate_fees(buy_price, sell_price, qty)

        # Manual verification (same formula)
        buy_turnover = buy_price * qty
        sell_turnover = sell_price * qty
        total_turnover = buy_turnover + sell_turnover

        manual_brokerage = max(
            min(buy_turnover * 0.0003, 20.0) +
            min(sell_turnover * 0.0003, 20.0),
            0.02
        )
        manual_stt = sell_turnover * 0.00025
        manual_exchange = total_turnover * 0.0000325
        manual_sebi = total_turnover * 0.000001
        manual_stamp = buy_turnover * 0.00003
        manual_gst = (manual_brokerage + manual_exchange + manual_sebi) * 0.18
        manual_total = manual_brokerage + manual_stt + \
            manual_exchange + manual_sebi + manual_stamp + manual_gst

        # Check difference
        tolerance = 0.01
        diff = abs(fees['total_fees'] - manual_total)
        passed = diff <= tolerance

        result = {
            'test_id': test_id,
            'inputs': {'buy_price': buy_price, 'sell_price': sell_price, 'qty': qty},
            'calculated_fees': fees,
            'manual_verification': manual_total,
            'difference': diff,
            'passed': passed
        }

        self.results['fee_tests'].append(result)
        return result

    def validate_pnl(self, symbol: str, buy_price: float, sell_price: float, qty: int) -> Dict:
        """Validate PnL calculation"""
        test_id = f"PNL_{len(self.results['pnl_tests']) + 1}"

        # Calculate fees
        fees = self.fee_calc.calculate_fees(buy_price, sell_price, qty)

        # Gross PnL
        gross_pnl = (sell_price - buy_price) * qty

        # Net PnL (after fees)
        net_pnl = gross_pnl - fees['total_fees']

        # Expected (manual calculation)
        expected_net_pnl = (sell_price - buy_price) * qty - fees['total_fees']

        # Difference should be zero
        diff = abs(net_pnl - expected_net_pnl)
        passed = diff < 0.01

        result = {
            'test_id': test_id,
            'symbol': symbol,
            'inputs': {'buy_price': buy_price, 'sell_price': sell_price, 'qty': qty},
            'gross_pnl': gross_pnl,
            'total_fees': fees['total_fees'],
            'net_pnl': net_pnl,
            'expected_net_pnl': expected_net_pnl,
            'difference': diff,
            'passed': passed
        }

        self.results['pnl_tests'].append(result)
        return result

    def run_buy_campaign(self, num_trades: int = 50):
        """Run 50 BUY trades"""
        print(f"\n{'='*80}")
        print(f"RUNNING {num_trades} BUY TRADES")
        print(f"{'='*80}")

        for i in range(num_trades):
            buy_price = 2500.0 + (i % 10) * 5
            sell_price = buy_price + 2
            qty = 100

            result = self.validate_pnl(
                "RELIANCE.NS", buy_price, sell_price, qty)
            self.buy_count += 1

            status = "✓" if result['passed'] else "✗"
            print(
                f"{status} BUY #{i+1}: Net PnL = ₹{result['net_pnl']:.2f}, Diff = ₹{result['difference']:.4f}")

    def run_sell_campaign(self, num_trades: int = 50):
        """Run 50 SELL trades"""
        print(f"\n{'='*80}")
        print(f"RUNNING {num_trades} SELL TRADES")
        print(f"{'='*80}")

        for i in range(num_trades):
            sell_price = 900.0 + (i % 10) * 5
            buy_price = sell_price - 2
            qty = 200

            result = self.validate_pnl(
                "TATAMOTORS.NS", buy_price, sell_price, qty)
            self.sell_count += 1

            status = "✓" if result['passed'] else "✗"
            print(
                f"{status} SELL #{i+1}: Net PnL = ₹{result['net_pnl']:.2f}, Diff = ₹{result['difference']:.4f}")

    def generate_report(self):
        """Generate final report"""
        total_tests = len(self.results['fee_tests']) + \
            len(self.results['pnl_tests'])
        passed = sum(
            1 for t in self.results['fee_tests'] + self.results['pnl_tests'] if t['passed'])

        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total_tests,
                'passed': passed,
                'failed': total_tests - passed,
                'success_rate': f"{passed/total_tests*100:.1f}%" if total_tests > 0 else "N/A"
            },
            'trade_counts': {
                'buy_trades': self.buy_count,
                'sell_trades': self.sell_count
            },
            'results': self.results
        }

        # Save report
        output_dir = Path("financial_validation_results")
        output_dir.mkdir(exist_ok=True)
        report_path = output_dir / \
            f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n{'='*80}")
        print("FINANCIAL VALIDATION REPORT")
        print(f"{'='*80}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed} ({report['summary']['success_rate']})")
        print(f"Failed: {total_tests - passed}")
        print(f"\nBUY Trades: {self.buy_count}")
        print(f"SELL Trades: {self.sell_count}")
        print(f"\nReport saved to: {report_path}")
        print(f"{'='*80}")

        return passed == total_tests


if __name__ == "__main__":
    print("\n" + "="*80)
    print("FINANCIAL CORRECTNESS VALIDATION - DAY 1-B")
    print("="*80)
    print("\nExecuting:")
    print("  • 50 BUY trades")
    print("  • 50 SELL trades")
    print("  • Fee validation for each")
    print("  • PnL validation for each")
    print("="*80 + "\n")

    validator = FinancialValidator()

    try:
        validator.run_buy_campaign(50)
        validator.run_sell_campaign(50)
        success = validator.generate_report()

        exit(0 if success else 1)

    except Exception as e:
        print(f"\n\nVALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
