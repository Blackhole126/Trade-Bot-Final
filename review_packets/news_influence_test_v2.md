````md
# news_influence_test.md

# PHASE 4 — SAMACHAR → PREDICTION LINK

## Objective

Validate that:

1. Prediction pipeline consumes ingested news
2. News sentiment affects prediction output
3. Output differs between:
   - Positive news
   - Negative news
   - No news

---

# SYSTEM FLOW VERIFIED

Swagger Request
→ FastAPI `/tools/predict`
→ MCP Adapter
→ `predict_stock_price()`
→ `compute_news_sentiment()`
→ Sentiment Multiplier Applied
→ Final Prediction Generated

---

# TEST 1 — NO NEWS

## Request

```json
{
  "symbol": "AAPL",
  "horizon": "short"
}
````

## Response

```json
{
  "success": true,
  "data": {
    "predictions": [
      {
        "symbol": "AAPL",
        "status": "success",
        "current_price": 287.5299987792969,
        "predicted_price": 268.61,
        "predicted_return": -6.58,
        "action": "SHORT",
        "confidence": 0.737,
        "error": null
      }
    ]
  },
  "error": null,
  "request_id": "predict_1778134251_4f5bdf"
}
```

## Logs

```text
[INFO] News sentiment score: 0.0000
[NEWS IMPACT] Multiplier Applied: 1.00
```

---

# TEST 2 — POSITIVE NEWS

## Request

```json
{
  "symbol": "AAPL",
  "horizon": "short",
  "news_data": [
    {
      "title": "Apple reports record quarterly earnings",
      "content": "iPhone sales surged globally. Analysts upgraded AAPL outlook with strong AI expansion expectations.",
      "sentiment": 1
    }
  ]
}
```

## Response

```json
{
  "success": true,
  "data": {
    "predictions": [
      {
        "symbol": "AAPL",
        "status": "success",
        "current_price": 287.5299987792969,
        "predicted_price": 273.98,
        "predicted_return": -4.71,
        "action": "SHORT",
        "confidence": 0.7455,
        "error": null
      }
    ]
  },
  "error": null,
  "request_id": "predict_1778134004_8d0419"
}
```

## Logs

```text
[DEBUG] Incoming news_data:
[{'title': 'Apple reports record quarterly earnings', ...}]

[INFO] News sentiment score: 1.0000
[NEWS IMPACT] Multiplier Applied: 1.02
[NEWS IMPACT] Final Prediction: 273.98
```

---

# TEST 3 — NEGATIVE NEWS

## Request

```json
{
  "symbol": "AAPL",
  "horizon": "short",
  "news_data": [
    {
      "title": "Apple faces major lawsuit",
      "content": "Revenue growth slowed sharply. Analysts warn of declining iPhone demand and weak guidance.",
      "sentiment": -1
    }
  ]
}
```

## Response

```json
{
  "success": true,
  "data": {
    "predictions": [
      {
        "symbol": "AAPL",
        "status": "success",
        "current_price": 287.5299987792969,
        "predicted_price": 263.24,
        "predicted_return": -8.45,
        "action": "SHORT",
        "confidence": 0.7264,
        "error": null
      }
    ]
  },
  "error": null,
  "request_id": "predict_1778134156_3ec8a1"
}
```

## Logs

```text
[DEBUG] Incoming news_data:
[{'title': 'Apple faces major lawsuit', ...}]

[INFO] News sentiment score: -1.0000
[NEWS IMPACT] Multiplier Applied: 0.98
[NEWS IMPACT] Final Prediction: 263.24
```

---

# VALIDATION RESULTS

| Scenario      | Sentiment | Multiplier | Predicted Price | Predicted Return | Confidence |
| ------------- | --------- | ---------- | --------------- | ---------------- | ---------- |
| Positive News | 1.0       | 1.02       | 273.98          | -4.71%           | 0.7455     |
| No News       | 0.0       | 1.00       | 268.61          | -6.58%           | 0.7370     |
| Negative News | -1.0      | 0.98       | 263.24          | -8.45%           | 0.7264     |

---

# CONCLUSION

Phase 4 validation successful.

Verified:

* Prediction pipeline consumes ingested news
* Sentiment engine processes incoming news
* Sentiment affects prediction output
* Different news inputs produce measurable prediction variation
* End-to-end Samachar → Prediction integration operational

STATUS: COMPLETE

```
```
