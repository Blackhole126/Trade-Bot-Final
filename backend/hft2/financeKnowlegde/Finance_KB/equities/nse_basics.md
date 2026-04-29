# NSE Market Basics

**Topic ID:** `nse_market_structure`  
**Version:** 1.0.0  
**Last Updated:** 2026-03-20

---

## Market Segments

The National Stock Exchange operates multiple trading segments:

### 1. Capital Market (CM) Segment
- **Equity trading in cash segment**
- **Settlement cycle:** T+1 (trade date + 1 day)
- **Trading hours:** 9:15 AM to 3:30 PM IST
- **Order types:** Market, Limit, Stop Loss, Bracket, Cover
- **Lot size:** Minimum 1 share for equity delivery

### 2. Futures & Options (F&O) Segment
- **Index derivatives:** NIFTY, BANK NIFTY, FIN NIFTY
- **Stock derivatives:** Individual stocks (200+ underlying)
- **Contract expiry:** Weekly and monthly series
- **Margin requirements:** SPAN + Exposure margin
- **Settlement:** Cash-settled for indices, physical for stocks

### 3. Currency Derivatives Segment
- **Currency pairs:** USD-INR, EUR-INR, GBP-INR, JPY-INR
- **Products:** Futures and options available
- **Trading hours:** Extended hours (7:30 AM - 5:00 PM IST)
- **Contract size:** Varies by currency pair

### 4. Commodity Derivatives Segment
- **Categories:** Bullion, base metals, energy, agri commodities
- **Operated through:** NSE Clearing Limited
- **Settlement:** Physical and cash-settled contracts

---

## Trading Mechanism

### Order Matching System
- **Price-time priority matching:** Best price first, then time precedence
- **Anonymous order book:** Identities of traders concealed
- **Continuous double auction:** Continuous matching during market hours
- **Best bid-offer display:** Top 5 bids and offers visible

### Order Types Available

#### 1. Market Orders
- Executed at best available price in the market
- Immediate execution guaranteed
- Price uncertainty (slippage possible)
- Used when urgency is more important than price

#### 2. Limit Orders
- Executed at specified price or better
- Price certainty but no execution guarantee
- Can be placed for entire day or specific duration
- Most commonly used order type

#### 3. Stop Loss Orders
- Triggered when price crosses specified threshold
- Becomes market order once triggered
- Protects against adverse price movements
- Two components: Trigger price and limit price (optional)

#### 4. Bracket Orders (BO)
- Entry order with target and stop-loss
- Automatic square-off on target/stop hit
- Intraday product only
- Higher leverage available (typically 5x)

#### 5. Cover Orders (CO)
- Intraday orders with mandatory stop-loss
- Better leverage than MIS (typically 5-10x)
- Stop-loss protects against large losses
- Must be squared off before market close

### Lot Size Requirements
- **Equity delivery:** Minimum 1 share
- **F&O lot sizes:** Defined per contract (e.g., NIFTY: 25 units, BANKNIFTY: 15 units)
- **Revisions:** Based on price revisions (NSE reviews periodically)
- **Value:** Typically ₹5-10 lakhs per lot at current prices

---

## Market Timings

### Regular Trading Session

#### Pre-Open Session (9:00 AM - 9:15 AM IST)
**Order Collection Period (9:00-9:08 AM):**
- Orders can be placed, modified, cancelled
- Indicative equilibrium price calculated
- No trades executed yet

**Order Matching Period (9:08-9:12 AM):**
- Orders matched at single equilibrium price
- Market open price discovered
- Surplus orders carried to normal session

**Buffer Period (9:12-9:15 AM):**
- Transition to normal trading
- System preparation

#### Normal Trading Session (9:15 AM - 3:30 PM IST)
- Continuous order matching
- Real-time price discovery
- Maximum liquidity available

#### Post-Closing Session (3:40 PM - 4:00 PM IST)
- Closing auction for specific securities
- Final settlement price determination
- Day-end processes

### Special Sessions

#### Block Deal Window
**Morning Session:** 8:45 AM - 9:00 AM  
**Afternoon Session:** 2:05 PM - 2:20 PM
- Minimum transaction value: ₹5 crore
- Price range: ±1% of previous close
- Anonymous execution
- For large institutional trades

#### Institutional Auction
- Separate dedicated window
- Government securities
- State development loans
- Treasury bills

---

## Circuit Breakers

