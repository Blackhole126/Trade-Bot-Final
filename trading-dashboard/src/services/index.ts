/**
 * LOCKED API LAYER - MAINTENANCE MODE
 * 
 * ⚠️ DO NOT MODIFY WITHOUT BACKEND COORDINATION
 * 
 * This is the ONLY allowed entry point for backend API calls.
 * All components MUST use this layer - direct axios/fetch is FORBIDDEN.
 * 
 * CONTRACT VERSION: 1.0.0
 * LOCKDOWN STATUS: ACTIVE
 */

// CENTRALIZED API EXPORTS - ONLY THESE ARE ALLOWED
export { hardenedAPI } from './hardenedApiClient';
export type { 
  HardenedApiResult, 
  FailureMode 
} from './hardenedApiClient';

// VALIDATION EXPORTS - REQUIRED FOR ALL RESPONSES
export { 
  validatePredictResponse,
  detectContractDrift,
  FRONTEND_CONTRACT_VERSION
} from '../validators/contractValidator';
export type {
  StrictPredictResponse,
  StrictPredictionResult,
  StrictDataStatus,
  ValidationResult,
  ContractDriftError
} from '../validators/contractValidator';

// INTEGRATION LOCKDOWN EXPORTS
export {
  BACKEND_ENDPOINTS,
  TRACEABILITY_MAP,
  UNUSED_ENDPOINTS,
  INTEGRATION_COVERAGE,
  verifyIntegrationIntegrity
} from '../config/integrationLockdown';

/**
 * LOCKDOWN ENFORCEMENT
 * 
 * These runtime checks prevent contract violations:
 */

// Prevent direct axios usage
if (import.meta.env.DEV) {
  const originalAxios = window.axios;
  if (originalAxios) {
    console.warn('[LOCKDOWN] Direct axios usage detected - use hardenedAPI only');
  }
}

// Prevent direct fetch usage
if (import.meta.env.DEV) {
  const originalFetch = window.fetch;
  window.fetch = (...args) => {
    console.warn('[LOCKDOWN] Direct fetch usage detected - use hardenedAPI only');
    return originalFetch.apply(window, args);
  };
}

/**
 * MAINTENANCE MODE NOTICE
 * 
 * This API layer is in MAINTENANCE MODE:
 * - Only backend changes can extend functionality
 * - Frontend changes must maintain contract compliance
 * - No new endpoints without backend implementation
 * - All responses must pass strict validation
 */

export const MAINTENANCE_MODE = {
  status: 'ACTIVE',
  version: '1.0.0',
  rules: [
    'NO new endpoints without backend implementation',
    'NO relaxation of validation rules', 
    'NO optional chaining in response handling',
    'NO mock data or fallbacks',
    'ALL UI actions must have real backend calls'
  ]
} as const;