# Trend-Following Technical Indicators

**Topic ID:** `ta_trend_indicators`  
**Version:** 1.0.0  
**Last Updated:** 2026-03-20

---

## Moving Averages (MA)

### Definition
Moving averages smooth price data to identify trend direction and potential support/resistance levels. They are lagging indicators that follow the price action.

### Types of Moving Averages

#### 1. Simple Moving Average (SMA)

**Calculation:**
```
SMA = (Sum of closing prices over n periods) / n
```

**Characteristics:**
- Equal weight to all data points
- Smoothest of all moving averages
- Most lagging (slowest to react)
- Best for identifying long-term trends

**Commonly Used Periods:**
- **20 SMA:** Short-term trend (monthly)
- **50 SMA:** Intermediate trend (quarterly)
- **100 SMA:** Long-term trend (semi-annual)
- **200 SMA:** Very long-term trend (annual)

**Interpretation:**
- **Price above SMA:** Bullish signal
- **Price below SMA:** Bearish signal
- **SMA slope upward:** Uptrend confirmation
- **SMA slope downward:** Downtrend confirmation

**Trading Signals:**

**Golden Cross (Bullish):**
- Short-term MA crosses above long-term MA
- Example: 50 SMA crosses above 200 SMA
- Indicates potential start of uptrend
- Stronger on higher timeframes

**Death Cross (Bearish):**
- Short-term MA crosses below long-term MA
- Example: 50 SMA crosses below 200 SMA
- Indicates potential start of downtrend
- Stronger on higher timeframes

**Dynamic Support/Resistance:**
- In uptrends, price often bounces off rising MA
- In downtrends, price often rejects from falling MA
- 20 EMA/50 SMA commonly act as support in strong trends

---

#### 2. Exponential Moving Average (EMA)

**Calculation:**
```
EMA = (Close - Previous EMA) × Multiplier + Previous EMA

Multiplier = 2 / (n + 1)

Example for 20-period EMA:
Multiplier = 2 / (20 + 1) = 0.0952 = 9.52%
```

**Characteristics:**
- Gives more weight to recent prices
- More responsive to new information than SMA
- Less lag than SMA
- Preferred by short-term traders

**Common EMA Periods:**
- **9 EMA:** Very short-term momentum (intraday/swing)
- **20 EMA:** Short-term trend (swing trading)
- **50 EMA:** Intermediate trend
- **200 EMA:** Long-term trend (same as 200 SMA)

**Trading Applications:**

**Trend Identification:**
- Price above all EMAs (9, 20, 50, 200): Strong uptrend
- Price below all EMAs: Strong downtrend
- Mixed positioning: Ranging/consolidation

**Entry Signals:**
- Pullback to 20 EMA in uptrend → Buy opportunity
- Rally to 20 EMA in downtrend → Sell opportunity
- EMA crossover (9 crossing 20) → Momentum shift

**Comparison with SMA:**
| Aspect | SMA | EMA |
|--------|-----|-----|
| Weight | Equal | Recent biased |
| Lag | Higher | Lower |
| Sensitivity | Lower | Higher |
| Best For | Long-term | Short-term |

---

#### 3. Weighted Moving Average (WMA)

**Calculation:**
```
WMA = (P1×n + P2×(n-1) + ... + Pn×1) / (n + (n-1) + ... + 1)

Where P1 is most recent price, Pn is oldest
```

**Characteristics:**
- Linear weighting scheme
- Most recent data gets highest weight
- More sensitive than SMA, less than EMA
- Less commonly used than SMA/EMA

---

### Strategic Uses of Moving Averages

#### 1. Trend Identification and Confirmation
- Multiple MAs aligned bullishly/bearishly confirm trend
- MA ribbon (multiple MAs) shows trend strength
- Divergence between price and MA warns of weakness

#### 2. Dynamic Support and Resistance Levels
- Rising MAs act as support in uptrends
- Falling MAs act as resistance in downtrends
- More reliable on higher timeframes (daily/weekly)

#### 3. Entry/Exit Signals via Crossovers
- Fast MA crossing slow MA = entry signal
- Price crossing key MA = exit signal
- Multiple MA crossovers filter false signals

#### 4. Risk Management (Stop-Loss Placement)
- Place stops below key MA for long positions
- Trail stops using rising MA
- Breach of major MA signals trend change

---

## Moving Average Convergence Divergence (MACD)

### Definition
MACD is a trend-following momentum indicator showing relationship between two EMAs of price. Developed by Gerald Appel in 1970s.

### Components

