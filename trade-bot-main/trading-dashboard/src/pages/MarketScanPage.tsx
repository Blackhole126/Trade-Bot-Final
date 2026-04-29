import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '../components/Layout';
import { stockAPI, type PredictionItem } from '../services/api';
import { predictionService, type PredictOutcome } from '../services/predictionService';
import { useAssetType } from '../contexts/AssetTypeContext';
import { useTheme } from '../contexts/ThemeContext';

import StocksView from '../components/StocksView';
import CryptoView from '../components/CryptoView';
import CommoditiesView from '../components/CommoditiesView';
import { TrendingUp, TrendingDown, Minus, BarChart3, ThumbsUp, Sparkles, Loader2, X, ChevronDown, ChevronUp, Brain, Cpu, Zap, AlertCircle } from 'lucide-react';
import StopLoss from '../components/StopLoss';
import CandlestickChart from '../components/CandlestickChart';

// Inner component that uses the context (wrapped by Layout)
const MarketScanContent = () => {
  const { assetType } = useAssetType();
  const { theme } = useTheme();

  const isLight = theme === 'light';
  const isSpace = theme === 'space';
  
  const [searchParams] = useSearchParams();
  const [searchQuery, setSearchQuery] = useState(searchParams.get('q') || '');
  const [predictionResults, setPredictionResults] = useState<Record<string, PredictOutcome>>({});
  const [resultOrder, setResultOrder] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{step: string; description: string; progress: number} | null>(null);
  const [horizon, setHorizon] = useState<'intraday' | 'short' | 'long'>('intraday');
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [selectedPrediction, setSelectedPrediction] = useState<PredictionItem | null>(null);
  const [showChart, setShowChart] = useState(false);
  const [chartSymbol, setChartSymbol] = useState<string | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [actualReturn, setActualReturn] = useState<string>('');
  const [feedbackText, setFeedbackText] = useState<string>('');

  const predictions = useMemo<PredictionItem[]>(() => {
    return resultOrder
      .map((symbol) => {
        const result = predictionResults[symbol];
        if (!result) return null;

        if (result.status === 'success' && result.data) {
          return result.data;
        }

        return {
          symbol: result.symbol,
          reason: result.error || 'Prediction unavailable for this symbol at the moment.',
          error: result.error,
          unavailable: true
        };
      })
      .filter((item): item is PredictionItem => Boolean(item));
  }, [predictionResults, resultOrder]);

  const isConnectionError = (message: string) => {
    const lower = message.toLowerCase();
    return (
      lower.includes('unable to connect') ||
      lower.includes('cannot connect') ||
      lower.includes('backend server is not') ||
      lower.includes('econnrefused') ||
      lower.includes('network error')
    );
  };

  const isAuthError = (message: string) => {
    const lower = message.toLowerCase();
    return (
      lower.includes('authentication') ||
      lower.includes('session expired') ||
      lower.includes('login')
    );
  };

  // Add progress listener
  useEffect(() => {
    const handleProgress = (update: {step: string; description: string; progress: number; error?: string}) => {
      setProgress({step: update.step, description: update.description, progress: update.progress});
    };
    
    predictionService.addProgressListener(handleProgress);
    
    return () => {
      predictionService.removeProgressListener(handleProgress);
    };
  }, []);

  // Check backend connection on mount and periodically
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const result = await stockAPI.checkConnection();
        if (!result.connected) {
          setGlobalError(result.error || 'Backend server is not reachable');
        } else {
          // Clear error if connection is successful
          setGlobalError((prevError) => {
            if (prevError && isConnectionError(prevError)) {
              return null;
            }
            return prevError;
          });
        }
      } catch (err) {
        setGlobalError('Backend server is not reachable');
      }
    };
    
    // Check immediately
    checkConnection();
    
    // Check every 120 seconds (2 minutes) to reduce API calls and stay under rate limit
    const interval = setInterval(checkConnection, 120000);
    
    return () => clearInterval(interval);
  }, []); // Empty dependency array - only run on mount

  // Load search query from URL params - DO NOT auto-trigger search
  useEffect(() => {
    const queryParam = searchParams.get('q');
    if (queryParam && searchQuery !== queryParam) {
      setSearchQuery(queryParam);
    }
  }, [searchParams]);

  // Reset state when asset type changes
  useEffect(() => {
    setPredictionResults({});
    setResultOrder([]);
    setGlobalError(null);
    // Don't clear searchQuery here - let URL params handle it
  }, [assetType]);

  const commitResults = (outcomes: PredictOutcome[]) => {
    if (!outcomes || outcomes.length === 0) {
      setPredictionResults({});
      setResultOrder([]);
      return;
    }

    const nextResults: Record<string, PredictOutcome> = {};
    const nextOrder: string[] = [];

    outcomes.forEach((outcome) => {
      const symbol = outcome.symbol?.trim().toUpperCase();
      if (!symbol) return;
      const normalizedOutcome: PredictOutcome = {
        symbol,
        status: outcome.status || 'failed',
        data: outcome.data,
        error: outcome.error
      };
      nextResults[symbol] = normalizedOutcome;
      nextOrder.push(symbol);
    });

    setPredictionResults(nextResults);
    setResultOrder(nextOrder);
  };

  const handleSearch = async (symbol: string, isUserInitiated: boolean = false, forceRefresh: boolean = false) => {
    if (!symbol || symbol.trim() === '') {
      return;
    }
    
    if (!isUserInitiated) {
      return;
    }
    
    // Normalize symbol
    const normalizedSymbol = symbol.trim().toUpperCase();
    
    // Validate symbol format
    if (!/^[A-Z0-9&.-]+$/.test(normalizedSymbol)) {
      commitResults([{
        symbol: normalizedSymbol,
        status: 'failed',
        error: 'Invalid symbol format. Use only letters, numbers, and symbols like . - &'
      }]);
      return;
    }
    
    if (import.meta.env.DEV) {
      console.log(`[SYMBOL] Processing: ${normalizedSymbol}`);
    }
    
    setLoading(true);
    setGlobalError(null);
    setProgress(null);
    setSearchQuery(normalizedSymbol);
    
    try {
      const outcome = await predictionService.predict(normalizedSymbol, horizon, { forceRefresh });
      const normalizedOutcome: PredictOutcome = {
        symbol: outcome.symbol?.trim().toUpperCase() || normalizedSymbol,
        status: outcome.status || 'failed',
        data: outcome.data,
        error: outcome.error
      };

      commitResults([normalizedOutcome]);

      if (import.meta.env.DEV) {
        if (normalizedOutcome.status === 'success') {
          console.log(`[SYMBOL] Prediction success: ${normalizedSymbol}`);
        } else {
          console.log(`[SYMBOL] Backend error: ${normalizedSymbol} - ${normalizedOutcome.error || 'Unknown error'}`);
        }
      }

      if (normalizedOutcome.error && (isConnectionError(normalizedOutcome.error) || isAuthError(normalizedOutcome.error))) {
        setGlobalError(normalizedOutcome.error);
      }
    } catch (error: any) {
      const errMsg = error?.message || 'Prediction failed';

      if (import.meta.env.DEV) {
        console.log(`[SYMBOL] Backend error: ${normalizedSymbol} - ${errMsg}`);
      }

      commitResults([{
        symbol: normalizedSymbol,
        status: 'failed',
        error: errMsg
      }]);

      if (isConnectionError(errMsg) || isAuthError(errMsg)) {
        setGlobalError(errMsg);
      }
    } finally {
      setLoading(false);
      setProgress(null);
    }
  };

  // Removed handleScanAll - not currently used in UI

  const handleFeedback = async () => {
    if (!selectedPrediction) {
      return;
    }
    
    // Validate feedback text
    if (!feedbackText.trim()) {
      setFeedbackError('Please provide feedback text');
      return;
    }
    
    setFeedbackLoading(true);
    setFeedbackError(null);
    
    try {
      // Parse actual_return if provided
      // Backend expects: number | null (not undefined)
      let actualReturnValue: number | null | undefined = undefined;
      if (actualReturn.trim() !== '') {
        const parsed = parseFloat(actualReturn.trim());
        if (isNaN(parsed)) {
          throw new Error('Actual return must be a valid number');
        }
        // Validate range before sending
        if (parsed < -100 || parsed > 1000) {
          throw new Error(`Actual return must be between -100% and 1000%, got: ${parsed}%`);
        }
        actualReturnValue = parsed;
      } else {
        // Empty string means no value - send undefined (will be omitted from payload)
        actualReturnValue = undefined;
      }

      // Map action: LONG -> BUY, SHORT -> SELL, HOLD -> HOLD
      // Also support if action is already BUY/SELL
      let action = selectedPrediction.action?.toUpperCase().trim() || 'HOLD';
      const actionMapping: { [key: string]: string } = {
        'LONG': 'BUY',
        'SHORT': 'SELL',
        'HOLD': 'HOLD'
      };
      // If action is already BUY/SELL, keep it; otherwise map LONG->BUY, SHORT->SELL
      if (actionMapping[action]) {
        action = actionMapping[action];
      }
      
      // Ensure symbol is valid
      const symbol = selectedPrediction.symbol?.trim() || '';
      if (!symbol) {
        throw new Error('Symbol is required');
      }
      
      const result = await stockAPI.feedback(
        symbol,
        action,
        feedbackText.trim(),
        actualReturnValue
      );

      // Check for validation warnings from backend
      if (result.validation_warning) {
        setFeedbackError(result.validation_warning);
        if (result.suggested_feedback) {
          setFeedbackError(`${result.validation_warning}\n\nSuggested feedback: ${result.suggested_feedback}`);
        }
        setFeedbackLoading(false);
        return;
      }

      // Success
      setShowFeedbackModal(false);
      setSelectedPrediction(null);
      setActualReturn('');
      setFeedbackText('');
      setFeedbackError(null);
      
      // Show success message with feedback stats if available
      const statsMsg = result.feedback_stats 
        ? `\n\nTotal feedback: ${result.feedback_stats.total_feedback_count || 0}\nSymbol feedback: ${result.feedback_stats.symbol_feedback_count || 0}`
        : '';
      alert(`Feedback submitted successfully!${statsMsg}`);
    } catch (error: any) {
      
      // Handle different error types
      let errorMessage = 'Failed to submit feedback';
      
      if (error.response?.data) {
        const responseData = error.response.data;
        
        if (responseData.detail) {
          const detail = responseData.detail;
          
          if (typeof detail === 'string') {
            errorMessage = detail;
          } else if (Array.isArray(detail)) {
            // Pydantic validation errors (422)
            const validationErrors = detail.map((err: any) => {
              const field = err.loc?.join('.') || 'unknown';
              return `${field}: ${err.msg}`;
            });
            errorMessage = `Validation errors:\n${validationErrors.join('\n')}`;
          } else if (typeof detail === 'object') {
            // Structured error response
            if (detail.error) {
              errorMessage = detail.error;
            }
            if (detail.validation_warning) {
              errorMessage += (errorMessage ? '\n\n' : '') + detail.validation_warning;
            }
            if (detail.suggested_feedback) {
              errorMessage += (errorMessage ? '\n\n' : '') + `Suggested: ${detail.suggested_feedback}`;
            }
          }
        } else if (responseData.error) {
          errorMessage = responseData.error;
        } else if (responseData.message) {
          errorMessage = responseData.message;
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      setFeedbackError(errorMessage);
    } finally {
      setFeedbackLoading(false);
    }
  };

  const getActionIcon = (action: string) => {
    switch (action?.toUpperCase()) {
      case 'LONG':
      case 'BUY':
        return <TrendingUp className="w-5 h-5 text-green-400" />;
      case 'SHORT':
      case 'SELL':
        return <TrendingDown className="w-5 h-5 text-red-400" />;
      case 'HOLD':
      default:
        return <Minus className="w-5 h-5 text-yellow-400" />;
    }
  };

  // Render appropriate view based on asset type
  const renderAssetView = () => {
    if (assetType === 'stocks') {
      return (
        <StocksView
          onSearch={handleSearch}
          predictions={predictions}
          loading={loading}
          error={globalError}
          horizon={horizon}
          onHorizonChange={setHorizon}
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
          progress={progress}
        />
      );
    } else if (assetType === 'crypto') {
      return (
        <CryptoView
          onSearch={handleSearch}
          predictions={predictions}
          loading={loading}
          error={globalError}
          horizon={horizon}
          onHorizonChange={setHorizon}
        />
      );
    } else if (assetType === 'commodities') {
      return (
        <CommoditiesView
          onSearch={handleSearch}
          predictions={predictions}
          loading={loading}
          error={globalError}
          horizon={horizon}
          onHorizonChange={setHorizon}
        />
      );
    }
    // Default fallback
    return (
      <StocksView
        onSearch={handleSearch}
        predictions={predictions}
        loading={loading}
        error={globalError}
        horizon={horizon}
        onHorizonChange={setHorizon}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        progress={progress}
      />
    );
  };

  return (
    <div className="space-y-4 animate-fadeIn">
      {/* Connection Error Banner - Visible at top if backend is not reachable */}
      {globalError && isConnectionError(globalError) && (
        <div className={`border-2 rounded-xl p-4 ${
          isLight ? 'bg-red-50 border-red-300' : 'bg-red-900/30 border-red-500/50'
        }`}>
          <div className="flex items-start gap-3">
            <AlertCircle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
              isLight ? 'text-red-600' : 'text-red-400'
            }`} />
            <div className="flex-1">
              <p className={`font-semibold mb-2 ${
                isLight ? 'text-red-700' : 'text-red-400'
              }`}>Backend Server Not Running</p>
              <p className={`text-sm mb-3 ${
                isLight ? 'text-red-600' : 'text-red-300'
              }`}>{globalError}</p>
              <div className={`rounded-lg p-3 mt-2 ${
                isLight ? 'bg-gray-100' : 'bg-slate-800/50'
              }`}>
                <p className={`text-xs font-medium mb-1 ${
                  isLight ? 'text-gray-700' : 'text-gray-300'
                }`}>To start the backend server:</p>
                <code className={`text-xs block p-2 rounded ${
                  isLight ? 'text-green-700 bg-green-50' : 'text-green-400 bg-slate-900/50'
                }`}>
                  cd backend && python api_server.py
                </code>
                <p className={`text-xs mt-2 ${
                  isLight ? 'text-gray-600' : 'text-gray-400'
                }`}>
                  Or use the startup script: <code className={isLight ? 'text-yellow-700' : 'text-yellow-400'}>START_BACKEND_WATCHDOG.bat</code>
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Loading Indicator - Visible at top */}
      {loading && (
        <div className={`border rounded p-3 flex items-center justify-center gap-2 ${
          isLight ? 'bg-blue-50 border-blue-300' : 'bg-blue-500/10 border-blue-500/30'
        }`}>
          <Loader2 className={`w-4 h-4 animate-spin ${
            isLight ? 'text-blue-600' : 'text-blue-400'
          }`} />
          <div className="text-left">
            <span className={`font-semibold text-sm block ${
              isLight ? 'text-blue-700' : 'text-blue-400'
            }`}>Processing your request...</span>
            <span className={`text-xs ${
              isLight ? 'text-blue-600' : 'text-blue-300'
            }`}>First-time predictions take 60-90 seconds as models train. Please wait patiently.</span>
          </div>
        </div>
      )}
      
      {/* Asset Type Specific View - SINGLE RENDERING PIPELINE */}
      {renderAssetView()}
      
      {/* Candlestick Chart */}
      {showChart && chartSymbol && (
        <CandlestickChart 
          symbol={chartSymbol} 
          exchange={assetType === 'stocks' ? 'NSE' : assetType === 'crypto' ? 'CRYPTO' : 'COMMODITY'}
          onClose={() => {
            setShowChart(false);
            setChartSymbol(null);
          }}
          onPriceUpdate={(price) => {
            // Update predictions with live price for stop-loss panel
            if (!chartSymbol) return;
            const symbolKey = chartSymbol.trim().toUpperCase();
            setPredictionResults(prev => {
              const existing = prev[symbolKey];
              if (!existing || existing.status !== 'success' || !existing.data) {
                return prev;
              }
              return {
                ...prev,
                [symbolKey]: {
                  ...existing,
                  data: {
                    ...existing.data,
                    current_price: price,
                    predicted_price: price
                  }
                }
              };
            });
          }}
        />
      )}
      
      {/* Stop-Loss Calculator - Only shown when chart is active */}
      {chartSymbol && (
        <StopLoss 
          chartSymbol={chartSymbol}
          chartPrice={predictions.find(p => p.symbol === chartSymbol)?.current_price || predictions.find(p => p.symbol === chartSymbol)?.predicted_price || null}
          onClose={() => {
            // Stop-loss panel closed - keep chart open
          }}
        />
      )}
      
      {/* Enhanced Analysis Results Section - Added to StocksView component for better organization */}
      
      {showFeedbackModal && selectedPrediction && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-fadeIn p-4">
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700 max-w-md w-full shadow-2xl animate-slideIn">
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <ThumbsUp className="w-5 h-5 text-blue-400" />
                  Provide Feedback
                </h3>
                <button
                  onClick={() => {
                    setShowFeedbackModal(false);
                    setSelectedPrediction(null);
                    setActualReturn('');
                    setFeedbackText('');
                    setFeedbackError(null);
                  }}
                  className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                  disabled={feedbackLoading}
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>

              {/* Prediction Info Card */}
              <div className="bg-gradient-to-br from-slate-700/50 to-slate-800/50 rounded-lg p-4 mb-4 border border-slate-600/50">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-white">{selectedPrediction.symbol}</span>
                    <span className={`px-3 py-1 rounded-lg text-xs font-bold ${
                      selectedPrediction.action?.toUpperCase() === 'LONG' || selectedPrediction.action?.toUpperCase() === 'BUY' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50' :
                      selectedPrediction.action?.toUpperCase() === 'SHORT' || selectedPrediction.action?.toUpperCase() === 'SELL' ? 'bg-purple-500/20 text-purple-400 border border-purple-500/50' :
                      'bg-gray-500/20 text-gray-400 border border-gray-500/50'
                    }`}>
                      {selectedPrediction.action?.toUpperCase() === 'LONG' ? 'UPTREND' :
                       selectedPrediction.action?.toUpperCase() === 'SHORT' ? 'DOWNTREND' :
                       selectedPrediction.action?.toUpperCase() || 'NEUTRAL'}
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 mt-3">
                  <div>
                    <p className="text-xs text-gray-400 mb-1">Model Reference Price</p>
                    <p className="text-sm font-semibold text-white">
                      ${(selectedPrediction.current_price || 0).toFixed(2)}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">Yahoo Finance OHLC</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 mb-1">Predicted Price</p>
                    <p className="text-sm font-semibold text-blue-400">
                      ${(selectedPrediction.predicted_price || selectedPrediction.current_price || 0).toFixed(2)}
                    </p>
                  </div>
                </div>
                {selectedPrediction.predicted_return !== undefined && (
                  <div className="mt-2 pt-2 border-t border-slate-600/50">
                    <p className="text-xs text-gray-400 mb-1">Predicted Return</p>
                    <p className={`text-sm font-bold ${
                      selectedPrediction.predicted_return >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {selectedPrediction.predicted_return >= 0 ? '+' : ''}
                      {selectedPrediction.predicted_return.toFixed(2)}%
                    </p>
                  </div>
                )}
              </div>

              {/* User Feedback Text Input (Required) */}
              <div className="mb-4">
                <label className="block text-xs font-medium text-gray-300 mb-2">
                  Your Feedback <span className="text-red-400">*</span>
                </label>
                <textarea
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  placeholder="e.g., Model suggested BUY but price reversed after entry"
                  rows={4}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all resize-none"
                  disabled={feedbackLoading}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Describe your feedback about this prediction (e.g., "correct", "incorrect", "price reversed", etc.)
                </p>
              </div>

              {/* Actual Return Input (Optional) */}
              <div className="mb-4">
                <label className="block text-xs font-medium text-gray-300 mb-2">
                  Actual Return % <span className="text-gray-500">(Optional)</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="-100"
                  max="1000"
                  value={actualReturn}
                  onChange={(e) => setActualReturn(e.target.value)}
                  placeholder="e.g., 5.25 or -2.10"
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
                  disabled={feedbackLoading}
                />
                <p className="text-xs text-gray-500 mt-1">Range: -100% to 1000%</p>
              </div>

              {/* Error Message */}
              {feedbackError && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-red-300 whitespace-pre-line">{feedbackError}</p>
                  </div>
                </div>
              )}

              {/* Submit and Cancel Buttons */}
              <div className="space-y-3">
                <button
                  onClick={handleFeedback}
                  disabled={feedbackLoading || !feedbackText.trim()}
                  className="w-full px-4 py-3 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 disabled:from-blue-500/50 disabled:to-blue-600/50 disabled:cursor-not-allowed text-white rounded-lg flex items-center justify-center gap-2 text-sm font-semibold transition-all hover:scale-[1.02] active:scale-[0.98] shadow-lg hover:shadow-blue-500/50"
                >
                  {feedbackLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Submitting...</span>
                    </>
                  ) : (
                    <>
                      <ThumbsUp className="w-4 h-4" />
                      <span>Submit Feedback</span>
                    </>
                  )}
                </button>
                <button
                  onClick={() => {
                    setShowFeedbackModal(false);
                    setSelectedPrediction(null);
                    setActualReturn('');
                    setFeedbackText('');
                    setFeedbackError(null);
                  }}
                  disabled={feedbackLoading}
                  className="w-full px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-700/50 disabled:cursor-not-allowed text-white rounded-lg transition-all text-sm font-medium"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
    </div>
  );
};

// Outer component that wraps with Layout
const MarketScanPage = () => {
  return (
    <Layout>
      <MarketScanContent />
    </Layout>
  );
};

export default MarketScanPage;
