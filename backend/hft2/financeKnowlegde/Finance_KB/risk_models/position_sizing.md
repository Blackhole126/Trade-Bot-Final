# Position Sizing Framework

**Topic ID:** `risk_position_sizing`  
**Version:** 1.0.0  
**Last Updated:** 2026-03-20

---

## Core Principles of Position Sizing

### Definition
Position sizing determines how much capital to allocate to a specific trade based on account size, risk tolerance, and trade characteristics. It is the most critical component of risk management.

### The Risk-First Approach

**Golden Rule:** Determine risk amount BEFORE entry, never after.

```
Position Sizing Sequence:
1. Identify entry price
2. Determine stop-loss level
3. Calculate risk per share/contract
4. Decide maximum account risk (%)
5. Calculate position size
6. Verify total portfolio impact
```

### The 2% Rule (Maximum Risk Per Trade)

**Conservative Approach:**
- Maximum risk per trade: **1%** of account equity
- Suitable for: Most traders, preserving capital

**Moderate Approach:**
- Maximum risk per trade: **2%** of account equity
- Suitable for: Experienced traders with proven systems

**Aggressive Approach:**
- Maximum risk per trade: **3%** of account equity
- Suitable for: Professional traders only
- ⚠️ Not recommended for beginners

**Mathematical Basis:**
- Prevents ruin from losing streaks
- Even with 10 consecutive losses at 2% = only 20% drawdown
- Allows recovery without catastrophic damage

### Total Portfolio Risk Limits

**Simultaneous Positions:**
- Maximum open positions: **5-10** (diversified)
- Avoid concentration in single sector

**Total Portfolio Risk:**
- Maximum simultaneous risk: **10-15%** of equity
- Example: If risking 2% per trade, max 5-7 positions

**Correlation Consideration:**
- Reduce individual sizes if positions correlated
- 3 banking stocks ≠ 30% risk, reduce to 15-18% total

---

## Position Sizing Methods

### Method 1: Fixed Fractional Position Sizing

**Concept:** Risk fixed percentage of account on each trade.

#### Formula
```
Position Size = (Account Equity × Risk %) / (Entry Price - Stop Loss Price)

Or equivalently:
Position Size = Account Risk Amount / Risk Per Share
```

#### Detailed Example

**Scenario:**
```
Account Equity: ₹10,00,000
Risk Per Trade: 2% = ₹20,000
Stock: RELIANCE
Entry Price: ₹2,500
Stop Loss: ₹2,400
```

**Calculation:**
```
Risk Per Share = Entry - Stop Loss
Risk Per Share = ₹2,500 - ₹2,400 = ₹100

Position Size = ₹20,000 / ₹100 = 200 shares

Capital Required = 200 shares × ₹2,500 = ₹5,00,000
(50% of account - acceptable for cash segment)
```

**For F&O:**
```
If RELIANCE Futures lot size = 250 shares
Number of Lots = 200 / 250 = 0.8 lots
→ Round down to 0 lots (can't afford full lot with 2% risk)
OR
Increase risk to 3% = ₹30,000
Lots = ₹30,000 / (₹100 × 250) = 1.2 → 1 lot
```

#### Advantages
✅ Simple to calculate and implement  
✅ Automatically reduces size after losses (capital preservation)  
✅ Increases size after wins (pyramiding effect)  
✅ Mathematically prevents ruin  
✅ Works across all asset classes  

#### Disadvantages
❌ Doesn't account for volatility differences  
❌ Same risk % regardless of setup quality  
❌ May be too conservative for low-volatility trades  
❌ Doesn't consider correlation  

#### Best For
- Beginners learning risk management
- Systematic traders with consistent setups
- Multi-strategy portfolios
- Capital preservation focus

---

### Method 2: Kelly Criterion (Optimal f)

**Concept:** Mathematically optimal bet size based on win rate and payoff ratio.

#### Formula
```
Kelly % = W - [(1 - W) / R]

Where:
W = Win probability (winning trades / total trades)
R = Win/Loss ratio (average win / average loss)
```

#### Detailed Example

**Trading System Statistics (based on 100+ trades):**
```
Win Rate: 60% (0.60)
Average Win: ₹15,000
Average Loss: ₹10,000
Win/Loss Ratio: 1.5
```

