import { useState, useCallback } from 'react';
import { backendAPI, type PredictResponse, type FetchDataResponse, type AnalyzeResponse } from '../services/apiClient';

interface DataState<T> {
  loading: boolean;
  success: boolean;
  error: string | null;
  invalid_data: boolean;
  data: T | null;
}

interface UsePredictionReturn {
  state: DataState<PredictResponse>;
  predict: (symbols: string[], horizon?: string) => Promise<void>;
  reset: () => void;
}

interface UseFetchDataReturn {
  state: DataState<FetchDataResponse>;
  fetchData: (symbols: string[]) => Promise<void>;
  reset: () => void;
}

interface UseAnalyzeReturn {
  state: DataState<AnalyzeResponse>;
  analyze: (symbol: string) => Promise<void>;
  reset: () => void;
}

interface UseDependenciesReturn {
  state: DataState<{ fetchData: boolean; calculateFeatures: boolean; trainModels: boolean }>;
  ensureDependencies: (symbols: string[]) => Promise<void>;
  reset: () => void;
}

function createInitialState<T>(): DataState<T> {
  return {
    loading: false,
    success: false,
    error: null,
    invalid_data: false,
    data: null,
  };
}

export function usePrediction(): UsePredictionReturn {
  const [state, setState] = useState<DataState<PredictResponse>>(createInitialState);

  const predict = useCallback(async (symbols: string[], horizon: string = 'intraday') => {
    setState(prev => ({ ...prev, loading: true, error: null, invalid_data: false }));

    const result = await backendAPI.predict(symbols, horizon);

    if (result.success && result.data) {
      setState({
        loading: false,
        success: true,
        error: null,
        invalid_data: false,
        data: result.data,
      });
    } else if (result.error) {
      setState({
        loading: false,
        success: false,
        error: result.error,
        invalid_data: false,
        data: null,
      });
    } else {
      setState({
        loading: false,
        success: false,
        error: null,
        invalid_data: true,
        data: null,
      });
    }
  }, []);

  const reset = useCallback(() => {
    setState(createInitialState);
  }, []);

  return { state, predict, reset };
}

export function useFetchData(): UseFetchDataReturn {
  const [state, setState] = useState<DataState<FetchDataResponse>>(createInitialState);

  const fetchData = useCallback(async (symbols: string[]) => {
    setState(prev => ({ ...prev, loading: true, error: null, invalid_data: false }));

    const result = await backendAPI.fetchData(symbols);

    if (result.success && result.data) {
      setState({
        loading: false,
        success: true,
        error: null,
        invalid_data: false,
        data: result.data,
      });
    } else if (result.error) {
      setState({
        loading: false,
        success: false,
        error: result.error,
        invalid_data: false,
        data: null,
      });
    } else {
      setState({
        loading: false,
        success: false,
        error: null,
        invalid_data: true,
        data: null,
      });
    }
  }, []);

  const reset = useCallback(() => {
    setState(createInitialState);
  }, []);

  return { state, fetchData, reset };
}

export function useAnalyze(): UseAnalyzeReturn {
  const [state, setState] = useState<DataState<AnalyzeResponse>>(createInitialState);

  const analyze = useCallback(async (symbol: string) => {
    setState(prev => ({ ...prev, loading: true, error: null, invalid_data: false }));

    const result = await backendAPI.analyze(symbol);

    if (result.success && result.data) {
      setState({
        loading: false,
        success: true,
        error: null,
        invalid_data: false,
        data: result.data,
      });
    } else if (result.error) {
      setState({
        loading: false,
        success: false,
        error: result.error,
        invalid_data: false,
        data: null,
      });
    } else {
      setState({
        loading: false,
        success: false,
        error: null,
        invalid_data: true,
        data: null,
      });
    }
  }, []);

  const reset = useCallback(() => {
    setState(createInitialState);
  }, []);

  return { state, analyze, reset };
}

export function useDependencies(): UseDependenciesReturn {
  const [state, setState] = useState<DataState<{ fetchData: boolean; calculateFeatures: boolean; trainModels: boolean }>>(createInitialState);

  const ensureDependencies = useCallback(async (symbols: string[]) => {
    setState(prev => ({ ...prev, loading: true, error: null, invalid_data: false }));

    try {
      // Execute dependency pipeline
      const fetchResult = await backendAPI.fetchData(symbols);
      if (!fetchResult.success) {
        throw new Error(fetchResult.error || 'Fetch data failed');
      }

      const featuresResult = await backendAPI.calculateFeatures(symbols);
      if (!featuresResult.success) {
        throw new Error(featuresResult.error || 'Calculate features failed');
      }

      const modelsResult = await backendAPI.trainModels(symbols);
      if (!modelsResult.success) {
        throw new Error(modelsResult.error || 'Train models failed');
      }

      setState({
        loading: false,
        success: true,
        error: null,
        invalid_data: false,
        data: {
          fetchData: true,
          calculateFeatures: true,
          trainModels: true,
        },
      });
    } catch (error: any) {
      setState({
        loading: false,
        success: false,
        error: error.message || 'Dependencies failed',
        invalid_data: false,
        data: null,
      });
    }
  }, []);

  const reset = useCallback(() => {
    setState(createInitialState);
  }, []);

  return { state, ensureDependencies, reset };
}