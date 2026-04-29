/**
 * STRICT BACKEND INTEGRATION
 * 
 * Rules:
 * 1. NO mock data - only real backend responses
 * 2. NO localStorage as data source - only UI preferences
 * 3. Backend is single source of truth
 * 4. Every error must surface to UI
 * 5. NO backend modifications
 * 
 * Available Backend Endpoints (9 total):
 * - GET  /
 * - GET  /auth/status
 * - GET  /tools/health
 * - POST /tools/predict
 * - POST /tools/scan_all
 * - POST /tools/analyze
 * - POST /tools/feedback
 * - POST /tools/train_rl
 * - POST /tools/fetch_data
 */

import axios, { AxiosError, AxiosInstance } from 'axios';

const API_BASE_URL = 'http://127.0.0.1:5000';
const API_TIMEOUT = 120000; // 2 minutes for model training

// Axios instance with strict configuration
const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Standard API response type
interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    message: string;
    status: number;
    endpoint: string;
  };
}

// Error handler - converts all errors to standard format
function handleError(error: any, endpoint: string): APIResponse {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError;
    
    // Network error (backend not running)
    if (!axiosError.response) {
      return {
        success: false,
        error: {
          message: `Cannot connect to backend at ${API_BASE_URL}. Ensure backend is running.`,
          status: 0,
          endpoint,
        },
      };
    }

    // HTTP error response
    const status = axiosError.response.status;
    const data: any = axiosError.response.data;
    
    let message = 'Unknown error occurred';
    if (data?.detail) {
      message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } else if (data?.error) {
      message = data.error;
    } else if (data?.message) {
      message = data.message;
    } else if (axiosError.message) {
      message = axiosError.message;
    }

    return {
      success: false,
      error: {
        message,
        status,
        endpoint,
      },
    };
  }

  // Non-axios error
  return {
    success: false,
    error: {
      message: error?.message || 'Unknown error',
      status: -1,
      endpoint,
    },
  };
}

// ============================================================================
// API FUNCTIONS - ONLY REAL BACKEND ENDPOINTS
// ============================================================================

export const api = {
  /**
   * GET / - API information
   */
  async getInfo(): Promise<APIResponse> {
    try {
      const response = await axiosInstance.get('/');
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return handleError(error, 'GET /');
    }
  },

  /**
   * GET /auth/status - Authentication/rate limit status
   */
  async getAuthStatus(): Promise<APIResponse> {
    try {
      const response = await axiosInstance.get('/auth/status');
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return handleError(error, 'GET /auth/status');
    }
  },

  /**
   * GET /tools/health - System health check
   */
  async getHealth(): Promise<APIResponse> {
    try {
      const response = await axiosInstance.get('/tools/health');
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return handleError(error, 'GET /tools/health');
    }
  },

  /**
   * POST /tools/predict - Generate predictions for symbols
   */
  async predict(payload: {
    symbols: string[];
    horizon?: string;
    risk_profile?: string;
    stop_loss_pct?: number;
    capital_risk_pct?: number;
    drawdown_limit_pct?: number;
  }): Promise<APIResponse> {
    try {
      const response = await axiosInstance.post('/tools/predict', payload);
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return handleError(error, 'POST /tools/predict');
    }
  },

  /**
   * POST /tools/scan_all - Scan and rank multiple symbols
   */
  async scanAll(payload: {
    symbols: string[];
    horizon?: string;
    min_confidence?: number;
    stop_loss_pct?: number;
    capital_risk_pct?: number;
  }): Promise<APIResponse> {
    try {
      const response = await axiosInstance.post('/tools/scan_all', payload);
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return handleError(error, 'POST /tools/scan_all');
    }
  },

  /**
   * POST /tools/analyze - Detailed analysis with multiple horizons
   */
  async analyze(payload: {
    symbol: string;
    horizons?: string[];
    stop_loss_pct?: number;
    capital_risk_pct?: number;
    drawdown_limit_pct?: number;
  }): Promise<APIResponse> {
    try {
      const response = await axiosInstance.post('/tools/analyze', payload);
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return handleError(error, 'POST /tools/analyze');
    }
  },

  /**
   * POST /tools/feedback - Submit user feedback
   */
  async submitFeedback(payload: {
    symbol: string;
    predicted_action: string;
    user_feedback: string;
    actual_return?: number;
  }): Promise<APIResponse> {
    try {
      const response = await axiosInstance.post('/tools/feedback', payload);
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return handleError(error, 'POST /tools/feedback');
    }
  },

  /**
   * POST /tools/train_rl - Train reinforcement learning model
   */
  async trainRL(payload: {
    symbol: string;
    horizon?: string;
    n_episodes?: number;
    force_retrain?: boolean;
  }): Promise<APIResponse> {
    try {
      const response = await axiosInstance.post('/tools/train_rl', payload);
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return handleError(error, 'POST /tools/train_rl');
    }
  },

  /**
   * POST /tools/fetch_data - Fetch historical data
   */
  async fetchData(payload: {
    symbols: string[];
    period?: string;
    include_features?: boolean;
    refresh?: boolean;
  }): Promise<APIResponse> {
    try {
      const response = await axiosInstance.post('/tools/fetch_data', payload);
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return handleError(error, 'POST /tools/fetch_data');
    }
  },

  /**
   * Check backend connection
   */
  async checkConnection(): Promise<APIResponse> {
    try {
      const response = await axiosInstance.get('/', { timeout: 5000 });
      return {
        success: true,
        data: { connected: true, info: response.data },
      };
    } catch (error) {
      return {
        success: false,
        error: {
          message: `Backend not reachable at ${API_BASE_URL}`,
          status: 0,
          endpoint: 'GET /',
        },
      };
    }
  },
};

// Export types
export type { APIResponse };
export { API_BASE_URL };
