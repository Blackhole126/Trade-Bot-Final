/**
 * Application Configuration
 * Centralized configuration for API endpoints and app settings
 */

export const config = {
  // API Configuration
  // Priority: Environment Variable > Production URL > Local Development
  API_BASE_URL: "http://127.0.0.1:8000",

  // Feature Flags
  ENABLE_AUTH: import.meta.env.VITE_ENABLE_AUTH !== 'false', // Default to true, can be disabled via env

  // Default Settings
  DEFAULT_HORIZON: 'intraday' as 'intraday' | 'short' | 'long',
  DEFAULT_MIN_CONFIDENCE: 0.3,
  DEFAULT_RISK_PARAMS: {
    stopLossPct: 2.0,
    capitalRiskPct: 1.0,
    drawdownLimitPct: 5.0,
  },

  // UI Settings
  REFRESH_INTERVAL: 120000, // 120 seconds (2 minutes) - dashboard refresh interval
  DEBOUNCE_DELAY: 300, // 300ms for search inputs
};
