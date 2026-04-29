# Stop-Loss Implementation Rules

**Topic ID:** `risk_stop_loss`  
**Version:** 1.0.0  
**Last Updated:** 2026-03-20

---

## Why Stop-Losses are MANDATORY

### Definition
A stop-loss order is a pre-determined exit point that limits losses on a position. It is the most important risk management tool for traders.

### Critical Importance

**Capital Preservation:**
- Limits losses to acceptable, predefined amount
- Prevents single trade from causing catastrophic damage
- Protects trading capital for future opportunities
- Ensures survival through losing streaks

**Psychological Benefits:**
- Removes emotion from exit decisions
- Eliminates "hope" as a strategy
- Reduces stress and anxiety
- Allows objective decision-making

**Professional Discipline:**
- Defines risk before reward
- Enables proper position sizing
- Creates accountability
- Separates professionals from amateurs

### The Unacceptable Alternative

**Trading Without Stops Leads To:**
```
Small Loss (₹5,000) 
  ↓
"Hold and hope, it will come back"
  ↓
Loss grows to ₹20,000
  ↓
"Now I have to wait for breakeven"
  ↓
Loss becomes ₹50,000
  ↓
Panic exit at worst possible time
  ↓
Account down 50%+ (requires 100% gain to recover)
```

**This pattern has destroyed countless trading accounts.**

---

## Types of Stop-Losses

### Type 1: Percentage-Based Stop-Loss

**Concept:** Exit when price moves against you by fixed percentage.

#### Calculation

**For Long Positions:**
```
Stop Price = Entry Price × (1 - Stop %)

Example:
Entry: ₹100
Stop %: 5%
Stop Price: ₹100 × (1 - 0.05) = ₹95
Risk per share: ₹5
```

**For Short Positions:**
```
Stop Price = Entry Price × (1 + Stop %)

Example:
Entry: ₹100
Stop %: 5%
Stop Price: ₹100 × (1 + 0.05) = ₹105
Risk per share: ₹5
```

#### Guidelines by Trading Style

**Intraday Trading:**
- Stop range: **1-2%**
- Rationale: Small moves, quick exits
- Example: Entry ₹1000, Stop ₹985-990

**Swing Trading (2-10 days):**
- Stop range: **3-5%**
- Rationale: Room for normal volatility
- Example: Entry ₹1000, Stop ₹950-970

**Position Trading (weeks-months):**
- Stop range: **8-12%**
- Rationale: Trend development needs space
- Example: Entry ₹1000, Stop ₹880-920

**Long-term Investing:**
- Stop range: **15-20%**
- Rationale: Major trend changes only
- Example: Entry ₹1000, Stop ₹800-850

#### Advantages
✅ Simple to calculate  
✅ Easy to implement  
✅ Works across all timeframes  
✅ Consistent approach  

#### Disadvantages
❌ Arbitrary levels not based on market structure  
❌ Can be triggered by normal volatility  
❌ Doesn't account for support/resistance  
❌ One-size-fits-all approach  

#### Best Practices
- Use round numbers for mental calculation
- Adjust based on stock's typical volatility
- Combine with other methods for better accuracy
- Never widen stop after entry

---

### Type 2: Technical Stop-Loss

**Concept:** Place stops at logical technical levels where trade thesis is invalidated.

#### Support/Resistance Stops

**Most Common and Reliable Method**

**For Long Positions:**
```
Place stop BELOW recent support level

Example:
Stock: HDFC BANK
Recent Support: ₹1,650 (tested 3 times)
Entry: ₹1,700
Stop Placement: ₹1,640-1,645

Buffer: ₹5-10 below support
Purpose: Avoid wick/spike stop runs
```

**For Short Positions:**
```
Place stop ABOVE recent resistance level

Example:
Stock: RELIANCE
Recent Resistance: ₹2,550
Entry: ₹2,500
Stop Placement: ₹2,555-2,560
```

**Why Add Buffer?**
- Market makers hunt for stops at obvious levels
- Wicks often pierce support/resistance briefly
- Give trade room to breathe
- Prevent premature exits

