import axios, { AxiosResponse } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_BACKEND_URL || 'http://127.0.0.1:8000';

// Backend response types (exact match to backend)
interface DataStatus {
  data_source: 'REALTIME_YAHOO_FINANCE' | 'CACHED_YAHOO_FINANCE' | 'FALLBACK_PROVIDER' | 'INVALID';
  data_freshness_seconds: number;
  market_context: 'NORMAL' | 'HIGH_VOLATILITY' | 'EVENT_WINDOW' | 'MARKET_CLOSED';
}

interface PredictionResult {
  symbol: string;
  action?: string;
  predicted_return?: number;
  current_price?: number;
  predicted_price?: number;
  model_agreement?: string;
  signal_strength?: number;
  trust_gate_active?: boolean;
  trust_gate_reason?: string;
  data_status?: DataStatus;
  error?: string;
  reason?: string;
}

interface PredictResponse {
  metadata: {
    count: number;
    horizon: string;
  };
  predictions: PredictionResult[];
}

interface FetchDataResult {
  symbol: string;
  current_price?: number;
  date?: string;
  volume?: number;
  data_status?: DataStatus;
  error?: string;
}

interface FetchDataResponse {
  metadata: {
    count: number;
  };
  data: FetchDataResult[];
}

interface AnalyzeResponse {
  metadata: { count: number };
  analysis: Array<{ symbol: string; news: any[]; sentiment: string }>;
}

interface HealthResponse {
  status: string;
}

interface ApiResult<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// Validation functions
function validateDataStatus(obj: any): obj is DataStatus {
  return (
    obj &&
    typeof obj.data_source === 'string' &&
    ['REALTIME_YAHOO_FINANCE', 'CACHED_YAHOO_FINANCE', 'FALLBACK_PROVIDER', 'INVALID'].includes(obj.data_source) &&
    typeof obj.data_freshness_seconds === 'number' &&
    typeof obj.market_context === 'string' &&
    ['NORMAL', 'HIGH_VOLATILITY', 'EVENT_WINDOW', 'MARKET_CLOSED'].includes(obj.market_context)
  );
}

function validatePredictionResult(obj: any): obj is PredictionResult {
  if (!obj || typeof obj.symbol !== 'string') return false;

  // Optional fields validation
  if (obj.data_status && !validateDataStatus(obj.data_status)) return false;
  if (obj.predicted_return !== undefined && typeof obj.predicted_return !== 'number') return false;
  if (obj.current_price !== undefined && typeof obj.current_price !== 'number') return false;
  if (obj.predicted_price !== undefined && typeof obj.predicted_price !== 'number') return false;
  if (obj.signal_strength !== undefined && typeof obj.signal_strength !== 'number') return false;
  if (obj.trust_gate_active !== undefined && typeof obj.trust_gate_active !== 'boolean') return false;

  return true;
}

function validatePredictResponse(obj: any): obj is PredictResponse {
  return (
    obj &&
    obj.metadata &&
    typeof obj.metadata.count === 'number' &&
    typeof obj.metadata.horizon === 'string' &&
    Array.isArray(obj.predictions) &&
    obj.predictions.every(validatePredictionResult)
  );
}

function validateFetchDataResult(obj: any): obj is FetchDataResult {
  if (!obj || typeof obj.symbol !== 'string') return false;

  if (obj.data_status && !validateDataStatus(obj.data_status)) return false;
  if (obj.current_price !== undefined && typeof obj.current_price !== 'number') return false;
  if (obj.volume !== undefined && typeof obj.volume !== 'number') return false;

  return true;
}

function validateFetchDataResponse(obj: any): obj is FetchDataResponse {
  return (
    obj &&
    obj.metadata &&
    typeof obj.metadata.count === 'number' &&
    Array.isArray(obj.data) &&
    obj.data.every(validateFetchDataResult)
  );
}

