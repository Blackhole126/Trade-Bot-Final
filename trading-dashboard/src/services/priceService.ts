/**
 * Enhanced Price Service with Market Data Validation
 * 
 * Centralized management of all stock prices in the application.
 * Single source of truth for current prices with data integrity validation.
 * Ensures no fallback, mock, or invalid prices are used.
 */

import { stockAPI } from './api';
import { validatePrice, validateApiResponsePrice } from '../utils/priceValidator';
import { marketDataValidator } from '../utils/marketDataValidator';

interface CachedPrice {
  symbol: string;
  price: number;
  timestamp: number;
  source: 'api' | 'user-input';
  reliable: boolean;
  lastError?: string;
  dataIntegrity?: {
    isReal: boolean;
    confidence: string;
    validationMessage: string;
  };
}

type PriceCallback = (symbol: string, price: number) => void;

class PriceServiceClass {
  private cache = new Map<string, CachedPrice>();
  private updateCallbacks = new Map<string, Set<PriceCallback>>();
  private refreshPromises = new Map<string, Promise<Map<string, number>>>();
  private isRefreshingAll = false;
  private lastRefreshTime = 0;
  private CACHE_TTL = 120000; // 2 minutes
  private MIN_REFRESH_INTERVAL = 60000; // 1 minute between refreshes
  
  /**
   * Get current price for a symbol (from cache or null if not available)
   */
  getPrice(symbol: string): { price: number; reliable: boolean; source: string; dataIntegrity?: any } | null {
    const cached = this.cache.get(symbol);
    if (!cached) {
      return null;
    }

    // Check if cache is still valid
    const isStale = Date.now() - cached.timestamp > this.CACHE_TTL;

    return {
      price: cached.price,
      reliable: cached.reliable && !isStale,
      source: cached.source,
      dataIntegrity: cached.dataIntegrity
    };
  }

  /**
   * Get price and throw error if invalid
   * Use in components that require a valid price
   */
  getPriceOrThrow(symbol: string): number {
    const priceData = this.getPrice(symbol);

    if (!priceData) {
      throw new Error(`[PRICE SERVICE] No price available for ${symbol}. Backend may not have returned data.`);
    }

    if (!priceData.reliable) {
      throw new Error(`[PRICE SERVICE] Price for ${symbol} is stale or unreliable. Please refresh.`);
    }

    return priceData.price;
  }

  /**
   * Refresh prices for a list of symbols
   * Returns map of valid symbol -> price pairs
   */
  async refreshPrices(symbols: string[]): Promise<Map<string, number>> {
    if (!symbols || symbols.length === 0) {
      console.log('[PRICE SERVICE] No symbols to refresh');
      return new Map();
    }

    // Deduplicate symbols
    const uniqueSymbols = [...new Set(symbols.map(s => s.toUpperCase()))];

    // Check if we've refreshed recently
    const timeSinceLastRefresh = Date.now() - this.lastRefreshTime;
    if (timeSinceLastRefresh < this.MIN_REFRESH_INTERVAL && !this.isRefreshingAll) {
      console.log(`[PRICE SERVICE] Skipping refresh - only ${Math.round(timeSinceLastRefresh / 1000)}s since last refresh`);
      return this.getCachedPrices(uniqueSymbols);
    }

    // Check if already refreshing these symbols
    const cacheKey = uniqueSymbols.sort().join(',');
    if (this.refreshPromises.has(cacheKey)) {
      console.log('[PRICE SERVICE] Already refreshing these symbols, waiting for existing request...');
      return this.refreshPromises.get(cacheKey)!;
    }

    // Create refresh promise
    const refreshPromise = this._performRefresh(uniqueSymbols);
    this.refreshPromises.set(cacheKey, refreshPromise);

    try {
      const result = await refreshPromise;
      this.lastRefreshTime = Date.now();
      return result;
    } finally {
      this.refreshPromises.delete(cacheKey);
    }
  }