**Buffer Guidelines:**
- Low-priced stocks (<₹500): ₹2-5 buffer
- Mid-priced (₹500-2000): ₹5-15 buffer
- High-priced (>₹2000): ₹15-30 buffer
- Or use 0.5-1% of price as buffer

#### Moving Average Stops

**Use Key MAs as Dynamic Stops**

**Common Choices:**

**20 EMA (Short-term Trend):**
```
Best for: Swing trading, strong trends
Application: Trail stop along rising 20 EMA
Exit: When price closes below 20 EMA

Example:
Entry: ₹1000 (20 EMA at ₹980)
Week 1: 20 EMA rises to ₹990 → Move stop to ₹985
Week 2: 20 EMA at ₹1005 → Move stop to ₹1000
Breakeven achieved
```

**50 SMA (Intermediate Trend):**
```
Best for: Position trading
Application: Stay in trade while above 50 SMA
Exit: Close below 50 SMA confirms trend change

More reliable than 20 EMA but slower
```

**200 SMA/EMA (Long-term Trend):**
```
Best for: Long-term investing
Application: Major trend filter
Exit: Breach signals major trend reversal

Widely watched by institutions
```

#### Trendline Stops

**Method:**
```
1. Identify uptrend (higher highs, higher lows)
2. Draw trendline connecting at least 2 higher lows
3. Extend trendline forward
4. Place stop below trendline
5. Adjust as trendline evolves

For downtrends (reverse for shorts):
- Connect lower highs
- Place stop above trendline
```

**Advantages:**
- Adapts to changing market conditions
- Visual representation of trend
- Objective exit point

**Disadvantages:**
- Subjective drawing (different traders draw differently)
- Requires regular updates
- Can be broken temporarily (false breakouts)

#### Swing High/Low Stops

**For Long Positions:**
```
Place stop below most recent swing low

Definition of Swing Low:
- Lowest point of pullback
- At least 3-candle formation
- Clear reversal visible

Example:
Uptrend: ₹100 → ₹110 → ₹105 → ₹115 → ?
Pullback low: ₹105
Entry: ₹112
Stop: ₹104 (below swing low)

Logic: If ₹105 breaks, uptrend structure damaged
```

**For Short Positions:**
```
Place stop above most recent swing high

Example:
Downtrend: ₹100 → ₹90 → ₹95 → ₹85 → ?
Rally high: ₹95
Entry: ₹88
Stop: ₹96 (above swing high)

Logic: If ₹95 breaks, downtrend may be ending
```

### Type 3: Volatility-Based Stop-Loss (ATR Stops)

**Concept:** Use Average True Range (ATR) to set stops based on current market volatility.

#### Why ATR Stops?

**Problem with Fixed Percentage:**
- Different stocks have different volatility
- Same % stop too tight for volatile stocks
- Same % stop too loose for stable stocks

**ATR Solution:**
- Adapts to each stock's characteristics
- Wider stops for high-volatility stocks
- Tighter stops for low-volatility stocks
- Scientifically determined distance

#### Calculation

**Basic Formula:**
```
Stop Distance = ATR × Multiplier

For Long Positions:
Stop Price = Entry Price - (ATR × Multiplier)

For Short Positions:
Stop Price = Entry Price + (ATR × Multiplier)
```

**Determining Multiplier:**

**Intraday Trading:**
- Multiplier: **1.5× - 2× ATR**
- Tight stops needed
- Quick exits

**Swing Trading:**
- Multiplier: **2× - 3× ATR**
- Room for normal volatility
- Most common range

**Position Trading:**
- Multiplier: **3× - 4× ATR**
- Allow for trend development
- Fewer premature exits

#### Detailed Example

**Scenario:**
```
Stock: INFY
Entry Price: ₹1,450
ATR (14-day): ₹35
Trading Style: Swing trading
Multiplier: 2.5×
```

