# Failure Propagation Validation — Phase 3

## Test 1 — Database Failure

### Scenario
Simulated database failure by modifying DB path.

### Result
- API Response: ❌ Failure returned
- Error Message: "Database write failed. Predictions not saved."
- DB State: No new entries created
- Logs: Error logged correctly

---

## Test 2 — Invalid Input

### Scenario
Sent invalid request:
{
  "symbols": [],
  "horizon": "intraday"
}

### Result
- API Response: ❌ 422 Validation Error
- Error Message: List should have at least 1 item
- DB State: No entries created
- Logs: Validation handled at input layer

---

## Test 3 — Partial Internal Failure

### Scenario
Sent mixed symbols:
{
  "symbols": ["TCS.NS", "INVALID123"],
  "horizon": "intraday"
}

### Result
- API Response: ⚠ Partial failure
- Valid Symbol: Processed successfully
- Invalid Symbol: Returned structured error
- DB State: Only valid data processed
- Logs: Correctly reflect mixed outcome

---

## Validation Summary

| Condition | Status |
|----------|--------|
| API returns failure correctly | ✅ |
| No DB corruption | ✅ |
| Logs reflect truth | ✅ |
| No silent failures | ✅ |
| Partial failures handled safely | ✅ |

---

## Conclusion

The system reliably propagates failures across all layers.  
It ensures no data corruption, no silent failures, and maintains transparency in error handling.  
The API is safe and ready for integration with external systems.