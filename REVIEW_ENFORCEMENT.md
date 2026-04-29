# REVIEW_ENFORCEMENT.md

## ⚠️ NON-NEGOTIABLE REVIEW SUBMISSION SYSTEM

**This document defines the enforcement layer for Samruddhi review system. These rules are MANDATORY. No exceptions. No waivers.**

---

## 1. AUTO-REJECTION CRITERIA

**If ANY of the following conditions are met, the submission is IMMEDIATELY REJECTED without review:**

### 1.1 Missing REVIEW_PACKET.md
- **Rule:** Every task submission MUST include REVIEW_PACKET.md at root level
- **Enforcement:** Automated check in PR/commit
- **Action:** REJECT with message: "Submission rejected: REVIEW_PACKET.md missing"

### 1.2 Missing LIVE FLOW Section
- **Rule:** Section 3 (LIVE FLOW) must contain real JSON output
- **Detection:** Contains placeholders like `{"example": "data"}` or `{"key": "value"}`
- **Action:** REJECT with message: "Submission rejected: LIVE FLOW contains placeholder data"

### 1.3 Missing FAILURE CASES
- **Rule:** Section 5 must include minimum 3 failure scenarios
- **Detection:** Fewer than 3 failure cases, or contains "It works perfectly"
- **Action:** REJECT with message: "Submission rejected: FAILURE CASES incomplete (minimum 3 required)"

### 1.4 Placeholder JSON Detected
- **Rule:** All JSON must be real execution output
- **Detection:** Generic keys like "data", "message", "result" without specific values
- **Action:** REJECT with message: "Submission rejected: Contains placeholder JSON. Use real execution data."

### 1.5 Missing PROOF Section
- **Rule:** Section 6 must have executable verification commands
- **Detection:** No curl commands, no test results, or screenshots instead of commands
- **Action:** REJECT with message: "Submission rejected: PROOF section missing executable commands"

---

## 2. REJECTION CRITERIA (REVIEWER DISCRETION)

**These criteria require reviewer judgment. If triggered, reviewer MAY reject:**

### 2.1 Vague File References
- **Issue:** File paths are absolute, incomplete, or missing line numbers
- **Example:** "Check the auth file" instead of `backend/hft2/backend/hft_auth.py:94-112`
- **Action:** CONDITIONAL - Request fixes before approval

### 2.2 Exceeds 3 Core Files
- **Issue:** Section 2 (CORE EXECUTION FLOW) lists more than 3 files
- **Rule:** If more than 3 files are critical, developer failed to identify core logic
- **Action:** CONDITIONAL - Request refactoring to identify true core files

### 2.3 No Execution Flow Diagram
- **Issue:** Section 2.4 missing or incomplete
- **Rule:** Must show step-by-step flow with file:line references
- **Action:** CONDITIONAL - Request complete flow diagram

### 2.4 Incomplete WHAT WAS BUILT
- **Issue:** New/modified files not listed, or dependencies missing
- **Rule:** Must account for all changes
- **Action:** CONDITIONAL - Request complete file list

### 2.5 Performance Metrics Missing
- **Issue:** Section 6.4 missing or uses placeholder values
- **Rule:** Must include real performance data
- **Action:** CONDITIONAL - Request actual metrics

---

## 3. REVIEW CHECKLIST

**Reviewer MUST complete this checklist for EVERY submission:**

### 3.1 Structure Validation (30 seconds)
- [ ] REVIEW_PACKET.md exists at root level
- [ ] All 6 sections present (ENTRY POINT, CORE EXECUTION FLOW, LIVE FLOW, WHAT WAS BUILT, FAILURE CASES, PROOF)
- [ ] No sections marked "TODO" or "Coming Soon"

### 3.2 Content Validation (2 minutes)
- [ ] Section 1: Entry point has exact file path, function name, line numbers
- [ ] Section 2: Maximum 3 files listed with specific line ranges
- [ ] Section 3: LIVE FLOW contains real JSON (not placeholders)
- [ ] Section 4: All new/modified files listed in tables
- [ ] Section 5: Minimum 3 failure cases with triggers and responses
- [ ] Section 6: PROOF has executable curl/python commands

### 3.3 Quality Validation (2 minutes)
- [ ] File paths are relative (e.g., `backend/api_server.py`)
- [ ] Line numbers included for all code references
- [ ] JSON output matches actual API responses
- [ ] Failure cases are realistic (not "what if server explodes")
- [ ] Test results show actual pass/fail counts
- [ ] Performance metrics are real (not guessed)

### 3.4 Integration Validation (30 seconds)
- [ ] Module integrates with existing systems (documented in 6.3)
- [ ] No breaking changes undocumented
- [ ] Environment variables listed if added
- [ ] Database migrations noted if required

**Total Review Time Target: <5 minutes**

---

## 4. REVIEW DECISION MATRIX

| Condition | Decision | Action |
|-----------|----------|--------|
| All 6 sections complete, real JSON, 3+ failure cases | **APPROVED** | Merge/deploy |
| Missing REVIEW_PACKET.md | **AUTO-REJECT** | Return to developer |
| Missing LIVE FLOW or placeholder JSON | **AUTO-REJECT** | Return to developer |
| Missing FAILURE CASES (<3) | **AUTO-REJECT** | Return to developer |
| Vague file references | **CONDITIONAL** | Request fixes, re-review |
| >3 core files | **CONDITIONAL** | Request refactoring |
| Missing performance metrics | **CONDITIONAL** | Request real data |
| Incomplete integration proof | **CONDITIONAL** | Request additional tests |

---

## 5. ENFORCEMENT MECHANISMS