**Calculation:**
```
Stop Distance = ₹35 × 2.5 = ₹87.5

Stop Price = ₹1,450 - ₹87.5 = ₹1,362.50
Round to: ₹1,360 or ₹1,365

Risk per share = ₹1,450 - ₹1,362.50 = ₹87.50

If Account: ₹10,00,000
Risk: 2% = ₹20,000

Position Size = ₹20,000 / ₹87.50 = 228 shares
Capital Required = 228 × ₹1,450 = ₹3,30,600
```

#### Advantages
✅ Adapts to changing volatility  
✅ Scientifically determined  
✅ Equalizes risk across different stocks  
✅ Reduces premature stop-outs  

#### Disadvantages
❌ Requires ATR calculation  
❌ ATR can expand rapidly during crises  
❌ More complex than fixed percentage  
❌ May give wide stops in high vol environments  

---

### Type 4: Time-Based Stop-Loss

**Concept:** Exit if trade doesn't move in your favor within specified timeframe.

#### Implementation by Style

**Day Trading:**
```
Maximum Hold Period: Same day (no overnight risk)

Time-based Rules:
- Enter before 11:00 AM
- Exit by 3:15 PM if no profit
- No overnight positions unless exceptional

Alternative:
- If no movement within 30 minutes → Exit
- Capital tied up without reason
```

**Swing Trading:**
```
Maximum Hold Period: 5-10 days

Rules:
- Day 1-3: Normal stop applies
- Day 4-5: If no progress, tighten stop
- Day 6-7: Exit if still no movement
- Day 8-10: Mandatory exit regardless

Rationale:
- Good trades work quickly
- Dead money = opportunity cost
- Force discipline
```

**Position Trading:**
```
Review Period: Quarterly

Rules:
- Quarter 1: Assess thesis validity
- Quarter 2: If no progress, reduce size
- Quarter 3: Exit if thesis broken
- Maximum hold: 4 quarters

Exception: Long-term investments (no time stop)
```

#### Time Decay Considerations (Options)

**Weekly Options:**
```
Buy Monday/Tuesday:
- Exit by Wednesday/Thursday
- Theta decay accelerates in last 2 days
- Don't hold into expiry week unless deep ITM

Buy Thursday/Friday:
- Exit before Monday (weekend theta)
- Or hold only if immediate move favorable
```

**Monthly Options:**
```
First Week:
- Time working slowly against you
- Can hold 1-2 weeks if thesis intact

Second Week Onwards:
- Theta decay accelerating
- Need price movement in your favor
- Exit if stagnant for >3 days

Last Week:
- Extreme theta decay
- Exit or roll to next month
- Don't hold unless deep ITM
```

#### Advantages
✅ Frees up capital for better opportunities  
✅ Prevents "dead money" positions  
✅ Forces discipline  
✅ Reduces opportunity cost  

#### Disadvantages
❌ Good trades may need more time  
❌ Arbitrary time limits  
❌ Should combine with price stops  
❌ May exit before move materializes  

---

### Type 5: Trailing Stop-Loss

**Concept:** Automatically adjust stop-loss as price moves in your favor.

#### Manual Trailing

**Step-by-Step Process:**

**Example Long Trade:**
```
Initial Setup:
Entry: ₹100
Initial Stop: ₹95 (5% risk)
Target: ₹120 (1:4 risk-reward)

Price Action:
Day 1: Entry at ₹100, Stop ₹95
Day 5: Price reaches ₹110
  → Move stop to ₹105 (lock in ₹5 profit)
Day 10: Price reaches ₹120
  → Move stop to ₹115 (lock in ₹15 profit)
Day 15: Price reaches ₹130
  → Move stop to ₹125 (lock in ₹25 profit)
Day 20: Price drops to ₹125
  → Stopped out with ₹25 profit

Result: Captured majority of move
Protected profits progressively
```

**Trailing Rules:**
1. **Never move stop further away** (only closer)
2. Move after clear milestone reached (resistance break, target hit)
3. Lock in minimum 25-50% of profits at first milestone
4. Use logical levels (support, moving averages)

#### Indicator-Based Trailing

