import axios, { AxiosResponse } from 'axios';
import { validatePredictResponse, detectContractDrift, type StrictPredictResponse, type ContractDriftError } from '../validators/contractValidator';

const API_BASE_URL = import.meta.env.VITE_API_BASE_BACKEND_URL || 'http://127.0.0.1:8000';

// FAILURE MODES - MUTUALLY EXCLUSIVE
export type FailureMode =
  | 'backend_unavailable'
  | 'backend_error_response'
  | 'invalid_data'
  | 'contract_drift'
  | 'trust_gate_active';

export interface HardenedApiResult<T> {
  success: boolean;
  data?: T;
  failureMode?: FailureMode;
  error?: string;
  contractDrift?: ContractDriftError;
  rawResponse?: any;
}

// DEV-ONLY LOGGING
function logIntegration(endpoint: string, response: any, validation: any, drift: any) {
  if (import.meta.env.DEV) {
    console.group(`[INTEGRATION] ${endpoint}`);
    console.log('Raw Response:', response);
    console.log('Validation:', validation);
    console.log('Contract Drift:', drift);
    console.groupEnd();
  }
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 480000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const hardenedAPI = {
  async predict(symbols: string[], horizon: string = 'intraday'): Promise<HardenedApiResult<StrictPredictResponse>> {
    try {
      const response: AxiosResponse = await apiClient.post('/tools/predict', {
        symbols,
        horizon,
      });

      // STRICT VALIDATION - NO OPTIONAL CHAINING
      const validation = validatePredictResponse(response.data);
      const drift = detectContractDrift(response.data, validation);

      logIntegration('POST /tools/predict', response.data, validation, drift);

      // CONTRACT DRIFT DETECTION
      if (drift) {
        return {
          success: false,
          failureMode: 'contract_drift',
          error: 'Backend response does not match expected contract',
          contractDrift: drift,
          rawResponse: response.data
        };
      }

      // VALIDATION FAILURE
      if (!validation.valid) {
        return {
          success: false,
          failureMode: 'invalid_data',
          error: `Response validation failed: ${validation.errors.join(', ')}`,
          rawResponse: response.data
        };
      }

      return {
        success: true,
        data: response.data as StrictPredictResponse,
        rawResponse: response.data
      };

    } catch (error: any) {
      // BACKEND UNAVAILABLE
      if (!error.response) {
        return {
          success: false,
          failureMode: 'backend_unavailable',
          error: 'Backend server is not reachable'
        };
      }

      // BACKEND ERROR RESPONSE
      return {
        success: false,
        failureMode: 'backend_error_response',
        error: error.response?.data?.detail || error.message || 'Backend returned error'
      };
    }
  },

  async health(): Promise<HardenedApiResult<{ status: string }>> {
    try {
      const response: AxiosResponse = await apiClient.get('/tools/health');

      // STRICT VALIDATION
      if (!response.data || typeof response.data.status !== 'string') {
        return {
          success: false,
          failureMode: 'invalid_data',
          error: 'Health response validation failed',
          rawResponse: response.data
        };
      }

      logIntegration('GET /tools/health', response.data, { valid: true }, null);

      return {
        success: true,
        data: response.data,
        rawResponse: response.data
      };

    } catch (error: any) {
      if (!error.response) {
        return {
          success: false,
          failureMode: 'backend_unavailable',
          error: 'Backend server is not reachable'
        };
      }

      return {
        success: false,
        failureMode: 'backend_error_response',
        error: error.response?.data?.detail || error.message || 'Health check failed'
      };
    }
  }
};