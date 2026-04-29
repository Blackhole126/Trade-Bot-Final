#!/usr/bin/env python3
"""
Discipline-First Trading API Integration
=========================================

Integrates live trading protocol with existing backend.
Provides endpoints for:
- Pre-market setup validation
- Trade logging with discipline tracking
- Real-time discipline scoring
- End-of-day analysis generation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import sys

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

logger = logging.getLogger(__name__)


@dataclass
class PreMarketSetup:
    """Pre-market setup declaration."""
    date: str
    capital_allocated: float
    max_risk_per_trade: float  # As percentage (e.g., 0.005 for 0.5%)
    max_risk_absolute: float  # In rupees
    instruments_allowed: List[str]  # ['equity', 'intraday']
    max_trades: int
    min_rr_ratio: float  # Minimum 1:1.5
    market_regime: str  # BULL, BEAR, SIDEWAYS
    volatility_level: str  # LOW, NORMAL, HIGH, EXTREME
    mental_state_ok: bool
    declaration_signed: bool
    timestamp: str


@dataclass
class TradeEntry:
    """Trade entry with discipline checks."""
    trade_number: int
    symbol: str
    direction: str  # BUY (Long) or SELL_FIRST (Short intraday)
    setup_type: str
    entry_reason: str
    entry_price: float
    stop_loss: float
    target_zone_min: float
    target_zone_max: float
    position_size: int
    risk_amount: float
    rr_ratio: float
    entry_time: str
    pre_entry_checklist_completed: bool
    all_checks_passed: bool
    violations: List[str]


@dataclass
class TradeExit:
    """Trade exit with discipline validation."""
    trade_number: int
    exit_time: str
    exit_price: float
    exit_reason: str  # STOP_LOSS, TARGET, TRAILING_STOP, TIME_STOP, THESIS_INVALIDATED, EMERGENCY
    pnl_absolute: float
    pnl_percent: float
    r_multiple: float
    emotional_state: str
    mistakes: List[str]
    lessons_learned: List[str]
    discipline_score: int  # 0-10
    stop_was_respected: bool
    exit_was_disciplined: bool


class DisciplineTradingAPI:
    """
    Integrates discipline-first trading with backend.
    """
    
    def __init__(self, user_id: str, db_session=None):
        self.user_id = user_id
        self.db = db_session
        self.log_dir = Path("data/logs/discipline")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Today's session
        self.pre_market_setup: Optional[PreMarketSetup] = None
        self.trades: Dict[int, Dict] = {}  # trade_number -> {entry, exit}
        self.running_stats = {
            'total_trades': 0,
            'winners': 0,
            'losers': 0,
            'net_pnl': 0.0,
            'current_streak': 0
        }
        
    def initialize_pre_market(self, setup_data: Dict) -> PreMarketSetup:
        """
        Initialize and validate pre-market setup.
        
        Args:
            setup_data: Dictionary with pre-market parameters
        
        Returns:
            PreMarketSetup object
        """
        setup = PreMarketSetup(
            date=setup_data['date'],
            capital_allocated=float(setup_data['capital']),
            max_risk_per_trade=float(setup_data['max_risk_percent']),
            max_risk_absolute=float(setup_data['capital']) * float(setup_data['max_risk_percent']),
            instruments_allowed=setup_data.get('instruments', ['intraday']),
            max_trades=int(setup_data.get('max_trades', 10)),
            min_rr_ratio=1.5,  # Enforced minimum
            market_regime=setup_data['market_regime'],
            volatility_level=setup_data['volatility_level'],
            mental_state_ok=setup_data.get('mental_state_ok', True),
            declaration_signed=setup_data.get('declaration_signed', False),
            timestamp=datetime.now().isoformat()
        )
        
        # VALIDATION CHECKS
        if not setup.declaration_signed:
            raise ValueError("Declaration MUST be signed before trading")
        
        if setup.volatility_level == "EXTREME":
            raise ValueError("NO TRADING allowed in EXTREME volatility")
        
        if setup.max_risk_per_trade > 0.008:  # > 0.8%
            logger.warning(f"Risk per trade {setup.max_risk_per_trade*100:.2f}% exceeds recommended 0.8%")
        
        self.pre_market_setup = setup
        
        # Save to log
        self._save_pre_market_log(setup)
        
        logger.info(f"Pre-market setup initialized for {setup.date}")
        logger.info(f"Max risk per trade: ₹{setup.max_risk_absolute:,.2f}")
        logger.info(f"Max trades: {setup.max_trades}")
        
        return setup
    
    def validate_trade_entry(self, entry_data: Dict) -> tuple[bool, List[str]]:
        """
        Validate trade entry against discipline rules.
        
        Returns:
            (is_valid, violations_list)
        """
        violations = []
        
        # Check 1: Pre-market setup exists
        if not self.pre_market_setup:
            violations.append("No pre-market setup declared")
            return False, violations
        
        # Check 2: Max trades not exceeded
        if self.running_stats['total_trades'] >= self.pre_market_setup.max_trades:
            violations.append(f"Max trades limit reached ({self.pre_market_setup.max_trades})")
        
        # Check 3: R:R ratio minimum 1:1.5
        rr_ratio = float(entry_data.get('rr_ratio', 0))
        if rr_ratio < 1.5:
            violations.append(f"R:R ratio {rr_ratio:.2f}:1 below minimum 1.5:1")
        
        # Check 4: Risk amount within limit
        risk_amount = float(entry_data.get('risk_amount', 0))
        if risk_amount > self.pre_market_setup.max_risk_absolute:
            violations.append(f"Risk ₹{risk_amount:.2f} exceeds max ₹{self.pre_market_setup.max_risk_absolute:.2f}")
        
        # Check 5: Stop loss mandatory
        if not entry_data.get('stop_loss') or float(entry_data['stop_loss']) <= 0:
            violations.append("Stop loss is MANDATORY")
        
        # Check 6: Entry reason documented
        if not entry_data.get('entry_reason') or entry_data['entry_reason'].strip() == "":
            violations.append("Entry reason must be documented")
        
        # Check 7: Target zone defined
        if not entry_data.get('target_zone_min') or not entry_data.get('target_zone_max'):
            violations.append("Target zone must be defined")
        
        # Check 8: Setup type valid (A+ only)
        valid_setups = ['Breakout_pullback', 'Continuation', 'Reversal', 'Breakdown_pullback']
        if entry_data.get('setup_type') not in valid_setups:
            violations.append(f"Invalid setup '{entry_data.get('setup_type')}'. Must be A+ setup only.")
        
        # Check 9: Pre-entry checklist completed
        if not entry_data.get('pre_entry_checklist_completed'):
            violations.append("Pre-entry checklist must be completed")
        
        # Check 10: Not revenge trading (within 30 min of loss)
        last_trade = self._get_last_trade()
        if last_trade and last_trade.get('exit'):
            last_exit = datetime.fromisoformat(last_trade['exit']['exit_time'])
            time_since = datetime.now() - last_exit
            if last_trade['exit']['pnl_absolute'] < 0 and time_since.total_seconds() < 1800:
                remaining = 1800 - time_since.total_seconds()
                violations.append(f"COOLING-OFF PERIOD: Wait {remaining/60:.1f} more minutes after last loss")
        
        is_valid = len(violations) == 0
        
        if is_valid:
            logger.info(f"Trade entry validated: {entry_data['symbol']}")
        else:
            logger.warning(f"Trade entry VIOLATIONS: {violations}")
        
        return is_valid, violations
    
    def log_trade_entry(self, entry_data: Dict) -> TradeEntry:
        """
        Log validated trade entry.
        """
        # Validate first
        is_valid, violations = self.validate_trade_entry(entry_data)
        
        if not is_valid:
            raise ValueError(f"Trade entry invalid: {violations}")
        
        trade_num = self.running_stats['total_trades'] + 1
        
        entry = TradeEntry(
            trade_number=trade_num,
            symbol=entry_data['symbol'],
            direction=entry_data['direction'],
            setup_type=entry_data['setup_type'],
            entry_reason=entry_data['entry_reason'],
            entry_price=float(entry_data['entry_price']),
            stop_loss=float(entry_data['stop_loss']),
            target_zone_min=float(entry_data['target_zone_min']),
            target_zone_max=float(entry_data['target_zone_max']),
            position_size=int(entry_data['position_size']),
            risk_amount=float(entry_data['risk_amount']),
            rr_ratio=float(entry_data['rr_ratio']),
            entry_time=datetime.now().isoformat(),
            pre_entry_checklist_completed=bool(entry_data.get('pre_entry_checklist_completed')),
            all_checks_passed=is_valid,
            violations=[]
        )
        
        self.trades[trade_num] = {'entry': asdict(entry), 'exit': None}
        self.running_stats['total_trades'] += 1
        
        # Save to log
        self._save_trade_log(trade_num, 'ENTRY', asdict(entry))
        
        logger.info(f"Trade #{trade_num} logged: {entry.symbol} {entry.direction}")
        
        return entry
    
    def log_trade_exit(self, exit_data: Dict) -> TradeExit:
        """
        Log trade exit with discipline validation.
        """
        trade_num = int(exit_data['trade_number'])
        
        if trade_num not in self.trades:
            raise ValueError(f"Trade #{trade_num} not found")
        
        entry = self.trades[trade_num]['entry']
        
        # Calculate R-multiple
        risk_per_share = abs(entry['entry_price'] - entry['stop_loss'])
        if risk_per_share > 0:
            r_multiple = exit_data['pnl_absolute'] / (risk_per_share * entry['position_size'])
        else:
            r_multiple = 0
        
        # Determine if exit was disciplined
        acceptable_exits = ['STOP_LOSS', 'TARGET', 'TRAILING_STOP', 'TIME_STOP', 'THESIS_INVALIDATED']
        exit_was_disciplined = exit_data['exit_reason'] in acceptable_exits
        
        # Check if stop was respected
        stop_was_respected = True
        if entry['direction'] == 'BUY':
            if exit_data['exit_price'] < entry['stop_loss'] and exit_data['exit_reason'] != 'STOP_LOSS':
                stop_was_respected = False
        else:  # SELL_FIRST
            if exit_data['exit_price'] > entry['stop_loss'] and exit_data['exit_reason'] != 'STOP_LOSS':
                stop_was_respected = False
        
        # Calculate discipline score (0-10)
        discipline_score = 10
        if not exit_was_disciplined:
            discipline_score -= 3
        if not stop_was_respected:
            discipline_score -= 4
        if exit_data.get('mistakes') and len(exit_data['mistakes']) > 0:
            discipline_score -= len(exit_data['mistakes'])
        if exit_data.get('lessons_learned') and len(exit_data['lessons_learned']) > 0:
            discipline_score += 1
        
        discipline_score = max(0, min(10, discipline_score))
        
        exit_obj = TradeExit(
            trade_number=trade_num,
            exit_time=datetime.now().isoformat(),
            exit_price=float(exit_data['exit_price']),
            exit_reason=exit_data['exit_reason'],
            pnl_absolute=float(exit_data['pnl_absolute']),
            pnl_percent=float(exit_data['pnl_percent']),
            r_multiple=round(r_multiple, 2),
            emotional_state=exit_data.get('emotional_state', 'Unknown'),
            mistakes=exit_data.get('mistakes', []),
            lessons_learned=exit_data.get('lessons_learned', []),
            discipline_score=discipline_score,
            stop_was_respected=stop_was_respected,
            exit_was_disciplined=exit_was_disciplined
        )
        
        self.trades[trade_num]['exit'] = asdict(exit_obj)
        
        # Update running stats
        if exit_obj.pnl_absolute > 0:
            self.running_stats['winners'] += 1
            self.running_stats['current_streak'] += 1
        else:
            self.running_stats['losers'] += 1
            self.running_stats['current_streak'] = -abs(self.running_stats['current_streak']) - 1
        
        self.running_stats['net_pnl'] += exit_obj.pnl_absolute
        
        # Save to log
        self._save_trade_log(trade_num, 'EXIT', asdict(exit_obj))
        self._update_running_stats()
        
        logger.info(f"Trade #{trade_num} exited: PnL ₹{exit_obj.pnl_absolute:,.2f}, Discipline {exit_obj.discipline_score}/10")
        
        return exit_obj
    
    def calculate_discipline_score(self) -> Dict[str, Any]:
        """
        Calculate overall discipline score for the day.
        """
        if not self.trades:
            return {'overall_score': 100.0, 'message': 'No trades - perfect discipline (vacuously true)'}
        
        total_trades = len(self.trades)
        
        # Checklist compliance
        checklists_completed = sum(1 for t in self.trades.values() 
                                   if t['entry'].get('pre_entry_checklist_completed'))
        checklist_compliance = (checklists_completed / total_trades) * 100
        
        # Stop-loss adherence
        stops_respected = sum(1 for t in self.trades.values() 
                             if t.get('exit') and t['exit'].get('stop_was_respected'))
        stop_adherence = (stops_respected / total_trades) * 100 if total_trades > 0 else 100
        
        # Exit discipline
        disciplined_exits = sum(1 for t in self.trades.values() 
                               if t.get('exit') and t['exit'].get('exit_was_disciplined'))
        exit_discipline = (disciplined_exits / total_trades) * 100 if total_trades > 0 else 100
        
        # Average discipline score from exits
        avg_discipline_score = 0
        exits_with_scores = [t['exit']['discipline_score'] for t in self.trades.values() if t.get('exit')]
        if exits_with_scores:
            avg_discipline_score = sum(exits_with_scores) / len(exits_with_scores)
        
        # Overall score (weighted)
        weights = {
            'checklist_compliance': 0.25,
            'stop_adherence': 0.35,
            'exit_discipline': 0.25,
            'avg_discipline_score_normalized': 0.15
        }
        
        overall_score = (
            checklist_compliance * weights['checklist_compliance'] +
            stop_adherence * weights['stop_adherence'] +
            exit_discipline * weights['exit_discipline'] +
            (avg_discipline_score / 10 * 100) * weights['avg_discipline_score_normalized']
        )
        
        return {
            'overall_score': round(overall_score, 2),
            'checklist_compliance': round(checklist_compliance, 2),
            'stop_loss_adherence': round(stop_adherence, 2),
            'exit_discipline': round(exit_discipline, 2),
            'average_discipline_score': round(avg_discipline_score, 1),
            'total_trades': total_trades,
            'grade': self._score_to_grade(overall_score)
        }
    
    def generate_eod_report(self) -> Dict[str, Any]:
        """
        Generate end-of-day analysis report.
        """
        if not self.trades:
            return {'error': 'No trades to analyze'}
        
        # Performance metrics
        winners = [t for t in self.trades.values() if t.get('exit') and t['exit']['pnl_absolute'] > 0]
        losers = [t for t in self.trades.values() if t.get('exit') and t['exit']['pnl_absolute'] < 0]
        
        win_rate = (len(winners) / len(self.trades) * 100) if self.trades else 0
        avg_winner = sum(t['exit']['pnl_absolute'] for t in winners) / len(winners) if winners else 0
        avg_loser = sum(abs(t['exit']['pnl_absolute']) for t in losers) / len(losers) if losers else 0
        gross_profit = sum(t['exit']['pnl_absolute'] for t in winners)
        gross_loss = abs(sum(t['exit']['pnl_absolute'] for t in losers))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        # Discipline metrics
        discipline_metrics = self.calculate_discipline_score()
        
        # Violations breakdown
        all_violations = []
        for trade in self.trades.values():
            if trade['entry'].get('violations'):
                all_violations.extend(trade['entry']['violations'])
        
        from collections import Counter
        violation_counts = Counter(all_violations)
        
        report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'user_id': self.user_id,
            'performance_metrics': {
                'total_trades': len(self.trades),
                'winners': len(winners),
                'losers': len(losers),
                'win_rate': round(win_rate, 2),
                'avg_winner': round(avg_winner, 2),
                'avg_loser': round(avg_loser, 2),
                'profit_factor': round(profit_factor, 2),
                'net_pnl': round(self.running_stats['net_pnl'], 2),
                'net_pnl_percent': round((self.running_stats['net_pnl'] / self.pre_market_setup.capital_allocated * 100) if self.pre_market_setup else 0, 2)
            },
            'discipline_metrics': discipline_metrics,
            'violations_by_type': dict(violation_counts),
            'trades': self.trades,
            'generated_at': datetime.now().isoformat()
        }
        
        # Save report
        self._save_eod_report(report)
        
        return report
    
    def _get_last_trade(self) -> Optional[Dict]:
        """Get most recent trade."""
        if not self.trades:
            return None
        
        trade_nums = sorted(self.trades.keys())
        return self.trades[trade_nums[-1]]
    
    def _save_pre_market_log(self, setup: PreMarketSetup):
        """Save pre-market declaration."""
        filename = self.log_dir / f"pre_market_{setup.date}.json"
        with open(filename, 'w') as f:
            json.dump(asdict(setup), f, indent=2)
    
    def _save_trade_log(self, trade_num: int, log_type: str, data: Dict):
        """Save trade entry/exit log."""
        filename = self.log_dir / f"trade_log_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'trade_number': trade_num,
            'log_type': log_type,
            'data': data
        }
        
        with open(filename, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def _update_running_stats(self):
        """Update running statistics file."""
        stats_file = self.log_dir / f"running_stats_{datetime.now().strftime('%Y%m%d')}.json"
        with open(stats_file, 'w') as f:
            json.dump(self.running_stats, f, indent=2)
    
    def _save_eod_report(self, report: Dict):
        """Save end-of-day report."""
        filename = self.log_dir / f"eod_report_{report['date']}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numerical score to letter grade."""
        if score >= 95:
            return "A+ (Excellent)"
        elif score >= 90:
            return "A (Very Good)"
        elif score >= 85:
            return "B+ (Good)"
        elif score >= 80:
            return "B (Above Average)"
        elif score >= 75:
            return "C (Average)"
        elif score >= 70:
            return "D (Below Average)"
        else:
            return "F (Poor)"