**Parabolic SAR Trailing:**
```
Setup:
- Enable Parabolic SAR indicator
- Default settings: Step 0.02, Max 0.20

Long Trade:
- Initial stop: Below first SAR dot
- Trail: Move stop to each new SAR dot
- Exit: When price crosses below SAR dot

Characteristics:
- Accelerates as trend progresses
- Tightens in strong trends
- Gives back some profits but captures most
```

**Moving Average Trailing:**
```
Choose MA: 20 EMA (aggressive) or 50 SMA (conservative)

Long Trade:
- Initial: Stop below MA at entry
- Trail: Move stop below rising MA
- Exit: When price closes below MA

Example:
Entry: ₹1000 (20 EMA at ₹985)
Week 1: 20 EMA → ₹995, Move stop to ₹990
Week 2: 20 EMA → ₹1010, Move stop to ₹1005
Week 3: Price closes at ₹1008 (below 20 EMA at ₹1012)
  → Exit next day

Captured: ₹1000 → ₹1008 = ₹8 profit
Would have held through entire uptrend
```

**Chandelier Exit (ATR-Based Trailing):**
```
Formula:
Trailing Stop = Highest High (22 periods) - (ATR × 3)

For Long Positions:
- Tracks highest high
- Subtracts multiple of ATR
- Only moves up (never down)

Characteristics:
- Wide enough to avoid noise
- Tight enough to protect profits
- Popularized by Chuck LeBeau
```

#### Percentage Trailing

**Fixed Percentage Trail:**
```
Trail by: Fixed % from highest close

Example (5% trail):
Day 1: Highest close ₹100 → Stop at ₹95
Day 5: Highest close ₹110 → Stop at ₹104.50
Day 10: Highest close ₹120 → Stop at ₹114
Day 15: Price drops to ₹114 → Stopped out

Broker Implementation:
Most brokers offer automatic trailing stops
Set percentage and activate
Automatically adjusts daily
```

#### Advantages
✅ Captures trends effectively  
✅ Locks in profits systematically  
✅ Removes emotion from profit-taking  
✅ Lets winners run while protecting gains  

#### Disadvantages
❌ Can exit too early in strong trends  
❌ Requires monitoring (for manual trailing)  
❌ Whipsaws in volatile markets  
❌ May give back significant profits before exit  

---

## Stop-Loss Best Practices

### The Golden Rules

#### Rule 1: ALWAYS Use Stop-Loss
```
No exceptions. Ever.

Not for:
- "Sure shot" trades
- "Can't lose" setups
- Tips from "experts"
- Your own "strong conviction"
- Even for small positions

Every. Single. Trade. Must. Have. Stop.
```

#### Rule 2: Set Stop BEFORE Entry
```
Correct Sequence:
1. Analyze chart, identify setup
2. Determine stop-loss level
3. Calculate position size based on stop distance
4. Enter trade with stop already in system

Wrong Sequence:
1. Enter trade (FOMO)
2. "I'll figure out stop later"
3. Trade goes against you
4. Panic, exit at worse price
```

#### Rule 3: Never Widen Stop After Entry
```
Acceptable Actions:
✅ Keep stop same
✅ Move stop closer (trail)
✅ Exit early if thesis broken

Unacceptable Actions:
❌ Move stop further ("giving it room")
❌ Remove stop entirely ("it'll come back")
❌ Convert intraday to delivery to avoid stop
❌ Average down to justify wider stop
```

#### Rule 4: Risk-Reward Ratio Minimum 1:2
```
Before Entry Check:
Entry: ₹100
Stop: ₹95 (Risk: ₹5)
Target: ₹110 (Reward: ₹10)
RRR: 1:2 ✓ Acceptable

OR

Entry: ₹100
Stop: ₹95 (Risk: ₹5)
Target: ₹115 (Reward: ₹15)
RRR: 1:3 ✓ Ideal

If RRR < 1:2:
→ Skip the trade
→ Not worth the risk
→ Wait for better setup
```

