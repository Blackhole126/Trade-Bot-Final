import axios, { AxiosError } from 'axios';
import { config } from '../config';
import { PredictionItem, type AnalyzeResponse } from '../types';
import { validatePrice } from '../utils/priceValidator';
import { marketDataValidator, validateApiResponse } from '../utils/marketDataValidator';
import { requestDeduplicator } from './requestDeduplicator';

// Export the types so they can be imported from this module
export type { PredictionItem, AnalyzeResponse };

// Debug logging (development only)
const DEBUG = import.meta.env.DEV || false;
const log = (...args: any[]) => {
  if (DEBUG) {
    // eslint-disable-next-line no-console
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

// API client for web_backend (port 5000) - auth, health, etc.
const api = axios.create({
  baseURL: config.API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 480000, // 8 minutes - first run on Render can take 4–6 min (fetch + features + model)
  withCredentials: false, // CORS is handled by backend
});

// API client for api_server (port 8000) - predictions, market scan
const PREDICTION_API_URL = import.meta.env.VITE_PREDICTION_API_URL || 'http://127.0.0.1:8000';
const predictionApi = axios.create({
  baseURL: PREDICTION_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 480000,
  withCredentials: false,
});

// Add token to requests if available
const applyTokenInterceptor = (instance: any) => {
  instance.interceptors.request.use(
    (config: any) => {
      // Priority: sessionStorage (tab-specific) > localStorage (persistent)
      const token = sessionStorage.getItem('token') || localStorage.getItem('token');
      
      // Only add token if it's a valid JWT (not 'no-auth-required')
      if (token && token !== 'no-auth-required' && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error: any) => {
      return Promise.reject(error);
    }
  );
};

// Apply to both API instances
applyTokenInterceptor(api);
applyTokenInterceptor(predictionApi);

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
        `Cannot reach backend at ${baseURL}. Start HFT2 backend: cd backend\\hft2\\backend then run "python run_hft2.py". Check the terminal for "Started web_backend (5000)" and open ${baseURL}/docs to verify.`
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
        const currentToken = sessionStorage.getItem('token') || localStorage.getItem('token');
        if (currentToken && currentToken !== 'no-auth-required') {
          sessionStorage.removeItem('token');
          sessionStorage.removeItem('username');
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

// Auth API – wired to hft2 backend (POST /api/auth/login, /api/auth/register, GET /api/auth/status)
export const authAPI = {
  login: async (username: string, password: string) => {
    try {
      const response = await api.post('/api/auth/login', { username, password });
      const data = response.data as { access_token?: string; token_type?: string; username?: string };
      if (data.access_token) {
        return { success: true, token: data.access_token, username: data.username || username };
      }
      return { success: false, error: 'No token in response' };
    } catch (error: any) {
      if (error.response?.status === 404) {
        return { success: true, username: username || 'anonymous', token: 'no-auth-required', message: 'Auth disabled' };
      }
      throw error;
    }
  },
  signup: async (username: string, password: string, _email?: string) => {
    try {
      const response = await api.post('/api/auth/register', { username, password });
      const data = response.data as { access_token?: string; username?: string };
      if (data.access_token) {
        return { success: true, token: data.access_token, username: data.username || username };
      }
      return { success: true, message: 'Account created. Please login.' };
    } catch (error: any) {
      const msg = error.response?.data?.detail || error.message;
      throw new Error(Array.isArray(msg) ? msg[0]?.msg || String(msg) : msg || 'Signup failed');
    }
  },
  logout: async () => {
    try {
      await api.post('/api/auth/logout');
    } catch {
      // Proceed even if backend unreachable so client still clears token
    }
    return { success: true, message: 'Logout successful' };
  },
  checkStatus: async () => {
    try {
      const response = await api.get('/api/auth/status');
      return response.data as { auth_status: string; authenticated?: boolean; username?: string };
    } catch {
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

      log('Calling /tools/predict (async + poll)...', payload);
      try {
        // Use async endpoint: start job then poll (no long-held request = no timeout)
        // Use predictionApi (port 8000) for /tools/predict endpoints
        const startResp = await predictionApi.post('/tools/predict/async', payload, { timeout: 60000 });
        const jobId = startResp.data?.job_id;
        if (!jobId) throw new Error('Backend did not return job_id');
        log('Predict job started:', jobId);
        let responseData: any = null;
        const pollIntervalMs = 12000;
        const pollTimeoutMs = 45000;
        const maxPolls = 150; // ~30 min
        for (let i = 0; i < maxPolls; i++) {
          const pollResp = await predictionApi.get(`/tools/predict/result/${jobId}`, { timeout: pollTimeoutMs });
          if (pollResp.status === 404) throw new Error('Prediction job expired or not found');
          if (pollResp.status === 200) {
            responseData = pollResp.data;
            if (responseData?.status === 'failed') throw new Error(responseData?.error || 'Prediction failed');
            break;
          }
          await new Promise(r => setTimeout(r, pollIntervalMs));
        }
        if (!responseData) throw new Error('Prediction timed out (backend did not finish in time)');
        log('Predict response received:', { hasPredictions: 'predictions' in responseData });

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
              timestamp: prediction.price_metadata?.price_timestamp || responseData?.metadata?.timestamp,
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

    const response = await predictionApi.post('/tools/scan_all', payload);
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
      const response = await predictionApi.post('/tools/analyze', {
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
    const response = await predictionApi.post('/tools/fetch_data', {
      symbols,
      period,
      include_features: includeFeatures,
      refresh,
    });
    return response.data;
  },

  calculateFeatures: async (symbols: string[]) => {
    const response = await predictionApi.post('/tools/calculate_features', { symbols });
    return response.data;
  },

  trainModels: async (symbols: string[], horizon: string = 'intraday') => {
    const response = await predictionApi.post('/tools/train_models', { symbols, horizon });
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
      const response = await predictionApi.post('/tools/feedback', payload);
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
    const response = await predictionApi.post('/tools/train_rl', {
      symbol,
      horizon,
      n_episodes: nEpisodes,
      force_retrain: forceRetrain,
    });
    return response.data;
  },

  listModels: async () => {
    try {
      const response = await predictionApi.get('/tools/models');
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
      // Use /api/health for web_backend (port 5000)
      const response = await api.get('/api/health', {
        timeout: 25000, // 25s — backend may be busy with prediction
      });
      return response.data;
    } catch (error: any) {
      // Retry on timeout or connection errors
      if (retries > 0 && (error.code === 'ECONNABORTED' || error.message?.includes('timeout') || error.message?.includes('Network Error'))) {
        await new Promise(resolve => setTimeout(resolve, 1000 * (3 - retries)));
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
      // Use /api/health instead of / to avoid 404 errors (root route tries to serve HTML file that doesn't exist)
      const response = await api.get('/api/health', {
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

      // Don't mark offline on timeout — backend may be busy with a long prediction
      const isTimeout = error.code === 'ECONNABORTED' || error.message?.includes('timeout');
      if (!isTimeout) {
        isBackendOnline = false;
      }
      connectionCheckInProgress = false;

      const errorMessage = error.code === 'ECONNREFUSED'
        ? 'Backend server is not running. Please start the backend server.'
        : error.code === 'ECONNABORTED' || error.message?.includes('timeout')
          ? 'Backend server is not responding. It may be starting up or overloaded.'
          : error.message || 'Unable to connect to backend server';

      return { connected: isBackendOnline, error: errorMessage };
    }
  },

  getRateLimitStatus: async () => {
    const response = await api.get('/api/auth/status');
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

// User Settings API – stored in backend MongoDB
export const userAPI = {
  getSettings: async () => {
    const response = await api.get('/api/user/profile');
    const data = response.data as { username?: string; fullName?: string; email?: string; preferences?: Record<string, unknown> };
    return { settings: { fullName: data.fullName, email: data.email, preferences: data.preferences }, ...data };
  },
  saveSettings: async (profile: { fullName?: string; email?: string; username?: string; preferences?: Record<string, unknown> }) => {
    const response = await api.post('/api/user/profile', {
      fullName: profile.fullName,
      email: profile.email,
      preferences: profile.preferences,
    });
    return response.data as { success: boolean; message?: string };
  },

  // --- Watchlist (per-user, database-backed) ---
  getWatchlist: async (): Promise<string[]> => {
    try {
      const response = await api.get('/api/user/watchlist');
      const data = response.data as { symbols?: string[] };
      return data.symbols ?? [];
    } catch {
      return [];
    }
  },
  saveWatchlist: async (symbols: string[]): Promise<void> => {
    await api.post('/api/user/watchlist', { symbols });
  },

  // --- User Preferences / Settings (per-user, database-backed) ---
  getUserSettings: async (): Promise<Record<string, unknown>> => {
    try {
      const response = await api.get('/api/user/settings');
      return (response.data as Record<string, unknown>) ?? {};
    } catch {
      return {};
    }
  },
  saveUserSettings: async (settings: Record<string, unknown>): Promise<void> => {
    await api.post('/api/user/settings', settings);
  },

  // --- Alerts (per-user, database-backed) ---
  getAlerts: async (): Promise<Record<string, unknown>> => {
    try {
      const response = await api.get('/api/user/alerts');
      return (response.data as Record<string, unknown>) ?? {};
    } catch {
      return {};
    }
  },
  saveAlerts: async (alerts: Record<string, unknown>): Promise<void> => {
    await api.post('/api/user/alerts', alerts);
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
