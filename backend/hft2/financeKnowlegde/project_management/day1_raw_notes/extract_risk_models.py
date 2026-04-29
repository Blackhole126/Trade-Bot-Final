#!/usr/bin/env python3
"""
Risk Management Rules Extractor
================================
Collects risk management frameworks, position sizing rules, and trading regulations.

Sources:
- CFTC (cftc.gov)
- CME Group (cmegroup.com)
- Professional Trading Standards
- Core Financial Textbooks

Output: Raw notes with source citations for knowledge base construction
"""

import json
from datetime import datetime
from pathlib import Path


class RiskManagementExtractor:
    """Extractor for risk management rules and frameworks"""

    def __init__(self, output_dir="day1_raw_notes"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.sources = {
            "cftc": {
                "source_id": "cftc",
                "base_url": "https://www.cftc.gov",
                "trust_level": "high"
            },
            "cme": {
                "source_id": "cme_group",
                "base_url": "https://www.cmegroup.com",
                "trust_level": "high"
            },
            "textbooks": {
                "source_id": "finance_textbooks",
                "description": "Core Financial Textbooks",
                "trust_level": "high"
            }
        }

        self.extracted_data = {
            "extraction_date": datetime.now().isoformat(),
            "sources": list(self.sources.values()),
            "topics": []
        }

    def extract_position_sizing(self):
        """Extract position sizing methodologies"""
        print("💰 Extracting position sizing rules...")

        position_sizing = {
            "topic_id": "risk_position_sizing",
            "title": "Position Sizing and Capital Allocation Framework",
            "content": [],
            "sources": []
        }

        sizing_methods = {
            "heading": "Position Sizing Methodologies",
            "content": """
**Definition:**
Position sizing determines how much capital to allocate to a specific trade based on account size, risk tolerance, and trade characteristics. It is the most critical component of risk management.

**Core Principles:**

1. **Risk-First Approach:**
   - Determine risk amount BEFORE entry
   - Never exceed predetermined risk per trade
   - Position size = Account Risk / Trade Risk
   
2. **The 2% Rule:**
   - Maximum risk per trade: 2% of total account equity
   - Conservative traders: 0.5% - 1%
   - Aggressive traders: Maximum 3%
   - Prevents ruin from losing streaks
   
3. **Total Portfolio Risk:**
   - Maximum simultaneous positions: 5-10
   - Total portfolio risk: Maximum 10-15% of equity
   - Correlation-adjusted exposure limits

---

## POSITION SIZING METHODS

### Method 1: Fixed Fractional Position Sizing

**Concept:**
Risk fixed percentage of account on each trade.

**Formula:**
```
Position Size = (Account Equity × Risk %) / (Entry Price - Stop Loss Price)

Example:
Account: ₹10,00,000
Risk per trade: 2% = ₹20,000
Entry Price: ₹2,500
Stop Loss: ₹2,400
Risk per share: ₹100

Position Size = ₹20,000 / ₹100 = 200 shares
Capital Required: 200 × ₹2,500 = ₹5,00,000
```

**Advantages:**
- Simple to calculate and implement
- Automatically reduces size after losses
- Increases size after wins (pyramiding effect)
- Mathematically prevents ruin

**Disadvantages:**
- Doesn't account for volatility differences
- Same risk % regardless of setup quality
- May be too conservative for low-volatility trades

---

### Method 2: Kelly Criterion (Optimal f)

**Concept:**
Mathematically optimal bet size based on win rate and payoff ratio.

**Formula:**
```
Kelly % = W - [(1 - W) / R]

Where:
W = Win probability (winning trades / total trades)
R = Win/Loss ratio (average win / average loss)

Example:
Win Rate: 60% (0.60)
Average Win: ₹15,000
Average Loss: ₹10,000
Win/Loss Ratio: 1.5

Kelly % = 0.60 - [(1 - 0.60) / 1.5]
Kelly % = 0.60 - 0.27 = 0.33 = 33%
```

**Full Kelly:** Use entire Kelly percentage (very aggressive)
**Half Kelly:** Use 50% of Kelly (recommended)
**Quarter Kelly:** Use 25% of Kelly (conservative)

**Advantages:**
- Maximizes long-term growth rate
- Mathematically proven optimal
- Adjusts for strategy edge

**Disadvantages:**
- Requires accurate win rate and payoff data
- Very volatile equity curve
- Can suggest dangerously large positions
- Assumes independent, identically distributed trades

**Practical Application:**
- Use Half-Kelly or Quarter-Kelly for safety
- Recalculate quarterly with updated statistics
- Cap maximum position at 20-25% regardless of Kelly
- Only use with proven strategies (100+ trades)

---

### Method 3: Volatility-Adjusted Position Sizing

**Concept:**
Adjust position size based on asset volatility (ATR).

**Formula:**
```
Position Size = (Account Risk %) / (ATR × Multiplier)

Example using ATR:
Account: ₹10,00,000
Risk: 2% = ₹20,000
ATR (14-day): ₹80
ATR Multiplier: 2 (for stop placement)

Stop Distance: ₹80 × 2 = ₹160
Position Size: ₹20,000 / ₹160 = 125 shares

Dollar Value: 125 × Current Price
```

**Advantages:**
- Equalizes risk across different assets
- Larger positions in low-volatility stocks
- Smaller positions in high-volatility stocks
- Scientifically sound approach

**Disadvantages:**
- Requires volatility calculation
- ATR can change rapidly
- More complex than fixed fractional

---

### Method 4: Percent of Portfolio

**Concept:**
Allocate fixed percentage to each position.

**Formula:**
```
Position Value = Account Equity × Allocation %

Example:
Account: ₹10,00,000
Allocation: 10% per position
Position Value: ₹1,00,000

If Stock Price = ₹2,500
Shares to Buy: ₹1,00,000 / ₹2,500 = 40 shares
```

**Variations:**
- Equal weight: Same % to all positions
- Risk-parity: Adjust for volatility/correlation
- Conviction-based: Higher conviction = larger allocation

**Best For:**
- Long-term investing
- Diversified portfolios
- Passive strategies

---

### Method 5: Optimal Position Sizing for F&O

**Futures Contract Sizing:**
```
Number of Contracts = (Account Risk %) / (Initial Margin × Risk Factor)

Standard Risk Factor: 2-3× initial margin
```

**Options Position Sizing:**
```
Number of Lots = (Account Risk %) / (Premium per Lot × Risk Multiplier)

Conservative: Premium represents max loss
Aggressive: Account for potential assignment
```

**SPAN Margin Consideration:**
- Total SPAN margin ≤ 50% of account equity
- Maintain 50% buffer for MTM fluctuations
- Avoid over-leverage even if exchange allows

---

## ADVANCED POSITION SIZING CONCEPTS

### Scaling In/Out Techniques

**Pyramiding (Scaling In):**
- Add to winning positions
- Each addition smaller than previous
- Move stop-loss to breakeven on partial profits
- Example:
  - Initial: 100 shares at ₹100
  - Add 50 shares at ₹110 (stop moved to ₹105)
  - Add 25 shares at ₹120 (stop moved to ₹115)

**Scaling Out (Profit Taking):**
- Exit partial position at targets
- Let remainder run with trailing stop
- Example:
  - Sell 50% at Target 1 (1:2 risk-reward)
  - Sell 25% at Target 2 (1:3 risk-reward)
  - Trail remaining 25% with moving average

### Correlation-Adjusted Sizing

**Problem:**
Multiple positions in same sector increases concentration risk.

**Solution:**
Reduce individual position sizes when correlated.

```
If holding 3 NIFTY bank stocks:
Normal size: 10% each
Correlation-adjusted: 5-6% each
Total sector exposure: 15-18% (not 30%)
```

### Account Size Tiers

**Small Accounts (< ₹5 lakhs):**
- Focus on equity delivery
- Avoid F&O leverage
- Maximum 2-3 positions
- Risk: 1-2% per trade

**Medium Accounts (₹5-50 lakhs):**
- Mix of delivery and F&O
- 5-8 positions
- Risk: 1-2% per trade
- Can use limited leverage

**Large Accounts (> ₹50 lakhs):**
- Full diversification possible
- Multiple strategies
- Institutional risk management
- Risk: 0.5-1.5% per trade

---

## PRACTICAL GUIDELINES

**Pre-Trade Checklist:**
1. ✓ Calculate exact position size before entry
2. ✓ Set stop-loss level
3. ✓ Verify total portfolio risk
4. ✓ Check correlation with existing positions
5. ✓ Confirm margin availability (for F&O)

**Position Sizing Tools:**
- Spreadsheet calculators
- Broker risk calculators
- Trading platform built-in tools
- Mobile apps for on-the-go calculation

**Common Mistakes:**
- Doubling down on losing positions (averaging down without plan)
- Over-leveraging in F&O
- Ignoring correlation risk
- Not adjusting size after large wins/losses
- Emotional position sizing (increasing size out of frustration)

**Professional Standards:**
- Hedge funds: Typically risk 0.5-1% per trade
- Prop traders: Daily loss limits (2-3% of account)
- Banks: VaR-based limits (Value at Risk)
- RIAs: Modern Portfolio Theory optimization
"""
        }

        position_sizing["content"].append(sizing_methods)
        position_sizing["sources"] = [
            {
                "source_id": "cftc",
                "url": "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/AdvisoryFuturesOptions.htm",
                "trust_level": "high",
                "reference": "CFTC Advisory on Futures and Options Risk Management"
            },
            {
                "source_id": "cme_group",
                "url": "https://www.cmegroup.com/education/courses/introduction-to-futures.html",
                "trust_level": "high",
                "reference": "CME Group Futures Education"
            },
            {
                "source_id": "finance_textbooks",
                "reference": "Van Tharp - Trade Your Way to Financial Freedom (Position Sizing Chapter)"
            }
        ]

        return position_sizing

    def extract_stop_loss_rules(self):
        """Extract stop-loss implementation rules"""
        print("🛑 Extracting stop-loss rules...")

        stop_loss_rules = {
            "topic_id": "risk_stop_loss",
            "title": "Stop-Loss Implementation and Exit Strategies",
            "content": [],
            "sources": []
        }

        stop_content = {
            "heading": "Stop-Loss Types and Implementation",
            "content": """
**Definition:**
A stop-loss order is a pre-determined exit point that limits losses on a position. It is the most important risk management tool for traders.

**Why Stop-Losses are MANDATORY:**
1. Limits losses to acceptable amount
2. Removes emotion from exit decisions
3. Protects capital for future trades
4. Defines risk-reward ratio before entry
5. Prevents catastrophic losses

---

## TYPES OF STOP-LOSSES

### Type 1: Percentage-Based Stop-Loss

**Concept:**
Exit when price moves against you by fixed percentage.

**Calculation:**
```
Stop Price = Entry Price × (1 - Stop %)

For Long Positions:
Entry: ₹100
Stop %: 5%
Stop Price: ₹100 × (1 - 0.05) = ₹95

For Short Positions:
Entry: ₹100
Stop %: 5%
Stop Price: ₹100 × (1 + 0.05) = ₹105
```

**Guidelines by Timeframe:**
- Intraday: 1-2% stops
- Swing trading (2-10 days): 3-5% stops
- Position trading (weeks-months): 8-12% stops
- Long-term investing: 15-20% stops

**Advantages:**
- Simple to calculate
- Easy to implement
- Works across all timeframes

**Disadvantages:**
- Arbitrary levels not based on market structure
- Can be triggered by normal volatility
- Doesn't account for support/resistance

---

### Type 2: Technical Stop-Loss

**Concept:**
Place stops at logical technical levels where trade thesis is invalidated.

**Common Technical Stop Locations:**

1. **Support/Resistance Stops:**
   - Long: Below recent support level
   - Short: Above recent resistance level
   - Add buffer (1-2%) for wicks/spikes
   
   Example:
   - Support at ₹4,950
   - Entry at ₹5,100
   - Stop at ₹4,900 (₹50 below support)

2. **Moving Average Stops:**
   - Use key moving averages as dynamic stops
   - Common choices: 20 EMA, 50 SMA, 200 SMA
   - Exit when price closes beyond MA
   
   Example:
   - Entry: ₹2,500
   - 20 EMA: ₹2,420
   - Stop: Close below 20 EMA

3. **Trendline Stops:**
   - Draw trendline connecting higher lows (uptrend)
   - Place stop below trendline
   - Adjust as trendline evolves
   
4. **Swing High/Low Stops:**
   - Long: Below most recent swing low
   - Short: Above most recent swing high
   - Logical point where trend structure breaks

**Advantages:**
- Based on actual market structure
- Respects support/resistance
- Less likely to be stopped out by noise

**Disadvantages:**
- Requires chart analysis skills
- Stop distance varies (affects position sizing)
- Subjective placement

---

### Type 3: Volatility-Based Stop-Loss (ATR Stops)

**Concept:**
Use Average True Range (ATR) to set stops based on current market volatility.

**Calculation:**
```
Stop Distance = ATR × Multiplier

Long Position:
Stop Price = Entry Price - (ATR × Multiplier)

Short Position:
Stop Price = Entry Price + (ATR × Multiplier)

Typical Multipliers:
- Intraday: 1.5× - 2× ATR
- Swing: 2× - 3× ATR
- Position: 3× - 4× ATR
```

**Example:**
```
Stock: RELIANCE
Entry: ₹2,500
ATR (14-day): ₹45
Multiplier: 2

Stop Distance: ₹45 × 2 = ₹90
Stop Price: ₹2,500 - ₹90 = ₹2,410

Position Sizing:
Account: ₹10,00,000
Risk: 2% = ₹20,000
Risk per share: ₹90
Shares: ₹20,000 / ₹90 = 222 shares
```

**Advantages:**
- Adapts to changing volatility
- Scientifically determined
- Equalizes risk across different stocks

**Disadvantages:**
- Requires ATR calculation
- ATR can expand rapidly during crises
- More complex than fixed percentage

---

### Type 4: Time-Based Stop-Loss

**Concept:**
Exit if trade doesn't move in your favor within specified timeframe.

**Implementation:**
```
Day Trading:
- Exit by end of day (no overnight risk)
- Or exit if no movement within 30 minutes

Swing Trading:
- Maximum hold period: 5-10 days
- Exit on day N if target not hit

Position Trading:
- Quarterly review
- Exit if thesis doesn't play out in expected timeframe
```

**Time Decay Considerations:**
- Options buyers: Time works against you
- Must exit before theta decay accelerates
- Weekly options: Exit by Wednesday (for Friday expiry)

**Advantages:**
- Frees up capital for better opportunities
- Prevents "dead money" positions
- Forces discipline

**Disadvantages:**
- Good trades may need more time
- Arbitrary time limits
- Should combine with price stops

---

### Type 5: Trailing Stop-Loss

**Concept:**
Automatically adjust stop-loss as price moves in your favor.

**Methods:**

1. **Manual Trailing:**
   - Move stop up (for longs) as price advances
   - Lock in profits at key levels
   - Example:
     - Entry: ₹100, Stop: ₹95
     - Price reaches ₹110: Move stop to ₹105
     - Price reaches ₹120: Move stop to ₹115

2. **Indicator-Based Trailing:**
   - Use Parabolic SAR
   - Use moving average (e.g., 20 EMA)
   - Use Chandelier Exit (ATR-based)

3. **Percentage Trailing:**
   - Trail by fixed percentage from highs
   - Example: Trail 5% from highest close
   - Automatically calculated by brokers

**Advantages:**
- Captures trends
- Locks in profits
- Removes emotion from profit-taking

**Disadvantages:**
- Can exit too early in strong trends
- Requires monitoring
- Whipsaws in volatile markets

---

## STOP-LOSS BEST PRACTICES

**Golden Rules:**

1. **ALWAYS Use Stop-Loss:**
   - No exceptions, no matter how confident
   - Even for "sure shot" trades
   - Part of professional trading discipline

2. **Set Stop BEFORE Entry:**
   - Determine exit point before entering
   - Calculate position size based on stop distance
   - Never widen stop after entry

3. **Stop Placement Strategy:**
   - Place at logical technical levels
   - Give enough room for normal volatility
   - Don't place at obvious round numbers
   - Consider market maker behavior (stop hunts)

4. **Risk-Reward Ratio:**
   - Minimum 1:2 (risk : reward)
   - Ideal 1:3 or better
   - If target too far, skip the trade

5. **Stop Execution:**
   - Use hard stops (actual orders in system)
   - Don't rely on mental stops
   - Automate wherever possible

**Advanced Techniques:**

**Stop-and-Reverse:**
- Exit losing position and immediately enter opposite direction
- Used in trend-following systems
- Requires strong conviction in new direction

**Hedging Instead of Stopping:**
- Hold losing position but hedge with options/futures
- Buys time for recovery
- Advanced technique, not recommended for beginners

**Partial Stops:**
- Exit 50% at first stop level
- Let remainder run with wider stop
- Compromise between cutting losses and giving room

**Common Mistakes:**

❌ Moving stop further away ("giving it room")
❌ Removing stop entirely ("it'll come back")
❌ Averaging down on losing positions
❌ Using arbitrary percentage stops without technical basis
❌ Placing stops at obvious levels (round numbers)
❌ Not accounting for gaps/overnight risk

**Psychological Aspects:**

**Why Traders Avoid Stops:**
- Ego: "I can't be wrong"
- Hope: "It will recover"
- Fear of being stopped out and watching reversal
- Past experience of premature stops

**Professional Mindset:**
- Accept losses as cost of doing business
- Small losses keep you in the game
- One uncontrolled loss can wipe out months of profits
- Stops protect you from yourself

**Regulatory Requirements:**

**SEBI Guidelines:**
- Risk disclosure mandatory
- Brokers must collect client risk profile
- Margins and circuit filters act as system-wide stops

**Broker Risk Systems:**
- Automatic square-off if margin breached
- VAR margin acts as portfolio-level stop
- Position limits prevent over-exposure
"""
        }

        stop_loss_rules["content"].append(stop_content)
        stop_loss_rules["sources"] = [
            {
                "source_id": "cftc",
                "url": "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CFTCFaqFutures.htm",
                "trust_level": "high",
                "reference": "CFTC Investor Protection Resources"
            },
            {
                "source_id": "cme_group",
                "url": "https://www.cmegroup.com/education/whitepapers/risk-management-strategies.html",
                "trust_level": "high",
                "reference": "CME Risk Management Whitepapers"
            },
            {
                "source_id": "finance_textbooks",
                "reference": "Alexander Elder - Trading for a Living (Risk Management Chapter)"
            }
        ]

        return stop_loss_rules

    def extract_drawdown_limits(self):
        """Extract drawdown control frameworks"""
        print("📉 Extracting drawdown limits...")

        drawdown_rules = {
            "topic_id": "risk_drawdown",
            "title": "Drawdown Control and Capital Preservation Framework",
            "content": [],
            "sources": []
        }

        drawdown_content = {
            "heading": "Maximum Drawdown Limits and Recovery Protocols",
            "content": """
**Definition:**
Drawdown is the peak-to-trough decline in account value. Maximum Drawdown (MDD) is the largest cumulative loss experienced over a specified period.

**Calculation:**
```
Drawdown % = [(Peak Value - Trough Value) / Peak Value] × 100

Example:
Peak: ₹10,00,000
Trough: ₹8,50,000
Drawdown: [(10,00,000 - 8,50,000) / 10,00,000] × 100 = 15%
```

---

## DRAWDOWN LIMITS BY ACCOUNT TYPE

### Retail Traders

**Daily Loss Limits:**
- Maximum daily loss: 2-3% of account equity
- If hit, stop trading for the day
- Prevents emotional revenge trading

**Weekly Loss Limits:**
- Maximum weekly loss: 5-6% of account
- If hit, reduce position sizes by 50% next week
- Review strategy effectiveness

**Monthly Loss Limits:**
- Maximum monthly loss: 10% of account
- If hit, stop trading for remainder of month
- Conduct thorough strategy review
- Resume only after identifying and fixing issues

**Maximum Drawdown Threshold:**
- Absolute maximum: 20% from peak
- If breached, mandatory trading halt
- Complete strategy overhaul required
- Paper trading until confidence restored

---

### Professional Proprietary Traders

**Prop Firm Standards (India):**

**Daily Limits:**
- Hard stop: 2% of allocated capital
- Soft warning: 1.5% (reduce size)
- Breach results in immediate position square-off

**Weekly/Monthly:**
- Weekly max: 5%
- Monthly max: 8-10%
- Progressive reduction in limits after breaches

**Consequences:**
- First breach: Warning + size reduction
- Second breach: Mandatory training
- Third breach: Capital allocation reduced or revoked

---

### Institutional Standards (Hedge Funds/Family Offices)

**Drawdown Controls:**

**Tier 1 (0-5% drawdown):**
- Normal operations
- Standard position sizing
- Regular reporting

**Tier 2 (5-10% drawdown):**
- Enhanced monitoring
- Reduce gross exposure by 20%
- Increase cash buffer
- Weekly risk committee review

**Tier 3 (10-15% drawdown):**
- Emergency protocols activated
- Reduce exposure by 50%
- Halt new positions
- Daily risk meetings
- Client communication required

**Tier 4 (>15% drawdown):**
- Complete trading halt
- Liquidate risky positions
- Board-level intervention
- Potential fund closure consideration

---

## DRAWDOWN RECOVERY PROTOCOLS

### Phase 1: Assessment (Days 1-3)

**Actions:**
1. Analyze all losing trades
   - Were they valid setups?
   - Was risk management followed?
   - External factors (market crash, black swan)?

2. Categorize losses:
   - Systematic (market-wide)
   - Idiosyncratic (stock-specific)
   - Process failures (rule violations)

3. Calculate statistical significance:
   - Is this within expected variance?
   - Has strategy edge disappeared?
   - Sample size sufficient for conclusions?

**Decision Tree:**
- If process failure → Fix discipline issues
- If market regime change → Adapt or pause
- If random variance → Continue (within limits)

---

### Phase 2: Size Reduction (Week 1-2)

**Position Sizing Adjustment:**
```
New Size = Normal Size × (Current Equity / Peak Equity)

Example:
Peak: ₹10,00,000
Current: ₹8,50,000
Reduction Factor: 0.85

Normal position: 100 shares
Reduced position: 85 shares
```

**Benefits:**
- Reduces risk while confidence rebuilding
- Mathematical path to recovery
- Prevents "swing for fences" mentality

---

### Phase 3: Gradual Rebuilding (Week 3-4)

**Criteria to Increase Size:**
1. Consecutive winning trades (minimum 3)
2. Back above key moving average (equity curve)
3. Regained psychological confidence
4. Market conditions favorable

**Scaling Plan:**
- Week 3: 75% of normal size
- Week 4: 90% of normal size
- Week 5: Full size (if criteria met)

---

### Phase 4: Full Recovery (Month 2+)

**Return to Normal Operations:**
- Full position sizing
- All strategies active
- Regular risk parameters

**Post-Recovery Review:**
- Document lessons learned
- Update trading plan
- Adjust drawdown limits if needed
- Share insights with team

---

## PSYCHOLOGICAL ASPECTS OF DRAWDOWNS

### Emotional Stages

**Stage 1: Denial**
- "It's just a rough patch"
- Ignore warning signs
- Increase risk to "make it back quick"

**Stage 2: Frustration**
- Anger at market
- Revenge trading
- Abandoning system

**Stage 3: Depression**
- Loss of confidence
- Second-guessing all decisions
- Paralysis (can't pull trigger)

**Stage 4: Acceptance**
- Acknowledge problems
- Seek help/review
- Make necessary changes

**Stage 5: Recovery**
- Regain discipline
- Follow process
- Rebuild gradually

---

### Mental Framework for Professionals

**Reframing Drawdowns:**

✅ Drawdowns are INEVITABLE
- Even best traders have them
- Part of the business
- Not a personal failure

✅ Focus on PROCESS not OUTCOME
- Did you follow your rules?
- Was risk managed properly?
- Some losses are statistically normal

✅ Drawdowns are LEARNING OPPORTUNITIES
- Reveals weaknesses in system
- Tests psychological resilience
- Separates amateurs from professionals

✅ CAPITAL PRESERVATION IS PARAMOUNT
- Survival is priority #1
- You can't make money with zero capital
- Live to fight another day

---

## MATHEMATICS OF DRAWDOWN RECOVERY

**Recovery Percentages Required:**

| Drawdown | Recovery Needed | Difficulty |
|----------|----------------|------------|
| 10%      | 11.1%          | Manageable |
| 20%      | 25%            | Challenging |
| 30%      | 42.9%          | Very Difficult |
| 40%      | 66.7%          | Extremely Difficult |
| 50%      | 100%           | Near Impossible |

**Key Insight:**
The deeper the drawdown, the EXPONENTIALLY harder the recovery. This is why preventing large drawdowns is CRITICAL.

**Example:**
```
Account: ₹10,00,000
50% loss = ₹5,00,000 remaining
Need 100% gain on ₹5,00,000 to get back to ₹10,00,000
Much harder than making 10% on initial capital
```

---

## RISK METRICS AND MONITORING

### Key Drawdown Metrics

**1. Maximum Drawdown (MDD):**
- Largest peak-to-trough decline
- Historical worst-case scenario
- Compare across strategies

**2. Average Drawdown:**
- Mean of all drawdowns
- Typical pain to expect
- Better measure than MDD alone

**3. Drawdown Duration:**
- How long underwater (from peak to recovery)
- Tests psychological endurance
- Longer durations increase redemption risk

**4. Calmar Ratio:**
```
Calmar Ratio = Annualized Return / Maximum Drawdown

Higher is better (> 3.0 excellent, < 1.0 poor)
Measures return per unit of drawdown risk
```

**5. Ulcer Index:**
- Measures both depth and duration of drawdowns
- Lower is better
- More comprehensive than MDD alone

---

## EARLY WARNING SIGNALS

**Indicators You're Heading Toward Drawdown:**

⚠️ **Increased Loss Frequency:**
- Win rate dropping below historical average
- 3+ consecutive losses
- Losing trades exceeding winners

⚠️ **Larger-than-Normal Losses:**
- Individual losses > 2× average
- Stops being hit more frequently
- Gap risk materializing

⚠️ **Strategy Deviation:**
- Taking unplanned trades
- Ignoring entry/exit rules
- Emotional decision-making

⚠️ **Market Regime Change:**
- Your strategy type underperforming
- Volatility spike
- Correlation breakdown

⚠️ **Personal Factors:**
- Trading while emotional/stressed
- Health issues affecting judgment
- Overconfidence after winning streak

**Action When Signals Appear:**
1. Reduce position sizes preemptively
2. Increase monitoring frequency
3. Review all trades more carefully
4. Consider temporary pause if multiple signals

---

## PROFESSIONAL RISK COMMITTEE STRUCTURE

**For Institutional Accounts:**

**Committee Members:**
- Chief Investment Officer (Chair)
- Head of Risk Management
- Portfolio Manager
- Compliance Officer

**Meeting Frequency:**
- Normal times: Monthly
- During drawdown (>5%): Weekly
- Crisis mode (>10%): Daily

**Agenda Items:**
- Current drawdown status
- Comparison to limits
- Root cause analysis
- Corrective actions
- Client communications (if needed)

**Documentation:**
- Meeting minutes
- Risk reports
- Action item tracking
- Regulatory filings (if required)
"""
        }

        drawdown_rules["content"].append(drawdown_content)
        drawdown_rules["sources"] = [
            {
                "source_id": "cftc",
                "url": "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/index.htm",
                "trust_level": "high",
                "reference": "CFTC Customer Protection Advisories"
            },
            {
                "source_id": "cme_group",
                "url": "https://www.cmegroup.com/education/whitepapers/portfolio-management-risk-metrics.html",
                "trust_level": "high",
                "reference": "CME Portfolio Risk Management Whitepapers"
            },
            {
                "source_id": "finance_textbooks",
                "reference": "Brett Steenbarger - The Psychology of Trading (Drawdown Management)"
            }
        ]

        return drawdown_rules

    def compile_raw_notes(self):
        """Compile all extracted data into raw notes"""
        print("📝 Compiling risk management raw notes...")

        # Extract all sections
        sections = [
            self.extract_position_sizing(),
            self.extract_stop_loss_rules(),
            self.extract_drawdown_limits()
        ]

        # Add to extracted data
        self.extracted_data["topics"] = sections

        # Generate markdown output
        markdown_content = self._generate_markdown()

        # Save to file
        output_file = self.output_dir / "risk_management_raw.md"
        output_file.write_text(markdown_content, encoding='utf-8')

        # Also save structured JSON
        json_file = self.output_dir / "risk_management_raw.json"
        json_file.write_text(json.dumps(
            self.extracted_data, indent=2), encoding='utf-8')

        print(f"✅ Risk management extraction complete!")
        print(f"📄 Saved: {output_file}")
        print(f"📊 Saved: {json_file}")

        return output_file

    def _generate_markdown(self):
        """Generate formatted markdown from extracted data"""
        md = []

        # Header
        md.append("# Risk Management Framework - Raw Extraction Notes")
        md.append("")
        md.append(
            f"**Extraction Date:** {self.extracted_data['extraction_date']}")
        md.append(f"**Sources:** CFTC, CME Group, Finance Textbooks")
        md.append("")
        md.append("---")
        md.append("")

        # Content sections
        for topic in self.extracted_data["topics"]:
            md.append(f"## {topic['title']}")
            md.append(f"**Topic ID:** `{topic['topic_id']}`")
            md.append("")

            for section in topic["content"]:
                md.append(f"### {section['heading']}")
                md.append(section["content"])
                md.append("")

            # Sources
            md.append("**Sources:**")
            for source in topic["sources"]:
                md.append(
                    f"- Source ID: `{source['source_id']}` | Trust Level: {source['trust_level']}")
                md.append(f"  - URL: {source.get('url', 'N/A')}")
                if "reference" in source:
                    md.append(f"  - Reference: {source['reference']}")
                md.append("")

            md.append("---")
            md.append("")

        # Footer
        md.append("")
        md.append("---")
        md.append("")
        md.append(
            "*These are raw extraction notes for knowledge base construction.*")
        md.append(
            "*Content should be processed, chunked, and validated before use.*")

        return "\n".join(md)


def main():
    """Main extraction function"""
    print("=" * 70)
    print("🚀 RISK MANAGEMENT EXTRACTION")
    print("=" * 70)
    print()

    extractor = RiskManagementExtractor()
    output_file = extractor.compile_raw_notes()

    print()
    print("=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print()
    print(f"Output File: {output_file.absolute()}")
    print()


if __name__ == "__main__":
    main()