#### Rule 5: Use Hard Stops, Not Mental Stops
```
Hard Stop (Actual Order in System):
✅ Automatically executes at stop price
✅ No discretion required
✅ Protects against gaps
✅ Enforces discipline

Mental Stop (You'll "manually exit"):
❌ Requires willpower to execute
❌ Hesitation leads to larger losses
❌ Emotional attachment clouds judgment
❌ Often not executed at all

Professional Standard: HARD STOPS ONLY
```

### Advanced Techniques

#### Stop-and-Reverse
```
Concept: Exit losing position and immediately enter opposite direction

Example:
Long @ ₹100, Stop @ ₹95
Price gaps down to ₹92
Action:
1. Stop hits at ₹92 (exit long)
2. Immediately go short @ ₹92
3. New stop for short: ₹97

When Appropriate:
- Strong trend reversal confirmed
- Original thesis completely invalidated
- Momentum strongly in opposite direction

Risk: Double loss if wrong twice
```

#### Partial Stops
```
Concept: Exit portion at first stop, let remainder run

Example:
Position: 100 shares @ ₹100
Initial Stop: ₹95

Partial Exit Plan:
- Sell 50 shares at ₹95 (first stop)
- Trail remaining 50 shares with wider stop
- Second stop: ₹90 (technical level)

Benefits:
- Reduces risk by 50%
- Psychological comfort (banked some cash)
- Participation if reversal occurs

Drawbacks:
- Complexity
- Still exposed to larger loss on remainder
```

#### Hedging Instead of Stopping
```
Advanced Technique (NOT for beginners)

Scenario:
Long 100 shares @ ₹100
Stop: ₹95
Price: ₹97 (approaching stop but not breached)

Hedge Instead of Stop-Out:
- Buy 1 ATM put option (₹100 strike)
- Cost: ₹3 premium
- Protects downside below ₹100
- Maintains upside participation

If Price Recovers:
- Put expires worthless (loss: ₹3)
- Stock position profitable
- Net result: Still profitable

If Price Crashes:
- Put value increases
- Offsets stock loss
- Protected below ₹100

Requirements:
- Options trading approval
- Understanding of options Greeks
- Active monitoring
- Higher transaction costs
```

---

## Common Stop-Loss Mistakes

### ❌ Mistake 1: Placing Stops at Obvious Levels

**Wrong:**
```
Support at exactly ₹1000
Everyone places stop at ₹1000 or ₹999
Market makers know this
Price wicks to ₹998, triggers all stops, then rallies

Result: Stopped out at worst price
```

**Right:**
```
Support at ₹1000
Place stop at ₹995 or ₹993
Give 0.5-1% buffer below obvious level
Avoid round numbers

Result: Survived stop hunt, trade works
```

### ❌ Mistake 2: Stops Too Tight

**Wrong:**
```
Stock ATR: ₹50 (high volatility)
Entry: ₹1000
Stop: ₹990 (1%, or 0.2× ATR)

Result:
Normal volatility wicks you out
Then stock rallies to target
Frustration, revenge trading
```

**Right:**
```
Stock ATR: ₹50
Entry: ₹1000
Stop: ₹1000 - (₹50 × 2.5) = ₹987.50
(2.5× ATR = appropriate for swing trading)

Result:
Trade has room to breathe
Captures full move
```

### ❌ Mistake 3: Stops Too Wide

**Wrong:**
```
Entry: ₹1000
Stop: ₹850 (15% for swing trade)

Problems:
- Position size must be tiny to maintain 2% risk
- Poor risk-reward ratio
- Inefficient capital use
- Psychology difficult (large rupee loss)
```

**Right:**
```
Find tighter technical stop:
Entry: ₹1000
Stop: ₹950 (5%, at support)

Better RRR, larger position size, easier psychology
```

### ❌ Mistake 4: Not Accounting for Gaps

**Wrong:**
```
Hold overnight/weekend without considering gap risk
Earnings announcement, global event, etc.

Example:
Close: ₹1000, Stop: ₹950
Negative news overnight
Next open: ₹900
Stop executes at ₹900 (not ₹950)
Loss: ₹100 per share instead of ₹50

Actual loss: 2× planned risk
```

