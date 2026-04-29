/**
 * Market Data Validator - Ensures data truthfulness and transparency
 * 
 * This module enforces that the frontend never presents data as "real" 
 * unless it is verifiably real and from a trusted source.
 */

interface MarketDataValidation {
  isValid: boolean;
  isReal: boolean;
  source: string;
  timestamp?: string;
  warnings: string[];
  errors: string[];
  dataAge?: number; // in minutes
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'INVALID';
}

interface PriceData {
  symbol: string;
  price: number;
  timestamp?: string;
  source?: string;
  metadata?: any;
}

interface ValidationConfig {
  maxAgeMinutes: number;
  trustedSources: string[];
  fallbackSources: string[];
}

const DEFAULT_CONFIG: ValidationConfig = {
  maxAgeMinutes: 15, // Data older than 15 minutes is considered stale
  trustedSources: [
    'yahoo_finance_live',
    'live_api',
    'real_time'
  ],
  fallbackSources: [
    'cached',
    'simulated',
    'model_derived',
    'fallback',
    'demo'
  ]
};

export class MarketDataValidator {
  private config: ValidationConfig;

  constructor(config: Partial<ValidationConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Validate market price data for truthfulness
   */
  validatePriceData(data: PriceData): MarketDataValidation {
    const validation: MarketDataValidation = {
      isValid: false,
      isReal: false,
      source: data.source || 'unknown',
      warnings: [],
      errors: [],
      confidence: 'INVALID'
    };

    // Check if price exists and is reasonable
    if (!data.price || data.price <= 0) {
      validation.errors.push('Invalid or missing price data');
      return validation;
    }

    // Check for obvious fallback values
    const fallbackPrices = [1, 100, 1000, 0.01];
    if (fallbackPrices.includes(data.price)) {
      validation.errors.push(`Price ${data.price} appears to be a fallback value`);
      validation.warnings.push('This may be simulated or demo data');
      return validation;
    }

    // Validate data source
    const sourceValidation = this.validateDataSource(data.source || 'unknown');
    validation.isReal = sourceValidation.isReal;
    validation.source = sourceValidation.normalizedSource;

    if (!sourceValidation.isReal) {
      validation.warnings.push(`Data source "${validation.source}" is not a real market feed`);
    }

    // Validate timestamp and data age
    if (data.timestamp) {
      const ageValidation = this.validateDataAge(data.timestamp);
      validation.dataAge = ageValidation.ageMinutes;
      validation.timestamp = data.timestamp;

      if (ageValidation.isStale) {
        validation.warnings.push(`Data is ${ageValidation.ageMinutes} minutes old`);
        if (ageValidation.ageMinutes > 60) {
          validation.errors.push('Data is too stale for trading decisions');
        }
      }
    } else {
      validation.warnings.push('No timestamp provided - cannot verify data freshness');
    }

    // Determine overall validity and confidence
    validation.isValid = validation.errors.length === 0;
    validation.confidence = this.calculateConfidence(validation);

    return validation;
  }

  /**
   * Validate API response for market data integrity
   */
  validateApiResponse(response: any): MarketDataValidation {
    const validation: MarketDataValidation = {
      isValid: false,
      isReal: false,
      source: 'api_response',
      warnings: [],
      errors: [],
      confidence: 'INVALID'
    };

    if (!response) {
      validation.errors.push('Empty API response');
      return validation;
    }

    // Check for error indicators
    if (response.error) {
      validation.errors.push(`API error: ${response.error}`);
      return validation;
    }

    // Validate predictions array
    if (response.predictions && Array.isArray(response.predictions)) {
      const invalidPredictions = response.predictions.filter((pred: any) => {
        if (pred.error) return true;
        if (!pred.current_price || pred.current_price <= 0) return true;
        return false;
      });

      if (invalidPredictions.length > 0) {
        validation.warnings.push(`${invalidPredictions.length} predictions have invalid data`);
      }

      // Check for price validation metadata
      const predictionsWithValidation = response.predictions.filter((pred: any) => 
        pred.price_metadata || pred._priceValidation
      );

      if (predictionsWithValidation.length === 0) {
        validation.warnings.push('No price validation metadata found in predictions');
      }
    }

    // Check metadata for data source information
    if (response.metadata) {
      if (response.metadata.data_source) {
        const sourceValidation = this.validateDataSource(response.metadata.data_source);
        validation.isReal = sourceValidation.isReal;
        validation.source = sourceValidation.normalizedSource;
      }

      if (response.metadata.timestamp) {
        validation.timestamp = response.metadata.timestamp;
        const ageValidation = this.validateDataAge(response.metadata.timestamp);
        validation.dataAge = ageValidation.ageMinutes;
      }
    }

    validation.isValid = validation.errors.length === 0;
    validation.confidence = this.calculateConfidence(validation);

    return validation;
  }

  /**
   * Validate data source trustworthiness
   */
  private validateDataSource(source: string): { isReal: boolean; normalizedSource: string } {
    const normalizedSource = source.toLowerCase().trim();

    // Check if it's a trusted real-time source
    const isReal = this.config.trustedSources.some(trusted => 
      normalizedSource.includes(trusted.toLowerCase())
    );

    // Check if it's a known fallback source
    const isFallback = this.config.fallbackSources.some(fallback => 
      normalizedSource.includes(fallback.toLowerCase())
    );

    return {
      isReal: isReal && !isFallback,
      normalizedSource: source
    };
  }

  /**
   * Validate data age
   */
  private validateDataAge(timestamp: string): { ageMinutes: number; isStale: boolean } {
    try {
      const dataTime = new Date(timestamp);
      const now = new Date();
      const ageMinutes = Math.floor((now.getTime() - dataTime.getTime()) / (1000 * 60));

      return {
        ageMinutes,
        isStale: ageMinutes > this.config.maxAgeMinutes
      };
    } catch (error) {
      return {
        ageMinutes: Infinity,
        isStale: true
      };
    }
  }

  /**
   * Calculate confidence level based on validation results
   */
  private calculateConfidence(validation: MarketDataValidation): 'HIGH' | 'MEDIUM' | 'LOW' | 'INVALID' {
    if (validation.errors.length > 0) {
      return 'INVALID';
    }

    if (!validation.isReal) {
      return 'LOW';
    }

    if (validation.warnings.length === 0 && validation.dataAge !== undefined && validation.dataAge < 5) {
      return 'HIGH';
    }

    if (validation.warnings.length <= 2 && validation.dataAge !== undefined && validation.dataAge < 30) {
      return 'MEDIUM';
    }

    return 'LOW';
  }

  /**
   * Generate user-friendly validation message
   */
  getValidationMessage(validation: MarketDataValidation): string {
    if (!validation.isValid) {
      return `Invalid data: ${validation.errors.join(', ')}`;
    }

    if (!validation.isReal) {
      return `Simulated data from ${validation.source}`;
    }

    const parts = [`Real market data from ${validation.source}`];
    
    if (validation.dataAge !== undefined) {
      if (validation.dataAge < 1) {
        parts.push('(Live)');
      } else if (validation.dataAge < 15) {
        parts.push(`(${validation.dataAge}min delay)`);
      } else {
        parts.push(`(${validation.dataAge}min old)`);
      }
    }

    if (validation.warnings.length > 0) {
      parts.push(`- ${validation.warnings.join(', ')}`);
    }

    return parts.join(' ');
  }

  /**
   * Check if data should be displayed to user
   */
  shouldDisplayData(validation: MarketDataValidation, requireReal: boolean = true): boolean {
    if (!validation.isValid) {
      return false;
    }

    if (requireReal && !validation.isReal) {
      return false;
    }

    return validation.confidence !== 'INVALID';
  }

  /**
   * Get display label for data source
   */
  getSourceLabel(validation: MarketDataValidation): string {
    if (!validation.isReal) {
      return 'SIMULATED';
    }

    if (validation.dataAge !== undefined) {
      if (validation.dataAge < 1) {
        return 'LIVE';
      } else if (validation.dataAge < 15) {
        return 'DELAYED';
      } else {
        return 'STALE';
      }
    }

    return 'UNKNOWN';
  }
}

// Export singleton instance
export const marketDataValidator = new MarketDataValidator();

// Export validation utilities
export const validateMarketPrice = (data: PriceData) => marketDataValidator.validatePriceData(data);
export const validateApiResponse = (response: any) => marketDataValidator.validateApiResponse(response);
export const shouldDisplayPrice = (validation: MarketDataValidation, requireReal = true) => 
  marketDataValidator.shouldDisplayData(validation, requireReal);