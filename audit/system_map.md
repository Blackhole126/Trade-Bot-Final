# System Mapping Report (Phase 1 — Evidence-Based Audit)

---

## Objective

Map actual live connections across the system and verify whether:

Samachar → Samruddhi → Trading System

are connected in reality, based only on observed evidence.

---

## 1. Entry Point Verification

### Samachar → /news/ingest

**Observation:**

* Backend logs were monitored during system startup and idle runtime.
* No automatic requests to `/news/ingest` were observed.
* Only manually triggered requests appeared in logs.

**Evidence:**

* No `POST /news/ingest` entries in logs without manual execution.

**Conclusion:**
Samachar system is not connected to the ingestion endpoint.

---

## 2. Ingestion Layer Verification

### `/news/ingest` API

**Test Input:**

```json
{
  "news_id": "audit_test_001",
  "title": "Company profits surge strongly",
  "content": "Company reports record profits and growth",
  "source": "Audit",
  "timestamp": "2026-05-02T12:10:00",
  "metadata": { "category": "finance" }
}
```

**API Response:**

```json
{
  "success": true,
  "data": {
    "sentiment": "positive",
    "impact_score": 0.04,
    "tags": []
  },
  "request_id": "news_1777703870_dcc25b"
}
```

**Observation:**

* Input is validated successfully.
* Sentiment and impact_score are generated.

**Conclusion:**
Ingestion API is functional and performs processing correctly.

---

## 3. Database Persistence Verification

**Database Checked:**
`backend/hft2/data/trading.db`

**Query Executed:**

```sql
SELECT * FROM news WHERE news_id = 'audit_test_001';
```

**Result:**

```text
(2, 'audit_test_001', 'Company profits surge strongly', ..., 'positive', 0.04, ..., 'news_1777703870_dcc25b')
```

**Observation:**

* Record exists in `news` table.
* All fields (sentiment, impact_score, request_id) are persisted.

**Conclusion:**
Ingested news is successfully stored in `trading.db`.

---

## 4. Main System Database Verification

**Database Checked:**
`backend/hft2/data/samruddhi_memory.db`

**Tables Observed:**

* users
* financial_knowledgebase
* market_events
* strategy_signals
* trades
* others

**Queries Executed:**

```sql
SELECT * FROM market_events;
```

**Result:**

* No rows returned

**Observation:**

* No `news` table exists in this database.
* No ingested data found in any table.

**Conclusion:**
Main system database does not contain ingested news data.

---

## 5. Code-Level Verification

**File:** `api_server.py`

**Observation:**

* `/news/ingest` performs database insertion using:

```python
INSERT INTO news (...)
```

* Database connection uses:

```python
sqlite3.connect(DB_PATH)
```

* `DB_PATH` resolves to `trading.db`

**Conclusion:**
Ingestion writes exclusively to `trading.db` and not to the main system database.

---

## 6. Cross-Layer Connectivity Verification

### Ingestion → Database

✔ Verified: Data is stored in `trading.db`

---

### Database → Downstream Systems

**Observation:**

* Prediction and execution systems operate on `samruddhi_memory.db`
* Ingested data resides in `trading.db`
* No shared tables or linkage identified

**Conclusion:**
No evidence found that ingested news is used downstream.

---

### Prediction System

**Observation:**

* Prediction system is configured separately and uses a different data source (`samruddhi_memory.db`)
* No linkage to `trading.db` identified

**Conclusion:**
No evidence that prediction system reads ingested news.

---

### Execution System

**Observation:**

* Execution system operates on strategy_signals, trades, and related tables in `samruddhi_memory.db`
* No linkage to `trading.db` identified

**Conclusion:**
No evidence found that execution system consumes or reacts to ingested news data.

Further behavioral validation required in later phases.

---

## 7. Actual System Flow (Verified Reality)

Samachar → ❌ Not connected

Manual API → Processing → trading.db (news stored)

trading.db → ❌ Not connected to samruddhi_memory.db

Prediction → No evidence of using ingested news

Execution → No evidence of using ingested news

---

## 8. Integration Status (Phase 1)

**Status:** Partially Integrated

**Reason:**

* Ingestion and persistence are functional (verified via API and DB)
* Data is stored in an isolated database (`trading.db`)
* No connection to main system (`samruddhi_memory.db`)
* No automatic input from Samachar
* No evidence of downstream usage

---

## Final Statement

All findings in this report are based strictly on:

* API responses
* Database queries
* Backend logs
* Code inspection

No assumptions have been made.