**Kelly Calculation:**
```
Kelly % = 0.60 - [(1 - 0.60) / 1.5]
Kelly % = 0.60 - [0.40 / 1.5]
Kelly % = 0.60 - 0.267
Kelly % = 0.333 = 33.3%
```

**Interpretation:**
- Full Kelly suggests betting 33.3% of capital per trade
- This is EXTREMELY aggressive
- Leads to high volatility in equity curve

#### Practical Application: Fractional Kelly

**Full Kelly (Not Recommended):**
- Use entire Kelly percentage
- Maximum long-term growth
- Extremely volatile equity curve
- Psychological stress very high

**Half-Kelly (Recommended):**
```
Position Size = Kelly % / 2
Position Size = 33.3% / 2 = 16.65%
```
- Reduces volatility by 50%
- Retains 75% of growth potential
- Much more psychologically manageable

**Quarter-Kelly (Conservative):**
```
Position Size = Kelly % / 4
Position Size = 33.3% / 4 = 8.325%
```
- Very smooth equity curve
- Lower returns but sustainable
- Good for large accounts

#### Advantages
✅ Maximizes long-term geometric growth rate  
✅ Mathematically proven optimal  
✅ Adjusts for strategy edge automatically  
✅ Accounts for both win rate and payoff  

#### Disadvantages
❌ Requires accurate statistics (100+ trades minimum)  
❌ Very volatile equity curve with full Kelly  
❌ Can suggest dangerously large positions  
❌ Assumes independent, identically distributed trades  
❌ Doesn't account for changing market conditions  

#### Requirements for Use
- Minimum 100 trades (preferably 200+)
- Consistent strategy (no major changes)
- Accurate record-keeping
- Strong psychological discipline
- Regular recalculation (quarterly)

#### When NOT to Use
❌ New traders without track record  
❌ Strategies with <50 trades  
❌ Changing market conditions  
❌ Small accounts (<₹10 lakhs)  
❌ Low risk tolerance  

---

### Method 3: Volatility-Adjusted Position Sizing

**Concept:** Adjust position size based on asset volatility using Average True Range (ATR).

#### ATR-Based Sizing Formula

```
Position Size = (Account Risk %) / (ATR × Multiplier)

Or:
Shares to Buy = Account Risk Amount / (ATR × Multiplier)
```

#### Detailed Example

**Scenario:**
```
Account: ₹10,00,000
Risk: 2% = ₹20,000
Stock: TATAMOTORS
Current Price: ₹650
ATR (14-day): ₹18
ATR Multiplier: 2 (for stop placement)
```

**Calculation:**
```
Stop Distance = ATR × Multiplier
Stop Distance = ₹18 × 2 = ₹36

Position Size = ₹20,000 / ₹36 = 555 shares

Dollar Value = 555 × ₹650 = ₹3,60,750
```

**Stop Loss Placement:**
```
Stop Price = Entry - Stop Distance
Stop Price = ₹650 - ₹36 = ₹614
```

#### ATR Multipliers by Timeframe

**Intraday Trading:**
- Multiplier: 1.5× - 2× ATR
- Tighter stops due to shorter time horizon
- Faster exits

**Swing Trading (2-10 days):**
- Multiplier: 2× - 3× ATR
- Room for normal volatility
- Most common range

**Position Trading (weeks-months):**
- Multiplier: 3× - 4× ATR
- Wider stops for trend development
- Fewer premature exits

#### Advantages
✅ Equalizes risk across different assets  
✅ Larger positions in low-volatility stocks  
✅ Smaller positions in high-volatility stocks  
✅ Scientifically sound approach  
✅ Adapts to changing volatility  

#### Disadvantages
❌ Requires ATR calculation  
❌ ATR can expand rapidly during crises  
❌ More complex than fixed fractional  
❌ May reduce size too much in high vol environments  

#### Strategic Applications

**Portfolio-Level Volatility Targeting:**
```
Target Portfolio Volatility: 15% annualized

Calculate individual position volatility:
Position Volatility = (Position Value / Portfolio) × Stock ATR %

Adjust sizes to keep total portfolio vol ≤ target
```

**Volatility-Weighted Portfolio:**
```
Low Volatility Stocks (ATR < 2%): Higher allocation (15-20%)
Medium Volatility (ATR 2-4%): Medium allocation (10-15%)
High Volatility (ATR > 4%): Lower allocation (5-8%)
```