### Individual Stock Circuit Filters

NSE implements price bands to prevent excessive volatility:

#### Price Band Categories
1. **2% Price Band**
   - Applied to highly volatile stocks
   - New listings initially
   - Stocks under surveillance

2. **5% Price Band**
   - Moderate volatility stocks
   - Small-cap stocks
   - Specific sectors as needed

3. **10% Price Band**
   - Normal stocks
   - Most mid-cap stocks
   - Standard band

4. **20% Price Band**
   - Liquid stocks
   - Index constituents (NIFTY 50)
   - Large-cap stocks

#### Dynamic Price Bands Application
- **Trigger:** When price hits upper/lower band
- **Cooling period:** 5 minutes trading halt
- **Purpose:** Allow market to absorb information
- **Resumption:** Trading resumes with wider bands if needed

### Index-Wide Circuit Breakers

Market-wide circuit breakers activated based on NIFTY 50 movement:

#### Level 1: 10% Movement
**Before 1:00 PM:**
- Trading halt for 45 minutes
- Resume at 1:00 PM or after 45 minutes (whichever later)

**Between 1:00 PM - 2:00 PM:**
- Trading halt for 15 minutes
- Resume after 15 minutes

**After 2:00 PM:**
- No trading halt
- Continue trading

#### Level 2: 15% Movement
**Before 12:30 PM:**
- Trading halt for 1 hour 45 minutes
- Resume at 12:30 PM or after halt period

**Between 12:30 PM - 1:30 PM:**
- Trading halt for 45 minutes
- Resume after 45 minutes

**After 1:30 PM:**
- No trading halt
- Continue trading

#### Level 3: 20% Movement
- **Trading halted for remainder of day**
- Extreme market condition
- Market-wide panic/crash scenario
- Protects against systemic risk

### Application Logic
- **Calculation base:** Previous day's closing level
- **Application:** Both upside and downside
- **Reset:** At start of each trading day
- **Monitoring:** Real-time by exchange

---

## Settlement Cycle

### T+1 Settlement Cycle (Effective January 2023)

India follows T+1 (Trade date + 1 day) settlement for equity cash segment.

#### Trade Date (T)

**During Market Hours (9:15 AM - 3:30 PM):**
- Trade execution
- Real-time confirmation
- Margin blocked immediately

**Evening (4:00 PM - 5:00 PM):**
- Trade confirmation to clients
- Contract note generation
- Pay-in/pay-out file preparation

#### Settlement Date (T+1)

**Morning (10:30 AM):**
- Securities pay-in deadline
- Sellers must deliver shares to pool account
- Failure leads to auction

**Afternoon (1:30 PM):**
- Funds pay-in deadline
- Buyers must make payment available
- Shortage leads to penalty

**Final Settlement (2:00 PM onwards):**
- Securities credited to buyer's demat
- Funds credited to seller's bank account
- Process complete

### F&O Settlement

#### Daily Settlement (Mark-to-Market)
- **Timing:** Every trading day
- **Basis:** Daily settlement price (closing price)
- **Payment:** Must be made before next day opening
- **Default:** Position square-off

#### Final Settlement (Expiry Day)

**Index Derivatives:**
- **Settlement type:** Cash-settled
- **Settlement price:** Final settlement price (based on spot)
- **Process:** Automatic profit/loss credit/debit
- **No physical delivery**

**Stock Derivatives:**
- **Settlement type:** Physical delivery MANDATORY
- **Buyer obligation:** Pay full amount, receive shares
- **Seller obligation:** Deliver shares from demat
- **Failure penalty:** Auction settlement with penalty

### Auction Settlement

Conducted when trade fails due to:
- Seller doesn't deliver shares
- Buyer doesn't make payment
- Insufficient quantity in pool

**Auction Process:**
1. Exchange conducts auction next day
2. Shares bought/sold in market
3. Defaulting member bears cost difference
4. Additional penalty: Up to 20% of shortfall
5. Repeated defaults lead to stricter action

---

## Sources

- **Source ID:** `nse_official` | Trust Level: high
  - URL: https://www.nseindia.com/products
  - Reference: NSE Circulars 2023-2026

- **Source ID:** `sebi_circulars` | Trust Level: high
  - URL: https://www.sebi.gov.in
  - Reference: SEBI LODR Regulations 2015

---

*This document is part of the Finance Knowledge Base system. For LLM ingestion, use topic ID: nse_market_structure*
