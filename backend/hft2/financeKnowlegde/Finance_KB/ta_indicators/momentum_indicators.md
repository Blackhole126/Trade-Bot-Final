# Momentum Oscillators

**Topic ID:** `ta_momentum_indicators`  
**Version:** 1.0.0  
**Last Updated:** 2026-03-20

---

## Relative Strength Index (RSI)

### Definition
RSI is a momentum oscillator measuring speed and magnitude of recent price changes. Evaluates whether asset is overbought or oversold. Developed by J. Welles Wilder (1978).

### Calculation
```
RSI = 100 - [100 / (1 + RS)]

Where:
RS = Average Gain / Average Loss (over specified period)

Gain = Current Close - Previous Close (if positive)
Loss = Previous Close - Current Close (if positive)

Average calculations use smoothed moving averages
```

**Scale:** 0 to 100

### Key Levels

#### Traditional Levels
- **Overbought:** RSI > 70
- **Oversold:** RSI < 30
- **Neutral Zone:** RSI 30-70

#### Strong Trend Adjustments
In strong trending markets:
- **Bullish trends:** Overbought > 80, Oversold > 40
- **Bearish trends:** Overbought < 60, Oversold < 20

### Trading Signals

#### 1. Overbought/Oversold Reversals

**Sell Signal (Overbought):**
```
Conditions:
1. RSI rises above 70 (overbought territory)
2. RSI crosses back below 70
3. Preferably with bearish divergence or price pattern

Entry: On cross below 70
Stop: Above recent swing high
Target: Previous support level
```

**Buy Signal (Oversold):**
```
Conditions:
1. RSI falls below 30 (oversold territory)
2. RSI crosses back above 30
3. Preferably with bullish divergence or price pattern

Entry: On cross above 30
Stop: Below recent swing low
Target: Previous resistance level
```

**Effectiveness:**
- ✅ Works best in ranging/sideways markets
- ❌ Gives premature signals in strong trends
- ⚠️ Can stay overbought/oversold during powerful moves

#### 2. Divergences (Most Reliable Signal)

**Bullish Divergence:**
```
Price Action: Makes lower low
RSI: Makes higher low

Interpretation:
- Selling pressure weakening
- Downward momentum slowing
- Potential reversal upward
- Leading signal (predictive)

Trading Setup:
- Wait for price confirmation (bullish candle)
- Enter long on break of minor resistance
- Stop below recent low
- Target previous resistance
```

**Bearish Divergence:**
```
Price Action: Makes higher high
RSI: Makes lower high

Interpretation:
- Buying pressure weakening
- Upward momentum slowing
- Potential reversal downward
- Leading signal (predictive)

Trading Setup:
- Wait for price confirmation (bearish candle)
- Enter short on break of minor support
- Stop above recent high
- Target previous support
```

**Divergence Reliability:**
- ✅ Higher on longer timeframes (daily/weekly)
- ✅ Stronger at key support/resistance levels
- ✅ More reliable when RSI in extreme zones
- ⚠️ Can persist before actual reversal (use stops)

#### 3. Centerline Crossover

**Bullish Centerline Cross:**
```
RSI crosses above 50

Indicates:
- Shift from bearish to bullish momentum
- Average gains exceeding average losses
- Confirmation of upward move

Use as:
- Secondary confirmation signal
- Filter for long trades only
- Not as strong as divergences
```

**Bearish Centerline Cross:**
```
RSI crosses below 50

Indicates:
- Shift from bullish to bearish momentum
- Average losses exceeding average gains
- Confirmation of downward move

Use as:
- Secondary confirmation signal
- Filter for short trades only
```

#### 4. Failure Swings (Wilder's Pattern)

**Bullish Failure Swing:**
```
Four-Step Pattern:
1. RSI drops below 30 (oversold)
2. RSI bounces above 30
3. RSI pulls back but stays above 30 (higher low)
4. RSI breaks above previous peak

Signal: Strong buy signal at step 4

Characteristics:
- Confirms momentum shift
- Multiple confirmations built-in
- Higher reliability than simple oversold
```

**Bearish Failure Swing:**
```
Four-Step Pattern:
1. RSI rises above 70 (overbought)
2. RSI declines below 70
3. RSI rallies but stays below 70 (lower high)
4. RSI breaks below previous trough

Signal: Strong sell signal at step 4

Characteristics:
- Confirms momentum shift
- Multiple confirmations built-in
- Higher reliability than simple overbought
```

### Advanced Concepts

#### RSI Range Shifting

**In Strong Uptrends:**
```
RSI tends to fluctuate between 40-90

Characteristics:
- 40-50 zone acts as support
- Rarely drops below 40
- Overbought (>70) readings common
- Oversold (<30) readings rare

Trading Implication:
- Buy when RSI reaches 40-50 zone
- Don't short just because RSI > 70
- Look for bullish setups on pullbacks
```