### 5.1 Automated Checks (CI/CD Pipeline)
```yaml
# Add to .github/workflows/review-check.yml
name: REVIEW_PACKET Validation
on: [pull_request]

jobs:
  validate-review-packet:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Check REVIEW_PACKET.md exists
        run: |
          if [ ! -f "REVIEW_PACKET.md" ]; then
            echo "::error::REVIEW_PACKET.md not found. Submission rejected."
            exit 1
          fi
      
      - name: Validate required sections
        run: |
          grep -q "## 1. ENTRY POINT" REVIEW_PACKET.md || exit 1
          grep -q "## 2. CORE EXECUTION FLOW" REVIEW_PACKET.md || exit 1
          grep -q "## 3. LIVE FLOW" REVIEW_PACKET.md || exit 1
          grep -q "## 4. WHAT WAS BUILT" REVIEW_PACKET.md || exit 1
          grep -q "## 5. FAILURE CASES" REVIEW_PACKET.md || exit 1
          grep -q "## 6. PROOF" REVIEW_PACKET.md || exit 1
```

### 5.2 Manual Review Process
1. **Developer submits PR with REVIEW_PACKET.md**
2. **CI/CD validates structure (automated)**
3. **Reviewer completes checklist (<5 minutes)**
4. **Decision: APPROVED / REJECTED / CONDITIONAL**
5. **If REJECTED:** Return to developer with specific rejection reason
6. **If CONDITIONAL:** List required fixes, developer resubmits
7. **If APPROVED:** Merge/deploy

### 5.3 Escalation Path
- **Level 1:** Developer fixes issues and resubmits
- **Level 2:** If disputed, Karan Bharda makes final decision
- **Level 3:** If systemic issue, update REVIEW_PACKET_TEMPLATE.md

---

## 6. SUBMISSION REQUIREMENTS BY ROLE

### 6.1 Backend Developers (Karan, Mohit)
- **Must include:** Full API request/response JSON
- **Must include:** Database state changes (before/after)
- **Must include:** Log output from execution
- **Must include:** Error handling for all failure cases

### 6.2 Frontend Developers
- **Must include:** Component rendering proof (not screenshots - use test output)
- **Must include:** API integration test results
- **Must include:** State management flow (Redux/Context changes)
- **Must include:** Cross-browser compatibility data

### 6.3 DevOps (Alay)
- **Must include:** Deployment logs
- **Must include:** Infrastructure state changes
- **Must include:** Monitoring/alerting setup
- **Must include:** Rollback procedure

### 6.4 Data Pipeline (Mohit)
- **Must include:** Data transformation proof (input/output JSON)
- **Must include:** Data quality validation results
- **Must include:** Pipeline performance metrics
- **Must include:** Error recovery procedure

### 6.5 Testing (Vinayak)
- **Must include:** Test execution results (pass/fail counts)
- **Must include:** Edge cases tested
- **Must include:** Performance benchmark results
- **Must include:** Known limitations documented

---

## 7. REJECTION MESSAGE TEMPLATES

**Use these exact templates for consistency:**

### 7.1 Missing REVIEW_PACKET.md
```
❌ SUBMISSION REJECTED

Reason: REVIEW_PACKET.md not found at root level.

Required Action:
1. Create REVIEW_PACKET.md following REVIEW_PACKET_TEMPLATE.md
2. Include all 6 sections with real execution data
3. Resubmit PR

Reference: REVIEW_ENFORCEMENT.md Section 1.1
```

### 7.2 Placeholder JSON Detected
```
❌ SUBMISSION REJECTED

Reason: LIVE FLOW section contains placeholder data.

Found:
{"data": "example output", "message": "success"}

Expected:
{"status_code": 200, "symbol": "RELIANCE.NS", "prediction": "LONG", "confidence": 0.8234}

Required Action:
1. Execute the module with real data
2. Capture actual JSON response
3. Replace all placeholder JSON in LIVE FLOW section
4. Resubmit PR

Reference: REVIEW_ENFORCEMENT.md Section 1.4
```

### 7.3 Incomplete FAILURE CASES
```
❌ SUBMISSION REJECTED

Reason: FAILURE CASES section has fewer than 3 scenarios.

Found: 1 failure case
Required: Minimum 3 failure cases

Required Action:
1. Add at least 2 more failure scenarios
2. Include trigger, expected behavior, actual behavior, recovery
3. Test each failure case and capture real output
4. Resubmit PR

Reference: REVIEW_ENFORCEMENT.md Section 1.3
```

---

## 8. COMPLIANCE TRACKING

### 8.1 Metrics to Track
- **Submission rejection rate:** Target <20%
- **Average review time:** Target <5 minutes
- **Resubmission rate:** Target <10%
- **Common rejection reasons:** Track for template improvements

### 8.2 Monthly Review
- Review rejection reasons
- Update template if common issues found
- Train developers on recurring mistakes
- Adjust enforcement rules if too strict/lenient

### 8.3 Accountability
- **Karan Bharda:** Enforces system across all submissions
- **Reviewers:** Must complete checklist for every submission
- **Developers:** Must follow template exactly
- **Violations:** 3 rejections = mandatory review with Karan

---

## 9. EXCEPTIONS

**NO EXCEPTIONS PERMITTED.**

This is a governance system. Exceptions undermine the entire purpose.

If a scenario truly doesn't fit the template:
1. Document why in PR description
2. Consult Karan Bharda BEFORE submission
3. If approved, update REVIEW_PACKET_TEMPLATE.md for future use

**Retroactive exceptions are NOT allowed.**

---

## 10. VERSION HISTORY

| Version | Date | Changes | Approved By |
|---------|------|---------|-------------|
| 1.0 | 2026-04-23 | Initial version | Karan Bharda |

---

**This document is EFFECTIVE IMMEDIATELY. All submissions after 2026-04-23 must comply.**

**Questions? Contact Karan Bharda. Do NOT guess. Do NOT assume.**
