# REVIEW PACKET SYSTEM - QUICK REFERENCE

## For All Team Members

---

## DEVELOPER CHECKLIST (Before Submitting)

```
┌─────────────────────────────────────────────────────┐
│  REVIEW_PACKET.md SELF-CHECK                        │
├─────────────────────────────────────────────────────┤
│ □ 1. ENTRY POINT - File path, function, lines?      │
│ □ 2. CORE EXECUTION FLOW - Max 3 files?             │
│ □ 3. LIVE FLOW - REAL JSON (no placeholders)?       │
│ □ 4. WHAT WAS BUILT - All files listed?             │
│ □ 5. FAILURE CASES - Minimum 3 scenarios?           │
│ □ 6. PROOF - Executable commands?                   │
│                                                      │
│ CRITICAL CHECKS:                                     │
│ □ File paths are RELATIVE?                          │
│ □ Line numbers included?                            │
│ □ JSON is from ACTUAL execution?                    │
│ □ Failure cases have triggers + recovery?           │
│ □ PROOF commands copy-paste runnable?               │
│                                                      │
│ If ANY box unchecked → DO NOT SUBMIT                │
└─────────────────────────────────────────────────────┘
```

---

## REVIEWER CHECKLIST (<5 Minutes)

```
┌─────────────────────────────────────────────────────┐
│  REVIEW CHECKLIST                                   │
├─────────────────────────────────────────────────────┤
│ STEP 1: Structure (30 sec)                          │
│ □ All 6 sections present?                           │
│ → If NO → AUTO-REJECT                               │
│                                                      │
│ STEP 2: Entry Point (30 sec)                        │
│ □ Specific file path?                               │
│ □ Function name?                                    │
│ □ Line numbers?                                     │
│ → If vague → CONDITIONAL                            │
│                                                      │
│ STEP 3: Core Flow (1 min)                           │
│ □ Max 3 files?                                      │
│ □ Flow diagram present?                             │
│ → If >3 files → CONDITIONAL                         │
│                                                      │
│ STEP 4: LIVE FLOW (1 min) ⚠️ CRITICAL               │
│ □ REAL JSON (not placeholders)?                     │
│ □ Matches actual API response?                      │
│ → If placeholder → AUTO-REJECT                      │
│                                                      │
│ STEP 5: Failure Cases (1 min)                       │
│ □ Minimum 3 scenarios?                              │
│ □ Each has trigger + recovery?                      │
│ → If <3 → AUTO-REJECT                               │
│                                                      │
│ STEP 6: PROOF (1 min)                               │
│ □ Commands execute?                                 │
│ □ Test results real?                                │
│ → If fail → CONDITIONAL                             │
│                                                      │
│ DECISION:                                           │
│ ✅ All pass → APPROVED                              │
│ ⚠️ Minor issues → CONDITIONAL                       │
│ ❌ Critical issues → REJECT                         │
└─────────────────────────────────────────────────────┘
```

---

## AUTO-REJECTION TRIGGERS

```
❌ MISSING REVIEW_PACKET.md → REJECT
❌ PLACEHOLDER JSON → REJECT
❌ <3 FAILURE CASES → REJECT
❌ MISSING PROOF COMMANDS → REJECT
❌ MISSING LIVE FLOW → REJECT
```

---

## PLACEHOLDER DETECTION

### ❌ WRONG (Placeholders)
```json
{"data": "some output"}
{"message": "success"}
{"result": "example"}
{"key": "value"}
```

### ✅ CORRECT (Real Execution)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "symbol": "RELIANCE.NS",
  "prediction": "LONG",
  "confidence": 0.8234,
  "execution_time_ms": 145
}
```

---

## ROLE-SPECIFIC FOCUS

| Role | Focus Area | Time |
|------|------------|------|
| **Developer** | Create REVIEW_PACKET.md while building | During dev |
| **Vinayak** | Validate FAILURE CASES, execute PROOF | <24 hours |
| **Alay** | Align deployment logs with LIVE FLOW | <24 hours |
| **Karan** | Review code flow, architecture, security | <5 minutes |
| **Mohit** | Validate JSON schema, data integrity | <24 hours |

---

## QUICK LINKS

| Document | Purpose |
|----------|---------|
| [REVIEW_PACKET_TEMPLATE.md](REVIEW_PACKET_TEMPLATE.md) | Exact structure required |
| [REVIEW_PACKET_SAMPLE.md](REVIEW_PACKET_SAMPLE.md) | Real example to follow |
| [REVIEW_ENFORCEMENT.md](REVIEW_ENFORCEMENT.md) | Rejection criteria |
| [REVIEWER_SOP.md](REVIEWER_SOP.md) | Review process |
| [REVIEW_PACKET_INTEGRATION.md](REVIEW_PACKET_INTEGRATION.md) | Team alignment |
| [TASK_ASSIGNMENT_TEMPLATE.md](TASK_ASSIGNMENT_TEMPLATE.md) | Task assignments |

---

## CONTACT

**Questions?** → Karan Bharda  
**Disputes?** → Karan makes final decision  
**Template issues?** → Propose update to Karan

---

## REMEMBER

✅ Real data, not placeholders  
✅ Specific file paths with line numbers  
✅ 3+ failure cases minimum  
✅ Executable PROOF commands  
✅ <5 minute review target  

❌ No exceptions  
❌ No waivers  
❌ No "I forgot"  

---

**Print this and keep at your desk.**