**In Strong Downtrends:**
```
RSI tends to fluctuate between 10-60

Characteristics:
- 50-60 zone acts as resistance
- Rarely rises above 60
- Oversold (<30) readings common
- Overbought (>70) readings rare

Trading Implication:
- Sell when RSI reaches 50-60 zone
- Don't buy just because RSI < 30
- Look for bearish setups on rallies
```

#### Hidden Divergences (Trend Continuation)

**Bullish Hidden Divergence:**
```
Price: Makes higher low (uptrend intact)
RSI: Makes lower low

Interpretation:
- Temporary weakness in uptrend
- Momentum reset without trend break
- Suggests trend continuation
- Entry opportunity in direction of trend

Trading Setup:
- Enter long on RSI recovery above 30
- Stop below price's higher low
- Target previous high
```

**Bearish Hidden Divergence:**
```
Price: Makes lower high (downtrend intact)
RSI: Makes higher high

Interpretation:
- Temporary strength in downtrend
- Momentum reset without trend break
- Suggests trend continuation
- Entry opportunity in direction of trend

Trading Setup:
- Enter short on RSI decline below 70
- Stop above price's lower high
- Target previous low
```

### Settings

#### Default Period: 14
- Balanced sensitivity
- Works across all timeframes
- Most widely followed setting

#### Alternative Settings

**Shorter Period (More Sensitive):**
- **7-10 periods:** For intraday trading
- More volatile RSI
- More overbought/oversold readings
- More signals but lower reliability

**Longer Period (Smoother):**
- **20-25 periods:** For position trading
- Smoother RSI line
- Fewer overbought/oversold readings
- Fewer signals but higher reliability

### Limitations

1. **Can Remain Overbought/Oversold During Strong Trends:**
   - RSI can stay >70 throughout powerful uptrend
   - Selling at 70 can miss major moves
   - Need trend context filter

2. **Premature Divergence Signals:**
   - Divergence can form before final price extreme
   - May need multiple divergences before reversal
   - Always use stop-losses

3. **Not Effective Alone in Strongly Trending Markets:**
   - Best combined with trend indicators
   - Use moving averages to determine trend
   - Align RSI signals with trend direction

### Best Practices

✅ **DO:**
- Use in conjunction with trend indicators (MA, MACD)
- Look for divergences at key support/resistance
- Adjust overbought/oversold levels based on market regime
- Confirm with price action and volume
- Use hidden divergences for trend continuation entries

❌ **DON'T:**
- Sell automatically at 70 or buy at 30 in strong trends
- Trade every divergence without confirmation
- Use RSI alone without trend context
- Ignore price action for RSI signals

---

## Stochastic Oscillator

### Definition
Stochastic oscillator compares closing price to price range over specific period. Shows where price is relative to recent high-low range. Developed by George Lane in 1950s.

### Calculation

#### %K Line (Fast Stochastic)
```
%K = [(Current Close - Lowest Low) / (Highest High - Lowest Low)] × 100

Where:
- Lowest Low = Lowest price over lookback period (typically 14)
- Highest High = Highest price over lookback period
- Current Close = Most recent closing price
```

#### %D Line (Slow Stochastic)
```
%D = Simple Moving Average of %K (typically 3 periods)

Acts as signal line
Smoother than %K
Generates fewer false signals
```

**Scale:** 0 to 100

### Key Levels
- **Overbought:** Above 80 (some use 70)
- **Oversold:** Below 20 (some use 30)
- **Centerline:** 50 (momentum inflection)

### Types of Stochastics

#### 1. Full Stochastic
**Most Customizable:**
- Separate settings for %K period
- %K smoothing period
- %D period

**Example Configuration:**
```
%K Period: 14
%K Smoothing: 3
%D Period: 3
```

#### 2. Fast Stochastic
**Original Formulation:**
- %K = Raw calculation (no smoothing)
- %D = 3-period SMA of %K
- Very sensitive
- Prone to whipsaws

#### 3. Slow Stochastic
**Most Commonly Used:**
- %K = 1-period SMA of fast %K (smoothed)
- %D = 3-period SMA of slow %K
- Reduces false signals
- Better for most traders

### Trading Signals

#### 1. Overbought/Oversold Readings

**Sell Signal (Overbought):**
```
Setup:
1. Stochastic rises above 80
2. %K turns down
3. %K crosses below %D (confirmation)

Entry: On %K cross below %D (while above 80)
Stop: Above recent high
Target: Move toward 50 or lower
```

