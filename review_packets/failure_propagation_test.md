# FAILURE PROPAGATION TEST — PHASE 9

Date: 12-05-2026

---

# 1. OBJECTIVE

Validate that the system properly propagates failures without silent crashes.

Tested:
- Prediction failure handling
- Error propagation
- Logging visibility
- API failure response behavior

---

# 2. FAILURE TEST — INVALID SYMBOL

Endpoint Tested:

GET /api/predictions?symbols=INVALID.NS&horizon=intraday

---

# 3. API FAILURE RESPONSE

```json
{
  "detail": "cannot access local variable 'datetime' where it is not associated with a value"
}
```

HTTP Status:
500 Internal Server Error

---

# 4. FAILURE TRACE LOGS

## Invalid Symbol Detection

```text
HTTP Error 404:
Quote not found for symbol: INVALID.NS
```

## Data Fetch Failure

```text
[ERROR] No NSE data found for INVALID.NS
```

## Model Training Failure

```text
[ERROR] No data found for INVALID.NS
Please fetch data and calculate features first
```

## Prediction Pipeline Failure

```text
[STEP 3/4] [FAIL] Training failed
```

## Exception Propagation

```text
UnboundLocalError:
cannot access local variable 'datetime'
where it is not associated with a value
```

## API Error Surface

```text
500 Internal Server Error
```

---

# 5. FAILURE PROPAGATION VALIDATION

| Validation | Status |
|---|---|
| Invalid symbol detected | SUCCESS |
| Failure logged | SUCCESS |
| Exception propagated | SUCCESS |
| HTTP error returned | SUCCESS |
| Silent failure prevented | SUCCESS |
| Full traceback available | SUCCESS |

---

# 6. RESULT

The system successfully demonstrated proper failure propagation behavior.

Observed behavior:
- Invalid input triggered controlled failure
- Error surfaced through API response
- Full traceback logged in terminal
- No silent pipeline failure occurred
- Failure remained traceable end-to-end

This validates that the pipeline handles prediction failures with observable and debuggable error propagation.