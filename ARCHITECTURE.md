# Trading Dashboard Architecture

## Core Principle: Backend Authority

**Frontend does not interpret backend dependency state.**

The backend is the single source of truth for:
- Data availability
- Feature calculation status
- Model training state
- Prediction readiness
- All error conditions

### Frontend Responsibilities

The frontend ONLY:
1. **Asks** - Makes API requests
2. **Waits** - Shows neutral loading states
3. **Renders** - Displays backend responses verbatim
4. **Fails** - Shows backend error messages exactly as received

### What Frontend Must NEVER Do

❌ Invent dependency errors  
❌ Explain backend workflow steps  
❌ Simulate missing dependencies  
❌ Infer what backend needs  
❌ Retry based on assumed state  
❌ Show technical step names (fetch_data, calculate_features, train_models)  

### Error Handling Policy

**Single Source of Truth:**
- If backend returns success → show results
- If backend returns error → show backend message ONLY
- If backend returns nothing → show generic failure
- NEVER synthesize domain-specific errors

**Any deviation from this is a bug.**

### Dependency Pipeline

The backend automatically handles:
1. Data fetching
2. Feature calculation
3. Model training
4. Prediction generation

Frontend calls `/tools/predict` and backend orchestrates all prerequisites silently.

### Progress Display

**Allowed:**
- Spinner
- "Analyzing..." text
- Progress bar (percentage only)

**Forbidden:**
- Step names
- Technical indicator mentions
- Model training status
- Dependency checklists

### Code Markers

Look for these comments in the codebase:
```typescript
// Frontend must not interpret backend dependency state
// Backend handles all dependency orchestration automatically
```

These mark critical boundaries that must not be crossed.

### Regression Prevention

If anyone suggests:
- "Let's show which step failed"
- "Let's help users understand backend flow"
- "Let's retry missing dependencies automatically"
- "Let's infer what backend needs"

**The answer is NO.** That's backend logic.

### Dev Invariants

The codebase includes dev-mode checks that will catch violations:
- Success state must suppress all error UI
- No synthetic dependency errors allowed
- Backend responses rendered verbatim only

---

**Last Updated:** 2024 - After Pandas 3.0 migration and frontend error purge
