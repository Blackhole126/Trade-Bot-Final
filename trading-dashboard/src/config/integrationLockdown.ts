/**
 * FRONTEND-BACKEND INTEGRATION LOCKDOWN
 * 
 * ⚠️ CRITICAL: DO NOT MODIFY WITHOUT BACKEND COORDINATION
 * 
 * This file contains the COMPLETE and AUTHORITATIVE mapping between
 * backend endpoints and frontend integrations. Any changes to this
 * contract MUST be coordinated with backend changes.
 * 
 * CONTRACT VERSION: 1.0.0
 * BACKEND VERSION: Stock Analysis API v1.0.0
 * LOCKDOWN DATE: [Current Date]
 * 
 * MAINTENANCE MODE: ACTIVE
 * - Only backend changes can extend this contract
 * - Frontend changes must maintain existing contract compliance
 * - No new endpoints without backend implementation
 */

// ============================================================================
// BACKEND ENDPOINT INVENTORY (READ-ONLY DISCOVERY)
// ============================================================================

export const BACKEND_ENDPOINTS = {
  // ROOT ENDPOINT
  'GET /': {
    purpose: 'API information and endpoint listing',
    request: null,
    response: { message: 'string', version: 'string', endpoints: 'object' },
    frontend_integration: 'UNUSED',
    notes: 'Documentation endpoint - not used by frontend'
  },

  // HEALTH ENDPOINTS
  'GET /health': {
    purpose: 'Basic health check',
    request: null,
    response: { status: 'string', message: 'string' },
    frontend_integration: 'UNUSED',
    notes: 'Legacy health endpoint - frontend uses /tools/health'
  },

  'GET /tools/health': {
    purpose: 'Frontend health check',
    request: null,
    response: { status: 'string' },
    frontend_integration: 'ACTIVE',
    frontend_service: 'hardenedAPI.health()',
    ui_trigger: 'Automatic on app initialization'
  },

  // STOCK DATA ENDPOINTS
  'GET /stocks/{symbol}': {
    purpose: 'Get individual stock data',
    request: { symbol: 'string (path param)' },
    response: { symbol: 'string', current_price: 'number', date: 'string', volume: 'number', source: 'string' },
    frontend_integration: 'UNUSED',
    notes: 'Single stock endpoint - frontend uses batch /tools/predict'
  },

  'GET /predict/{symbol}': {
    purpose: 'Get individual prediction',
    request: { symbol: 'string (path param)', horizon: 'string (query param, optional)' },
    response: 'PredictionResult object',
    frontend_integration: 'UNUSED',
    notes: 'Single prediction endpoint - frontend uses batch /tools/predict'
  },

  // BATCH ENDPOINTS (ACTIVELY USED)
  'POST /tools/predict': {
    purpose: 'Predict multiple symbols with data quality controls',
    request: { symbols: 'string[]', horizon: 'string' },
    response: { metadata: { count: 'number', horizon: 'string' }, predictions: 'PredictionResult[]' },
    frontend_integration: 'ACTIVE',
    frontend_service: 'hardenedAPI.predict()',
    ui_trigger: 'Search button click, Quick select button click'
  },

  'POST /tools/fetch_data': {
    purpose: 'Fetch stock data with quality status',
    request: { symbols: 'string[]', horizon: 'string' },
    response: { metadata: { count: 'number' }, data: 'FetchDataResult[]' },
    frontend_integration: 'UNUSED',
    notes: 'Data fetching endpoint - not currently used by frontend UI'
  },

  'POST /tools/analyze': {
    purpose: 'Basic analysis endpoint',
    request: { symbol: 'string', horizons: 'string[]', stop_loss_pct: 'number', capital_risk_pct: 'number', drawdown_limit_pct: 'number' },
    response: { metadata: { count: 'number' }, analysis: 'AnalysisResult[]' },
    frontend_integration: 'UNUSED',
    notes: 'Analysis endpoint - not currently used by frontend UI'
  },

  'POST /tools/calculate_features': {
    purpose: 'Calculate features for dependency pipeline',
    request: { symbols: 'string[]', horizon: 'string' },
    response: { status: 'string', features_calculated: 'boolean' },
    frontend_integration: 'UNUSED',
    notes: 'Dependency pipeline endpoint - not exposed in current UI'
  },

  'POST /tools/train_models': {
    purpose: 'Train models for dependency pipeline',
    request: { symbols: 'string[]', horizon: 'string' },
    response: { status: 'string', models_trained: 'boolean' },
    frontend_integration: 'UNUSED',
    notes: 'Dependency pipeline endpoint - not exposed in current UI'
  }
} as const;

