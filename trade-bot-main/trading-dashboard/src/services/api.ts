import axios, { AxiosError } from 'axios';
import { config } from '../config';
import { PredictionItem, type AnalyzeResponse } from '../types';
import { validatePrice } from '../utils/priceValidator';
import { marketDataValidator, validateApiResponse } from '../utils/marketDataValidator';
import { requestDeduplicator } from './requestDeduplicator';

// Export the types so they can be imported from this module
export type { PredictionItem, AnalyzeResponse };

// Debug logging (can be disabled in production)
const DEBUG = import.meta.env.DEV || false;
const log = (...args: any[]) => {
  if (DEBUG) {
    console.log('[API]', ...args);
  }
};

// Custom error class for timeouts on long-running requests
// This allows components to distinguish "still processing" from "actual failure"
export class TimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'TimeoutError';
  }
}

// Connection state management
let isBackendOnline = true;
let connectionCheckInProgress = false;

const api = axios.create({
  baseURL: config.API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 120 seconds (2 minutes) - predictions can take 60-90 seconds on first run
  withCredentials: false, // CORS is handled by backend
});

// Add token to requests if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    // Only add token if it's a valid JWT (not 'no-auth-required')
    if (token && token !== 'no-auth-required' && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Enhanced error handling with retry logic
api.interceptors.response.use(
  (response) => {
    // Mark backend as online on successful response
    isBackendOnline = true;
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as any;

    // Handle network errors (no response from server)
    if (!error.response && error.request) {
      // Check if it's a timeout vs connection error
      const isTimeout = error.code === 'ECONNABORTED' || error.message?.includes('timeout') || error.message?.includes('Timeout');

      if (isTimeout) {
        // Timeout - server is running but request took too long
        // Check if this is a long-running request (predict, scanAll, analyze, trainRL)
        const url = originalRequest?.url || '';
        const isLongRunningRequest = url.includes('/tools/predict') ||
          url.includes('/tools/scan_all') ||
          url.includes('/tools/analyze') ||
          url.includes('/tools/train_rl');

        if (isLongRunningRequest) {
          // For long-running requests, timeout means "still processing", not failure
          // Throw special TimeoutError that components can handle gracefully
          return Promise.reject(new TimeoutError(
            'Request is taking longer than expected. The backend is still processing your request. ' +
            'This is normal when models need training (60-90 seconds per symbol). Please wait...'
          ));
        } else {
          // For other requests, timeout is a real error
          return Promise.reject(new Error(
            'Request timed out. Please try again or check your connection.'
          ));
        }
      }

      // Real connection error
      isBackendOnline = false;

      // Retry logic for connection errors (only once)
      if (!originalRequest._retry && originalRequest) {
        originalRequest._retry = true;

        // Wait a bit before retrying
        await new Promise(resolve => setTimeout(resolve, 1000));

        try {
          return await api(originalRequest);
        } catch (retryError) {
          // Retry failed, return original error
        }
      }

      const baseURL = config.API_BASE_URL;
      return Promise.reject(new Error(
        `Unable to connect to backend server at ${baseURL}. ` +
        `Please ensure the backend is running.`
      ));
    }

    // Handle server errors (response received but with error status)
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data as any;

      // Extract error message
      let message = 'An error occurred';
      if (data?.detail) {
        message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } else if (data?.error) {
        message = typeof data.error === 'string' ? data.error : JSON.stringify(data.error);
      } else if (data?.message) {
        message = data.message;
      }

      // Handle specific error codes
      if (status === 401) {
        // Unauthorized - try to auto-login if credentials are available
        const storedUsername = localStorage.getItem('username');
        const storedToken = localStorage.getItem('token');

        // Only clear if token was invalid (not if it's missing)
        if (storedToken && storedToken !== 'no-auth-required') {
          localStorage.removeItem('token');
          localStorage.removeItem('username');
          message = 'Session expired. Please login again.';
        } else {
          // No token - redirect to login
          message = 'Authentication required. Please login.';
          // Trigger login redirect
          if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
            setTimeout(() => {
              window.location.href = '/login';
            }, 100);
          }
        }
      } else if (status === 403) {
        message = 'Access forbidden. Please check your permissions.';
      } else if (status === 404) {
        message = 'Endpoint not found. Please check the API version.';
      } else if (status === 429) {
        // Rate limit exceeded - extract retry_after if available
        const retryAfter = data?.detail?.retry_after || data?.retry_after || 60;
        const detailMsg = data?.detail?.message || data?.message || '';
        message = detailMsg || `Rate limit exceeded. Please wait ${retryAfter} seconds before trying again.`;

        // Don't retry rate limit errors automatically - let the user handle it
        // Clear any pending retries
        if (originalRequest) {
          originalRequest._retry = true; // Prevent retry
        }
      } else if (status === 503) {
        message = 'Service temporarily unavailable. The prediction engine is initializing. Please try again in a moment.';
      } else if (status >= 500) {
        message = `Server error (${status}). Please try again later.`;
      }

      return Promise.reject(new Error(message));
    }

    // Handle other errors
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (username: string, password: string) => {
    // Check if auth endpoint exists first
    try {
      const response = await api.post('/auth/login', { username, password });
      return response.data;
    } catch (error: any) {
      // If 404, auth is disabled - return success with no-auth token
      if (error.response?.status === 404) {
        return {
          success: true,
          username: username || 'anonymous',
          token: 'no-auth-required',
          message: 'Authentication is disabled - open access mode'
        };
      }
      throw error;
    }
  },
  signup: async () => {
    throw new Error('Signup is not supported. This backend does not have user registration. Please contact administrator for account creation.');
  },
  logout: async () => {
    // Call backend logout endpoint to clear session
    try {
      const response = await api.post('/auth/logout');
      return response.data;
    } catch (error: any) {
      // If 404, auth is disabled - just return success
      if (error.response?.status === 404) {
        return {
          success: true,
          message: 'Logout successful'
        };
      }
      throw error;
    }
  },
  checkStatus: async () => {
    try {
      const response = await api.get('/auth/status');
      return response.data;
    } catch (error) {
      // Return unauthenticated on error
      return { authenticated: false, auth_status: 'enabled' };
    }
  },
};