# FastAPI Routes (to be integrated into api_server.py)

"""
To integrate with your existing API server, add these routes:

@app.post("/discipline/pre-market")
async def initialize_pre_market(setup_data: Dict):
    '''Initialize pre-market setup.'''
    api = DisciplineTradingAPI(user_id="admin")
    try:
        setup = api.initialize_pre_market(setup_data)
        return {"status": "success", "setup": asdict(setup)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/discipline/trade/entry")
async def log_trade_entry(entry_data: Dict):
    '''Log and validate trade entry.'''
    api = DisciplineTradingAPI(user_id="admin")
    try:
        entry = api.log_trade_entry(entry_data)
        return {"status": "success", "entry": asdict(entry)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/discipline/trade/exit")
async def log_trade_exit(exit_data: Dict):
    '''Log trade exit.'''
    api = DisciplineTradingAPI(user_id="admin")
    try:
        exit_obj = api.log_trade_exit(exit_data)
        return {"status": "success", "exit": asdict(exit_obj)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/discipline/score")
async def get_discipline_score():
    '''Get current discipline score.'''
    api = DisciplineTradingAPI(user_id="admin")
    score = api.calculate_discipline_score()
    return {"status": "success", "score": score}

@app.get("/discipline/eod-report")
async def get_eod_report():
    '''Generate end-of-day report.'''
    api = DisciplineTradingAPI(user_id="admin")
    report = api.generate_eod_report()
    return {"status": "success", "report": report}
"""

