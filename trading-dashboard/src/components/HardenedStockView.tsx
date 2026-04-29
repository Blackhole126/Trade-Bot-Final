import React, { useState } from 'react';
import { Search, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { useHardenedPrediction } from '../hooks/useHardenedData';
import { 
  HardenedDataStatusGuard, 
  HardenedTrustGateGuard, 
  HardenedPriceDisplayGuard, 
  FailureModeDisplay,
  HardenedLoadingGuard 
} from './HardenedUIGuards';
import { IntegrationInspector } from './IntegrationInspector';
import { type StrictPredictionResult } from '../validators/contractValidator';

const POPULAR_STOCKS = [
  'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'INFY.NS',
  'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'
];

interface DataStatusPanelProps {
  dataStatus: StrictPredictionResult['data_status'];
}

function DataStatusPanel({ dataStatus }: DataStatusPanelProps) {
  if (!dataStatus) return null;

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
  prediction: StrictPredictionResult;
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

interface HardenedPredictionCardProps {
  prediction: StrictPredictionResult;
}

function HardenedPredictionCard({ prediction }: HardenedPredictionCardProps) {
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

      {/* STRICT DATA STATUS GUARD */}
      <HardenedDataStatusGuard dataStatus={prediction.data_status}>
        <DataStatusPanel dataStatus={prediction.data_status} />
      </HardenedDataStatusGuard>

      <ModelOutputPanel prediction={prediction} />

      {/* STRICT TRUST GATE GUARD */}
      <HardenedTrustGateGuard prediction={prediction}>
        <div className="space-y-2">
          {prediction.current_price !== undefined && (
            <div className="flex justify-between">
              <span className="text-gray-600 text-sm">Current Price:</span>
              <span className="text-gray-900 font-semibold">${prediction.current_price.toFixed(2)}</span>
            </div>
          )}
          
          {/* STRICT PRICE DISPLAY GUARD */}
          <HardenedPriceDisplayGuard prediction={prediction}>
            <div className="flex justify-between">
              <span className="text-gray-600 text-sm">Predicted Price:</span>
              <span className="text-gray-900 font-semibold">${prediction.predicted_price!.toFixed(2)}</span>
            </div>
          </HardenedPriceDisplayGuard>

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
      </HardenedTrustGateGuard>

      {prediction.reason && (
        <div className="pt-3 border-t border-gray-200">
          <p className="text-gray-700 text-xs">{prediction.reason}</p>
        </div>
      )}
    </div>
  );
}

export default function HardenedStockView() {
  const [searchQuery, setSearchQuery] = useState('');
  const [horizon, setHorizon] = useState<'intraday' | 'short' | 'long'>('intraday');

  const { state, predict, reset, guardStates, apiResult } = useHardenedPrediction();

  const handleSearch = async (symbol: string) => {
    if (!symbol) return;
    reset();
    await predict([symbol], horizon);
  };

  const handleQuickSelect = (symbol: string) => {
    setSearchQuery(symbol);
    handleSearch(symbol);
  };

  return (
    <div className="space-y-6">
      {/* MANDATORY SESSION DISCLAIMER */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-center">
          <AlertTriangle className="h-5 w-5 text-yellow-600 mr-2" />
          <p className="text-yellow-800 text-sm font-medium">
            Signals reflect model behavior, not future price. Verify market data independently.
          </p>
        </div>
      </div>

      {/* SEARCH INTERFACE */}
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
            disabled={!searchQuery || state.loading}
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

      {/* LOADING STATE */}
      <HardenedLoadingGuard loading={state.loading}>
        {/* FAILURE MODE DISPLAYS - MUTUALLY EXCLUSIVE */}
        {state.backend_unavailable && (
          <FailureModeDisplay mode="backend_unavailable" error={state.error} />
        )}
        
        {state.backend_error_response && (
          <FailureModeDisplay mode="backend_error_response" error={state.error} />
        )}
        
        {state.invalid_data && (
          <FailureModeDisplay mode="invalid_data" error={state.error} />
        )}
        
        {state.contract_drift && (
          <FailureModeDisplay 
            mode="contract_drift" 
            error={state.error} 
            contractDriftDetails={state.contractDriftDetails} 
          />
        )}

        {/* SUCCESS STATE - ONLY RENDER IF VALIDATION PASSED */}
        {state.success && state.data && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-900">
              Predictions for {searchQuery} ({horizon})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {state.data.predictions.map((pred, index) => (
                <HardenedPredictionCard key={index} prediction={pred} />
              ))}
            </div>
          </div>
        )}
      </HardenedLoadingGuard>

      {/* DEV-ONLY INTEGRATION INSPECTOR */}
      <IntegrationInspector result={apiResult} guardStates={guardStates} />
    </div>
  );
}