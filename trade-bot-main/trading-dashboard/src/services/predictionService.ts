import { stockAPI } from './api';
import type { PredictionItem } from '../types';

// Types
export type PredictStatus = 'success' | 'failed';

export interface PredictOutcome {
  symbol: string;
  status: PredictStatus;
  data?: PredictionItem;
  error?: string;
}

interface ProgressUpdate {
  step: 'checking_dependencies' | 'predicting' | 'complete' | 'error';
  description: string;
  progress: number;
  symbol: string;
  error?: string;
  canRetry?: boolean;
  suggestedAction?: string;
}

class PredictionError extends Error {
  constructor(message: string, public code: string, public details?: any) {
    super(message);
    this.name = 'PredictionError';
  }
}

export class PredictionService {
  private static instance: PredictionService;
  private listeners: Set<(update: ProgressUpdate) => void> = new Set();

  private constructor() {}

  static getInstance(): PredictionService {
    if (!PredictionService.instance) {
      PredictionService.instance = new PredictionService();
    }
    return PredictionService.instance;
  }

  addProgressListener(listener: (update: ProgressUpdate) => void): void {
    this.listeners.add(listener);
  }

  removeProgressListener(listener: (update: ProgressUpdate) => void): void {
    this.listeners.delete(listener);
  }

  private notifyProgress(update: ProgressUpdate): void {
    this.listeners.forEach(listener => listener(update));
  }

  /**
   * Execute prediction using /tools/predict only (Market Scan contract)
   */
  async predict(
    symbol: string,
    horizon: 'intraday' | 'short' | 'long' = 'intraday',
    options: {
      riskProfile?: string;
      stopLossPct?: number;
      capitalRiskPct?: number;
      drawdownLimitPct?: number;
      forceRefresh?: boolean;
      _retryCount?: number;
    } = {}
  ): Promise<PredictOutcome> {
    const normalizedSymbol = symbol.trim().toUpperCase();

    // DEV-ONLY: Log force refresh
    if (import.meta.env.DEV && options.forceRefresh) {
      console.log('[REFRESH] Forcing full pipeline re-run for', normalizedSymbol);
    }

    if (import.meta.env.DEV) {
      console.log(`[API] POST /tools/predict called for ${normalizedSymbol}`);
      console.log(`[API] Request payload:`, { symbols: [normalizedSymbol], horizon, forceRefresh: options.forceRefresh || false });
    }

    try {
      this.notifyProgress({
        step: 'checking_dependencies',
        description: options.forceRefresh ? 'Refreshing analysis...' : `Analyzing ${normalizedSymbol}...`,
        progress: 0,
        symbol: normalizedSymbol
      });

      // Execute prediction directly
      this.notifyProgress({
        step: 'predicting',
        description: options.forceRefresh ? `Refreshing prediction for ${normalizedSymbol}...` : `Generating prediction for ${normalizedSymbol}...`,
        progress: 50,
        symbol: normalizedSymbol
      });

      const result = await stockAPI.predict(
        [normalizedSymbol],
        horizon,
        options.riskProfile,
        options.stopLossPct,
        options.capitalRiskPct,
        options.drawdownLimitPct,
        options.forceRefresh || false
      );

      const outcome = this.normalizePredictResponse(result, normalizedSymbol);

      if (outcome.status === 'success') {
        if (import.meta.env.DEV) {
          console.log(`[API] ✅ Success - prediction generated for ${normalizedSymbol}`);
          console.log(`[API] Response data:`, outcome.data);
        }

        this.notifyProgress({
          step: 'complete',
          description: `Prediction complete for ${normalizedSymbol}`,
          progress: 100,
          symbol: normalizedSymbol
        });
      } else {
        if (import.meta.env.DEV) {
          console.log(`[API] ❌ Failed - ${normalizedSymbol}: ${outcome.error || 'Unknown error'}`);
        }
        this.notifyProgress({
          step: 'error',
          description: outcome.error || 'Prediction failed',
          progress: 0,
          symbol: normalizedSymbol,
          error: outcome.error
        });
      }

      return outcome;
    } catch (error: any) {
      const message = error?.message || 'Prediction failed';

      console.error(`[PredictionService] Prediction failed for ${normalizedSymbol}:`, error);

      this.notifyProgress({
        step: 'error',
        description: message,
        progress: 0,
        symbol: normalizedSymbol,
        error: message
      });

      return {
        symbol: normalizedSymbol,
        status: 'failed',
        error: message
      };
    }
  }

  /**
   * Normalize prediction response to the strict Market Scan contract:
   * { results: [{ symbol, status, data?, error? }] }
   */
  private normalizePredictResponse(response: any, requestedSymbol: string): PredictOutcome {
    const fallbackSymbol = requestedSymbol.trim().toUpperCase();

    if (!response || typeof response !== 'object') {
      return {
        symbol: fallbackSymbol,
        status: 'failed',
        error: 'Invalid response from backend'
      };
    }

    // Primary contract: results array
    if (Array.isArray(response.results)) {
      const match = response.results.find((item: any) => {
        const itemSymbol = typeof item?.symbol === 'string' ? item.symbol.trim().toUpperCase() : '';
        return itemSymbol === fallbackSymbol;
      }) || response.results[0];

      if (!match) {
        return {
          symbol: fallbackSymbol,
          status: 'failed',
          error: 'No result returned for symbol'
        };
      }

      const symbol = typeof match.symbol === 'string' && match.symbol.trim() ? match.symbol : fallbackSymbol;
      const status = String(match.status || '').toLowerCase() === 'success' ? 'success' : 'failed';

      if (status === 'success') {
        if (match.data && typeof match.data === 'object') {
          return {
            symbol,
            status,
            data: { ...(match.data as PredictionItem), symbol }
          };
        }

        return {
          symbol,
          status: 'failed',
          error: match.error || 'Prediction data missing for symbol'
        };
      }

      return {
        symbol,
        status: 'failed',
        error: match.error || 'Prediction unavailable for this symbol'
      };
    }

    // Legacy contract: predictions array
    if (Array.isArray(response.predictions)) {
      const prediction = response.predictions.find((item: any) => {
        const itemSymbol = typeof item?.symbol === 'string' ? item.symbol.trim().toUpperCase() : '';
        return itemSymbol === fallbackSymbol;
      }) || response.predictions[0];

      if (!prediction) {
        return {
          symbol: fallbackSymbol,
          status: 'failed',
          error: 'No prediction returned from backend'
        };
      }

      const symbol = typeof prediction.symbol === 'string' && prediction.symbol.trim() ? prediction.symbol : fallbackSymbol;

      if (prediction.error) {
        return {
          symbol,
          status: 'failed',
          error: prediction.error
        };
      }

      return {
        symbol,
        status: 'success',
        data: { ...(prediction as PredictionItem), symbol }
      };
    }

    return {
      symbol: fallbackSymbol,
      status: 'failed',
      error: 'Invalid response from backend'
    };
  }

  async batchPredict(
    symbols: string[],
    horizon: 'intraday' | 'short' | 'long' = 'intraday',
    options: {
      riskProfile?: string;
      stopLossPct?: number;
      capitalRiskPct?: number;
      drawdownLimitPct?: number;
    } = {}
  ): Promise<Record<string, PredictOutcome>> {
    const results: Record<string, PredictOutcome> = {};

    for (const symbol of symbols) {
      const outcome = await this.predict(symbol, horizon, options);
      results[outcome.symbol] = outcome;
    }

    return results;
  }
}

export const predictionService = PredictionService.getInstance();
