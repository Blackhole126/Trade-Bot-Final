# TASK ASSIGNMENT TEMPLATE

## ⚠️ MANDATORY: REVIEW_PACKET.md REQUIREMENT

**This template must be used for ALL task assignments in Samruddhi. The REVIEW_PACKET.md requirement is NON-NEGOTIABLE.**

---

## TASK DETAILS

**Task Title:** [Clear, specific title]

**Assigned To:** [Developer name]

**Assigned Date:** [YYYY-MM-DD]

**Due Date:** [YYYY-MM-DD]

**Priority:** [HIGH / MEDIUM / LOW]

---

## TASK DESCRIPTION

### Objective
[One paragraph: What needs to be built/fixed/changed?]

### Success Criteria
- [ ] Criterion 1 (measurable, testable)
- [ ] Criterion 2 (measurable, testable)
- [ ] Criterion 3 (measurable, testable)

### Technical Requirements
- **Entry Point:** [Which file/function to start from?]
- **Dependencies:** [What systems/services are involved?]
- **Constraints:** [Any technical limitations?]

---

## ⚠️ SUBMISSION REQUIREMENTS (NON-NEGOTIABLE)

### Mandatory Deliverables

**1. REVIEW_PACKET.md**
- **Location:** Root level of project (`/REVIEW_PACKET.md`)
- **Template:** Follow REVIEW_PACKET_TEMPLATE.md EXACTLY
- **Structure:** All 6 sections required:
  1. ENTRY POINT
  2. CORE EXECUTION FLOW (max 3 files)
  3. LIVE FLOW (real execution JSON - NO PLACEHOLDERS)
  4. WHAT WAS BUILT
  5. FAILURE CASES (minimum 3 scenarios)
  6. PROOF (executable verification commands)

**Consequences:**
- **Missing REVIEW_PACKET.md → AUTO-REJECT**
- **Placeholder JSON in LIVE FLOW → AUTO-REJECT**
- **<3 FAILURE CASES → AUTO-REJECT**
- **Missing PROOF commands → AUTO-REJECT**

### Additional Deliverables
- [ ] Code changes (committed to branch)
- [ ] Tests (if applicable)
- [ ] Documentation updates (if applicable)
- [ ] Environment variable updates (if applicable)

---

## REVIEW PROCESS

### Step 1: Developer Self-Check
Before submitting, verify:
- [ ] REVIEW_PACKET.md follows template exactly
- [ ] All 6 sections complete
- [ ] LIVE FLOW has real JSON (not placeholders)
- [ ] FAILURE CASES has minimum 3 scenarios
- [ ] PROOF commands are copy-paste executable
- [ ] All file paths are relative with line numbers

### Step 2: Automated Checks (CI/CD)
- REVIEW_PACKET.md existence check
- Section structure validation
- Basic formatting checks

### Step 3: Manual Review
**Reviewer:** [Assign reviewer name]

**Review Checklist:**
- Structure validation (30 seconds)
- Content validation (2 minutes)
- Quality validation (2 minutes)
- Integration validation (30 seconds)

**Target Review Time:** <5 minutes

### Step 4: Decision
- **APPROVED:** Merge/deploy
- **CONDITIONAL:** Fix specific issues, quick re-check
- **REJECTED:** Resubmit from scratch with correct REVIEW_PACKET.md

---

## REFERENCE DOCUMENTS

