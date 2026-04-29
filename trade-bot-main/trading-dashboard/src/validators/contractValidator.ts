// FRONTEND CONTRACT VERSION - DO NOT MODIFY WITHOUT BACKEND COORDINATION
export const FRONTEND_CONTRACT_VERSION = '1.0.0';

// STRICT BACKEND CONTRACT - ALL FIELDS REQUIRED UNLESS EXPLICITLY OPTIONAL
export interface StrictDataStatus {
  data_source: 'REALTIME_YAHOO_FINANCE' | 'CACHED_YAHOO_FINANCE' | 'FALLBACK_PROVIDER' | 'INVALID';
  data_freshness_seconds: number;
  market_context: 'NORMAL' | 'HIGH_VOLATILITY' | 'EVENT_WINDOW' | 'MARKET_CLOSED';
}

export interface StrictPredictionResult {
  symbol: string;
  data_status: StrictDataStatus; // REQUIRED
  trust_gate_active: boolean; // REQUIRED
  // Optional fields that backend may omit
  action?: string;
  predicted_return?: number;
  current_price?: number;
  predicted_price?: number;
  model_agreement?: string;
  signal_strength?: number;
  trust_gate_reason?: string;
  error?: string;
  reason?: string;
}

export interface StrictPredictResponse {
  metadata: {
    count: number;
    horizon: string;
  };
  predictions: StrictPredictionResult[];
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  contractDrift: boolean;
}

// STRICT VALIDATION - NO OPTIONAL CHAINING, NO SILENT DEFAULTS
export function validateDataStatus(obj: any): ValidationResult {
  const errors: string[] = [];
  
  if (!obj) {
    errors.push('data_status is null or undefined');
    return { valid: false, errors, contractDrift: true };
  }
  
  if (typeof obj.data_source !== 'string') {
    errors.push('data_status.data_source must be string');
  } else if (!['REALTIME_YAHOO_FINANCE', 'CACHED_YAHOO_FINANCE', 'FALLBACK_PROVIDER', 'INVALID'].includes(obj.data_source)) {
    errors.push(`data_status.data_source invalid value: ${obj.data_source}`);
  }
  
  if (typeof obj.data_freshness_seconds !== 'number') {
    errors.push('data_status.data_freshness_seconds must be number');
  }
  
  if (typeof obj.market_context !== 'string') {
    errors.push('data_status.market_context must be string');
  } else if (!['NORMAL', 'HIGH_VOLATILITY', 'EVENT_WINDOW', 'MARKET_CLOSED'].includes(obj.market_context)) {
    errors.push(`data_status.market_context invalid value: ${obj.market_context}`);
  }
  
  return {
    valid: errors.length === 0,
    errors,
    contractDrift: errors.length > 0
  };
}

export function validatePredictionResult(obj: any): ValidationResult {
  const errors: string[] = [];
  
  if (!obj) {
    errors.push('prediction is null or undefined');
    return { valid: false, errors, contractDrift: true };
  }
  
  // REQUIRED FIELDS
  if (typeof obj.symbol !== 'string') {
    errors.push('prediction.symbol must be string');
  }
  
  if (typeof obj.trust_gate_active !== 'boolean') {
    errors.push('prediction.trust_gate_active must be boolean');
  }
  
  // data_status is REQUIRED
  const dataStatusValidation = validateDataStatus(obj.data_status);
  if (!dataStatusValidation.valid) {
    errors.push(...dataStatusValidation.errors.map(e => `prediction.${e}`));
  }
  
  // OPTIONAL FIELDS - validate type if present
  if (obj.predicted_return !== undefined && typeof obj.predicted_return !== 'number') {
    errors.push('prediction.predicted_return must be number if present');
  }
  
  if (obj.current_price !== undefined && typeof obj.current_price !== 'number') {
    errors.push('prediction.current_price must be number if present');
  }
  
  if (obj.predicted_price !== undefined && typeof obj.predicted_price !== 'number') {
    errors.push('prediction.predicted_price must be number if present');
  }
  
  if (obj.signal_strength !== undefined && typeof obj.signal_strength !== 'number') {
    errors.push('prediction.signal_strength must be number if present');
  }
  
  return {
    valid: errors.length === 0,
    errors,
    contractDrift: errors.length > 0
  };
}

export function validatePredictResponse(obj: any): ValidationResult {
  const errors: string[] = [];
  
  if (!obj) {
    errors.push('response is null or undefined');
    return { valid: false, errors, contractDrift: true };
  }
  
  // REQUIRED metadata
  if (!obj.metadata) {
    errors.push('response.metadata is required');
  } else {
    if (typeof obj.metadata.count !== 'number') {
      errors.push('response.metadata.count must be number');
    }
    if (typeof obj.metadata.horizon !== 'string') {
      errors.push('response.metadata.horizon must be string');
    }
  }
  
  // REQUIRED predictions array
  if (!Array.isArray(obj.predictions)) {
    errors.push('response.predictions must be array');
  } else {
    obj.predictions.forEach((pred: any, index: number) => {
      const predValidation = validatePredictionResult(pred);
      if (!predValidation.valid) {
        errors.push(...predValidation.errors.map(e => `response.predictions[${index}].${e}`));
      }
    });
  }
  
  return {
    valid: errors.length === 0,
    errors,
    contractDrift: errors.length > 0
  };
}

// DRIFT DETECTION
export interface ContractDriftError {
  type: 'CONTRACT_DRIFT';
  contractVersion: string;
  errors: string[];
  rawResponse: any;
}

export function detectContractDrift(response: any, validationResult: ValidationResult): ContractDriftError | null {
  if (validationResult.contractDrift) {
    return {
      type: 'CONTRACT_DRIFT',
      contractVersion: FRONTEND_CONTRACT_VERSION,
      errors: validationResult.errors,
      rawResponse: response
    };
  }
  return null;
}