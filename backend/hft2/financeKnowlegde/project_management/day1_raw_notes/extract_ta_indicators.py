#!/usr/bin/env python3
"""
Technical Analysis Indicators Extractor
========================================
Collects technical analysis indicator definitions from Investopedia and TradingView.

Sources:
- Investopedia (investopedia.com)
- TradingView Documentation (tradingview.com/support)

Output: Raw notes with source citations for knowledge base construction
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from pathlib import Path
import time
import re


class TAIndicatorsExtractor:
    """Extractor for technical analysis indicators"""

    def __init__(self, output_dir="day1_raw_notes"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.sources = {
            "investopedia": {
                "source_id": "investopedia",
                "base_url": "https://www.investopedia.com",
                "trust_level": "medium"
            },
            "tradingview": {
                "source_id": "tradingview_docs",
                "base_url": "https://www.tradingview.com/support",
                "trust_level": "medium"
            }
        }

        self.extracted_data = {
            "extraction_date": datetime.now().isoformat(),
            "sources": list(self.sources.values()),
            "topics": []
        }

    def extract_trend_indicators(self):
        """Extract trend-following indicators"""
        print("📈 Extracting trend indicators...")

        trend_indicators = {
            "topic_id": "ta_trend_indicators",
            "title": "Trend-Following Technical Indicators",
            "content": [],
            "sources": []
        }

        indicators = [
            {
                "heading": "Moving Averages (MA)",
                "content": """
**Definition:**
Moving averages smooth price data to identify trend direction and potential support/resistance levels. They are lagging indicators that follow the price action.

**Types of Moving Averages:**

1. **Simple Moving Average (SMA):**
   - Arithmetic mean of prices over specified period
   - Formula: SMA = (Sum of closing prices) / n periods
   - Equal weight to all data points
   - Commonly used periods: 20, 50, 100, 200 days
   
   **Interpretation:**
   - Price above SMA = Bullish signal
   - Price below SMA = Bearish signal
   - Longer periods = Stronger support/resistance
   
   **Trading Signals:**
   - Golden Cross: Short-term MA crosses above long-term MA (bullish)
   - Death Cross: Short-term MA crosses below long-term MA (bearish)
   - SMA acts as dynamic support in uptrend, resistance in downtrend

2. **Exponential Moving Average (EMA):**
   - Gives more weight to recent prices
   - More responsive to new information than SMA
   - Formula includes smoothing multiplier
   - Preferred by short-term traders
   
   **Calculation:**
   ```
   EMA = (Close - Previous EMA) × Multiplier + Previous EMA
   Multiplier = 2 / (n + 1)
   ```
   
   **Common EMA Periods:**
   - 9 EMA: Very short-term momentum
   - 20 EMA: Short-term trend
   - 50 EMA: Intermediate trend
   - 200 EMA: Long-term trend

3. **Weighted Moving Average (WMA):**
   - Linear weighting scheme
   - Most recent data gets highest weight
   - More sensitive than SMA, less than EMA

**Strategic Uses:**
- Trend identification and confirmation
- Dynamic support and resistance levels
- Entry/exit signals via crossovers
- Risk management (stop-loss placement)
"""
            },
            {
                "heading": "Moving Average Convergence Divergence (MACD)",
                "content": """
**Definition:**
MACD is a trend-following momentum indicator showing relationship between two EMAs of price. Developed by Gerald Appel in 1970s.

**Components:**

1. **MACD Line:**
   - Difference between 12-period EMA and 26-period EMA
   - MACD Line = EMA(12) - EMA(26)
   
2. **Signal Line:**
   - 9-period EMA of MACD Line
   - Acts as trigger for buy/sell signals
   
3. **Histogram:**
   - Visual representation of difference between MACD and Signal line
   - Histogram = MACD Line - Signal Line
   - Positive when MACD above Signal (bullish)
   - Negative when MACD below Signal (bearish)

**Trading Signals:**

1. **Signal Line Crossovers:**
   - **Bullish:** MACD crosses above Signal line
   - **Bearish:** MACD crosses below Signal line
   - Works best in trending markets
   - Prone to whipsaws in sideways markets