// Stock Data API
export const stockAPI = {
  predict: async (
    symbols: string[],
    horizon: string = 'intraday',
    riskProfile?: string,
    stopLossPct?: number,
    capitalRiskPct?: number,
    drawdownLimitPct?: number,
    forceRefresh?: boolean
  ) => {
    const key = `predict_${symbols.join(',')}_${horizon}`;
    
    return requestDeduplicator.deduplicate(key, async () => {
      const payload: any = {
        symbols,
        horizon,
      };
      if (riskProfile) payload.risk_profile = riskProfile;
      if (stopLossPct !== undefined) payload.stop_loss_pct = stopLossPct;
      if (capitalRiskPct !== undefined) payload.capital_risk_pct = capitalRiskPct;
      if (drawdownLimitPct !== undefined) payload.drawdown_limit_pct = drawdownLimitPct;

      log('Calling /tools/predict with:', payload);
      try {
      const response = await api.post('/tools/predict', payload);
      log('Predict response received:', { status: response.status, hasPredictions: 'predictions' in response.data });

      const responseData = response.data;
      
      // Validate API response for data integrity
      const apiValidation = validateApiResponse(responseData);

      const normalizedPredictions = Array.isArray(responseData?.predictions)
        ? responseData.predictions
        : Array.isArray(responseData?.results)
          ? responseData.results.map((item: any) => {
              const symbol = typeof item?.symbol === 'string' ? item.symbol : 'UNKNOWN';
              const status = String(item?.status || '').toLowerCase();
              if (status === 'success' && item?.data && typeof item.data === 'object') {
                return { ...item.data, symbol };
              }
              return { symbol, error: item?.error || 'Prediction unavailable' };
            })
          : null;
      
      // Validate and enrich response with comprehensive validation metadata
      if (normalizedPredictions) {
        const validatedPredictions = normalizedPredictions.map((prediction: any) => {
          if (prediction.error) return prediction;
          
          // Legacy price validation
          const predictedPriceValid = prediction.predicted_price !== undefined ? 
            validatePrice(prediction.predicted_price, prediction.symbol) : null;
            const currentPriceValid = prediction.current_price !== undefined ? 
              validatePrice(prediction.current_price, prediction.symbol) : null;
            
            // Market data validation
            const marketDataValidation = marketDataValidator.validatePriceData({
              symbol: prediction.symbol,
              price: prediction.current_price,
              timestamp: prediction.price_metadata?.price_timestamp || response.data.metadata?.timestamp,
              source: prediction.price_metadata?.price_source || 'api_response',
              metadata: prediction.price_metadata
            });
            
          return {
            ...prediction,
            _priceValidation: {
              predictedPrice: predictedPriceValid,
              currentPrice: currentPriceValid,
              hasValidPrice: (predictedPriceValid?.valid || currentPriceValid?.valid) ?? false
            },
            _marketDataValidation: marketDataValidation,
            _dataIntegrity: {
              isReal: marketDataValidation.isReal,
              confidence: marketDataValidation.confidence,
              shouldDisplay: marketDataValidator.shouldDisplayData(marketDataValidation, false),
              sourceLabel: marketDataValidator.getSourceLabel(marketDataValidation),
              validationMessage: marketDataValidator.getValidationMessage(marketDataValidation)
            }
          };
        });
        
        return {
          ...responseData,
          predictions: validatedPredictions,
          _apiValidation: apiValidation
        };
      }
      
      return responseData;
      } catch (error: any) {
        log('Predict error:', {
          message: error.message,
          code: error.code,
          status: error.response?.status,
          hasResponse: !!error.response
        });
        throw error;
      }
    }, { forceRefresh });
  },

  scanAll: async (
    symbols: string[],
    horizon: string = 'intraday',
    minConfidence: number = 0.3,
    stopLossPct?: number,
    capitalRiskPct?: number
  ) => {
    const payload: any = {
      symbols,
      horizon,
      min_confidence: minConfidence,
    };
    if (stopLossPct !== undefined) payload.stop_loss_pct = stopLossPct;
    if (capitalRiskPct !== undefined) payload.capital_risk_pct = capitalRiskPct;

    const response = await api.post('/tools/scan_all', payload);
    return response.data;
  },

  analyze: async (
    symbol: string,
    horizons: string[] = ['intraday'],
    stopLossPct: number = 2.0,
    capitalRiskPct: number = 1.0,
    drawdownLimitPct: number = 5.0
  ) => {
    const key = `analyze_${symbol}_${horizons.join(',')}`;
    
    return requestDeduplicator.deduplicate(key, async () => {
      const response = await api.post('/tools/analyze', {
        symbol,
        horizons,
        stop_loss_pct: stopLossPct,
        capital_risk_pct: capitalRiskPct,
        drawdown_limit_pct: drawdownLimitPct,
      });
      return response.data;
    });
  },

  fetchData: async (
    symbols: string[],
    period: string = '2y',
    includeFeatures: boolean = false,
    refresh: boolean = false
  ) => {
    const response = await api.post('/tools/fetch_data', {
      symbols,
      period,
      include_features: includeFeatures,
      refresh,
    });
    return response.data;
  },

  calculateFeatures: async (symbols: string[]) => {
    const response = await api.post('/tools/calculate_features', { symbols });
    return response.data;
  },

  trainModels: async (symbols: string[], horizon: string = 'intraday') => {
    const response = await api.post('/tools/train_models', { symbols, horizon });
    return response.data;
  },

  feedback: async (
    symbol: string,
    predictedAction: string,
    userFeedback: string,  // Now accepts free text
    actualReturn?: number | null
  ) => {
    // Normalize symbol (1-20 characters, uppercase)
    const normalizedSymbol = symbol.trim().toUpperCase();
    if (normalizedSymbol.length < 1 || normalizedSymbol.length > 20) {
      throw new Error(`Symbol must be between 1 and 20 characters, got: ${normalizedSymbol.length}`);
    }

    // Normalize predicted_action: accepts BUY/SELL/LONG/SHORT/HOLD
    const normalizedAction = predictedAction.toUpperCase().trim();
    const validActions = ['LONG', 'SHORT', 'HOLD', 'BUY', 'SELL'];
    if (!validActions.includes(normalizedAction)) {
      throw new Error(`Invalid predicted_action: ${predictedAction}. Must be one of: ${validActions.join(', ')}`);
    }

    // Validate user_feedback is not empty (accepts any text)
    const feedbackText = userFeedback.trim();
    if (!feedbackText) {
      throw new Error('user_feedback cannot be empty');
    }

    // Build payload according to backend schema
    const payload: {
      symbol: string;
      predicted_action: string;
      user_feedback: string;
      actual_return?: number | null;
    } = {
      symbol: normalizedSymbol,
      predicted_action: normalizedAction,
      user_feedback: feedbackText,
    };

    // Handle actual_return: can be number, null, or undefined (omit if undefined)
    // Backend schema: actual_return: Optional[float] = Field(None, ge=-100.0, le=1000.0)
    if (actualReturn !== undefined && actualReturn !== null) {
      // Validate range if provided
      if (isNaN(actualReturn) || actualReturn < -100 || actualReturn > 1000) {
        throw new Error(`actual_return must be between -100 and 1000, got: ${actualReturn}`);
      }
      payload.actual_return = actualReturn;
    } else if (actualReturn === null) {
      // Explicitly send null if null is passed
      payload.actual_return = null;
    }
    // If undefined, omit the field entirely (backend will use default None)

    try {
      const response = await api.post('/tools/feedback', payload);
      return response.data;
    } catch (error: any) {
      throw error;
    }
  },

  trainRL: async (
    symbol: string,
    horizon: string = 'intraday',
    nEpisodes: number = 10,
    forceRetrain: boolean = false
  ) => {
    const response = await api.post('/tools/train_rl', {
      symbol,
      horizon,
      n_episodes: nEpisodes,
      force_retrain: forceRetrain,
    });
    return response.data;
  },

  listModels: async () => {
    try {
      const response = await api.get('/tools/models');
      return response.data;
    } catch (error: any) {
      // If endpoint doesn't exist, return empty list
      if (error.response?.status === 404) {
        return { models: [] };
      }
      throw error;
    }
  },

  health: async (retries: number = 2): Promise<any> => {
    try {
      const response = await api.get('/tools/health', {
        timeout: 15000, // 15 seconds for health check
      });
      return response.data;
    } catch (error: any) {
      // Retry on timeout or connection errors
      if (retries > 0 && (error.code === 'ECONNABORTED' || error.message?.includes('timeout') || error.message?.includes('Network Error'))) {
        await new Promise(resolve => setTimeout(resolve, 1000 * (3 - retries))); // Exponential backoff
        return stockAPI.health(retries - 1);
      }
      throw error;
    }
  },

  checkConnection: async (retries: number = 3): Promise<{ connected: boolean; data?: any; error?: string }> => {
    // Prevent multiple simultaneous connection checks
    if (connectionCheckInProgress) {
      return { connected: isBackendOnline, error: isBackendOnline ? undefined : 'Connection check in progress' };
    }

    connectionCheckInProgress = true;

    try {
      // Use the api instance for consistency - this ensures CORS and other configs are applied
      const response = await api.get('/', {
        timeout: 10000, // 10 seconds for connection check (increased from 5)
      });

      isBackendOnline = true;
      connectionCheckInProgress = false;
      return { connected: true, data: response.data };
    } catch (error: any) {
      // Retry logic for network errors
      if (retries > 0 && (!error.response || error.code === 'ECONNABORTED' || error.code === 'ECONNREFUSED' || error.message?.includes('timeout') || error.message?.includes('Network Error'))) {
        connectionCheckInProgress = false;
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second before retry
        return stockAPI.checkConnection(retries - 1);
      }

      // If we got a response, server is reachable (even if error)
      if (error.response) {
        isBackendOnline = true;
        connectionCheckInProgress = false;
        return { connected: true, data: error.response.data };
      }

      isBackendOnline = false;
      connectionCheckInProgress = false;

      const errorMessage = error.code === 'ECONNREFUSED'
        ? 'Backend server is not running. Please start the backend server.'
        : error.code === 'ECONNABORTED' || error.message?.includes('timeout')
          ? 'Backend server is not responding. It may be starting up or overloaded.'
          : error.message || 'Unable to connect to backend server';

      return { connected: false, error: errorMessage };
    }
  },

  getRateLimitStatus: async () => {
    const response = await api.get('/auth/status');
    return response.data;
  },
};

