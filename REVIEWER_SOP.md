# REVIEWER_SOP.md

## Standard Operating Procedure for Reviewing Submissions

**Goal: Complete any submission review in under 5 minutes with deterministic results.**

---

## 1. PRE-REVIEW SETUP (30 seconds)

### 1.1 Required Documents
Before starting review, ensure you have:
- [ ] REVIEW_PACKET.md (submitted by developer)
- [ ] REVIEW_PACKET_TEMPLATE.md (reference for required structure)
- [ ] REVIEW_ENFORCEMENT.md (rejection criteria)
- [ ] This SOP document

### 1.2 Review Environment
- Open REVIEW_PACKET.md in split-screen with template
- Have terminal ready to execute PROOF commands
- Keep REJECTION MESSAGE TEMPLATES accessible

---

## 2. REVIEW PROCESS (4 minutes 30 seconds)

### Step 1: Structure Validation (30 seconds)

**What to check:**
```
Open REVIEW_PACKET.md
↓
Scan for 6 section headers:
  ✓ 1. ENTRY POINT
  ✓ 2. CORE EXECUTION FLOW
  ✓ 3. LIVE FLOW
  ✓ 4. WHAT WAS BUILT
  ✓ 5. FAILURE CASES
  ✓ 6. PROOF
↓
If ANY missing → AUTO-REJECT immediately
```

**Decision:**
- All 6 present → Continue to Step 2
- Any missing → Stop, send rejection message (Section 4.1)

### Step 2: Entry Point Validation (30 seconds)

**What to check in Section 1:**
- File path is relative (e.g., `backend/api_server.py`)
- Function/class name is specific (e.g., `auth_login()`)
- Line numbers included (e.g., `Lines: 4619-4668`)
- Invocation command is copy-paste executable

**Red flags:**
- ❌ Absolute paths (`/Users/name/project/file.py`)
- ❌ Vague references ("check the auth file")
- ❌ Missing line numbers
- ❌ No invocation command

**Decision:**
- All specific → Continue to Step 3
- Vague/incomplete → CONDITIONAL, request fixes (Section 4.2)

### Step 3: Core Execution Flow (1 minute)

**What to check in Section 2:**
- Maximum 3 files listed (NOT 4, NOT 5)
- Each file has:
  - Relative path
  - One-sentence purpose
  - Line range
  - Key function snippet (max 15 lines)
- Execution flow diagram present