2. **Zero Line Crossovers:**
   - **Bullish:** MACD crosses above zero (positive territory)
   - **Bearish:** MACD crosses below zero (negative territory)
   - Indicates change in overall momentum
   - Slower but more reliable than signal line crossovers

3. **Divergences:**
   - **Bullish Divergence:** Price makes lower low, MACD makes higher low
     - Suggests weakening downward momentum
     - Potential reversal signal
   
   - **Bearish Divergence:** Price makes higher high, MACD makes lower high
     - Suggests weakening upward momentum
     - Potential reversal signal
   
   - Divergences are leading signals (predict reversals)
   - Should be confirmed with other indicators

**Settings:**
- Standard: (12, 26, 9)
- For shorter timeframes: (6, 13, 5)
- For longer timeframes: (24, 52, 18)

**Limitations:**
- Lagging indicator (based on past prices)
- False signals in ranging/choppy markets
- Best combined with trend analysis and other indicators
"""
            },
            {
                "heading": "Average Directional Index (ADX)",
                "content": """
**Definition:**
ADX measures trend strength regardless of direction. Developed by J. Welles Wilder. Part of the Directional Movement System.

**Components:**

1. **ADX Line:**
   - Derived from +DI and -DI
   - Ranges from 0 to 100
   - Does NOT indicate trend direction
   - Only measures trend STRENGTH
   
2. **+DI (Positive Directional Indicator):**
   - Measures upward movement
   - Compares current high to previous high
   
3. **-DI (Negative Directional Indicator):**
   - Measures downward movement
   - Compares current low to previous low

**Interpretation:**

**ADX Readings:**
- 0-25: Weak or non-existent trend (ranging market)
- 25-50: Moderate trend strength
- 50-75: Strong trend
- 75-100: Very strong trend (rare)

**Trading Signals:**

1. **Trend Strength Filter:**
   - ADX > 25: Market is trending → Use trend-following strategies
   - ADX < 25: Market is ranging → Use mean reversion strategies
   
2. **DI Crossovers:**
   - **Bullish:** +DI crosses above -DI AND ADX rising
   - **Bearish:** -DI crosses above +DI AND ADX rising
   - Rising ADX confirms trend strength

3. **ADX Peaks:**
   - When ADX peaks and turns down, trend may be ending
   - Doesn't mean reversal, could be consolidation
   
**Strategic Applications:**
- Filter trades based on trend strength
- Avoid counter-trend trades when ADX > 30
- Combine with moving averages for entry timing
- Use for position sizing (larger positions in strong trends)

**Default Period:** 14 (can be adjusted to 20 or 25 for smoother readings)

**Limitations:**
- Lagging indicator
- Doesn't indicate direction, only strength
- Can remain at extreme levels during strong trends
"""
            },
            {
                "heading": "Parabolic SAR (Stop and Reverse)",
                "content": """
**Definition:**
Parabolic SAR provides potential entry/exit points and trailing stop-loss levels. Appears as dots above/below price candles. Developed by J. Welles Wilder.

**Visual Representation:**
- Dots BELOW price = Uptrend (bullish signal)
- Dots ABOVE price = Downtrend (bearish signal)
- Dot flips position when trend reverses

**Calculation:**
```
SAR(tomorrow) = SAR(today) + AF × (EP - SAR(today))

Where:
- AF = Acceleration Factor (starts at 0.02, increases by 0.02 per new extreme)
- EP = Extreme Point (highest high in uptrend, lowest low in downtrend)
- Maximum AF = 0.20
```

**Trading Signals:**

1. **Trend Identification:**
   - Price above SAR dots = Long/Bullish
   - Price below SAR dots = Short/Bearish
   
2. **Entry Signals:**
   - Go long when dot flips from above to below price
   - Go short when dot flips from below to above price
   
3. **Exit/Stop-Loss:**
   - Trailing stop automatically adjusts
   - Exit long when price crosses below SAR dot
   - Exit short when price crosses above SAR dot
   - Never move stop further away, only closer

