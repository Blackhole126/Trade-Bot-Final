import axios, { AxiosResponse } from 'axios';
import { validatePredictResponse, detectContractDrift, type StrictPredictResponse, type ContractDriftError } from '../validators/contractValidator';

const API_BASE_URL = import.meta.env.VITE_API_BASE_BACKEND_URL || 'https://trade-bot-api.onrender.com';

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
  timeout: 120000,
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
      const drift = detectContractDrift(response.data);
      
      logIntegration('predict', response.data, validation, drift);

      if (!validation.valid) {
        return {
          success: false,
          failureMode: 'invalid_data',
          error: validation.error,
          rawResponse: response.data,
        };
      }

      if (drift.hasDrift) {
        return {
          success: false,
          failureMode: 'contract_drift',
          error: `Contract drift detected: ${drift.errors?.join(', ')}`,
          contractDrift: drift,
          rawResponse: response.data,
        };
      }

      // Check for trust gate
      const hasTrustGate = response.data.predictions?.some(
        (p: any) => p.trust_gate_active === true
      );

      if (hasTrustGate) {
        return {
          success: false,
          failureMode: 'trust_gate_active',
          error: 'Trust gate is active - predictions blocked',
          rawResponse: response.data,
        };
      }

      return {
        success: true,
        data: response.data as StrictPredictResponse,
      };

    } catch (error: any) {
      if (error.response) {
        return {
          success: false,
          failureMode: 'backend_error_response',
          error: error.response.data?.detail || error.response.data?.error || 'Backend error',
          rawResponse: error.response.data,
        };
      }

      return {
        success: false,
        failureMode: 'backend_unavailable',
        error: 'Cannot connect to backend',
      };
    }
  },

  async fetchData(symbols: string[]): Promise<HardenedApiResult<FetchDataResponse>> {
    try {
      const response: AxiosResponse = await apiClient.post('/tools/fetch_data', {
        symbols,
      });

      return {
        success: true,
        data: response.data as FetchDataResponse,
      };

    } catch (error: any) {
      if (error.response) {
        return {
          success: false,
          failureMode: 'backend_error_response',
          error: error.response.data?.detail || error.response.data?.error || 'Backend error',
        };
      }

      return {
        success: false,
        failureMode: 'backend_unavailable',
        error: 'Cannot connect to backend',
      };
    }
  },
};

export { API_BASE_URL };
export type { PredictResponse, PredictionResult, FetchDataResponse, FetchDataResult, DataStatus };