// ============================================================================
// BACKEND DOES NOT SUPPORT THESE FEATURES
// The following APIs are NOT IMPLEMENTED in the backend
// They are kept here for reference but will throw errors if called
// ============================================================================

// Risk Management API - ❌ NOT IMPLEMENTED IN BACKEND
// Backend has NO /api/risk endpoints
// Use client-side calculations instead
export const riskAPI = {
  assess: async () => {
    throw new Error('Risk assessment endpoint not available. Backend does not implement /api/risk/assess. Use client-side calculations.');
  },
  setStopLoss: async () => {
    throw new Error('Stop-loss endpoint not available. Backend does not implement /api/risk/stop-loss. Use client-side storage.');
  },
};

// Trade Execution API - ❌ NOT IMPLEMENTED IN BACKEND
// Backend has NO /tools/execute endpoint
// This is a prediction-only system, not a trading platform
export const tradeAPI = {
  execute: async () => {
    throw new Error('Trade execution not available. Backend does not implement /tools/execute. This is a prediction system, not a trading platform.');
  },
};

// AI Chat API - ❌ NOT IMPLEMENTED IN BACKEND
// Backend has NO /api/ai/chat endpoint
export const aiAPI = {
  chat: async () => {
    throw new Error('AI Chat not available. Backend does not implement /api/ai/chat. Feature coming soon.');
  },
};

