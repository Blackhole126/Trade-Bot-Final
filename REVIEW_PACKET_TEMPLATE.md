# REVIEW_PACKET_TEMPLATE.md

## ⚠️ MANDATORY SUBMISSION REQUIREMENT
**This template is NON-NEGOTIABLE. All task submissions MUST follow this exact structure.**
**Missing any section = AUTO-REJECT. No exceptions.**

---

## 1. ENTRY POINT

### 1.1 Task Overview
- **Task Title:** [Exact title from assignment]
- **Assigned Date:** [YYYY-MM-DD]
- **Completed Date:** [YYYY-MM-DD]
- **Assigned To:** [Developer name]
- **Reviewer:** [Reviewer name]

### 1.2 System Entry Point
**File:** `relative/path/to/entry_file.ext`

**Function/Class:** `exact_function_name()`

**Line Numbers:** [start-end]

**How to Invoke:**
```bash
# Exact command to trigger this module
curl -X POST http://localhost:PORT/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

OR

```python
# Python invocation
from module import ClassName
instance = ClassName()
result = instance.method()
```

### 1.3 Dependencies
- **Requires:** [list of services, databases, APIs]
- **Environment Variables:** [list required .env vars]
- **External Systems:** [MongoDB, Yahoo Finance, Dhan API, etc.]

---

## 2. CORE EXECUTION FLOW

**⚠️ MAXIMUM 3 FILES. If more than 3 files are critical, you've failed to identify the core.**

### 2.1 Primary File
**File:** `relative/path/to/file1.ext`
**Purpose:** [One sentence: what does this file do?]
**Lines:** [critical line range]

**Key Functions:**
```python
def critical_function():
    # What it does
    # Input: X
    # Output: Y
    # Side effects: Z
```

### 2.2 Secondary File
**File:** `relative/path/to/file2.ext`
**Purpose:** [One sentence]
**Lines:** [critical line range]

**Key Functions:**
```python
# Core logic snippet (max 15 lines)
```

### 2.3 Tertiary File (if applicable)
**File:** `relative/path/to/file3.ext`
**Purpose:** [One sentence]
**Lines:** [critical line range]

### 2.4 Execution Flow Diagram
```
Entry Point
  ↓
Step 1: [function call] → File:Line
  ↓
Step 2: [data transformation] → File:Line
  ↓
Step 3: [output/result] → File:Line
  ↓
Return/Response
```

---

## 3. LIVE FLOW (REAL EXECUTION PATH + JSON)

**⚠️ THIS SECTION MUST CONTAIN ACTUAL EXECUTION OUTPUT. NO PLACEHOLDERS. NO THEORETICAL EXAMPLES.**

### 3.1 Real Request
```json
{
  "endpoint": "POST /api/actual/endpoint",
  "timestamp": "2026-04-23T14:32:10.123Z",
  "request_body": {
    "actual": "data",
    "from": "live execution"
  }
}
```

### 3.2 Real Response
```json
{
  "status_code": 200,
  "response_body": {
    "actual": "response",
    "from": "live system",
    "data": "proves it works"
  },
  "execution_time_ms": 245
}
```

### 3.3 Real Log Output
```
2026-04-23 14:32:10,123 - module.name - INFO - Actual log message from execution
2026-04-23 14:32:10,456 - module.name - INFO - Another real log line
2026-04-23 14:32:10,789 - module.name - INFO - Proves system executed
```

### 3.4 Database State Change (if applicable)
**Before:**
```json
{
  "collection": "actual_collection",
  "document_id": "12345",
  "state": "before execution"
}
```

**After:**
```json
{
  "collection": "actual_collection",
  "document_id": "12345",
  "state": "after execution",
  "changed_fields": ["field1", "field2"]
}
```

---

## 4. WHAT WAS BUILT

### 4.1 New Files Created
| File Path | Purpose | Lines |
|-----------|---------|-------|
| `relative/path/to/file1.py` | Exact purpose | 245 |
| `relative/path/to/file2.py` | Exact purpose | 180 |

### 4.2 Files Modified
| File Path | Changes Made | Lines Changed |
|-----------|--------------|---------------|
| `relative/path/to/existing.py` | Added auth validation | +45, -12 |
| `relative/path/to/config.py` | Added new config vars | +8 |

### 4.3 New Dependencies
- **Package:** `package_name==version`
- **Purpose:** Why it's needed
- **Added to:** `requirements.txt` or `package.json`

### 4.4 Architecture Impact
- **Breaking Changes:** [Yes/No - if yes, what breaks?]
- **Backward Compatible:** [Yes/No]
- **Database Migration Required:** [Yes/No]
- **Environment Variables Added:** [list them]

---

## 5. FAILURE CASES

**⚠️ MUST INCLUDE MINIMUM 3 FAILURE SCENARIOS. "It works" is not acceptable.**

### 5.1 Failure Case 1: [Descriptive Name]
**Trigger:** [What causes this failure?]

**Expected Behavior:**
```json
{
  "status_code": 400,
  "error": "Expected error message",
  "handling": "How system responds"
}
```

**Actual Behavior:**
```json
{
  "status_code": 400,
  "error": "Actual error from live test",
  "logged_to": "path/to/error.log"
}
```

**Recovery:** [How does system recover? Manual intervention required?]

### 5.2 Failure Case 2: [Descriptive Name]
**Trigger:** [What causes this?]

**Expected Behavior:**
```json
{
  "status_code": 503,
  "error": "Service unavailable"
}
```

**Actual Behavior:**
```json
{
  "status_code": 503,
  "error": "Actual error from test"
}
```

**Recovery:** [Recovery mechanism]

### 5.3 Failure Case 3: [Descriptive Name]
**Trigger:** [Edge case, timeout, invalid data, etc.]

**System State After Failure:**
- Data integrity: [Maintained/Corrupted]
- Partial writes: [Yes/No]
- Rollback: [Automatic/Manual/None]

---

## 6. PROOF

**⚠️ PROOF MUST BE EXECUTABLE AND VERIFIABLE. SCREENSHOTS ARE NOT ACCEPTABLE.**

### 6.1 Verification Commands
```bash
# Command 1: Prove it works
curl http://localhost:8000/api/endpoint
# Expected: 200 OK with actual data

