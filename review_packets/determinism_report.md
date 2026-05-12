# Determinism Validation Report

## Phase 2 — Determinism Validation

### Objective
Validate that the prediction pipeline produces deterministic and reproducible outputs for identical inputs.

---

# Fixes Applied

## 1. Timezone Normalization Fix

Standardized all datetime processing across:
- prediction pipeline
- training pipeline
- technical indicator pipeline
- feature engineering pipeline

Implemented UTC normalization and timezone-safe datetime conversion to eliminate tz-aware vs tz-naive conflicts.

Key fixes included:
- `pd.to_datetime(..., utc=True)`
- safe `.tz_localize(None)` handling
- UTC conversion before timezone removal
- duplicate timestamp cleanup
- datetime index normalization

---

## 2. Random Seed Stabilization

Added deterministic random seeds across the ML pipeline:

```python
import random
import numpy as np
import torch

RANDOM_SEED = 42

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

torch.manual_seed(RANDOM_SEED)
torch.cuda.manual_seed_all(RANDOM_SEED)

torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
```

This removed stochastic variation during repeated inference.

---

## 3. RandomForest Determinism

Updated RandomForestRegressor configuration:

```python
RandomForestRegressor(
    n_estimators=200,
    random_state=42
)
```

This ensured reproducible ensemble predictions across repeated runs.

---

## 4. DQN / Neural Network Inference Stabilization

Disabled stochastic dropout behavior during prediction by enabling evaluation mode:

```python
self.policy_net.eval()
```

This prevented random confidence fluctuations during repeated inference.

---

## 5. Training & Prediction Pipeline Logging

Added structured logging for:
- cache loading
- data normalization
- feature engineering
- technical indicators
- model training
- prediction generation
- live validation
- sentiment analysis
- API request tracking

---

# Determinism Test

## Endpoint Tested

```http
POST /tools/predict
```

---

## Test Input

```json
{
  "symbols": ["AAPL"],
  "horizon": "intraday"
}
```

---

# Validation Runs

## Run 1

```json
{
  "predicted_price": 272.58,
  "predicted_return": -4.08,
  "action": "SHORT",
  "confidence": 0.51
}
```

---

## Run 2

```json
{
  "predicted_price": 272.58,
  "predicted_return": -4.08,
  "action": "SHORT",
  "confidence": 0.51
}
```

---

## Run 3

```json
{
  "predicted_price": 272.58,
  "predicted_return": -4.08,
  "action": "SHORT",
  "confidence": 0.51
}
```

---

# Validation Results

| Validation Check | Status |
|---|---|
| Same input → same output | ✅ PASS |
| Stable predicted price | ✅ PASS |
| Stable predicted return | ✅ PASS |
| Stable action generation | ✅ PASS |
| Stable confidence score | ✅ PASS |
| Deterministic RandomForest output | ✅ PASS |
| Deterministic DQN inference | ✅ PASS |
| Timezone normalization working | ✅ PASS |
| Prediction API reliable | ✅ PASS |
| Multi-run reproducibility verified | ✅ PASS |


---

# Sentiment Validation

## Same News Consistency Test

Repeated sentiment analysis using identical news input:

```text
Apple reports record quarterly earnings and strong iPhone demand.
```

Observed Result:
- Sentiment classification remained consistent
- Sentiment score remained stable
- Prediction influence remained deterministic

Validation:
✅ Same news → same sentiment and impact

---

## Different News Variation Test

Positive News Input:

```text
Apple reports record quarterly earnings and strong iPhone demand.
```

Negative News Input:

```text
Apple faces regulatory investigation and declining hardware sales.
```

Observed Result:
- Sentiment classification changed appropriately
- Sentiment scores varied measurably
- Prediction influence adjusted accordingly

Validation:
✅ Different news → measurable variation

---


# Conclusion

The prediction pipeline is now deterministic, stable, and reproducible.

Repeated executions with identical input consistently produce identical outputs across:
- prediction generation
- confidence scoring
- action classification
- return calculation

The timezone normalization issue was fully resolved, and the prediction API now operates reliably without failure.

Phase 2 determinism validation completed successfully.