# COMMODITY DATA SOURCES - BHIV REGISTRY MAPPING

## 📊 Dataset Inventory for Commodity Intelligence

**Date:** March 20, 2026  
**Version:** 1.0  
**Status:** Dataset Mapping Complete

---

## DATASET CATEGORIES

### Category 1: Agricultural Commodities (FAO)

#### FAO Food Price Index (FFPI)
- **Source:** Food and Agriculture Organization (FAO)
- **Dataset ID:** `FAO_FFPI_MONTHLY`
- **Frequency:** Monthly
- **Coverage:** Global
- **Time Range:** 1990-Present
- **Format:** CSV, JSON API
- **URL:** https://www.fao.org/worldfoodsituation/foodpriceindex/en/

**Data Structure:**
```csv
date,ffpi_meat,ffpi_dairy,ffpi_sugar,ffpi_cereals,ffpi_vegoil,ffpi_total
2024-01,120.5,130.2,95.3,140.8,180.5,135.2
2024-02,121.3,129.8,96.1,141.2,182.3,136.1
```

**Fields:**
- `ffpi_meat` - Meat price index
- `ffpi_dairy` - Dairy price index
- `ffpi_sugar` - Sugar price index
- `ffpi_cereals` - Cereals price index
- `ffpi_vegoil` - Vegetable oil price index
- `ffpi_total` - Overall food price index

**Use Cases:**
- Inflation prediction
- Agricultural commodity trading
- Food security analysis

---

#### FAO Cereal Supply and Demand
- **Source:** FAO
- **Dataset ID:** `FAO_CEREAL_SD`
- **Frequency:** Quarterly
- **Coverage:** Global, Regional
- **Format:** CSV, Excel

**Data Structure:**
```csv
date,region,cereal_type,supply_mt,demand_mt,stock_mt,production_mt
2024-Q1,World,Wheat,850000,820000,180000,780000
2024-Q1,Asia,Rice,420000,410000,95000,390000
```

---

### Category 2: World Bank Commodity Prices

#### World Bank Pink Sheet Data
- **Source:** World Bank
- **Dataset ID:** `WB_PINK_SHEET`
- **Frequency:** Monthly
- **Coverage:** Global commodities
- **Time Range:** 1960-Present
- **Format:** CSV, JSON, Excel
- **URL:** https://www.worldbank.org/en/research/commodity-markets

**Commodities Covered:**
- **Energy:** Crude oil, natural gas, coal
- **Agriculture:** Wheat, corn, soybeans, cotton, sugar, coffee
- **Metals:** Aluminum, copper, iron ore, zinc
- **Precious Metals:** Gold, silver, platinum

**Data Structure:**
```csv
date,commodity,price_usd,unit,index_2010
2024-01,Crude_oil,82.5,USD/barrel,145.2
2024-01,Wheat,220.5,USD/tonne,132.8
2024-01,Gold,2045.0,USD/oz,178.5
```

---

#### World Bank Commodity Price Index
- **Source:** World Bank
- **Dataset ID:** `WB_COMPRICE_INDEX`
- **Frequency:** Monthly
- **Base Year:** 2010=100
- **Format:** CSV, JSON

**Indices:**
- Energy Index
- Non-energy Index
- Agriculture Index
- Metals Index
- Fertilizers Index

---

### Category 3: Indian Commodity Markets (MCX)

#### MCX Commodity Prices
- **Source:** Multi Commodity Exchange of India (MCX)
- **Dataset ID:** `MCX_LIVE_PRICES`
- **Frequency:** Real-time / End-of-day
- **Coverage:** Indian market
- **Format:** API, CSV
- **URL:** https://www.mcxindia.com/

**Commodities:**
- **Precious Metals:** Gold, Silver
- **Base Metals:** Copper, Zinc, Lead, Aluminum
- **Energy:** Crude Oil, Natural Gas
- **Agriculture:** Cotton, Cardamom, Mentha Oil

**Data Structure:**
```csv
timestamp,symbol,ltp,change,change_pct,volume,open_interest
2024-03-20T15:30:00,GOLD,62500,250,0.40,15234,8523
2024-03-20T15:30:00,SILVER,78500,-450,-0.57,23451,12456
```

---

#### MCX Bhavcopy
- **Source:** MCX
- **Dataset ID:** `MCX_BHAVCOPY`
- **Frequency:** Daily
- **Format:** CSV, Excel
- **URL:** https://www.mcxindia.com/market-data/bhavcopy

**Fields:**
```csv
date,symbol,instrument,expiry,open,high,low,close,volume,oi
2024-03-20,GOLD,FUTURES,2024-04-05,62200,62800,62000,62500,15234,8523
```

---

### Category 4: Global Commodity Feeds

#### Bloomberg Commodity Indices
- **Source:** Bloomberg
- **Dataset ID:** `BCOM_INDICES`
- **Frequency:** Real-time
- **Coverage:** Global
- **Format:** API (Paid)

**Indices:**
- Bloomberg Commodity Index (BCOM)
- Bloomberg Industrial Metals Subindex
- Bloomberg Energy Subindex
- Bloomberg Agriculture Subindex

---

#### Reuters Commodity Prices
- **Source:** Reuters/Refinitiv
- **Dataset ID:** `REUTERS_COMM`
- **Frequency:** Real-time
- **Format:** API (Paid)

---

