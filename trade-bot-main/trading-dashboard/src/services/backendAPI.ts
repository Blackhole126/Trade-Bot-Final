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

const API_BASE_URL = import.meta.env.VITE_API_BASE_BACKEND_URL || 'https://trade-bot-api.onrender.com';
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

export { axiosInstance, handleError, API_BASE_URL };
export type { APIResponse };