# Command 2: Prove error handling
curl http://localhost:8000/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}'
# Expected: 400 with validation error

# Command 3: Prove edge case handling
curl http://localhost:8000/api/endpoint?param=extreme_value
# Expected: Graceful handling
```

### 6.2 Test Results
```
======================================
TEST RESULTS - [Date]
======================================

✓ Test 1: Core functionality
  - Input: X
  - Output: Y
  - Status: PASS

✓ Test 2: Error handling
  - Input: Invalid data
  - Output: Proper error response
  - Status: PASS

✓ Test 3: Edge case
  - Input: Boundary value
  - Output: Handled gracefully
  - Status: PASS

✗ Test 4: Known limitation
  - Issue: [Documented limitation]
  - Workaround: [If any]
  - Status: FAIL (ACCEPTED)

Total: 3/4 PASS, 1/4 FAIL (ACCEPTED)
```

### 6.3 Integration Proof
**Proves this module works with:**
- [ ] System A: [endpoint/test that proves integration]
- [ ] System B: [endpoint/test that proves integration]
- [ ] Database: [query that proves data persistence]

### 6.4 Performance Metrics
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Response Time | 245ms | <500ms | ✓ PASS |
| Memory Usage | 120MB | <256MB | ✓ PASS |
| Throughput | 50 req/s | >20 req/s | ✓ PASS |

---

## REVIEWER CHECKLIST

**To be completed by reviewer before approval:**

- [ ] ENTRY POINT clearly identifies how to invoke the module
- [ ] CORE EXECUTION FLOW uses maximum 3 files
- [ ] LIVE FLOW contains actual JSON output (not placeholders)
- [ ] WHAT WAS BUILT lists all new/modified files
- [ ] FAILURE CASES includes minimum 3 scenarios
- [ ] PROOF section has executable verification commands
- [ ] All file paths are relative and correct
- [ ] No theoretical examples - only real execution data
- [ ] System is reviewable without reading full repo

**Reviewer Decision:**
- [ ] **APPROVED** - Meets all standards
- [ ] **REJECTED** - Missing critical sections (specify which)
- [ ] **CONDITIONAL** - Minor fixes required (list them)

**Reviewer Notes:**
```
[Specific feedback for developer]
```

**Reviewer:** _________________  
**Date:** _________________  
**Time Spent on Review:** _________________ (target: <5 minutes)

---

## ⚠️ STRICT FORMATTING RULES

1. **File Paths:** Always relative to project root (e.g., `backend/api_server.py`, NOT `/absolute/path`)
2. **Line Numbers:** Always include for code references (e.g., `Lines: 145-180`)
3. **JSON Output:** Must be real execution data, NEVER placeholders like `{"example": "data"}`
4. **Code Snippets:** Maximum 15 lines per snippet. Highlight only critical logic.
5. **Failure Cases:** Minimum 3. "It works perfectly" is NOT a failure case.
6. **Proof:** Must be copy-paste executable. No screenshots. No "trust me" statements.
7. **Tables:** Use markdown tables for structured data (files, metrics, etc.)
8. **Timestamps:** ISO 8601 format (YYYY-MM-DDTHH:MM:SS.sssZ)
9. **Status Codes:** Use actual HTTP status codes (200, 400, 401, 500, 503, etc.)
10. **Rejection Criteria:** Missing LIVE FLOW, missing FAILURE CASES, or placeholder JSON = AUTO-REJECT

---

## EXAMPLE PLACEHOLDERS (FOR REFERENCE ONLY)

### ✅ CORRECT: Real Execution Data
```json
{
  "status_code": 200,
  "symbol": "RELIANCE.NS",
  "prediction": "LONG",
  "confidence": 0.8234,
  "timestamp": "2026-04-23T14:32:10.123Z"
}
```

### ❌ WRONG: Placeholder/Theoretical Data
```json
{
  "status_code": 200,
  "data": "some data here",
  "message": "success"
}
```

### ✅ CORRECT: Specific File Reference
**File:** `backend/core/mcp_adapter.py`  
**Function:** `predict()`  
**Lines:** 120-280  
**Purpose:** Orchestrates ML prediction pipeline with live price validation

### ❌ WRONG: Vague Reference
**File:** `some_file.py`  
**Function:** `do_stuff()`  
**Purpose:** Does the main thing

---

## SUBMISSION CHECKLIST (DEVELOPER)

Before submitting, verify:
- [ ] All 6 sections present and complete
- [ ] LIVE FLOW contains real JSON output
- [ ] FAILURE CASES has minimum 3 scenarios
- [ ] PROOF commands are copy-paste executable
- [ ] All file paths are relative
- [ ] No placeholder data anywhere
- [ ] Review can be completed in <5 minutes

**If any checkbox is unchecked, DO NOT SUBMIT. Fix it first.**