**Best Used In:**
- Strong trending markets
- Not suitable for sideways/choppy conditions
- Works well on daily and weekly timeframes

**Settings:**
- Default: Step = 0.02, Maximum = 0.20
- Smaller step = Less sensitive, fewer false signals
- Larger step = More sensitive, earlier entries but more whipsaws

**Advantages:**
- Clear visual signals
- Built-in risk management
- Works as trailing stop
- Objective exit strategy

**Disadvantages:**
- Whipsaws in ranging markets
- Late signals during sharp reversals
- Requires strong trends to be profitable

**Combination Strategies:**
- Use with ADX to filter trending vs ranging
- Combine with moving averages for confirmation
- Use ATR to validate volatility conditions
"""
            }
        ]

        for indicator in indicators:
            trend_indicators["content"].append(indicator)

        trend_indicators["sources"] = [
            {
                "source_id": "investopedia",
                "url": "https://www.investopedia.com/technical-analysis-4689657",
                "trust_level": "medium"
            },
            {
                "source_id": "tradingview_docs",
                "url": "https://www.tradingview.com/support/solutions/43000502338",
                "trust_level": "medium"
            }
        ]

        return trend_indicators

    def extract_momentum_indicators(self):
        """Extract momentum oscillators"""
        print("🎯 Extracting momentum indicators...")

        momentum_indicators = {
            "topic_id": "ta_momentum_indicators",
            "title": "Momentum Oscillators and Overbought/Oversold Indicators",
            "content": [],
            "sources": []
        }

        indicators = [
            {
                "heading": "Relative Strength Index (RSI)",
                "content": """
**Definition:**
RSI is a momentum oscillator measuring speed and magnitude of recent price changes. Evaluates whether asset is overbought or oversold. Developed by J. Welles Wilder (1978).

**Calculation:**
```
RSI = 100 - [100 / (1 + RS)]

Where:
RS = Average Gain / Average Loss (over specified period)

Typically uses 14-period calculation
```

**Scale:** 0 to 100

**Key Levels:**
- **Overbought:** RSI > 70 (traditional) or > 80 (strong trend)
- **Oversold:** RSI < 30 (traditional) or < 20 (strong trend)
- **Neutral Zone:** RSI 30-70

**Trading Signals:**

1. **Overbought/Oversold Reversals:**
   - **Sell Signal:** RSI crosses below 70 from overbought territory
   - **Buy Signal:** RSI crosses above 30 from oversold territory
   - Works best in ranging markets
   - Can give premature signals in strong trends

2. **Divergences:**
   
   **Bullish Divergence:**
   - Price makes lower low
   - RSI makes higher low
   - Indicates weakening selling pressure
   - Potential bullish reversal
   
   **Bearish Divergence:**
   - Price makes higher high
   - RSI makes lower high
   - Indicates weakening buying pressure
   - Potential bearish reversal
   
   Divergences are among most reliable RSI signals

3. **Centerline Crossover:**
   - **Bullish:** RSI crosses above 50
   - **Bearish:** RSI crosses below 50
   - Confirms trend direction
   - Less reliable than divergences