---

### Method 4: Percent of Portfolio Allocation

**Concept:** Allocate fixed percentage to each position regardless of stop distance.

#### Formula
```
Position Value = Account Equity × Allocation %

Shares to Buy = Position Value / Current Price
```

#### Example

**Equal-Weight Portfolio:**
```
Account: ₹10,00,000
Number of Positions: 10
Allocation per Position: 10%

Position Value = ₹10,00,000 × 10% = ₹1,00,000

If Stock Price = ₹2,500
Shares to Buy = ₹1,00,000 / ₹2,500 = 40 shares
```

#### Variations

**1. Equal Weight:**
- Same % to all positions
- Simple rebalancing
- True diversification

**2. Risk Parity (Volatility-Adjusted):**
```
Allocate based on inverse volatility:

Weight_i = (1 / Volatility_i) / Sum(1 / Volatility_all)

Low vol stocks get higher weight
High vol stocks get lower weight
Equalizes risk contribution
```

**3. Conviction-Based:**
```
High Conviction (Top Ideas): 15-20%
Medium Conviction: 10%
Low Conviction (Satellite): 5%

Requires strong conviction scale
Subjective but flexible
```

#### Advantages
✅ Simple to implement  
✅ Easy rebalancing  
✅ Good for long-term investing  
✅ Natural diversification  

#### Disadvantages
❌ Doesn't account for risk per trade  
❌ No stop-loss consideration  
❌ May overexpose to high-volatility stocks  
❌ Not suitable for active trading  

#### Best For
- Long-term investors
- Passive index portfolios
- Core-satellite strategies
- Retirement accounts

---

### Method 5: F&O-Specific Position Sizing

#### Futures Contract Sizing

**Formula:**
```
Number of Contracts = (Account Risk %) / (Initial Margin × Risk Factor)

Standard Risk Factor: 2-3× initial margin
```

**Example:**
```
Account: ₹10,00,000
Risk: 2% = ₹20,000
NIFTY Futures Lot: 25 units
Price: 22,000
Contract Value: ₹5,50,000
Initial Margin: ₹1,10,000 (20%)

Risk Factor: 2.5×
Max Risk per Contract = ₹1,10,000 × 2.5 = ₹2,75,000

Number of Contracts = ₹20,000 / ₹2,75,000 = 0.073
→ Round down to 0 contracts (can't trade with 2% risk)

Practical Solution:
- Increase risk to 5% = ₹50,000
- Or trade smaller contracts (BANKNIFTY has smaller lot)
- Or use options instead
```

#### Options Position Sizing

**For Option Buyers:**
```
Maximum Loss = Premium Paid

Position Size = Account Risk % / Premium per Lot

Example:
Account: ₹10,00,000
Risk: 2% = ₹20,000
Option Premium: ₹100
Lot Size: 50

Premium per Lot = ₹100 × 50 = ₹5,000
Number of Lots = ₹20,000 / ₹5,000 = 4 lots
```

**For Option Sellers (Writing):**
```
Consider maximum potential loss (unlimited for naked calls)

Conservative Approach:
- Margin required = Exchange SPAN + Exposure
- Maximum allocation: 20-25% per position
- Always hedge tail risk

Example:
Account: ₹10,00,000
Margin per lot: ₹1,50,000
Maximum lots: ₹10,00,000 / ₹1,50,000 = 6.67 → 6 lots
But limit to 20% exposure = 1-2 lots maximum
```

#### SPAN Margin Considerations

**Total Portfolio Margin:**
```
Total SPAN Margin ≤ 50% of Account Equity

Maintain 50% buffer for MTM fluctuations
Prevents margin calls during adverse moves
```

**Example:**
```
Account: ₹10,00,000
Available for Margin: ₹5,00,000 (50%)

If NIFTY 1 lot margin = ₹1,10,000
Maximum Lots = ₹5,00,000 / ₹1,10,000 = 4.5 → 4 lots

Remaining buffer: ₹60,000 for MTM
```

---

## Advanced Position Sizing Concepts

### Scaling In/Out Techniques

#### Pyramiding (Scaling In)

**Adding to Winning Positions:**

