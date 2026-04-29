#!/usr/bin/env python3
"""
Daily Discipline Tracker
========================

Tracks and scores your trading discipline daily.
Focus: Process over outcome, discipline over profits.

Usage:
    python discipline_tracker.py --user_id YOUR_ID --date 2026-03-27
"""

import argparse
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discipline_tracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DisciplineCategory(Enum):
    """Categories of trading discipline."""
    CHECKLIST_COMPLIANCE = "checklist_compliance"
    STOP_LOSS_ADHERENCE = "stop_loss_adherence"
    POSITION_SIZE_ACCURACY = "position_size_accuracy"
    NO_REVENGE_TRADING = "no_revenge_trading"
    NO_CHASED_ENTRIES = "no_chased_entries"
    RISK_MANAGEMENT = "risk_management"
    EMOTIONAL_CONTROL = "emotional_control"
    JOURNAL_QUALITY = "journal_quality"


@dataclass
class TradeDiscipline:
    """Discipline tracking for a single trade."""
    trade_id: str
    symbol: str
    timestamp: datetime

    # Pre-trade checks
    setup_type_documented: bool = False
    entry_reasoning_documented: bool = False
    stop_loss_calculated: bool = False
    target_set: bool = False
    risk_reward_acceptable: bool = False

    # Execution checks
    entry_at_planned_price: bool = False
    position_size_correct: bool = False
    stop_loss_entered: bool = False

    # Exit checks
    exit_disciplined: bool = False
    stop_respected: bool = False
    emotional_exit: bool = False

    # Post-trade
    lessons_documented: bool = False
    mistakes_acknowledged: bool = False

    @property
    def score(self) -> float:
        """Calculate discipline score for this trade (0-100%)."""
        checks = [
            self.setup_type_documented,
            self.entry_reasoning_documented,
            self.stop_loss_calculated,
            self.target_set,
            self.risk_reward_acceptable,
            self.entry_at_planned_price,
            self.position_size_correct,
            self.stop_loss_entered,
            self.exit_disciplined,
            self.stop_respected,
            not self.emotional_exit,
            self.lessons_documented,
            self.mistakes_acknowledged
        ]

        return round(sum(checks) / len(checks) * 100, 2)

    def violations(self) -> List[str]:
        """List discipline violations."""
        violations = []

        if not self.setup_type_documented:
            violations.append("Missing setup type")
        if not self.entry_reasoning_documented:
            violations.append("Missing entry reasoning")
        if not self.stop_loss_calculated:
            violations.append("Stop loss not calculated")
        if not self.target_set:
            violations.append("Target not set")
        if not self.risk_reward_acceptable:
            violations.append("Risk-reward < 1:2")
        if not self.entry_at_planned_price:
            violations.append("Entry price missed (chased)")
        if not self.position_size_correct:
            violations.append("Position size incorrect")
        if not self.stop_loss_entered:
            violations.append("Stop loss not entered")
        if not self.exit_disciplined:
            violations.append("Undisciplined exit")
        if not self.stop_respected:
            violations.append("Stop loss violated")
        if self.emotional_exit:
            violations.append("Emotional exit")
        if not self.lessons_documented:
            violations.append("No lessons documented")
        if not self.mistakes_acknowledged:
            violations.append("Mistakes not acknowledged")

        return violations


@dataclass
class DailyDisciplineReport:
    """Daily discipline summary."""
    date: str
    user_id: str

    # Trade-level metrics
    total_trades: int = 0
    average_discipline_score: float = 0.0
    trades_with_violations: int = 0

    # Category scores (0-100%)
    checklist_compliance: float = 0.0
    stop_loss_adherence: float = 0.0
    position_size_accuracy: float = 0.0
    no_revenge_trading: float = 0.0
    no_chased_entries: float = 0.0
    risk_management: float = 0.0
    emotional_control: float = 0.0
    journal_quality: float = 0.0

    # Overall score
    overall_discipline_score: float = 0.0

    # Violations breakdown
    violations_by_type: Dict[str, int] = None

    # Manual reflections
    emotional_state_morning: str = ""
    emotional_state_afternoon: str = ""
    emotional_state_evening: str = ""
    best_trade_notes: str = ""
    worst_trade_notes: str = ""
    lessons_learned: List[str] = None
    improvements_for_tomorrow: List[str] = None

    def __post_init__(self):
        if self.violations_by_type is None:
            self.violations_by_type = {}
        if self.lessons_learned is None:
            self.lessons_learned = []
        if self.improvements_for_tomorrow is None:
            self.improvements_for_tomorrow = []

    @property
    def grade(self) -> str:
        """Convert score to letter grade."""
        if self.overall_discipline_score >= 95:
            return "A+ (Excellent)"
        elif self.overall_discipline_score >= 90:
            return "A (Very Good)"
        elif self.overall_discipline_score >= 85:
            return "B+ (Good)"
        elif self.overall_discipline_score >= 80:
            return "B (Above Average)"
        elif self.overall_discipline_score >= 75:
            return "C (Average)"
        elif self.overall_discipline_score >= 70:
            return "D (Below Average)"
        else:
            return "F (Poor - Needs Immediate Attention)"