  /**
   * Internal method to perform the actual API call
   */
  private async _performRefresh(symbols: string[]): Promise<Map<string, number>> {
    try {
      console.log('[PRICE SERVICE] Refreshing prices for:', symbols);

      const response = await stockAPI.predict(symbols);

      if (!response.predictions) {
        console.error('[PRICE SERVICE] No predictions in response');
        return new Map();
      }

      const validPrices = new Map<string, number>();

      // Process predictions with enhanced validation
      for (const pred of response.predictions) {
        const validation = validatePrice(pred.current_price, pred.symbol);

        if (!validation.valid || validation.isFallback) {
          console.warn(`[PRICE SERVICE] Skipping invalid price for ${pred.symbol}: ${pred.current_price}`);
          continue;
        }

        // Market data validation
        const marketValidation = marketDataValidator.validatePriceData({
          symbol: pred.symbol,
          price: pred.current_price,
          timestamp: pred.price_metadata?.price_timestamp,
          source: pred.price_metadata?.price_source || 'api_response',
          metadata: pred.price_metadata
        });

        // Update cache with validation metadata
        this.cache.set(pred.symbol, {
          symbol: pred.symbol,
          price: pred.current_price,
          timestamp: Date.now(),
          source: 'api',
          reliable: marketValidation.isReal && marketValidation.confidence !== 'INVALID',
          dataIntegrity: {
            isReal: marketValidation.isReal,
            confidence: marketValidation.confidence,
            validationMessage: marketDataValidator.getValidationMessage(marketValidation)
          }
        });

        validPrices.set(pred.symbol, pred.current_price);

        // Notify subscribers
        this._notifyCallbacks(pred.symbol, pred.current_price);
      }

      // Log any missing symbols
      const cachedSymbols = Array.from(validPrices.keys());
      const missingSymbols = symbols.filter(s => !cachedSymbols.includes(s));

      if (missingSymbols.length > 0) {
        console.warn('[PRICE SERVICE] Missing prices for:', missingSymbols);

        // Mark missing symbols in cache with error
        for (const symbol of missingSymbols) {
          this.cache.set(symbol, {
            symbol,
            price: 0,
            timestamp: Date.now(),
            source: 'api',
            reliable: false,
            lastError: 'No price returned from API'
          });
        }
      }

      console.log(`[PRICE SERVICE] Refresh complete: ${validPrices.size}/${symbols.length} prices valid`);

      return validPrices;
    } catch (error: any) {
      console.error('[PRICE SERVICE] Refresh failed:', error.message);

      // Mark all symbols as unreliable on API error
      for (const symbol of symbols) {
        const cached = this.cache.get(symbol);
        if (cached) {
          cached.reliable = false;
          cached.lastError = error.message;
        }
      }

      // Return whatever we have cached (even if unreliable)
      return this.getCachedPrices(symbols);
    }
  }

  /**
   * Get cached prices for symbols (unreliable if stale)
   */
  private getCachedPrices(symbols: string[]): Map<string, number> {
    const prices = new Map<string, number>();

    for (const symbol of symbols) {
      const cached = this.cache.get(symbol);
      if (cached) {
        prices.set(symbol, cached.price);
      }
    }

    return prices;
  }

  /**
   * Subscribe to price changes for a symbol
   */
  onPriceChange(symbol: string, callback: PriceCallback): () => void {
    if (!this.updateCallbacks.has(symbol)) {
      this.updateCallbacks.set(symbol, new Set());
    }

    this.updateCallbacks.get(symbol)!.add(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.updateCallbacks.get(symbol);
      if (callbacks) {
        callbacks.delete(callback);
      }
    };
  }

  /**
   * Notify all subscribers of a price update
   */
  private _notifyCallbacks(symbol: string, price: number) {
    const callbacks = this.updateCallbacks.get(symbol);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(symbol, price);
        } catch (error) {
          console.error(`[PRICE SERVICE] Callback error for ${symbol}:`, error);
        }
      });
    }
  }

  /**
   * Clear cache (for testing or manual reset)
   */
  clearCache() {
    this.cache.clear();
    this.refreshPromises.clear();
    this.lastRefreshTime = 0;
    console.log('[PRICE SERVICE] Cache cleared');
  }

  /**
   * Get cache statistics (for debugging)
   */
  getStats() {
    const symbols = Array.from(this.cache.keys());
    const reliablePrices = symbols.filter(s => {
      const cached = this.cache.get(s)!;
      return cached.reliable && (Date.now() - cached.timestamp < this.CACHE_TTL);
    });

    return {
      totalCached: symbols.length,
      reliableCount: reliablePrices.length,
      symbols,
      details: Array.from(this.cache.entries()).map(([symbol, cached]) => ({
        symbol,
        price: cached.price,
        reliable: cached.reliable,
        age: Date.now() - cached.timestamp,
        source: cached.source,
        dataIntegrity: cached.dataIntegrity
      }))
    };
  }
}

// Export singleton instance
export const priceService = new PriceServiceClass();

// Export for testing
export { PriceServiceClass };