if __name__ == "__main__":
    # Test example
    logging.basicConfig(level=logging.INFO)
    
    api = DisciplineTradingAPI(user_id="test_user")
    
    # Initialize pre-market
    setup_data = {
        'date': '2026-03-27',
        'capital': 100000,
        'max_risk_percent': 0.005,  # 0.5%
        'market_regime': 'NORMAL',
        'volatility_level': 'NORMAL',
        'declaration_signed': True
    }
    
    setup = api.initialize_pre_market(setup_data)
    print(f"Pre-market setup: {setup}")
    
    # Log a trade entry
    entry_data = {
        'symbol': 'RELIANCE.NS',
        'direction': 'BUY',
        'setup_type': 'Breakout_pullback',
        'entry_reason': 'Broke above 2840 resistance, pulled back with declining volume',
        'entry_price': 2850.0,
        'stop_loss': 2820.0,
        'target_zone_min': 2900.0,
        'target_zone_max': 2910.0,
        'position_size': 100,
        'risk_amount': 3000.0,
        'rr_ratio': 3.0,
        'pre_entry_checklist_completed': True
    }
    
    entry = api.log_trade_entry(entry_data)
    print(f"Trade entry logged: {entry}")
    
    # Log exit
    exit_data = {
        'trade_number': 1,
        'exit_price': 2880.0,
        'exit_reason': 'TRAILING_STOP',
        'pnl_absolute': 3000.0,
        'pnl_percent': 1.05,
        'emotional_state': 'Calm',
        'mistakes': [],
        'lessons_learned': ['Perfect execution']
    }
    
    exit_obj = api.log_trade_exit(exit_data)
    print(f"Trade exit logged: {exit_obj}")
    
    # Get discipline score
    score = api.calculate_discipline_score()
    print(f"Discipline score: {score}")