// Popular stock symbols for search autocomplete
export const POPULAR_STOCKS = [
  // Top Indian Stocks (NSE) - Featured prominently
  'RELIANCE.NS',        // Reliance Industries
  'TATAMOTORS.NS',      // Tata Motors
  'TATASTEEL.NS',       // Tata Steel
  'TATACONSUM.NS',      // Tata Consumer Products
  'TATAPOWER.NS',       // Tata Power
  'TCS.NS',             // Tata Consultancy Services
  'HDFCBANK.NS',        // HDFC Bank
  'ICICIBANK.NS',       // ICICI Bank
  'INFY.NS',            // Infosys
  'BHARTIARTL.NS',      // Bharti Airtel
  'ITC.NS',             // ITC Limited
  'SBIN.NS',            // State Bank of India
  'BAJFINANCE.NS',      // Bajaj Finance
  'HINDUNILVR.NS',      // Hindustan Unilever
  'LT.NS',              // Larsen & Toubro
  'ASIANPAINT.NS',      // Asian Paints
  'MARUTI.NS',          // Maruti Suzuki
  'SUNPHARMA.NS',       // Sun Pharma
  'WIPRO.NS',           // Wipro
  'AXISBANK.NS',        // Axis Bank
  // Popular US Stocks
  'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'JNJ',
  'WMT', 'PG', 'MA', 'UNH', 'DIS', 'HD', 'BAC', 'PYPL', 'NFLX', 'ADBE',
  // Additional Indian Stocks
  'KOTAKBANK.NS', 'LICI.NS', 'HCLTECH.NS', 'TITAN.NS', 'ULTRACEMCO.NS',
  'NESTLEIND.NS', 'ONGC.NS', 'NTPC.NS', 'POWERGRID.NS', 'JSWSTEEL.NS',
  'ADANIPORTS.NS', 'TECHM.NS', 'TATAELXSI.NS', 'TATACOMM.NS',
];