**Developer MUST read before starting:**
1. [REVIEW_PACKET_TEMPLATE.md](file:///c:/Users/Admin/Desktop/final/Trade_Bot_/REVIEW_PACKET_TEMPLATE.md) - Exact structure required
2. [REVIEW_PACKET_SAMPLE.md](file:///c:/Users/Admin/Desktop/final/Trade_Bot_/REVIEW_PACKET_SAMPLE.md) - Real example from codebase
3. [REVIEW_ENFORCEMENT.md](file:///c:/Users/Admin/Desktop/final/Trade_Bot_/REVIEW_ENFORCEMENT.md) - Rejection criteria
4. [REVIEWER_SOP.md](file:///c:/Users/Admin/Desktop/final/Trade_Bot_/REVIEWER_SOP.md) - Review process (for reviewers)
5. [REVIEW_PACKET_INTEGRATION.md](file:///c:/Users/Admin/Desktop/final/Trade_Bot_/REVIEW_PACKET_INTEGRATION.md) - System alignment

---

## ROLE-SPECIFIC REQUIREMENTS

### Backend Developers (Karan, Mohit)
**REVIEW_PACKET.md must include:**
- Full API request/response JSON in LIVE FLOW
- Database state changes (before/after)
- Log output from execution
- Error handling for all failure cases

### Frontend Developers
**REVIEW_PACKET.md must include:**
- Component rendering proof (test output, not screenshots)
- API integration test results
- State management flow (Redux/Context changes)
- Cross-browser compatibility data

### DevOps (Alay)
**REVIEW_PACKET.md must include:**
- Deployment logs
- Infrastructure state changes
- Monitoring/alerting setup
- Rollback procedure

### Data Pipeline (Mohit)
**REVIEW_PACKET.md must include:**
- Data transformation proof (input/output JSON)
- Data quality validation results
- Pipeline performance metrics
- Error recovery procedure

### Testing (Vinayak)
**REVIEW_PACKET.md must include:**
- Test execution results (pass/fail counts)
- Edge cases tested
- Performance benchmark results
- Known limitations documented

---

## TIMELINE

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Development | [X days] | Code complete, tested |
| REVIEW_PACKET.md Creation | [X hours] | REVIEW_PACKET.md at root |
| Review | <5 minutes | APPROVED/CONDITIONAL/REJECTED |
| Fixes (if conditional) | [X hours] | Updated REVIEW_PACKET.md |
| Deployment | [X hours] | Merged and deployed |

---

## ACCEPTANCE CRITERIA

**Task is considered COMPLETE when:**
1. Code is functional and tested
2. REVIEW_PACKET.md is APPROVED by reviewer
3. All team members have validated their integration points:
   - [ ] Testing (Vinayak): FAILURE CASES validated
   - [ ] DevOps (Alay): Deployment logs aligned
   - [ ] Backend (Karan): Execution flow verified
   - [ ] Data Pipeline (Mohit): JSON schema validated
4. Code is merged to main branch
5. Deployed to production (if applicable)

---

## CONSEQUENCES OF NON-COMPLIANCE

**If REVIEW_PACKET.md is missing or incomplete:**
1. **First offense:** Rejected with feedback, coaching session
2. **Second offense:** Rejected, mandatory review with Karan Bharda
3. **Third offense:** Escalated to project lead, performance discussion

**This is not punitive. This ensures system-wide reviewability and quality.**

---

## QUESTIONS?

**Before starting work:**
- Unclear requirements? → Contact task assigner
- Unsure about REVIEW_PACKET.md? → Review template + sample
- Need clarification on enforcement? → Contact Karan Bharda

**Do NOT:**
- ❌ Guess what's required
- ❌ Submit without REVIEW_PACKET.md
- ❌ Use placeholder JSON
- ❌ Assume reviewer will read your code

---

## ACKNOWLEDGMENT

**Developer must acknowledge before starting:**

- [ ] I have read REVIEW_PACKET_TEMPLATE.md
- [ ] I have read REVIEW_PACKET_SAMPLE.md
- [ ] I have read REVIEW_ENFORCEMENT.md
- [ ] I understand that missing REVIEW_PACKET.md = AUTO-REJECT
- [ ] I understand that placeholder JSON = AUTO-REJECT
- [ ] I understand that <3 failure cases = AUTO-REJECT
- [ ] I will create REVIEW_PACKET.md BEFORE submitting

**Developer:** _________________  
**Date:** _________________  
**Signature:** _________________

---

## REVIEWER ASSIGNMENT

**Reviewer:** _________________  
**Expected Review Time:** <5 minutes  
**Review Deadline:** [YYYY-MM-DD]

---

## TASK COMPLETION

**Status:** ☐ IN PROGRESS  ☐ CONDITIONAL  ☐ APPROVED  ☐ REJECTED

**Completion Date:** _________________

**Reviewer Notes:**
```
[Specific feedback, recommendations, concerns]
```

**Final Decision:** ☐ APPROVED  ☐ REJECTED

**Reviewer:** _________________  
**Date:** _________________

---

## VERSION HISTORY

| Version | Date | Changes | Approved By |
|---------|------|---------|-------------|
| 1.0 | 2026-04-23 | Initial version with mandatory REVIEW_PACKET.md requirement | Karan Bharda |

---

**This template is EFFECTIVE IMMEDIATELY. All task assignments must include the REVIEW_PACKET.md requirement.**

**No exceptions. No waivers. No "I forgot".**