**Buy Signal (Oversold):**
```
Setup:
1. Stochastic falls below 20
2. %K turns up
3. %K crosses above %D (confirmation)

Entry: On %K cross above %D (while below 20)
Stop: Below recent low
Target: Move toward 50 or higher
```

**Important Notes:**
- Works best in ranging markets
- Can give premature signals in strong trends
- Wait for crossover confirmation
- Don't trade against strong trend

#### 2. Signal Line Crossovers

**Bullish Crossover:**
```
%K crosses above %D

Best When:
- Occurring in oversold territory (<20)
- Aligned with uptrend on higher timeframe
- At key support level
- With bullish divergence

Reliability: High in ranges, low in trends
```

**Bearish Crossover:**
```
%K crosses below %D

Best When:
- Occurring in overbought territory (>80)
- Aligned with downtrend on higher timeframe
- At key resistance level
- With bearish divergence

Reliability: High in ranges, low in trends
```

#### 3. Divergences

**Bullish Divergence:**
```
Price: Makes lower low
Stochastic: Makes higher low

Interpretation:
- Downward momentum exhausting
- Selling pressure weakening
- Potential reversal upward

Trading:
- Wait for %K to cross above %D
- Enter on confirmation
- Stop below low
```

**Bearish Divergence:**
```
Price: Makes higher high
Stochastic: Makes lower high

Interpretation:
- Upward momentum exhausting
- Buying pressure weakening
- Potential reversal downward

Trading:
- Wait for %K to cross below %D
- Enter on confirmation
- Stop above high
```

#### 4. Centerline Crossover

**Bullish Centerline Cross:**
```
%K crosses above 50

Indicates:
- Momentum shifting bullish
- Closing price in upper half of range
- Confirmation of upward move

Use as secondary signal
```

**Bearish Centerline Cross:**
```
%K crosses below 50

Indicates:
- Momentum shifting bearish
- Closing price in lower half of range
- Confirmation of downward move

Use as secondary signal
```

### Settings

#### Standard Setting: (14, 3, 3)
**For Slow Stochastic:**
- %K Period: 14
- %K Smoothing: 3
- %D Period: 3

**Best For:**
- Daily charts
- Swing trading
- General purpose

#### Alternative Settings

**For Day Trading (More Sensitive):**
```
(5, 3, 3)
- Faster signals
- More trades
- More whipsaws
- Use on 5-min, 15-min charts
```

**For Swing Trading (Balanced):**
```
(14, 3, 3) or (14, 5, 5)
- Good balance of sensitivity/reliability
- Works on daily charts
- Most popular
```

**For Position Trading (Smoother):**
```
(21, 5, 5) or (30, 5, 5)
- Fewer signals
- Higher reliability
- Less noise
- Use on daily/weekly charts
```

### Comparison with RSI

| Aspect | Stochastic | RSI |
|--------|------------|-----|
| Sensitivity | Higher | Lower |
| Signal Frequency | More | Fewer |
| False Signals | More | Fewer |
| Best Market Type | Ranging | Both |
| Calculation Basis | Close vs Range | Gains vs Losses |

**Using Together:**
- Stochastic gives earlier entries
- RSI provides confirmation
- Both showing overbought = stronger signal
- Divergences on both = higher reliability

### Best Markets

✅ **Works Well In:**
- Ranging/sideways markets
- Mean reversion strategies
- Counter-trend trading
- Identifying short-term extremes

❌ **Less Effective In:**
- Strong trending markets
- Breakout situations
- Momentum continuation plays
- Needs trend filter

### Strategic Uses

#### 1. Identify Potential Reversal Points
```
Strategy:
- Wait for stochastic to reach extreme (>80 or <20)
- Look for divergence
- Wait for crossover confirmation
- Enter with stop beyond extreme
```

#### 2. Time Entries in Direction of Trend
```
Trend-Pullback Strategy:
- Identify uptrend on daily chart
- Wait for pullback on hourly
- Hourly stochastic drops <20 then crosses up
- Enter long in direction of daily trend
- Stop below pullback low
```

#### 3. Set Profit Targets
```
Take Profit Logic:
- Long entry at oversold (<20)
- Take partial profits at 50
- Take remainder at overbought (>80)
- Reverse for shorts
```

#### 4. Combine with Trend Filters
```
200 MA Filter:
IF Price > 200 MA (uptrend):
    → Only take stochastic buy signals
    → Ignore sell signals
    → Buy dips to oversold

IF Price < 200 MA (downtrend):
    → Only take stochastic sell signals
    → Ignore buy signals
    → Sell rallies to overbought
```

### Limitations

1. **Many False Signals in Trending Markets:**
   - Can stay overbought/oversold during strong trends
   - Multiple crossovers without sustained moves
   - Requires trend filter