// Popular crypto symbols (Yahoo Finance format)
export const POPULAR_CRYPTO = [
  'BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'XRP-USD',
  'ADA-USD', 'DOGE-USD', 'DOT-USD', 'MATIC-USD', 'AVAX-USD',
  'LINK-USD', 'UNI-USD', 'LTC-USD', 'ATOM-USD', 'ETC-USD',
  'XLM-USD', 'ALGO-USD', 'VET-USD', 'ICP-USD', 'FIL-USD',
  'TRX-USD', 'EOS-USD', 'AAVE-USD', 'MKR-USD', 'COMP-USD',
];

// Popular commodities symbols (Yahoo Finance format)
export const POPULAR_COMMODITIES = [
  'GC=F',      // Gold Futures
  'SI=F',      // Silver Futures
  'CL=F',      // Crude Oil Futures
  'NG=F',      // Natural Gas Futures
  'HG=F',      // Copper Futures
  'ZC=F',      // Corn Futures
  'ZS=F',      // Soybean Futures
  'ZW=F',      // Wheat Futures
  'KC=F',      // Coffee Futures
  'SB=F',      // Sugar Futures
  'CT=F',      // Cotton Futures
  'CC=F',      // Cocoa Futures
  'OJ=F',      // Orange Juice Futures
  'LE=F',      // Live Cattle Futures
  'HE=F',      // Lean Hogs Futures
];