#### 1. MACD Line
```
MACD Line = 12-period EMA - 26-period EMA

Shows short-term vs medium-term momentum
Positive when 12 EMA > 26 EMA (bullish)
Negative when 12 EMA < 26 EMA (bearish)
```

#### 2. Signal Line
```
Signal Line = 9-period EMA of MACD Line

Acts as trigger for buy/sell signals
Smoother than MACD line
Lagging component
```

#### 3. Histogram
```
Histogram = MACD Line - Signal Line

Visual representation of convergence/divergence
Positive when MACD above Signal (bullish momentum increasing)
Negative when MACD below Signal (bearish momentum increasing)
Zero when lines cross
```

### Trading Signals

#### 1. Signal Line Crossovers

**Bullish Crossover:**
- MACD crosses above Signal line
- Best when occurring below zero line
- Confirms upward momentum shift
- Works best in trending markets

**Bearish Crossover:**
- MACD crosses below Signal line
- Best when occurring above zero line
- Confirms downward momentum shift
- Prone to whipsaws in sideways markets

**Reliability Factors:**
- Stronger near zero line
- Weaker at extreme levels
- Confirm with price action
- Use with trend filter

#### 2. Zero Line Crossovers

**Bullish Zero Cross:**
- MACD crosses above zero
- Indicates 12 EMA crossed above 26 EMA
- Confirms change to bullish momentum
- Slower but more reliable than signal line crosses

**Bearish Zero Cross:**
- MACD crosses below zero
- Indicates 12 EMA crossed below 26 EMA
- Confirms change to bearish momentum
- Often coincides with price breakdown

#### 3. Divergences

**Bullish Divergence:**
```
Price Action: Makes lower low
MACD: Makes higher low

Interpretation:
- Downward momentum weakening
- Selling pressure exhausting
- Potential reversal upward
- Leading signal (predictive)
```

**Bearish Divergence:**
```
Price Action: Makes higher high
MACD: Makes lower high

Interpretation:
- Upward momentum weakening
- Buying pressure exhausting
- Potential reversal downward
- Leading signal (predictive)
```

**Divergence Trading:**
- Wait for confirmation (price reversal)
- Use with other indicators
- Strongest at key support/resistance
- Can persist longer than expected (use stops)

### Settings and Customization

#### Standard Settings
- **Fast EMA:** 12 periods
- **Slow EMA:** 26 periods
- **Signal Line:** 9 periods
- **Best For:** Daily charts, swing trading

#### Alternative Settings

**For Shorter Timeframes (Intraday):**
- (6, 13, 5) - More sensitive, faster signals
- Increases trade frequency but also false signals

**For Longer Timeframes (Position Trading):**
- (24, 52, 18) - Smoother, fewer signals
- Reduces whipsaws but later entries

### Limitations

1. **Lagging Indicator:**
   - Based on past prices (EMAs)
   - Signals occur after move has started
   - Not predictive (except divergences)

2. **False Signals in Ranging Markets:**
   - Multiple crossovers without sustained moves
   - Whipsaws around zero line
   - Requires trend filter

3. **Best Combined With:**
   - Trend analysis (moving averages, trendlines)
   - Other indicators (RSI for overbought/oversold)
   - Price action (support/resistance, patterns)

---

## Average Directional Index (ADX)

### Definition
ADX measures trend strength regardless of direction. Developed by J. Welles Wilder. Part of the Directional Movement System.

### Components

#### 1. ADX Line
```
Derived from +DI and -DI
Ranges from 0 to 100
Does NOT indicate trend direction
Only measures trend STRENGTH
Smoothed average of DI difference
```

#### 2. +DI (Positive Directional Indicator)
```
Measures upward movement
Compares current high to previous high
Calculates True Directional Movement
Plotted alongside ADX
```

#### 3. -DI (Negative Directional Indicator)
```
Measures downward movement
Compares current low to previous low
Mirrors +DI calculation
Crosses +DI for signals
```

### Interpretation

#### ADX Readings - Trend Strength

| ADX Value | Trend Strength | Market Condition | Strategy |
|-----------|----------------|------------------|----------|
| 0-25 | Weak/None | Ranging | Mean reversion |
| 25-50 | Moderate | Trending | Trend following |
| 50-75 | Strong | Strong trend | Stay in trend |
| 75-100 | Very Strong | Extreme trend | Rare, prepare for reversal |

#### Key Thresholds

**ADX < 25:**
- Market is ranging/sideways
- Avoid trend-following strategies
- Use oscillators (RSI, Stochastic)
- Buy support, sell resistance