2. **Premature Reversal Signals:**
   - Early identification of tops/bottoms
   - May need multiple attempts before reversal
   - Always use protective stops

3. **Requires Confirmation:**
   - Should not be used alone
   - Combine with trend analysis
   - Use with other indicators (volume, price action)

### Best Practices

✅ **DO:**
- Use in ranging markets primarily
- Combine with trend filters (moving averages)
- Wait for crossover confirmation
- Look for divergences at key levels
- Use with price action analysis

❌ **DON'T:**
- Trade against strong trends
- Buy/sell at extremes without confirmation
- Use as sole timing tool
- Ignore overbought/oversold context

---

## Commodity Channel Index (CCI)

### Definition
CCI measures current price level relative to average price over specified period. Originally developed for commodities, now used for stocks and forex. Created by Donald Lambert in 1980.

### Calculation
```
CCI = (Typical Price - SMA of TP) / (0.015 × Mean Deviation)

Where:
Typical Price (TP) = (High + Low + Close) / 3
SMA = Simple Moving Average of TP (typically 20 periods)
Mean Deviation = Average absolute deviation from SMA
Constant 0.015 ensures ~70-80% readings between ±100
```

**Scale:** Unbounded (typically ranges -300 to +300)

### Key Levels
- **+100:** Overbought threshold
- **-100:** Oversold threshold
- **±200:** Extreme levels (strong trend)
- **Zero Line:** Centerline (neutral)

### Trading Signals

#### 1. Overbought/Oversold

**Buy Signal:**
```
Setup:
1. CCI drops below -100 (oversold)
2. CCI turns up
3. CCI crosses back above -100

Entry: On cross above -100
Stop: Below recent low
Target: Move toward zero or +100
```

**Sell Signal:**
```
Setup:
1. CCI rises above +100 (overbought)
2. CCI turns down
3. CCI crosses back below +100

Entry: On cross below +100
Stop: Above recent high
Target: Move toward zero or -100
```

#### 2. Zero Line Crossovers

**Bullish Zero Cross:**
```
CCI crosses above zero

Indicates:
- Momentum shifting bullish
- Price above average
- Confirmation of upward move
```

**Bearish Zero Cross:**
```
CCI crosses below zero

Indicates:
- Momentum shifting bearish
- Price below average
- Confirmation of downward move
```

#### 3. Divergences

**Bullish Divergence:**
```
Price: Makes lower low
CCI: Makes higher low

Interpretation:
- Downward momentum weakening
- Potential reversal upward
- Leading signal
```

**Bearish Divergence:**
```
Price: Makes higher high
CCI: Makes lower high

Interpretation:
- Upward momentum weakening
- Potential reversal downward
- Leading signal
```

#### 4. Pattern Recognition
```
CCI can form chart patterns:
- Head and shoulders
- Double tops/bottoms
- Triangles
- Trendlines

Breakouts on CCI often precede price breakouts
Trendlines on CCI can be drawn and broken before price
```

### Settings

#### Default: 20 periods
- Balanced sensitivity
- Works across timeframes
- Most widely used

#### Alternative Settings

**Shorter (More Volatile):**
- **10-14 periods:** More signals, more whipsaws
- For intraday trading

**Longer (Smoother):**
- **30-40 periods:** Fewer but stronger signals
- For position trading

### Unique Characteristics

✅ **Versatile:**
- Works across all timeframes
- Applicable to stocks, futures, forex, crypto

✅ **Leading and Lagging:**
- Can lead price (divergences)
- Also follows price (trend confirmation)

✅ **Unbounded Scale:**
- No absolute maximum/minimum
- Adapts to volatility

### Limitations

1. **Unbounded Scale:**
   - No absolute extremes
   - ±100 are guidelines, not hard limits

2. **Late Signals in Fast Markets:**
   - Can lag during sharp moves
   - May miss initial reversal

3. **Whipsaws in Choppy Conditions:**
   - Multiple zero line crosses
   - Requires volatility filter

### Best Practices

✅ **DO:**
- Combine with trend-following indicators
- Use divergences at key support/resistance
- Apply with price action analysis
- Adjust thresholds for different assets

❌ **DON'T:**
- Use as sole indicator
- Trade every zero line cross
- Ignore market context
- Expect precise turning points

---

## Sources

- **Source ID:** `investopedia` | Trust Level: medium
  - URL: https://www.investopedia.com/technical-analysis-4689657

- **Source ID:** `tradingview_docs` | Trust Level: medium
  - URL: https://www.tradingview.com/support/solutions/43000502338

---

*This document is part of the Finance Knowledge Base system. For LLM ingestion, use topic ID: ta_momentum_indicators*