**Red flags:**
- ❌ More than 3 files (developer didn't identify core)
- ❌ Code snippets >15 lines (too verbose)
- ❌ No flow diagram
- ❌ Flow doesn't match file references

**Quick validation:**
```bash
# Spot-check one file reference
head -n 4668 backend/hft2/backend/web_backend.py | tail -n 50
# Does the actual code match what's documented?
```

**Decision:**
- Clear, concise, accurate → Continue to Step 4
- Issues found → CONDITIONAL, request fixes (Section 4.2)

### Step 4: LIVE FLOW Validation (1 minute) **CRITICAL**

**What to check in Section 3:**
- JSON contains REAL execution data (not placeholders)
- Request matches actual API format
- Response matches actual API response
- Log output looks authentic (timestamps, log levels)
- If database changes: before/after state documented

**How to detect placeholders:**
```
❌ PLACEHOLDER INDICATORS:
- {"data": "some data"}
- {"message": "success"}
- {"result": "output here"}
- {"key": "value"}
- Timestamps like "2024-01-01T00:00:00"

✅ REAL DATA INDICATORS:
- {"access_token": "eyJhbGciOiJIUzI1NiIs..."}
- {"symbol": "RELIANCE.NS", "prediction": "LONG"}
- {"status_code": 200, "execution_time_ms": 145}
- Timestamps like "2026-04-23T14:32:10.123Z"
```

**Quick validation:**
```bash
# Execute the documented request
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "secure123"}'

# Does response match documented JSON?
# If yes → LIVE FLOW is real
# If no → REJECT immediately
```

**Decision:**
- Real JSON, matches execution → Continue to Step 5
- Placeholder detected → AUTO-REJECT (Section 4.1)

### Step 5: Failure Cases Validation (1 minute)

**What to check in Section 5:**
- Minimum 3 failure cases (NOT 2, NOT 4+)
- Each has:
  - Trigger (what causes failure)
  - Expected behavior (what should happen)
  - Actual behavior (what actually happens)
  - Recovery (how to recover)

**Quality check:**
```
❌ WEAK FAILURE CASES:
- "Server crashes" (too generic)
- "User enters wrong data" (not specific)
- "Network fails" (no recovery documented)

✅ STRONG FAILURE CASES:
- "MongoDB connection refused during login"
  → Trigger: MongoDB service stopped
  → Expected: 503 error
  → Actual: 503 "Database temporarily unavailable"
  → Recovery: Restart MongoDB, client retries
```

**Quick validation:**
```bash
# Test one failure case
# Stop MongoDB, then run documented command
# Does system fail as documented?
```

**Decision:**
- 3+ strong failure cases → Continue to Step 6
- <3 cases or weak cases → CONDITIONAL or REJECT

### Step 6: PROOF Validation (1 minute)

**What to check in Section 6:**
- Verification commands are copy-paste executable
- Test results show actual pass/fail counts
- Integration proof lists specific systems
- Performance metrics have real values

**Quick validation:**
```bash
# Copy-paste ONE verification command from PROOF section
curl http://localhost:8000/api/endpoint

# Does it work as documented?
# If yes → PROOF is valid
# If no → CONDITIONAL, request fixes
```

**Check test results:**
```
❌ WEAK: "All tests passed"
✅ STRONG: "5/6 PASS, 1/6 FAIL (ACCEPTED)"
           with specific test names and outcomes
```

**Decision:**
- Executable commands, real results → APPROVED
- Commands fail or results vague → CONDITIONAL

---

## 3. REVIEW DECISION (30 seconds)

### 3.1 APPROVED
**Criteria:**
- All 6 sections complete
- LIVE FLOW has real JSON
- 3+ failure cases with real output
- PROOF commands execute successfully
- No red flags detected

**Action:**
- Check all boxes in REVIEW_PACKET.md checklist
- Add reviewer notes (specific feedback)
- Sign with name and date
- Approve PR/merge

### 3.2 CONDITIONAL
**Criteria:**
- Minor issues that don't invalidate submission
- Examples: vague file refs, missing metrics, incomplete flow diagram

**Action:**
- Check boxes for sections that pass
- List specific fixes required in reviewer notes
- Return to developer with CONDITIONAL status
- Developer fixes and resubmits (no full re-review needed)

### 3.3 REJECTED
**Criteria:**
- Missing REVIEW_PACKET.md
- Placeholder JSON in LIVE FLOW
- <3 failure cases
- PROOF commands fail completely

**Action:**
- Use rejection message template (Section 4)
- Do NOT check any boxes
- Return to developer with REJECTED status
- Developer must resubmit from scratch

---

## 4. REJECTION MESSAGE TEMPLATES

### 4.1 Auto-Rejection (Critical Issues)

```
❌ SUBMISSION REJECTED - AUTO-REJECT

[CHOOSE ONE:]
□ REVIEW_PACKET.md not found
□ LIVE FLOW contains placeholder JSON
□ FAILURE CASES has fewer than 3 scenarios
□ PROOF section missing executable commands

Required Action:
1. Review REVIEW_PACKET_TEMPLATE.md
2. Fix the issue identified above
3. Ensure all JSON is real execution data
4. Resubmit PR

Reference: REVIEW_ENFORCEMENT.md Section 1.x
```

### 4.2 Conditional Rejection (Fixable Issues)

```
⚠️ SUBMISSION CONDITIONAL - Fixes Required

Issues found:
1. [Specific issue, e.g., "File reference missing line numbers in Section 2.1"]
2. [Specific issue, e.g., "Performance metrics table empty in Section 6.4"]
3. [Specific issue, e.g., "Failure case 2 recovery mechanism not documented"]

Required Fixes:
1. [Exact fix, e.g., "Add line numbers: backend/auth.py:23-112"]
2. [Exact fix, e.g., "Run performance test, fill table with real data"]
3. [Exact fix, e.g., "Document recovery: 'Restart service, no data loss'"]

Once fixed:
- No need to resubmit full PR
- Reply to this review with fixes applied
- I'll do quick re-check (<2 minutes)

Reference: REVIEW_ENFORCEMENT.md Section 2.x
```

### 4.3 Approval

```
✅ SUBMISSION APPROVED

Strengths:
- [What was done well, e.g., "Clear execution flow with accurate file references"]
- [What was done well, e.g., "Comprehensive failure cases with real output"]

Recommendations (optional):
- [Future improvement, e.g., "Consider adding refresh token mechanism"]
- [Future improvement, e.g., "Add rate limiting metrics to PROOF section"]

Review time: 4 minutes 12 seconds
```

---

## 5. COMMON WEAK SUBMISSION PATTERNS

### 5.1 The "It Works" Submission
**Symptom:** "Everything works perfectly, no failures"
**Reality:** Developer didn't test failure cases
**Action:** REJECT - require 3 failure scenarios

### 5.2 The "Trust Me" Submission
**Symptom:** PROOF section has screenshots but no commands
**Reality:** Commands might not work
**Action:** CONDITIONAL - require executable commands

### 5.3 The "Theoretical" Submission
**Symptom:** LIVE FLOW has `{"example": "data"}`
**Reality:** Developer didn't actually run the code
**Action:** REJECT - require real execution output

### 5.4 The "Everything Changed" Submission
**Symptom:** Section 2 lists 8+ core files
**Reality:** Developer can't identify what's actually core
**Action:** CONDITIONAL - require refactoring to max 3 files

### 5.5 The "Vague References" Submission
**Symptom:** "Check the auth module" with no file path
**Reality:** Reviewer must hunt through repo
**Action:** CONDITIONAL - require specific file:line references

---

## 6. REVIEW TIME TRACKING

**Track your review times to identify process improvements:**

| Submission | Developer | Time | Decision | Notes |
|------------|-----------|------|----------|-------|
| Auth Module | Backend Team | 4m 32s | APPROVED | Excellent LIVE FLOW |
| Payment API | Dev 2 | 6m 15s | CONDITIONAL | Missing failure case 3 |
| UI Component | Dev 3 | 2m 45s | REJECTED | Placeholder JSON |

**Target metrics:**
- Average review time: <5 minutes
- Approval rate: >60%
- Conditional rate: <30%
- Rejection rate: <10%

If rejection rate >20%:
- Developers not following template
- Schedule training session
- Review template clarity

---

## 7. ESCALATION PATH

### Level 1: Developer Fixes
- Reviewer returns submission with specific feedback
- Developer fixes and resubmits
- Reviewer does quick re-check (<2 minutes)

### Level 2: Karan Bharda Decision
- Developer disputes rejection
- Reviewer and developer can't agree
- Karan makes final decision (binding)

### Level 3: Template Update
- Systemic issue found (many submissions fail same way)
- Template is unclear or missing guidance
- Update REVIEW_PACKET_TEMPLATE.md
- Communicate changes to all developers

---

## 8. REVIEWER BEST PRACTICES

### Do:
- ✅ Copy-paste PROOF commands to verify they work
- ✅ Spot-check file references against actual code
- ✅ Look for placeholder JSON patterns
- ✅ Use rejection message templates for consistency
- ✅ Track review times for process improvement
- ✅ Give specific, actionable feedback

### Don't:
- ❌ Accept "it works" as a failure case
- ❌ Approve submissions with placeholder JSON
- ❌ Spend >10 minutes on one review (something's wrong)
- ❌ Make exceptions to enforcement rules
- ❌ Accept screenshots as PROOF
- ❌ Approve vague file references

---

## 9. QUICK REFERENCE CARD

**Print this and keep at your desk:**

```
┌─────────────────────────────────────────────┐
│         REVIEW CHECKLIST (<5 MIN)           │
├─────────────────────────────────────────────┤
│ □ 6 sections present?                       │
│ □ File paths relative + line numbers?       │
│ □ Max 3 core files?                         │
│ □ LIVE FLOW has real JSON? (NO PLACEHOLDERS)│
│ □ 3+ failure cases with triggers?           │
│ □ PROOF commands execute?                   │
│                                             │
│ DECISION:                                   │
│ ✅ All pass → APPROVED                      │
│ ⚠️ Minor issues → CONDITIONAL               │
│ ❌ Critical issues → REJECT                 │
└─────────────────────────────────────────────┘
```

---

**This SOP is EFFECTIVE IMMEDIATELY. All reviewers must follow this process.**

**Questions? Contact Karan Bharda before proceeding.**