**Classic Pyramid:**
```
Initial Position: 100 shares at ₹100
Add 1: 50 shares at ₹110 (stop moved to ₹105)
Add 2: 25 shares at ₹120 (stop moved to ₹115)

Characteristics:
- Each addition smaller than previous
- Inverted pyramid shape
- Stop-loss trailed upward
- Locks in profits progressively
```

**Rules for Pyramiding:**
1. Only add to winning positions (never losers)
2. Each addition must show profit before next add
3. Move stop-loss to breakeven on partial profits
4. Reduce addition sizes (don't over-leverage at top)
5. Have predefined exit plan

**When to Pyramid:**
✅ Strong trending market  
✅ Position showing quick profit  
✅ ADX > 30 (strong trend)  
✅ Multiple timeframe alignment  

**When NOT to Pyramid:**
❌ Ranging/choppy market  
❌ Position at breakeven or loss  
❌ ADX < 25 (weak trend)  
❌ Near major resistance  

#### Scaling Out (Profit Taking)

**Partial Exits at Targets:**

**Example Structure:**
```
Position: 100 shares at ₹100
Target 1 (1:2 RR): Sell 50 shares at ₹120
Target 2 (1:3 RR): Sell 25 shares at ₹130
Remainder: Trail with 20 EMA

Result:
- 50% booked at Target 1 (covers risk)
- 25% at Target 2 (pure profit)
- 25% lets runner capture trend
```

**Benefits:**
- Reduces risk after partial exit
- Locks in profits systematically
-心理ologically easier (banking profits)
- Allows participation in extended moves

### Correlation-Adjusted Sizing

**The Problem:**
Multiple positions in same sector increases concentration risk beyond apparent diversification.

**Solution:**
Reduce individual position sizes when holding correlated assets.

#### Correlation Adjustment Formula

```
If holding N correlated positions:
Adjusted Size = Normal Size / √N

Example:
Holding 3 banking stocks (HDFC, ICICI, KOTAK)
Normal size per stock: 10%
Correlation-adjusted: 10% / √3 = 10% / 1.732 = 5.77%

Total sector exposure: 3 × 5.77% = 17.3% (not 30%)
```

#### Practical Guidelines

**Sector Exposure Limits:**
```
Single Sector Maximum: 25-30% of portfolio
Highly Correlated Sub-sector: 15-20%
Individual Stock Cap: 10% (unless high conviction)
```

**Correlation Matrix Approach:**
```
Calculate pairwise correlations monthly:

If correlation > 0.7:
→ Treat as single position for sizing
→ Reduce individual allocations

If correlation 0.4-0.7:
→ Moderate reduction
→ Monitor closely

If correlation < 0.4:
→ True diversification
→ Full allocation acceptable
```

### Account Size Tier Considerations

#### Small Accounts (< ₹5 lakhs)

**Constraints:**
- Limited diversification possible
- F&O margins challenging
- Impact of fixed costs (brokerage, STT)

**Recommendations:**
```
Focus: Equity delivery/cash segment
Maximum Positions: 2-3
Risk Per Trade: 1-2%
Avoid: F&O leverage (except very small lots)
Priority: Capital preservation, consistent returns
```

#### Medium Accounts (₹5-50 lakhs)

**Opportunities:**
- Proper diversification possible
- Can participate in F&O selectively
- Better risk management flexibility

**Recommendations:**
```
Mix: 60-70% equity delivery, 30-40% F&O
Positions: 5-8 concurrent
Risk Per Trade: 1-2%
F&O: Selective (index options preferred)
Focus: Balanced growth with controlled risk
```

#### Large Accounts (> ₹50 lakhs)

**Capabilities:**
- Full institutional diversification
- Multiple strategies simultaneously
- Access to all instruments

**Recommendations:**
```
Allocation: Diversified across asset classes
Positions: 10-15+ possible
Risk Per Trade: 0.5-1.5% (lower % but larger absolute)
Strategies: Long-short, arbitrage, hedging
Focus: Risk-adjusted returns, capital preservation
```

---

## Common Position Sizing Mistakes

### ❌ Mistake 1: Doubling Down on Losers

**Wrong Approach:**
```
Buy 100 shares at ₹100
Price drops to ₹80
"Average down" by buying 200 more shares at ₹80

Result:
- Increased exposure to losing trade
- Emotional decision (not planned)
- Violates risk management rules
```

**Correct Approach:**
```
Only add to winners (pyramiding)
Never increase size on losing positions
If thesis broken, exit completely
If thesis intact, wait for reversal confirmation
```

### ❌ Mistake 2: Over-Leveraging in F&O

**Wrong Approach:**
```
Account: ₹10,00,000
Use maximum margin available
Buy 8 lots of NIFTY (₹8.8 lakhs margin)
No buffer for MTM

Result:
- Single adverse move triggers margin call
- Forced square-off at loss
- Account wiped out
```

**Correct Approach:**
```
Use maximum 50% of available margin
Maintain 50% buffer for MTM
Risk maximum 2% per trade
Have predefined exit before entry
```

### ❌ Mistake 3: Ignoring Correlation Risk

**Wrong Approach:**
```
Portfolio:
- HDFC Bank: 10%
- ICICI Bank: 10%
- KOTAK Bank: 10%
- AXIS Bank: 10%
Total Banking: 40%

Problem:
All highly correlated (0.8+)
Banking sector crash = 40% portfolio hit
```

**Correct Approach:**
```
Limit banking sector to 20-25% total
Diversify across sectors (IT, Pharma, FMCG, Auto)
Use correlation-adjusted sizing
Monitor sector exposure daily
```

### ❌ Mistake 4: Not Adjusting After Large Wins/Losses

**Wrong Approach:**
```
After 50% gain: Still use original position sizes
After 30% loss: Desperately increase size to "make back"

Both lead to suboptimal outcomes
```

**Correct Approach:**
```
After Large Wins:
- Gradually increase sizes (compound gains)
- But stay within risk limits
- Don't get overconfident

After Large Losses:
- Reduce sizes immediately
- Preserve remaining capital
- Rebuild confidence gradually
- Review what went wrong
```

### ❌ Mistake 5: Emotional Position Sizing

**Wrong Approaches:**
- Increasing size out of frustration ("revenge trading")
- Decreasing size after trauma (missing opportunities)
- Sizing based on "feeling" rather than calculation
- Changing risk % mid-trade

**Correct Approach:**
- Pre-calculate all position sizes
- Follow system regardless of recent P&L
- Review sizing quarterly, not daily
- Remove emotion through automation

---

## Professional Standards and Benchmarks

### Hedge Fund Practices

**Typical Risk Parameters:**
```
Risk per trade: 0.5-1.5%
Maximum positions: 20-50+
Gross exposure: 100-300% (with leverage)
Net exposure: 50-150%
Maximum drawdown limit: 10-15%
```

**Risk Management Infrastructure:**
- Daily VaR calculations
- Stress testing weekly
- Position limits enforced by system
- Independent risk officer

### Proprietary Trading Firms

**Daily Loss Limits:**
```
Hard stop: 2% of allocated capital
Soft warning: 1.5% (reduce size)
Breach consequences: Immediate square-off, review
```

**Weekly/Monthly Limits:**
```
Weekly max: 5%
Monthly max: 8-10%
Progressive restrictions after breaches
```

### Retail Trader Best Practices

**Recommended Standards:**
```
Risk per trade: 1-2% (maximum 3%)
Daily loss limit: 3% (stop trading if hit)
Weekly loss limit: 6% (review if hit)
Monthly loss limit: 10% (mandatory break if hit)
Maximum drawdown: 20% (complete strategy overhaul)
```

**Tools for Implementation:**
- Position size calculators (spreadsheet/apps)
- Broker risk management tools
- Pre-trade checklists
- Trading journal with size tracking

---

## Sources

- **Source ID:** `cftc` | Trust Level: high
  - URL: https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/AdvisoryFuturesOptions.htm
  - Reference: CFTC Advisory on Futures and Options Risk Management

- **Source ID:** `cme_group` | Trust Level: high
  - URL: https://www.cmegroup.com/education/courses/introduction-to-futures.html
  - Reference: CME Group Futures Education

- **Source ID:** `finance_textbooks` | Trust Level: high
  - Reference: Van Tharp - Trade Your Way to Financial Freedom (Position Sizing Chapter)
  - Reference: Alexander Elder - Trading for a Living (Risk Management)

---

*This document is part of the Finance Knowledge Base system. For LLM ingestion, use topic ID: risk_position_sizing*