// Trading History API - ❌ NOT IMPLEMENTED IN BACKEND
// Backend has NO /api/trades/history endpoints
// Use localStorage for client-side history tracking
export const historyAPI = {
  getHistory: async () => {
    throw new Error('Trading history endpoint not available. Backend does not implement /api/trades/history. Use localStorage.');
  },
  saveTrade: async () => {
    throw new Error('Save trade endpoint not available. Backend does not implement /api/trades/history. Use localStorage.');
  },
};

// Educational API - ❌ NOT IMPLEMENTED IN BACKEND
// Backend has NO /api/education endpoints
// Use static content or localStorage for progress tracking
export const educationalAPI = {
  getModules: async () => {
    throw new Error('Educational modules endpoint not available. Backend does not implement /api/education. Use static content.');
  },
  getProgress: async () => {
    throw new Error('Progress endpoint not available. Backend does not implement /api/education/progress. Use localStorage.');
  },
  saveProgress: async () => {
    throw new Error('Save progress endpoint not available. Backend does not implement /api/education/progress. Use localStorage.');
  },
};

// User Settings API - ❌ NOT IMPLEMENTED IN BACKEND
// Backend has NO /api/user/settings endpoints
// Use localStorage for settings persistence
export const userAPI = {
  getSettings: async () => {
    throw new Error('User settings endpoint not available. Backend does not implement /api/user/settings. Use localStorage.');
  },
  saveSettings: async () => {
    throw new Error('Save settings endpoint not available. Backend does not implement /api/user/settings. Use localStorage.');
  },
};

// Alert API - ❌ NOT IMPLEMENTED IN BACKEND
// Backend has NO /api/alerts endpoints
// Use localStorage with browser notifications for client-side alerts
export const alertAPI = {
  create: async () => {
    throw new Error('Alerts endpoint not available. Backend does not implement /api/alerts. Use localStorage with browser notifications.');
  },
  list: async () => {
    throw new Error('Alerts endpoint not available. Backend does not implement /api/alerts. Use localStorage.');
  },
  update: async () => {
    throw new Error('Alerts endpoint not available. Backend does not implement /api/alerts. Use localStorage.');
  },
  delete: async () => {
    throw new Error('Alerts endpoint not available. Backend does not implement /api/alerts. Use localStorage.');
  },
  check: async () => {
    throw new Error('Alerts endpoint not available. Backend does not implement /api/alerts. Use client-side checking.');
  },
  test: async () => {
    throw new Error('Alerts endpoint not available. Backend does not implement /api/alerts.');
  },
};

// Data Control API - ❌ NOT IMPLEMENTED IN BACKEND
// Backend has NO /api/data endpoints
export const dataAPI = {
  clearAll: async () => {
    throw new Error('Data control endpoint not available. Backend does not implement /api/data. Use localStorage.clear().');
  },
  exportAll: async () => {
    throw new Error('Data export endpoint not available. Backend does not implement /api/data. Export localStorage manually.');
  },
};

export default api;