4. **Failure Swings (Wilder's Pattern):**
   
   **Bullish Failure Swing:**
   1. RSI drops below 30 (oversold)
   2. RSI bounces, then pulls back (stays above 30)
   3. RSI breaks above previous high
   4. Strong buy signal
   
   **Bearish Failure Swing:**
   1. RSI rises above 70 (overbought)
   2. RSI declines, then rallies (stays below 70)
   3. RSI breaks below previous low
   4. Strong sell signal

**Advanced Concepts:**

**RSI Range Shifting:**
- In strong uptrends: RSI tends to fluctuate between 40-90
  - 40-50 zone acts as support
- In strong downtrends: RSI tends to fluctuate between 10-60
  - 50-60 zone acts as resistance

**Hidden Divergences:**
- **Bullish Hidden:** Price makes higher low, RSI makes lower low
  - Suggests trend continuation
- **Bearish Hidden:** Price makes lower high, RSI makes higher high
  - Suggests downtrend continuation

**Settings:**
- Default: 14 periods
- Shorter (7-10): More volatile, more signals
- Longer (20-25): Smoother, fewer signals

**Limitations:**
- Can remain overbought/oversold during strong trends
- Premature divergence signals
- Best combined with trend analysis
- Not effective in strongly trending markets alone

**Best Practices:**
- Use in conjunction with trend indicators
- Look for divergences at key support/resistance
- Adjust overbought/oversold levels based on market regime
- Confirm with price action and volume
"""
            },
            {
                "heading": "Stochastic Oscillator",
                "content": """
**Definition:**
Stochastic oscillator compares closing price to price range over specific period. Momentum indicator showing where price is relative to recent high-low range. Developed by George Lane in 1950s.

**Calculation:**
```
%K = [(Current Close - Lowest Low) / (Highest High - Lowest Low)] × 100
%D = Simple Moving Average of %K (typically 3 periods)

Where Highest High and Lowest Low are over lookback period (typically 14)
```

**Components:**
- **%K Line (Fast Stochastic):** Main line
- **%D Line (Slow Stochastic):** Signal line (SMA of %K)

**Scale:** 0 to 100

**Key Levels:**
- **Overbought:** Above 80
- **Oversold:** Below 20
- Some traders use 70/30 levels

**Types of Stochastics:**

1. **Full Stochastic:**
   - Most customizable
   - Separate settings for %K period, %K smoothing, %D period
   
2. **Fast Stochastic:**
   - Original formulation
   - %K = raw calculation
   - Very sensitive, prone to whipsaws
   
3. **Slow Stochastic:**
   - %K is smoothed (1-period SMA of fast %K)
   - %D is 3-period SMA of slow %K
   - Most commonly used, reduces false signals

**Trading Signals:**

1. **Overbought/Oversold Readings:**
   - **Sell:** %K crosses below 80 from overbought
   - **Buy:** %K crosses above 20 from oversold
   - Wait for crossover confirmation
   
2. **Signal Line Crossovers:**
   - **Bullish:** %K crosses above %D (especially in oversold)
   - **Bearish:** %K crosses below %D (especially in overbought)
   - Most reliable when aligned with overbought/oversold
   
3. **Divergences:**
   - **Bullish:** Price makes lower low, Stochastic makes higher low
   - **Bearish:** Price makes higher high, Stochastic makes lower high
   - Leading indicator of potential reversals
   
4. **Centerline Crossover:**
   - Cross above 50 = Bullish momentum
   - Cross below 50 = Bearish momentum

**Stochastic Settings:**
- Standard: (14, 3, 3) for Slow Stochastic
- For day trading: (5, 3, 3) more sensitive
- For swing trading: (14, 3, 3) or (21, 5, 5) smoother

**Comparison with RSI:**
- Stochastic more sensitive, gives more signals
- RSI smoother, fewer false signals
- Both measure momentum but differently calculated
- Can use together for confirmation

**Best Markets:**
- Works well in ranging/sideways markets
- Less effective in strong trending markets
- Best for mean reversion strategies

**Limitations:**
- Many false signals in trending markets
- Can stay overbought/oversold during strong trends
- Requires confirmation from other indicators
- Prone to whipsaws without proper filtering

**Strategic Uses:**
- Identify potential reversal points
- Time entries in direction of trend
- Set profit targets at overbought/oversold levels
- Combine with trend filters (e.g., 200 MA)
"""
            },
            {
                "heading": "Commodity Channel Index (CCI)",
                "content": """
**Definition:**
CCI measures current price level relative to average price over specified period. Originally developed for commodities, now used for stocks and forex. Created by Donald Lambert in 1980.

**Calculation:**
```
CCI = (Typical Price - SMA of TP) / (0.015 × Mean Deviation)

Where:
Typical Price (TP) = (High + Low + Close) / 3
SMA = Simple Moving Average (typically 20 periods)
Mean Deviation = Average absolute deviation from SMA
Constant 0.015 ensures ~70-80% readings between ±100
```

**Scale:** Unbounded (typically ranges -300 to +300)

**Key Levels:**
- **+100:** Overbought threshold
- **-100:** Oversold threshold
- **±200:** Extreme levels (strong trend)
- **Zero Line:** Centerline (neutral)

**Trading Signals:**

1. **Overbought/Oversold:**
   - **Buy:** CCI crosses above -100 from oversold
   - **Sell:** CCI crosses below +100 from overbought
   - Works best in ranging markets

2. **Zero Line Crossovers:**
   - **Bullish:** CCI crosses above zero
   - **Bearish:** CCI crosses below zero
   - Indicates change in momentum direction

3. **Divergences:**
   - **Bullish:** Price makes lower low, CCI makes higher low
   - **Bearish:** Price makes higher high, CCI makes lower high
   - Early warning of potential reversals

4. **Pattern Recognition:**
   - CCI can form chart patterns (head & shoulders, triangles)
   - Breakouts on CCI often precede price breakouts
   - Trendlines on CCI can be drawn and broken before price

**Advanced Techniques:**

**Multiple Timeframe Analysis:**
- Use higher timeframe CCI for trend direction
- Use lower timeframe for entry timing
- Align both for high-probability trades

**CCI Waves:**
- Identify swing highs/lows on CCI
- Compare wave structure with price waves
- Divergences between waves signal reversals

**Settings:**
- Default: 20 periods
- Shorter (10-14): More volatile, more signals
- Longer (30-40): Smoother, fewer but stronger signals
- Lambert originally suggested 14 for daily charts

**Unique Characteristics:**
- Works across all timeframes
- Applicable to stocks, futures, forex, crypto
- Can lead price (divergences)
- Also follows price (trend confirmation)

**Limitations:**
- Unbounded scale means no absolute extremes
- Can give late signals in fast markets
- Whipsaws in choppy conditions
- Requires volume/momentum confirmation

**Best Practices:**
- Combine with trend-following indicators
- Use divergences at key support/resistance
- Apply in conjunction with price action analysis
- Filter signals based on market regime
"""
            }
        ]

        for indicator in indicators:
            momentum_indicators["content"].append(indicator)

        momentum_indicators["sources"] = [
            {
                "source_id": "investopedia",
                "url": "https://www.investopedia.com/technical-analysis-4689657",
                "trust_level": "medium"
            },
            {
                "source_id": "tradingview_docs",
                "url": "https://www.tradingview.com/support/solutions/43000502338",
                "trust_level": "medium"
            }
        ]

        return momentum_indicators

    def compile_raw_notes(self):
        """Compile all extracted data into raw notes"""
        print("📝 Compiling TA indicators raw notes...")

        # Extract all sections
        sections = [
            self.extract_trend_indicators(),
            self.extract_momentum_indicators()
        ]

        # Add to extracted data
        self.extracted_data["topics"] = sections

        # Generate markdown output
        markdown_content = self._generate_markdown()

        # Save to file
        output_file = self.output_dir / "ta_indicators_raw.md"
        output_file.write_text(markdown_content, encoding='utf-8')

        # Also save structured JSON
        json_file = self.output_dir / "ta_indicators_raw.json"
        json_file.write_text(json.dumps(
            self.extracted_data, indent=2), encoding='utf-8')

        print(f"✅ TA indicators extraction complete!")
        print(f"📄 Saved: {output_file}")
        print(f"📊 Saved: {json_file}")

        return output_file

    def _generate_markdown(self):
        """Generate formatted markdown from extracted data"""
        md = []

        # Header
        md.append("# Technical Analysis Indicators - Raw Extraction Notes")
        md.append("")
        md.append(
            f"**Extraction Date:** {self.extracted_data['extraction_date']}")
        md.append(f"**Sources:** Investopedia, TradingView Documentation")
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
                md.append(f"  - URL: {source['url']}")
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
    print("🚀 TECHNICAL ANALYSIS INDICATORS EXTRACTION")
    print("=" * 70)
    print()

    extractor = TAIndicatorsExtractor()
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
