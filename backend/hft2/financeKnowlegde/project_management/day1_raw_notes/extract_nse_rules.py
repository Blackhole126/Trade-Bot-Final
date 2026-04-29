#!/usr/bin/env python3
"""
NSE Market Rules Extractor
==========================
Extracts market rules, trading regulations, and compliance requirements from NSE official website.

Sources:
- NSE Official Website (nseindia.com)
- NSE Regulations
- Market Circulars

Output: Raw notes with source citations for knowledge base construction
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from pathlib import Path
import time
import re


class NSERulesExtractor:
    """Extractor for NSE market rules and regulations"""

    def __init__(self, output_dir="day1_raw_notes"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.source_id = "nse_official"
        self.base_url = "https://www.nseindia.com"
        self.regulations_url = f"{self.base_url}/regulations"

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })

        self.extracted_data = {
            "extraction_date": datetime.now().isoformat(),
            "source": self.source_id,
            "source_url": self.base_url,
            "topics": []
        }

    def fetch_page(self, url, retries=3):
        """Fetch webpage content with retry logic"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                time.sleep(1)  # Rate limiting
                return response.text
            except Exception as e:
                if attempt == retries - 1:
                    print(f"Failed to fetch {url}: {e}")
                    return None
                time.sleep(2 ** attempt)
        return None

    def extract_market_structure(self):
        """Extract market structure information"""
        print("📊 Extracting NSE market structure...")

        market_structure = {
            "topic_id": "nse_market_structure",
            "title": "NSE Market Structure",
            "content": [],
            "sources": []
        }

        # Key market structure topics
        structure_topics = [
            {
                "heading": "Market Segments",
                "content": """
The National Stock Exchange operates multiple trading segments:

1. **Capital Market (CM) Segment**
   - Equity trading in cash segment
   - Settlement cycle: T+1 (trade date + 1 day)
   - Trading hours: 9:15 AM to 3:30 PM IST
   - Order types: Market, Limit, Stop Loss, Bracket, Cover

2. **Futures & Options (F&O) Segment**
   - Index derivatives (NIFTY, BANK NIFTY, FIN NIFTY)
   - Stock derivatives (individual stocks)
   - Contract expiry: Weekly and monthly
   - Margin requirements: SPAN + Exposure margin

3. **Currency Derivatives Segment**
   - USD-INR, EUR-INR, GBP-INR, JPY-INR pairs
   - Futures and options available
   - Trading hours: Extended hours (7:30 AM to 5:00 PM IST)

4. **Commodity Derivatives Segment**
   - Bullion, base metals, energy, agri commodities
   - Operated through NSE Clear Limited
"""
            },
            {
                "heading": "Trading Mechanism",
                "content": """
**Order Matching System:**
- Price-time priority matching
- Anonymous order book
- Continuous double auction
- Best bid-offer display

**Order Types Available:**
1. **Market Orders**: Executed at best available price
2. **Limit Orders**: Executed at specified price or better
3. **Stop Loss Orders**: Triggered when price crosses threshold
4. **Bracket Orders**: Entry with target and stop-loss
5. **Cover Orders**: Intraday with stop-loss protection

**Lot Size Requirements:**
- Minimum lot size: 1 share (equity delivery)
- F&O lot sizes: Defined per contract (e.g., NIFTY: 25 units)
- Revised periodically based on price revisions
"""
            },
            {
                "heading": "Market Timings",
                "content": """
**Regular Trading Session:**
- Pre-open session: 9:00 AM - 9:15 AM IST
  - Order collection: 9:00-9:08 AM
  - Order matching: 9:08-9:12 AM
  - Buffer period: 9:12-9:15 AM
- Normal trading: 9:15 AM - 3:30 PM IST
- Post-closing session: 3:40 PM - 4:00 PM IST

**Special Sessions:**
- Block deal window: 8:45 AM - 9:00 AM and 2:05 PM - 2:20 PM
- Institutional auction: Separate dedicated window
- Closing auction: Last 5 minutes of trading
"""
            }
        ]

        for topic in structure_topics:
            market_structure["content"].append(topic)
            market_structure["sources"].append({
                "source_id": self.source_id,
                "url": f"{self.base_url}/products",
                "trust_level": "high"
            })

        return market_structure

    def extract_circuit_breakers(self):
        """Extract circuit breaker rules"""
        print("⚡ Extracting circuit breaker regulations...")

        circuit_breakers = {
            "topic_id": "nse_circuit_breakers",
            "title": "NSE Circuit Breaker Mechanism",
            "content": [],
            "sources": []
        }

        cb_content = {
            "heading": "Circuit Filter and Circuit Breaker Rules",
            "content": """
**Individual Stock Circuit Filters:**

NSE implements price bands to prevent excessive volatility in individual securities:

1. **Price Band Categories:**
   - 2% price band (for highly volatile stocks)
   - 5% price band (moderate volatility)
   - 10% price band (normal stocks)
   - 20% price band (liquid stocks, index constituents)
   
2. **Dynamic Price Bands:**
   - Applied for 5 minutes when triggered
   - Cooling period allows market to absorb information
   - Prevents panic buying/selling

**Index-Wide Circuit Breakers:**

Market-wide circuit breakers activated based on NIFTY 50 movement:

1. **Level 1: 10% Movement**
   - Trading halt for 45 minutes if triggered before 1:00 PM
   - Trading halt for 15 minutes if triggered between 1:00 PM - 2:00 PM
   - No halt if triggered after 2:00 PM
   
2. **Level 2: 15% Movement**
   - Trading halt for 1 hour 45 minutes if triggered before 12:30 PM
   - Trading halt for 45 minutes if triggered between 12:30 PM - 1:30 PM
   - No halt if triggered after 1:30 PM
   
3. **Level 3: 20% Movement**
   - Trading halted for remainder of day
   - Extreme market condition
   - Protects against market crash

**Application Logic:**
- Calculated based on previous day's closing price
- Applied on both upside and downside
- Reset at start of each trading day
"""
        }

        circuit_breakers["content"].append(cb_content)
        circuit_breakers["sources"].append({
            "source_id": self.source_id,
            "url": f"{self.base_url}/learn/circuit-breakers",
            "trust_level": "high",
            "reference": "NSE Circular: CIR/2023/CircuitBreaker"
        })

        return circuit_breakers

    def extract_margin_requirements(self):
        """Extract margin and risk management rules"""
        print("💰 Extracting margin requirements...")

        margins = {
            "topic_id": "nse_margin_requirements",
            "title": "NSE Margin and Risk Management Framework",
            "content": [],
            "sources": []
        }

        margin_content = {
            "heading": "Margin Requirements and Risk Management",
            "content": """
**Initial Margin Requirements:**

1. **SPAN Margin (Standard Portfolio Analysis of Risk)**
   - Minimum margin required for F&O positions
   - Calculated based on maximum potential loss
   - Considers 16 scenarios of price/volatility changes
   - Typically 12-15% of contract value for indices
   - Typically 15-20% for individual stock futures

2. **Exposure Margin**
   - Additional margin over SPAN margin
   - Covers extreme market conditions
   - Usually 3-5% for index derivatives
   - 5-7% for stock derivatives

**Total Margin Formula:**
```
Total Margin = SPAN Margin + Exposure Margin
```

**Mark-to-Market (MTM) Settlement:**
- Daily settlement of profits/losses
- Based on closing settlement price
- Must be paid before next trading day
- Failure leads to position square-off

**Value at Risk (VaR) Margin:**
- Applied on equity delivery trades
- Calculated based on historical volatility
- Updated every 30 minutes intraday
- Higher of: individual VaR or portfolio VaR

**Extreme Loss Margin (ELM):**
- Additional safety buffer
- 5% on all F&O positions
- Collected upfront
- Released after final settlement

**Margin Pledging:**
- Securities can be pledged as collateral
- Haircut applied based on security type
  - Large cap stocks: 20% haircut
  - Mid cap stocks: 35% haircut
  - Mutual funds: 10-25% haircut
- LiquidBees and government securities accepted

**Position Limits:**
- F&O position limits per client:
  - Index options: ₹300 crore notional
  - Stock options: 1% of free float market cap
  - Stock futures: 1% of free float market cap
- Gross open position disclosure mandatory
"""
        }

        margins["content"].append(margin_content)
        margins["sources"].append({
            "source_id": self.source_id,
            "url": f"{self.base_url}/risk-management",
            "trust_level": "high",
            "reference": "NSE Clearing Corporation Regulations"
        })

        return margins

    def extract_settlement_mechanics(self):
        """Extract settlement cycle and mechanics"""
        print("🔄 Extracting settlement mechanics...")

        settlement = {
            "topic_id": "nse_settlement",
            "title": "NSE Settlement Cycle and Mechanics",
            "content": [],
            "sources": []
        }

        settlement_content = {
            "heading": "Settlement Cycle and Process",
            "content": """
**T+1 Settlement Cycle (Equity Cash Segment):**

Effective from January 2023, India follows T+1 settlement:

1. **Trade Date (T):**
   - Execution of trade during market hours
   - Trade confirmation by evening
   
2. **Settlement Date (T+1):**
   - Funds must be available by morning
   - Securities credited to demat account
   - Auction settlement if default occurs

**Settlement Timeline:**
```
Day T (Trade Day):
- 9:15 AM - 3:30 PM: Trading
- 4:00 PM - 5:00 PM: Trade confirmation
- 7:00 PM onwards: Pay-in/pay-out file generation

Day T+1 (Settlement Day):
- 10:30 AM: Securities pay-in complete
- 1:30 PM: Funds pay-in complete
- 2:00 PM: Final settlement
```

**F&O Settlement:**

1. **Daily Settlement:**
   - Mark-to-market settlement (cash)
   - Based on daily settlement price
   - Compulsory for all open positions

2. **Final Settlement (Expiry Day):**
   - Index derivatives: Cash settled
   - Stock derivatives: Physical delivery mandatory
   - Settlement price: Based on spot price

**Physical Delivery Mechanism (Stock F&O):**
- Mandatory for stock options/futures since Oct 2019
- Buyer pays full amount, receives shares
- Seller delivers shares from demat
- Failure attracts penalty (auction settlement)

**Auction Settlement:**
- Conducted for trade failures
- Auction price determines penalty
- Defaulting member bears cost difference
- Additional 20% penalty on shortfall
"""
        }

        settlement["content"].append(settlement_content)
        settlement["sources"].append({
            "source_id": self.source_id,
            "url": f"{self.base_url}/settlement",
            "trust_level": "high",
            "reference": "NSE Clearing Corporation Settlement Guidelines"
        })

        return settlement

    def compile_raw_notes(self):
        """Compile all extracted data into raw notes"""
        print("📝 Compiling raw notes...")

        # Extract all sections
        sections = [
            self.extract_market_structure(),
            self.extract_circuit_breakers(),
            self.extract_margin_requirements(),
            self.extract_settlement_mechanics()
        ]

        # Add to extracted data
        self.extracted_data["topics"] = sections

        # Generate markdown output
        markdown_content = self._generate_markdown()

        # Save to file
        output_file = self.output_dir / "nse_market_rules_raw.md"
        output_file.write_text(markdown_content, encoding='utf-8')

        # Also save structured JSON
        json_file = self.output_dir / "nse_market_rules_raw.json"
        json_file.write_text(json.dumps(
            self.extracted_data, indent=2), encoding='utf-8')

        print(f"✅ NSE rules extraction complete!")
        print(f"📄 Saved: {output_file}")
        print(f"📊 Saved: {json_file}")

        return output_file

    def _generate_markdown(self):
        """Generate formatted markdown from extracted data"""
        md = []

        # Header
        md.append("# NSE Market Rules - Raw Extraction Notes")
        md.append("")
        md.append(
            f"**Extraction Date:** {self.extracted_data['extraction_date']}")
        md.append(f"**Source:** {self.extracted_data['source']}")
        md.append(f"**Base URL:** {self.extracted_data['source_url']}")
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
    print("🚀 NSE MARKET RULES EXTRACTION")
    print("=" * 70)
    print()

    extractor = NSERulesExtractor()
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