class DisciplineTracker:
    """
    Main tracker class.
    """

    def __init__(self, user_id: str, data_dir: str = "data/logs"):
        self.user_id = user_id
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.trades: List[TradeDiscipline] = []
        self.daily_report: Optional[DailyDisciplineReport] = None

    def add_trade(self, trade_data: Dict) -> TradeDiscipline:
        """
        Add a trade to the tracker.

        Expected trade_data format:
        {
            'trade_id': 'T001',
            'symbol': 'RELIANCE.NS',
            'timestamp': '2026-03-27T10:15:00',

            # Pre-trade
            'setup_type': 'Breakout_pullback',
            'entry_reasoning': '...',
            'stop_loss': 2820.00,
            'target': 2910.00,
            'entry_price': 2850.00,
            'planned_entry_price': 2850.00,
            'position_size': 100,
            'calculated_position_size': 100,
            'risk_reward_ratio': 2.0,

            # Execution
            'actual_entry_price': 2850.00,
            'stop_loss_entered': True,

            # Exit
            'exit_price': 2880.00,
            'exit_reason': 'Trailing_stop',
            'exit_was_emotional': False,
            'stop_was_respected': True,

            # Post-trade
            'lessons_learned': ['Wait for confirmation'],
            'mistakes_made': []
        }
        """
        trade = TradeDiscipline(
            trade_id=trade_data['trade_id'],
            symbol=trade_data['symbol'],
            timestamp=datetime.fromisoformat(trade_data['timestamp'])
        )

        # Pre-trade checks
        trade.setup_type_documented = bool(trade_data.get('setup_type'))
        trade.entry_reasoning_documented = bool(
            trade_data.get('entry_reasoning'))
        trade.stop_loss_calculated = bool(trade_data.get('stop_loss'))
        trade.target_set = bool(trade_data.get('target'))
        trade.risk_reward_acceptable = trade_data.get(
            'risk_reward_ratio', 0) >= 2.0

        # Execution checks
        planned_price = trade_data.get(
            'planned_entry_price', trade_data.get('entry_price'))
        actual_price = trade_data.get(
            'actual_entry_price', trade_data.get('entry_price'))
        trade.entry_at_planned_price = abs(
            actual_price - planned_price) / planned_price <= 0.005  # 0.5%
        trade.position_size_correct = trade_data.get(
            'position_size') == trade_data.get('calculated_position_size')
        trade.stop_loss_entered = trade_data.get('stop_loss_entered', False)

        # Exit checks
        trade.exit_disciplined = trade_data.get('exit_reason') in [
            'Target', 'Trailing_stop', 'Time_stop', 'Stop_loss']
        trade.stop_respected = trade_data.get('stop_was_respected', True)
        trade.emotional_exit = trade_data.get('exit_was_emotional', False)

        # Post-trade
        trade.lessons_documented = bool(trade_data.get('lessons_learned'))
        trade.mistakes_acknowledged = bool(trade_data.get(
            'mistakes_made')) or trade_data.get('pnl', 0) >= 0

        self.trades.append(trade)

        logger.info(
            f"Added trade {trade.trade_id} - Discipline Score: {trade.score}%")

        return trade

    def calculate_daily_metrics(self, date: datetime) -> DailyDisciplineReport:
        """
        Calculate all discipline metrics for the day.
        """
        date_str = date.strftime('%Y-%m-%d')

        # Filter trades for this date
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(
            hour=23, minute=59, second=59, microsecond=999999)

        days_trades = [t for t in self.trades
                       if day_start <= t.timestamp <= day_end]

        if not days_trades:
            logger.warning(f"No trades found for {date_str}")
            # Return empty report
            return DailyDisciplineReport(
                date=date_str,
                user_id=self.user_id,
                overall_discipline_score=100.0  # No trades = perfect discipline
            )

        # Calculate metrics
        report = DailyDisciplineReport(
            date=date_str,
            user_id=self.user_id,
            total_trades=len(days_trades),
            average_discipline_score=sum(
                t.score for t in days_trades) / len(days_trades),
            trades_with_violations=sum(
                1 for t in days_trades if t.violations())
        )

        # Checklist compliance
        checklist_checks = [
            t.setup_type_documented and
            t.entry_reasoning_documented and
            t.stop_loss_calculated and
            t.target_set
            for t in days_trades
        ]
        report.checklist_compliance = sum(
            checklist_checks) / len(checklist_checks) * 100

        # Stop-loss adherence
        stop_checks = [
            t.stop_loss_entered and t.stop_respected for t in days_trades]
        report.stop_loss_adherence = sum(stop_checks) / len(stop_checks) * 100

        # Position size accuracy
        position_checks = [t.position_size_correct for t in days_trades]
        report.position_size_accuracy = sum(
            position_checks) / len(position_checks) * 100

        # Revenge trading (simplified - would need time-series analysis)
        report.no_revenge_trading = 100.0  # Assume OK unless proven otherwise

        # Chased entries
        chase_checks = [t.entry_at_planned_price for t in days_trades]
        report.no_chased_entries = sum(chase_checks) / len(chase_checks) * 100

        # Risk management
        rr_checks = [t.risk_reward_acceptable for t in days_trades]
        report.risk_management = sum(rr_checks) / len(rr_checks) * 100

        # Emotional control
        emotional_checks = [not t.emotional_exit for t in days_trades]
        report.emotional_control = sum(
            emotional_checks) / len(emotional_checks) * 100

        # Journal quality
        journal_checks = [
            t.lessons_documented or t.mistakes_acknowledged for t in days_trades]
        report.journal_quality = sum(
            journal_checks) / len(journal_checks) * 100

        # Overall score (weighted average)
        weights = {
            'checklist_compliance': 0.20,
            'stop_loss_adherence': 0.25,
            'position_size_accuracy': 0.15,
            'no_revenge_trading': 0.10,
            'no_chased_entries': 0.10,
            'risk_management': 0.15,
            'emotional_control': 0.05,
            'journal_quality': 0.05
        }

        report.overall_discipline_score = sum(
            getattr(report, cat) * weight 
            for cat, weight in weights.items()
        )
        
        # Cap at 100%
        report.overall_discipline_score = min(100.0, report.overall_discipline_score)

        # Violations breakdown
        all_violations = []
        for trade in days_trades:
            all_violations.extend(trade.violations())

        from collections import Counter
        violation_counts = Counter(all_violations)
        report.violations_by_type = dict(violation_counts)

        self.daily_report = report

        logger.info(f"Daily metrics calculated for {date_str}:")
        logger.info(f"  Total Trades: {report.total_trades}")
        logger.info(
            f"  Discipline Score: {report.overall_discipline_score:.2f}%")
        logger.info(f"  Grade: {report.grade}")

        return report

    def save_report(self, output_path: str = None):
        """Save daily report to JSON file."""
        if not self.daily_report:
            raise ValueError(
                "No report to save. Call calculate_daily_metrics first.")

        if output_path is None:
            output_path = self.data_dir / \
                f"discipline_{self.daily_report.date}.json"
        else:
            output_path = Path(output_path)

        report_dict = asdict(self.daily_report)
        report_dict['trades'] = [asdict(t) for t in self.trades]

        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)

        logger.info(f"Report saved to {output_path}")

        return output_path

    def print_summary(self):
        """Print formatted discipline summary."""
        if not self.daily_report:
            print("No report available. Run calculate_daily_metrics first.")
            return

        r = self.daily_report

        print("\n" + "="*70)
        print(f"DAILY DISCIPLINE REPORT - {r.date}")
        print("="*70)
                
        print(f"\n[PERFORMANCE SUMMARY]")
        print(f"  Total Trades: {r.total_trades}")
        print(f"  Trades with Violations: {r.trades_with_violations}")
        print(f"  Average Discipline Score: {r.average_discipline_score:.2f}%")

        print(f"\n[CATEGORY SCORES]")
        print(f"  [+] Checklist Compliance:     {r.checklist_compliance:.1f}%")
        print(f"  [+] Stop-Loss Adherence:      {r.stop_loss_adherence:.1f}%")
        print(f"  [+] Position Size Accuracy:   {r.position_size_accuracy:.1f}%")
        print(f"  [+] No Revenge Trading:       {r.no_revenge_trading:.1f}%")
        print(f"  [+] No Chased Entries:        {r.no_chased_entries:.1f}%")
        print(f"  [+] Risk Management:          {r.risk_management:.1f}%")
        print(f"  [+] Emotional Control:        {r.emotional_control:.1f}%")
        print(f"  [+] Journal Quality:          {r.journal_quality:.1f}%")
                
        print(f"\n[OVERALL ASSESSMENT]")
        print(f"  Discipline Score: {r.overall_discipline_score:.2f}%")
        print(f"  Grade: {r.grade}")
                
        if r.violations_by_type:
            print(f"\n[VIOLATIONS BREAKDOWN]")
            for violation, count in sorted(r.violations_by_type.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {violation}: {count} occurrence(s)")
                
        print(f"\n[MANUAL REFLECTIONS]")
        print(
            f"  Morning Emotional State:   {r.emotional_state_morning or 'Not recorded'}")
        print(
            f"  Afternoon Emotional State: {r.emotional_state_afternoon or 'Not recorded'}")
        print(
            f"  Evening Emotional State:   {r.emotional_state_evening or 'Not recorded'}")

        if r.best_trade_notes:
            print(f"\n  Best Trade: {r.best_trade_notes}")
        if r.worst_trade_notes:
            print(f"  Worst Trade: {r.worst_trade_notes}")

        if r.lessons_learned:
            print(f"\n[LESSONS LEARNED]")
            for lesson in r.lessons_learned:
                print(f"  - {lesson}")
                
        if r.improvements_for_tomorrow:
            print(f"\n[IMPROVEMENTS FOR TOMORROW]")
            for improvement in r.improvements_for_tomorrow:
                print(f"  - {improvement}")
                
        print("\n" + "="*70)
                
        # Motivational message based on score
        if r.overall_discipline_score >= 95:
            print("\n*** OUTSTANDING! You are a discipline master. Keep it up!")
        elif r.overall_discipline_score >= 90:
            print("\n[OK] Excellent work! Very close to perfect discipline.")
        elif r.overall_discipline_score >= 85:
            print("\n[GOOD] Good job! Room for minor improvements.")
        elif r.overall_discipline_score >= 80:
            print("\n[WARN] Above average, but focus on reducing violations.")
        elif r.overall_discipline_score >= 75:
            print("\n[WARN] Average performance. Need to tighten discipline.")
        else:
            print("\n[ALERT] POOR discipline! Review your rules and reset.")
                
        print("\nRemember: Process > Outcome. Discipline > Profits.\n")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Daily Discipline Tracker')
    parser.add_argument('--user_id', type=str, required=True, help='User ID')
    parser.add_argument('--date', type=str, default=datetime.now().strftime('%Y-%m-%d'),
                        help='Date to track (YYYY-MM-DD)')
    parser.add_argument('--trades', type=str, help='JSON file with trade data')
    parser.add_argument('--output', type=str, help='Output file path')

    args = parser.parse_args()

    # Initialize tracker
    tracker = DisciplineTracker(user_id=args.user_id)

    # Load trades from file if provided
    if args.trades:
        with open(args.trades, 'r') as f:
            trades_data = json.load(f)

        if isinstance(trades_data, list):
            for trade_data in trades_data:
                tracker.add_trade(trade_data)
        else:
            tracker.add_trade(trades_data)

    # Calculate metrics
    date_obj = datetime.strptime(args.date, '%Y-%m-%d')
    tracker.calculate_daily_metrics(date_obj)

    # Print summary
    tracker.print_summary()

    # Save report
    output_path = tracker.save_report(args.output)
    print(f"\n📄 Report saved to: {output_path}")


if __name__ == '__main__':
    main()