**ADX > 25:**
- Market is trending
- Trend-following strategies work best
- Pullbacks offer entry opportunities
- Avoid counter-trend trades

**ADX Rising:**
- Trend gaining strength
- Current strategy working
- Add to positions on pullbacks
- Don't fight the trend

**ADX Falling:**
- Trend losing strength
- Market entering consolidation
- Reduce position size
- Prepare for range-bound trading

### Trading Signals

#### 1. Trend Strength Filter

**Application:**
```
IF ADX > 25:
    → Market is trending
    → Use trend-following strategies
    → Enter on pullbacks to moving averages
    → Trail stops wider

IF ADX < 25:
    → Market is ranging
    → Use mean reversion strategies
    → Buy support, sell resistance
    → Take profits quickly
```

#### 2. DI Crossovers

**Bullish Signal:**
- +DI crosses above -DI
- ADX should be rising (confirming strength)
- Best when ADX < 25 and starting to rise
- Entry: On crossover or pullback

**Bearish Signal:**
- -DI crosses above +DI
- ADX should be rising (confirming strength)
- Best when ADX < 25 and starting to rise
- Entry: On crossover or pullback

**Filter for Reliability:**
- Only take signals in direction of higher timeframe trend
- Wait for ADX confirmation (rising)
- Combine with price action

#### 3. ADX Peaks and Reversals

**ADX Peak Pattern:**
```
1. ADX rises to extreme (>40)
2. ADX peaks and turns down
3. Indicates trend maturing
4. Doesn't mean immediate reversal
5. Could enter consolidation
```

**Trading Implications:**
- Reduce position size
- Tighten trailing stops
- Don't add to positions
- Watch for actual trend reversal confirmation

### Strategic Applications

#### 1. Position Sizing Based on ADX
```
Strong Trend (ADX > 30):
    → Larger position size
    → Wider stops
    → Pyramiding allowed

Weak Trend/Ranging (ADX < 25):
    → Smaller position size
    → Tighter stops
    → Quick profits
```

#### 2. Strategy Selection
```
High ADX Environment:
    → Moving average crossovers
    → Breakout systems
    → Trend continuation patterns

Low ADX Environment:
    → Range trading
    → Mean reversion
    → Oscillator-based systems
```

#### 3. Multi-Timeframe Analysis
```
Daily Chart: Determine primary trend direction
Hourly Chart: Time entries using ADX readings

Example:
- Daily ADX > 30 (strong uptrend)
- Hourly ADX drops < 25 (pullback)
- Wait for hourly ADX to rise back above 25
- Enter in direction of daily trend
```

### Settings

**Default Period:** 14
- Balanced sensitivity
- Works across timeframes
- Widely followed

**Alternative Periods:**
- **10 periods:** More sensitive, earlier signals
- **20 periods:** Smoother, fewer false signals
- **25 periods:** Even smoother for long-term trends

### Limitations

1. **Lagging Indicator:**
   - Based on past price data
   - Signals occur after trend established
   - Not predictive

2. **Doesn't Indicate Direction:**
   - Only measures strength
   - Must use with +DI/-DI or other directional tools
   - High ADX could mean strong uptrend OR downtrend

3. **Can Remain at Extremes:**
   - During very strong trends, ADX stays elevated
   - Don't assume peak means immediate reversal
   - Wait for price confirmation

### Combination Strategies

#### ADX + Moving Averages
```
Trend Filter:
- Price above 200 SMA (long-term uptrend)
- ADX > 25 (trend has strength)
- Use 20 EMA pullbacks for entries
- Exit when ADX falls below 25
```

#### ADX + MACD
```
Entry System:
- ADX > 25 (trending market)
- MACD crossover in trend direction
- Higher probability than either alone
- ADX filters out MACD whipsaws
```

#### ADX + RSI
```
Strategy Selection:
- ADX > 25: Ignore RSI overbought/oversold
  (trends can stay overbought/oversold)
- ADX < 25: Use RSI extremes for reversals
  (range-bound market)
```

---

## Sources

- **Source ID:** `investopedia` | Trust Level: medium
  - URL: https://www.investopedia.com/technical-analysis-4689657
  - Reference: Technical Analysis Course

- **Source ID:** `tradingview_docs` | Trust Level: medium
  - URL: https://www.tradingview.com/support/solutions/43000502338
  - Reference: TradingView Indicators Documentation

---

*This document is part of the Finance Knowledge Base system. For LLM ingestion, use topic ID: ta_trend_indicators*
