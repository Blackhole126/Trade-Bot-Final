import { useState, useCallback } from 'react';
import { hardenedAPI, type HardenedApiResult, type FailureMode } from '../services/hardenedApiClient';
import { type StrictPredictResponse, type ContractDriftError } from '../validators/contractValidator';

// MUTUALLY EXCLUSIVE STATES - NO OVERLAP
interface HardenedDataState {
  loading: boolean;
  backend_unavailable: boolean;
  backend_error_response: boolean;
  invalid_data: boolean;
  contract_drift: boolean;
  success: boolean;
  data: StrictPredictResponse | null;
  error: string | null;
  contractDriftDetails: ContractDriftError | null;
  rawResponse: any;
}

function createInitialState(): HardenedDataState {
  return {
    loading: false,
    backend_unavailable: false,
    backend_error_response: false,
    invalid_data: false,
    contract_drift: false,
    success: false,
    data: null,
    error: null,
    contractDriftDetails: null,
    rawResponse: null,
  };
}

function setFailureState(
  setState: React.Dispatch<React.SetStateAction<HardenedDataState>>,
  result: HardenedApiResult<StrictPredictResponse>
) {
  const baseState = {
    loading: false,
    backend_unavailable: false,
    backend_error_response: false,
    invalid_data: false,
    contract_drift: false,
    success: false,
    data: null,
    error: result.error || null,
    contractDriftDetails: result.contractDrift || null,
    rawResponse: result.rawResponse || null,
  };

  switch (result.failureMode) {
    case 'backend_unavailable':
      setState({ ...baseState, backend_unavailable: true });
      break;
    case 'backend_error_response':
      setState({ ...baseState, backend_error_response: true });
      break;
    case 'invalid_data':
      setState({ ...baseState, invalid_data: true });
      break;
    case 'contract_drift':
      setState({ ...baseState, contract_drift: true });
      break;
    default:
      setState({ ...baseState, backend_error_response: true });
  }
}

export function useHardenedPrediction() {
  const [state, setState] = useState<HardenedDataState>(createInitialState);

  const predict = useCallback(async (symbols: string[], horizon: string = 'intraday') => {
    setState(prev => ({ ...prev, loading: true }));

    const result = await hardenedAPI.predict(symbols, horizon);

    if (result.success && result.data) {
      setState({
        loading: false,
        backend_unavailable: false,
        backend_error_response: false,
        invalid_data: false,
        contract_drift: false,
        success: true,
        data: result.data,
        error: null,
        contractDriftDetails: null,
        rawResponse: result.rawResponse || null,
      });
    } else {
      setFailureState(setState, result);
    }
  }, []);

  const reset = useCallback(() => {
    setState(createInitialState);
  }, []);

  // GUARD STATE CALCULATION
  const guardStates = {
    trustGateActive: state.data?.predictions.filter(p => p.trust_gate_active) || [],
    dataSourceBlocked: state.data?.predictions.filter(p => p.data_status?.data_source === 'INVALID') || [],
    priceDisplayBlocked: state.data?.predictions.filter(p => p.trust_gate_active || !p.predicted_price) || [],
  };

  return {
    state,
    predict,
    reset,
    guardStates: {
      trustGateActive: guardStates.trustGateActive.map(() => true),
      dataSourceBlocked: guardStates.dataSourceBlocked.map(() => true),
      priceDisplayBlocked: guardStates.priceDisplayBlocked.map(() => true),
    },
    apiResult: {
      success: state.success,
      failureMode: state.backend_unavailable ? 'backend_unavailable' as FailureMode :
                   state.backend_error_response ? 'backend_error_response' as FailureMode :
                   state.invalid_data ? 'invalid_data' as FailureMode :
                   state.contract_drift ? 'contract_drift' as FailureMode :
                   undefined,
      error: state.error,
      contractDrift: state.contractDriftDetails,
      rawResponse: state.rawResponse,
      data: state.data,
    } as HardenedApiResult<StrictPredictResponse>
  };
}