#### LME Metal Prices
- **Source:** London Metal Exchange
- **Dataset ID:** `LME_PRICES`
- **Frequency:** Daily
- **Coverage:** Base metals
- **Format:** CSV, API
- **URL:** https://www.lme.com/

**Metals:**
- Aluminum
- Copper
- Zinc
- Lead
- Nickel
- Tin

---

### Category 5: Economic Indicators

#### US Dollar Index (DXY)
- **Source:** Federal Reserve
- **Dataset ID:** `USD_INDEX`
- **Frequency:** Daily
- **Impact:** Commodity prices inversely correlated

---

#### CRB Commodity Research Bureau Index
- **Source:** ICE Data Services
- **Dataset ID:** `CRB_INDEX`
- **Frequency:** Daily
- **Commodities:** 19 commodities

---

## DATASET PRIORITY MATRIX

### Priority 1 (Critical - Implement First)

| Dataset | Source | Format | Update Frequency | Priority Score |
|---------|--------|--------|------------------|----------------|
| FAO Food Price Index | FAO | CSV/API | Monthly | 95/100 |
| World Bank Pink Sheet | World Bank | CSV/JSON | Monthly | 95/100 |
| MCX Live Prices | MCX | API | Real-time | 90/100 |
| MCX Bhavcopy | MCX | CSV | Daily | 90/100 |

### Priority 2 (High Value)

| Dataset | Source | Format | Priority Score |
|---------|--------|--------|----------------|
| FAO Cereal Supply/Demand | FAO | CSV | 85/100 |
| LME Metal Prices | LME | API | 85/100 |
| WB Commodity Price Index | World Bank | CSV | 85/100 |

### Priority 3 (Supplementary)

| Dataset | Source | Format | Priority Score |
|---------|--------|--------|----------------|
| Bloomberg BCOM | Bloomberg | API (Paid) | 70/100 |
| Reuters Commodities | Reuters | API (Paid) | 70/100 |
| CRB Index | ICE | API | 70/100 |

---

## DATA ACQUISITION STRATEGY

### Phase 1: Free & Open Sources (Week 1)

✅ **FAO Datasets**
- Download via FAO API or bulk CSV
- Update frequency: Monthly
- Storage: SQLite + CSV cache

✅ **World Bank Datasets**
- Download via World Bank API
- Update frequency: Monthly
- Storage: SQLite + CSV cache

✅ **MCX Public Data**
- Scrape bhavcopy from MCX website
- Update frequency: Daily
- Storage: SQLite + CSV cache

### Phase 2: Premium APIs (Week 2-3)

⏳ **Bloomberg/Reuters** (if budget available)
- API integration
- Real-time updates
- Storage: High-frequency database

### Phase 3: Alternative Sources (Week 4)

⏳ **Custom scrapers**
- Government agriculture data
- Weather data for crop predictions
- Shipping/freight data

---

## STORAGE ARCHITECTURE

```
backend/hft2/data/commodities/
├── raw/                    # Raw downloaded data
│   ├── fao/
│   ├── worldbank/
│   └── mcx/
├── processed/              # Normalized data
│   ├── daily_prices.db
│   ├── indices.db
│   └── features.db
└── cache/                  # Temporary cache
    ├── api_responses/
    └── csv_cache/
```

---

## UPDATE SCHEDULE

| Dataset | Update Frequency | Auto-Update Time |
|---------|------------------|------------------|
| FAO FFPI | Monthly | 1st of month, 02:00 UTC |
| World Bank | Monthly | 15th of month, 02:00 UTC |
| MCX Bhavcopy | Daily | Daily 18:00 IST |
| MCX Live | Real-time | Market hours polling |
| LME Prices | Daily | Daily 20:00 UTC |

---

## QUALITY METRICS

### Data Quality Checks

✅ **Completeness:** No missing values > 5%  
✅ **Timeliness:** Updates within 24h of release  
✅ **Consistency:** Cross-validate overlapping sources  
✅ **Accuracy:** Spot-check against official sources  

---

## INTEGRATION POINTS

### With Samruddhi Memory Layer

```python
# Store commodity data in dedicated tables
class CommodityPrice(Base):
    __tablename__ = 'commodity_prices'
    
    id = Column(Integer, primary_key=True)
    commodity_id = Column(String(100), index=True)
    source = Column(String(100))
    timestamp = Column(DateTime, index=True)
    price = Column(Numeric(18, 4))
    currency = Column(String(3))
    unit = Column(String(50))
    dataset_id = Column(String(100))
```

### With Signal Generation

```python
# Generate commodity signals
signal = generate_commodity_signal(
    commodity='GOLD',
    signal_type='MOMENTUM_UP',
    confidence=0.85,
    data_source='MCX'
)
```

---

## NEXT STEPS

1. ✅ Create data ingestion engine (`commodity_data_ingestion.py`)
2. ✅ Implement FAO dataset downloader
3. ✅ Implement World Bank dataset downloader
4. ✅ Implement MCX data scraper
5. ✅ Set up automated update schedules
6. ✅ Create feature engineering pipeline
7. ✅ Build signal generation engine

---

## DOCUMENTATION SIGN-OFF

**Author:** AI Trading System Architect  
**Date:** March 20, 2026  
**Status:** ✅ Dataset Mapping Complete  

**Ready for:** Day 1 Implementation - Data Ingestion Engine
