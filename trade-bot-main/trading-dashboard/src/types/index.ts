// Backend response types (exact match to backend)
export interface DataStatus {
  data_source: 'REALTIME_YAHOO_FINANCE' | 'CACHED_YAHOO_FINANCE' | 'FALLBACK_PROVIDER' | 'INVALID';
  data_freshness_seconds: number;
  market_context: 'NORMAL' | 'HIGH_VOLATILITY' | 'EVENT_WINDOW' | 'MARKET_CLOSED';
}

export interface PredictionItem {
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
  timestamp?: string;
  confidence?: number;
  individual_predictions?: Record<string, any>;
  unavailable?: boolean;
}

// Analyze Response Type Definition
export interface AnalyzeResponse {
  symbol: string;
  predictions: PredictionItem[];
  metadata?: {
    consensus?: string;
    average_confidence?: number;
    horizons?: string[];
    [key: string]: unknown;
  };
  error?: string;
}

// Portfolio Holding Type Definition
export interface Holding {
  symbol: string;
  shares: number;
  avgPrice: number;
  currentPrice: number;
  value: number;
}