**Right:**
```
Before holding overnight:
✓ Check for earnings announcements
✓ Check for major events
✓ Reduce position size if uncertain
✓ Consider hedging with options
✓ Or exit before close (intraday)
```

### ❌ Mistake 5: Moving Stop Further ("Giving It Room")

**The Deadly Pattern:**
```
Original Plan:
Entry: ₹100, Stop: ₹95 (Risk: ₹5)

Trade Goes Against You:
Price: ₹96 (approaching stop)
Thought: "Just needs a little room, I'll move stop to ₹93"

Price Continues Down:
Price: ₹94 (now down ₹6)
Thought: "Now I'm almost at breakeven, can't exit here. Move to ₹90"

Price Crashes:
Price: ₹85
Panic exit
Total Loss: ₹15 per share (3× original plan)

Account Impact:
Instead of 2% loss → 6% loss
Requires 6.2% gain to recover (not 2%)
```

**Never, EVER do this.**

---

## Psychological Aspects

### Why Traders Avoid Stops

#### Ego Protection
```
"I can't be wrong"
"The market will prove me right"
"Stops are for losers"

Reality Check:
- Every trader has losing trades (even best in world)
- Stops protect you from being WRONG and BROKE
- Taking small loss = professional behavior
```

#### Hope as Strategy
```
"It'll come back"
"Just need to hold a bit longer"
"I've seen it recover before"

Reality Check:
- Hope has no place in trading
- Some stocks DON'T come back (see: Yes Bank, Suzlon)
- Unlimited hope = unlimited losses
```

#### Fear of Being Wrong
```
"If I don't stop, I haven't really lost"
"Once it comes back, I'll be proven right"

Reality Check:
- Unrealized losses are STILL losses
- Paper losses become real when you exit
- Better to admit wrong early than late
```

#### Past Trauma
```
"Last time I was stopped out, it reversed immediately"
"Stops don't work"

Reality Check:
- One bad experience ≠ pattern
- That trade would have been catastrophic without stop
- Focus on process, not individual outcomes
```

### Professional Mindset

#### Reframing Stop-Losses

✅ **Stops Are Insurance:**
```
You pay premium (occasional stop-out)
For protection against catastrophe
Like car insurance (hope never to use, glad you have it)
```

✅ **Stops Define Risk:**
```
Know exact maximum loss before entry
Enables proper position sizing
Sleep well at night
```

✅ **Stops Enable Objectivity:**
```
Removes emotion from exits
No debate, no hesitation
System executes automatically
```

✅ **Stops Are Freedom:**
```
Freedom from fear
Freedom from hope
Freedom to trade professionally
```

### Building Stop-Loss Discipline

#### Step 1: Write It Down
```
Before every trade, document:
- Entry price
- Stop-loss price
- Target price
- Risk-reward ratio
- Reason for stop placement

Keep trading journal
Review monthly
```

#### Step 2: Automate
```
Enter stop-loss IMMEDIATELY with trade
Use broker's GTT/AMO facility
Don't rely on manual execution
Remove human element
```

#### Step 3: Start Small
```
Practice with small positions initially
Build confidence in process
Gradually increase size as discipline strengthens
```

#### Step 4: Review Religiously
```
Weekly review of all stopped-out trades:
- Was stop placement logical?
- Was size appropriate?
- Any pattern of premature stop-outs?
- Adjust technique (not discipline)

Never adjust commitment to using stops
```

---

## Sources

- **Source ID:** `cftc` | Trust Level: high
  - URL: https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CFTCFaqFutures.htm
  - Reference: CFTC Investor Protection Resources

- **Source ID:** `cme_group` | Trust Level: high
  - URL: https://www.cmegroup.com/education/whitepapers/risk-management-strategies.html
  - Reference: CME Risk Management Whitepapers

- **Source ID:** `finance_textbooks` | Trust Level: high
  - Reference: Alexander Elder - Trading for a Living (Risk Management Chapter)
  - Reference: Van Tharp - Trade Your Way to Financial Freedom

---

*This document is part of the Finance Knowledge Base system. For LLM ingestion, use topic ID: risk_stop_loss*