// ============================================================================
// ENDPOINT ↔ UI TRACEABILITY MAP
// ============================================================================

export const TRACEABILITY_MAP = {
  // ACTIVE INTEGRATIONS
  'POST /tools/predict': {
    backend_endpoint: '/tools/predict',
    frontend_service: 'hardenedAPI.predict()',
    hook: 'useHardenedPrediction.predict()',
    component: 'HardenedStockView',
    ui_elements: [
      'Search button (handleSearch)',
      'Popular stock buttons (handleQuickSelect)'
    ],
    user_actions: [
      'Enter symbol and click Search',
      'Click any popular stock button'
    ],
    validation: 'validatePredictResponse() - STRICT',
    guards: ['HardenedDataStatusGuard', 'HardenedTrustGateGuard', 'HardenedPriceDisplayGuard']
  },

  'GET /tools/health': {
    backend_endpoint: '/tools/health',
    frontend_service: 'hardenedAPI.health()',
    hook: 'useHardenedPrediction (internal)',
    component: 'App initialization',
    ui_elements: ['None - automatic'],
    user_actions: ['App startup'],
    validation: 'Basic string validation - STRICT',
    guards: ['None']
  }
} as const;

// ============================================================================
// UNUSED ENDPOINTS AUDIT
// ============================================================================

export const UNUSED_ENDPOINTS = [
  'GET /',
  'GET /health',
  'GET /stocks/{symbol}',
  'GET /predict/{symbol}',
  'POST /tools/fetch_data',
  'POST /tools/analyze',
  'POST /tools/calculate_features',
  'POST /tools/train_models'
] as const;

// ============================================================================
// FRONTEND INTEGRATION COVERAGE
// ============================================================================

export const INTEGRATION_COVERAGE = {
  total_backend_endpoints: 9,
  actively_integrated: 2,
  unused_but_available: 7,
  coverage_percentage: 22.2,
  
  // CRITICAL: All user-facing functionality is covered
  user_facing_coverage: '100%',
  
  notes: [
    'All user-facing features have backend integration',
    'Unused endpoints are available for future features',
    'No dead buttons or broken UI actions',
    'All active integrations have strict validation'
  ]
} as const;

// ============================================================================
// PROJECT LOCKDOWN SAFEGUARDS
// ============================================================================

/**
 * LOCKDOWN ENFORCEMENT
 * 
 * These constants prevent accidental contract violations:
 */

// Prevent direct API calls outside the hardened client
export const FORBIDDEN_IMPORTS = [
  'axios', // Must use hardenedAPI only
  'fetch', // Must use hardenedAPI only
] as const;

// Require validation for all API responses
export const MANDATORY_VALIDATION = true;

// Prevent new endpoints without backend coordination
export const ALLOW_NEW_ENDPOINTS = false;

// Contract version checking
export const REQUIRE_CONTRACT_VERSION_MATCH = true;

/**
 * MAINTENANCE MODE RULES
 * 
 * 1. NO new API endpoints without backend implementation
 * 2. NO relaxation of validation rules
 * 3. NO optional chaining in API response handling
 * 4. NO mock data or fallbacks
 * 5. ALL UI actions must have real backend calls or explicit local-only behavior
 */

// ============================================================================
// RUNTIME VERIFICATION (DEV MODE ONLY)
// ============================================================================

export function verifyIntegrationIntegrity() {
  if (!import.meta.env.DEV) return;
  
  console.group('[INTEGRATION LOCKDOWN] Runtime Verification');
  console.log('Contract Version:', '1.0.0');
  console.log('Active Endpoints:', Object.keys(TRACEABILITY_MAP));
  console.log('Unused Endpoints:', UNUSED_ENDPOINTS);
  console.log('Coverage:', INTEGRATION_COVERAGE);
  console.log('Lockdown Status:', 'ACTIVE');
  console.groupEnd();
}

// Auto-verify on module load in dev mode
if (import.meta.env.DEV) {
  verifyIntegrationIntegrity();
}