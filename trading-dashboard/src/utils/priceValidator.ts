/**
 * Price Validation Utility
 * Ensures stock prices are valid and not fallback values
 */

interface PriceValidationResult {
  valid: boolean;
  isFallback: boolean;
  error?: string;
  source?: string;
}

// Common fallback/default prices that should be rejected
const FALLBACK_PRICES = [0, 1, 100, 1000];

// Reasonable price ranges by market
const PRICE_RANGES: Record<string, { min: number; max: number }> = {
  'US': { min: 0.01, max: 10000 },
  'INDIA': { min: 0.05, max: 50000 },
  'DEFAULT': { min: 0.01, max: 100000 }
};

/**
 * Validate a stock price
 * @param price - The price to validate
 * @param symbol - The stock symbol (for market-specific validation)
 * @returns Validation result with status and error information
 */
export function validatePrice(price: number, symbol: string): PriceValidationResult {
  // Check if price exists and is a number
  if (price === null || price === undefined || isNaN(price)) {
    return {
      valid: false,
      isFallback: true,
      error: 'Price is null or undefined',
      source: 'validation'
    };
  }

  // Check for fallback values
  if (FALLBACK_PRICES.includes(price)) {
    return {
      valid: false,
      isFallback: true,
      error: `Price ${price} is a common fallback value`,
      source: 'fallback_detection'
    };
  }

  // Check if price is positive
  if (price <= 0) {
    return {
      valid: false,
      isFallback: true,
      error: `Price must be positive, got ${price}`,
      source: 'range_check'
    };
  }

  // Determine market for range validation
  const market = symbol.includes('.NS') || symbol.includes('.BO') ? 'INDIA' : 'US';
  const range = PRICE_RANGES[market] || PRICE_RANGES.DEFAULT;

  // Check if price is within reasonable range
  if (price < range.min || price > range.max) {
    return {
      valid: false,
      isFallback: false,
      error: `Price ${price} is outside reasonable range for ${market} market (${range.min}-${range.max})`,
      source: 'range_check'
    };
  }

  // Log successful validation
  console.log(`[PRICE_VALIDATION] ${symbol}: ${price} validated successfully`);
  
  return {
    valid: true,
    isFallback: false,
    source: 'validated'
  };
}

/**
 * Validate API response price data
 * @param prediction - Prediction object from API
 * @param symbol - Stock symbol
 * @returns Validated price or throws error
 */
export function validateApiResponsePrice(prediction: any, symbol: string): number {
  const predictedPrice = prediction?.predicted_price;
  const currentPrice = prediction?.current_price;
  
  // Try predicted price first
  if (predictedPrice !== undefined && predictedPrice !== null) {
    const validation = validatePrice(predictedPrice, symbol);
    if (validation.valid) {
      console.log(`[API_VALIDATION] Using predicted_price for ${symbol}: ${predictedPrice}`);
      return predictedPrice;
    }
    console.warn(`[API_VALIDATION] Invalid predicted_price for ${symbol}:`, validation.error);
  }
  
  // Fall back to current_price
  if (currentPrice !== undefined && currentPrice !== null) {
    const validation = validatePrice(currentPrice, symbol);
    if (validation.valid) {
      console.log(`[API_VALIDATION] Using current_price for ${symbol}: ${currentPrice}`);
      return currentPrice;
    }
    console.warn(`[API_VALIDATION] Invalid current_price for ${symbol}:`, validation.error);
  }
  
  // No valid price found
  throw new Error(`No valid price available for ${symbol}. Predicted: ${predictedPrice}, Current: ${currentPrice}`);
}

/**
 * Get price source information for debugging
 * @param price - The price value
 * @param symbol - Stock symbol
 * @returns Source information string
 */
export function getPriceSourceInfo(price: number, symbol: string): string {
  const validation = validatePrice(price, symbol);
  
  if (validation.isFallback) {
    return `FALLBACK (${validation.error})`;
  }
  
  if (!validation.valid) {
    return `INVALID (${validation.error})`;
  }
  
  return `VALID (${validation.source})`;
}