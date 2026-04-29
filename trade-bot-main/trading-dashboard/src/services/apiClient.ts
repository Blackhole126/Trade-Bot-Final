import axios, { AxiosResponse } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_BACKEND_URL || 'https://trade-bot-api.onrender.com';

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
