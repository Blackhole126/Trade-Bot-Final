# Samachar → Samruddhi News Ingestion Contract

## Endpoint
POST /news/ingest

---

## Purpose
Defines the contract for ingesting news data from the Samachar system into the Samruddhi system.  
Ensures structured processing, storage, and compatibility with downstream systems including execution and knowledge layers.

---

## Input Schema (Samachar → Samruddhi)

```json
{
  "news_id": "string",
  "title": "string",
  "content": "string",
  "source": "string",
  "timestamp": "ISO8601 string",
  "metadata": {
    "category": "string",
    "region": "string"
  }
}
````

### Field Description

| Field             | Type   | Description                           |
| ----------------- | ------ | ------------------------------------- |
| news_id           | string | Unique identifier for the news item   |
| title             | string | Headline of the news                  |
| content           | string | Full textual content                  |
| source            | string | Origin (e.g., Economic Times)         |
| timestamp         | string | ISO8601 formatted timestamp           |
| metadata.category | string | News category (e.g., finance, policy) |
| metadata.region   | string | Geographic relevance                  |

---

## Output Schema (Samruddhi Response)

```json
{
  "success": true,
  "data": {
    "sentiment": "positive | negative | neutral",
    "impact_score": 0.0,
    "tags": []
  },
  "error": null,
  "timestamp": "ISO8601",
  "request_id": "news_xxx"
}
```

### Field Description

| Field        | Type        | Description                                  |
| ------------ | ----------- | -------------------------------------------- |
| success      | boolean     | Indicates processing success                 |
| sentiment    | string      | Derived sentiment from content               |
| impact_score | float       | Normalized score (0–1) indicating importance |
| tags         | array       | Extracted contextual tags                    |
| error        | string/null | Error message if failure occurs              |
| timestamp    | string      | Response generation time                     |
| request_id   | string      | Unique request trace identifier              |

---

## Processing Logic

* **Sentiment Analysis**

  * Positive → keywords like "growth", "profit"
  * Negative → keywords like "loss", "decline"
  * Neutral → otherwise

* **Impact Score**

  * Based on content length (normalized between 0–1)

* **Tag Extraction**

  * Keyword-based tagging (e.g., "market", "policy")

---

## Data Storage

All ingested news is stored in the `news` table with the following structure:

* news_id
* title
* content
* source
* timestamp
* category
* region
* sentiment
* impact_score
* tags
* request_id

### Guarantees

* Each request generates a unique `request_id`
* No partial or corrupt writes
* Deterministic storage for identical inputs

---

## Retrieval

### Endpoint

GET /news/{news_id}

### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "news_id": "...",
    "title": "...",
    "content": "...",
    "source": "...",
    "timestamp": "...",
    "category": "...",
    "region": "...",
    "sentiment": "...",
    "impact_score": 0.0,
    "tags": "...",
    "request_id": "..."
  }
}
```

---

## Determinism

* Same input → same sentiment, tags, and structure
* No randomness in schema
* Controlled variance only in request_id and timestamp

---

## Error Handling

| Scenario               | Behavior                     |
| ---------------------- | ---------------------------- |
| Missing required field | Returns error with message   |
| Invalid input          | Request rejected             |
| Internal failure       | Safe error response returned |
| DB failure             | No partial data written      |

---

## Cross-Layer Compatibility

The system ensures compatibility with downstream components:

### Execution Layer

* Sentiment and impact_score can be used for trading signals

### Knowledge Layer

* Structured JSON enables ML models and analytics
* Tags and metadata support filtering and categorization
* Content preserved for advanced NLP processing

---

## Validation Summary

| Requirement                | Status |
| -------------------------- | ------ |
| Stored in DB               | ✅      |
| Available for retrieval    | ✅      |
| Deterministic output       | ✅      |
| Failure-safe behavior      | ✅      |
| Knowledge-layer compatible | ✅      |

---

## Conclusion

The Samachar ingestion contract ensures reliable, deterministic, and structured integration of news data into the Samruddhi system.
It guarantees data integrity, traceability, and readiness for execution and knowledge-layer consumption.

```