function validateAnalyzeResponse(obj: any): obj is AnalyzeResponse {
  return (
    obj &&
    obj.metadata &&
    typeof obj.metadata.count === 'number' &&
    Array.isArray(obj.analysis) &&
    obj.analysis.every((item: any) =>
      item &&
      typeof item.symbol === 'string' &&
      Array.isArray(item.news) &&
      typeof item.sentiment === 'string'
    )
  );
}

function validateHealthResponse(obj: any): obj is HealthResponse {
  return obj && typeof obj.status === 'string';
}

// API client
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 480000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Log responses in dev mode
const logResponse = (endpoint: string, response: any, valid: boolean) => {
  if (import.meta.env.DEV) {
    console.log(`[API] ${endpoint}:`, { response, valid });
  }
};

export const backendAPI = {
  async health(): Promise<ApiResult<HealthResponse>> {
    try {
      const response: AxiosResponse = await apiClient.get('/tools/health');
      const valid = validateHealthResponse(response.data);
      logResponse('GET /tools/health', response.data, valid);

      if (!valid) {
        return { success: false, error: 'Invalid health response format' };
      }

      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message || 'Health check failed' };
    }
  },

  async predict(symbols: string[], horizon: string = 'intraday'): Promise<ApiResult<PredictResponse>> {
    try {
      const response: AxiosResponse = await apiClient.post('/tools/predict', {
        symbols,
        horizon,
      });

      const valid = validatePredictResponse(response.data);
      logResponse('POST /tools/predict', response.data, valid);

      if (!valid) {
        return { success: false, error: 'Invalid predict response format' };
      }

      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message || 'Prediction failed' };
    }
  },

  async fetchData(symbols: string[]): Promise<ApiResult<FetchDataResponse>> {
    try {
      const response: AxiosResponse = await apiClient.post('/tools/fetch_data', {
        symbols,
        horizon: 'intraday',
      });

      const valid = validateFetchDataResponse(response.data);
      logResponse('POST /tools/fetch_data', response.data, valid);

      if (!valid) {
        return { success: false, error: 'Invalid fetch data response format' };
      }

      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message || 'Fetch data failed' };
    }
  },

  async analyze(symbol: string): Promise<ApiResult<AnalyzeResponse>> {
    try {
      const response: AxiosResponse = await apiClient.post('/tools/analyze', {
        symbol,
        horizons: ['intraday'],
        stop_loss_pct: 2,
        capital_risk_pct: 1,
        drawdown_limit_pct: 5,
      });

      const valid = validateAnalyzeResponse(response.data);
      logResponse('POST /tools/analyze', response.data, valid);

      if (!valid) {
        return { success: false, error: 'Invalid analyze response format' };
      }

      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message || 'Analysis failed' };
    }
  },

  async calculateFeatures(symbols: string[]): Promise<ApiResult<{ status: string; features_calculated: boolean }>> {
    try {
      const response: AxiosResponse = await apiClient.post('/tools/calculate_features', {
        symbols,
        horizon: 'intraday',
      });

      const valid = response.data && typeof response.data.status === 'string' && typeof response.data.features_calculated === 'boolean';
      logResponse('POST /tools/calculate_features', response.data, valid);

      if (!valid) {
        return { success: false, error: 'Invalid calculate features response format' };
      }

      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message || 'Calculate features failed' };
    }
  },

  async trainModels(symbols: string[]): Promise<ApiResult<{ status: string; models_trained: boolean }>> {
    try {
      const response: AxiosResponse = await apiClient.post('/tools/train_models', {
        symbols,
        horizon: 'intraday',
      });

      const valid = response.data && typeof response.data.status === 'string' && typeof response.data.models_trained === 'boolean';
      logResponse('POST /tools/train_models', response.data, valid);

      if (!valid) {
        return { success: false, error: 'Invalid train models response format' };
      }

      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message || 'Train models failed' };
    }
  },
};

export type { DataStatus, PredictionResult, PredictResponse, FetchDataResult, FetchDataResponse, AnalyzeResponse, HealthResponse, ApiResult };