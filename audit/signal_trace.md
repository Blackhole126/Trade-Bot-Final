# Signal Trace Report (Phase 3 — Signal Propagation Tracking)

---

## Objective

To verify whether ingested news propagates across system layers:

Storage → Retrieval → Prediction → Trading Signals → Execution

All observations are based on real system behavior.

---

## Test Case

Representative Input: audit_pos_001
(Same behavior observed for other injected cases)

---

## 1. Storage Verification

**Method:**
SQL query on `trading.db`

**Query:**
SELECT * FROM news WHERE news_id='audit_pos_001';

**Result:**
Record found with correct values:

* sentiment: positive
* impact_score: 0.06
* request_id matches

**Conclusion:**
✔ Data successfully stored

---

## 2. Retrieval Verification

**Method:**
API call — GET /news/audit_pos_001

**Result:**

* success: true
* Full record returned
* Data matches DB values

**Conclusion:**
✔ Data successfully retrievable

---

## 3. Prediction System Behavior

**Method:**
API call — POST /tools/predict

**Input:**
{ "symbol": "RELIANCE" }

**Result:**

* Error returned:
  "Training failed: Mixed timezones detected"

* No prediction output generated

**Conclusion:**
❌ Prediction system is non-operational
❌ Cannot evaluate or consume ingested news

---

## 4. Trading Signal Verification

**Database Checked:**
samruddhi_memory.db

**Queries:**
SELECT COUNT(*) FROM strategy_signals; → (0)
SELECT COUNT(*) FROM trades; → (0)

**Observation:**

* No signals generated
* No trades executed
* No change after news injection

**Conclusion:**
❌ No trading signal reflects ingested news

---

## 5. Execution Layer (Karan’s System)

**Observation:**

* Execution system operates on `samruddhi_memory.db`
* Ingested news stored in `trading.db`
* No shared linkage identified between systems

**Evidence:**

* No signals or trades generated
* No DB interaction observed

**Conclusion:**
❌ Execution system does not react to ingested news

---

## Signal Propagation Result

✔ Input → Storage → Retrieval

❌ Retrieval → Prediction
❌ Prediction → Execution

---

## Final Conclusion

No signal propagation exists across system layers.

System is NOT integrated.

---

## Final Statement

All findings are based on:

* API responses
* Database queries
* System behavior observation

No assumptions have been made.
