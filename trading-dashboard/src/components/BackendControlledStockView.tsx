import React, { useState } from 'react';
import { Search, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { usePrediction, useFetchData, useAnalyze, useDependencies } from '../hooks/useBackendData';
import { DataStatusGuard, TrustGateGuard, PriceDisplayGuard, BackendErrorBoundary, LoadingGuard } from './UIGuards';
import { type PredictionResult, type DataStatus } from '../services/apiClient';

const POPULAR_STOCKS = [
  'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'INFY.NS',
  'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'
];

interface DataStatusPanelProps {
  dataStatus: DataStatus;
}

function DataStatusPanel({ dataStatus }: DataStatusPanelProps) {
  const getSourceLabel = (source: string) => {
    switch (source) {
      case 'REALTIME_YAHOO_FINANCE': return 'Real-time Yahoo Finance';
      case 'CACHED_YAHOO_FINANCE': return 'Cached Yahoo Finance';
      case 'FALLBACK_PROVIDER': return 'Fallback Provider';
      case 'INVALID': return 'Invalid Data';
      default: return source;
    }
  };

  const formatFreshness = (seconds: number) => {
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
  };

  const getStatusColor = () => {
    if (dataStatus.data_source === 'REALTIME_YAHOO_FINANCE') return 'text-green-600';
    if (dataStatus.data_source === 'CACHED_YAHOO_FINANCE' && dataStatus.data_freshness_seconds < 300) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-gray-50 border rounded-lg p-3">
      <h4 className="font-medium text-gray-900 mb-2">DATA STATUS</h4>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Source:</span>
          <span className={getStatusColor()}>{getSourceLabel(dataStatus.data_source)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Last Updated:</span>
          <span className="text-gray-900">{formatFreshness(dataStatus.data_freshness_seconds)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Market Context:</span>
          <span className="text-gray-900">{dataStatus.market_context}</span>
        </div>
      </div>
    </div>
  );
}

interface ModelOutputPanelProps {
  prediction: PredictionResult;
}

function ModelOutputPanel({ prediction }: ModelOutputPanelProps) {
  const getDirectionalBias = () => {
    if (prediction.action === 'LONG') return 'Bullish';
    if (prediction.action === 'SHORT') return 'Bearish';
    return 'Neutral';
  };

  const getBiasColor = () => {
    if (prediction.action === 'LONG') return 'text-green-600';
    if (prediction.action === 'SHORT') return 'text-red-600';
    return 'text-gray-600';
  };

  return (
    <div className="bg-gray-50 border rounded-lg p-3">
      <h4 className="font-medium text-gray-900 mb-2">MODEL OUTPUT</h4>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Directional Bias:</span>
          <span className={getBiasColor()}>{getDirectionalBias()}</span>
        </div>
        {prediction.model_agreement && (
          <div className="flex justify-between">
            <span className="text-gray-600">Model Agreement:</span>
            <span className="text-gray-900">{prediction.model_agreement}</span>
          </div>
        )}
        {prediction.signal_strength !== undefined && (
          <div className="flex justify-between">
            <span className="text-gray-600">Signal Strength:</span>
            <span className="text-gray-900">{prediction.signal_strength}/100</span>
          </div>
        )}
      </div>
    </div>
  );
}

interface PredictionCardProps {
  prediction: PredictionResult;
}

function PredictionCard({ prediction }: PredictionCardProps) {
  if (prediction.error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="font-medium text-red-800 mb-2">{prediction.symbol}</h3>
        <p className="text-red-600 text-sm">{prediction.error}</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-lg text-gray-900">{prediction.symbol}</h3>
        {prediction.action === 'LONG' && <TrendingUp className="w-5 h-5 text-green-600" />}
        {prediction.action === 'SHORT' && <TrendingDown className="w-5 h-5 text-red-600" />}
      </div>

      {prediction.data_status && (
        <DataStatusGuard dataStatus={prediction.data_status}>
          <DataStatusPanel dataStatus={prediction.data_status} />
        </DataStatusGuard>
      )}

      <ModelOutputPanel prediction={prediction} />

      <TrustGateGuard prediction={prediction}>
        <div className="space-y-2">
          {prediction.current_price !== undefined && (
            <div className="flex justify-between">
              <span className="text-gray-600 text-sm">Current Price:</span>
              <span className="text-gray-900 font-semibold">${prediction.current_price.toFixed(2)}</span>
            </div>
          )}
          
          <PriceDisplayGuard prediction={prediction}>
            {prediction.predicted_price !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-600 text-sm">Predicted Price:</span>
                <span className="text-gray-900 font-semibold">${prediction.predicted_price.toFixed(2)}</span>
              </div>
            )}
          </PriceDisplayGuard>

          {prediction.predicted_return !== undefined && (
            <div className="flex justify-between">
              <span className="text-gray-600 text-sm">Expected Return:</span>
              <span className={`font-semibold ${
                prediction.predicted_return > 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {prediction.predicted_return > 0 ? '+' : ''}{prediction.predicted_return.toFixed(2)}%
              </span>
            </div>
          )}
        </div>
      </TrustGateGuard>

      {prediction.reason && (
        <div className="pt-3 border-t border-gray-200">
          <p className="text-gray-700 text-xs">{prediction.reason}</p>
        </div>
      )}
    </div>
  );
}

export default function BackendControlledStockView() {
  const [searchQuery, setSearchQuery] = useState('');
  const [horizon, setHorizon] = useState<'intraday' | 'short' | 'long'>('intraday');

  const prediction = usePrediction();
  const fetchData = useFetchData();
  const analyze = useAnalyze();
  const dependencies = useDependencies();

  const handleSearch = async (symbol: string) => {
    if (!symbol) return;

    // Reset all states
    prediction.reset();
    fetchData.reset();
    analyze.reset();
    dependencies.reset();

    // Execute backend pipeline
    await dependencies.ensureDependencies([symbol]);
    await prediction.predict([symbol], horizon);
  };

  const handleQuickSelect = (symbol: string) => {
    setSearchQuery(symbol);
    handleSearch(symbol);
  };

  return (
    <div className="space-y-6">
      {/* Session Disclaimer */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-center">
          <AlertTriangle className="h-5 w-5 text-yellow-600 mr-2" />
          <p className="text-yellow-800 text-sm font-medium">
            Signals reflect model behavior, not future price. Verify market data independently.
          </p>
        </div>
      </div>

      {/* Search Interface */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex gap-3 mb-4">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
            placeholder="Enter stock symbol (e.g., AAPL, TCS.NS)"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={horizon}
            onChange={(e) => setHorizon(e.target.value as any)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="intraday">Intraday</option>
            <option value="short">Short (5 days)</option>
            <option value="long">Long (30 days)</option>
          </select>
          <button
            onClick={() => handleSearch(searchQuery)}
            disabled={!searchQuery || prediction.state.loading || dependencies.state.loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Search className="w-4 h-4" />
            Search
          </button>
        </div>

        <div>
          <p className="text-gray-700 mb-2 font-medium">Popular Stocks:</p>
          <div className="flex flex-wrap gap-2">
            {POPULAR_STOCKS.map((symbol) => (
              <button
                key={symbol}
                onClick={() => handleQuickSelect(symbol)}
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md hover:bg-blue-500 hover:text-white transition-colors text-sm"
              >
                {symbol.replace('.NS', '')}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Dependencies Status */}
      <LoadingGuard loading={dependencies.state.loading}>
        <BackendErrorBoundary error={dependencies.state.error} invalid_data={dependencies.state.invalid_data}>
          {dependencies.state.success && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <p className="text-green-800 text-sm font-medium">✓ Backend dependencies ready</p>
            </div>
          )}
        </BackendErrorBoundary>
      </LoadingGuard>

      {/* Predictions */}
      <LoadingGuard loading={prediction.state.loading}>
        <BackendErrorBoundary error={prediction.state.error} invalid_data={prediction.state.invalid_data}>
          {prediction.state.success && prediction.state.data && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-gray-900">
                Predictions for {searchQuery} ({horizon})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {prediction.state.data.predictions.map((pred, index) => (
                  <PredictionCard key={index} prediction={pred} />
                ))}
              </div>
            </div>
          )}
        </BackendErrorBoundary>
      </LoadingGuard>

      {/* No Data State */}
      {!prediction.state.loading && !prediction.state.error && !prediction.state.invalid_data && !prediction.state.data && searchQuery && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
          <p className="text-gray-600">No predictions available. Try searching for a different symbol.</p>
        </div>
      )}
    </div>
  );
}