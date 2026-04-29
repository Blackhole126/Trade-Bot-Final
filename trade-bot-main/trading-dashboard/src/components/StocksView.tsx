import { useState, useEffect } from 'react';
import { Search, TrendingUp, TrendingDown, Sparkles, Loader2, BarChart3, Newspaper, Zap } from 'lucide-react';
import { POPULAR_STOCKS } from '../services/api';
import { formatUSDToINR } from '../utils/currencyConverter';
import SymbolAutocomplete from './SymbolAutocomplete';
import { useTheme } from '../contexts/ThemeContext';
import { DataStatusPanel } from './DataStatusPanel';
import { ModelOutputPanel } from './ModelOutputPanel';
import { TrustGateWarning } from './TrustGateWarning';
import { SessionDisclaimer } from './SessionDisclaimer';

interface StocksViewProps {
  onSearch: (symbol: string, isUserInitiated?: boolean, forceRefresh?: boolean) => void;
  predictions: any[];
  loading: boolean;
  error: string | null;
  horizon?: 'intraday' | 'short' | 'long';
  onHorizonChange?: (horizon: 'intraday' | 'short' | 'long') => void;
  searchQuery?: string;
  onSearchQueryChange?: (query: string) => void;
  progress?: {step: string; description: string; progress: number} | null;
}

const StocksView = ({
  onSearch,
  predictions,
  loading,
  error,
  horizon = 'intraday',
  onHorizonChange,
  searchQuery: externalSearchQuery,
  onSearchQueryChange,
  progress
}: StocksViewProps) => {
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const isSpace = theme === 'space';
  const [internalSearchQuery, setInternalSearchQuery] = useState('');
  const searchQuery = externalSearchQuery !== undefined ? externalSearchQuery : internalSearchQuery;
  const setSearchQuery = onSearchQueryChange || setInternalSearchQuery;
  
  // Request lock to prevent duplicate calls
  const [isRequestInProgress, setIsRequestInProgress] = useState(false);
  
  // Near-Live mode state
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(60); // seconds
  const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null);
  const [nextRefreshIn, setNextRefreshIn] = useState<number | null>(null);

  // Sync external search query to internal state
  useEffect(() => {
    if (externalSearchQuery !== undefined) {
      setInternalSearchQuery(externalSearchQuery);
    }
  }, [externalSearchQuery]);
  
  // Auto-refresh loop
  useEffect(() => {
    if (!autoRefreshEnabled || !searchQuery || isRequestInProgress) {
      setNextRefreshIn(null);
      return;
    }
    
    // Countdown timer
    const countdownInterval = setInterval(() => {
      if (lastRefreshTime) {
        const elapsed = Math.floor((Date.now() - lastRefreshTime.getTime()) / 1000);
        const remaining = Math.max(0, refreshInterval - elapsed);
        setNextRefreshIn(remaining);
      }
    }, 1000);
    
    // Auto-refresh timer
    const refreshTimer = setInterval(() => {
      if (!document.hidden && !isRequestInProgress) {
        console.log('[AUTO-REFRESH] Triggering snapshot update');
        handlePredict(searchQuery, true, true);
      }
    }, refreshInterval * 1000);
    
    return () => {
      clearInterval(countdownInterval);
      clearInterval(refreshTimer);
    };
  }, [autoRefreshEnabled, searchQuery, refreshInterval, isRequestInProgress, lastRefreshTime]);
  
  // Pause auto-refresh when tab is hidden
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden && autoRefreshEnabled) {
        console.log('[AUTO-REFRESH] Paused (tab hidden)');
      } else if (!document.hidden && autoRefreshEnabled) {
        console.log('[AUTO-REFRESH] Resumed (tab visible)');
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [autoRefreshEnabled]);
  
  // Combined search execution with request lock
  const handlePredict = async (symbol: string, userInitiated: boolean = true, forceRefresh: boolean = false) => {
    if (!symbol || isRequestInProgress) return;
    
    setIsRequestInProgress(true);
    try {
      await onSearch(symbol, userInitiated, forceRefresh);
      
      // Update last refresh time
      setLastRefreshTime(new Date());
    } catch (err) {
      console.error('[AUTO-REFRESH] Error during refresh:', err);
      // Stop auto-refresh on error
      if (autoRefreshEnabled) {
        setAutoRefreshEnabled(false);
        console.log('[AUTO-REFRESH] Stopped due to error');
      }
    } finally {
      setIsRequestInProgress(false);
    }
  };

  return (
    <div className="space-y-4">
      <SessionDisclaimer />
      <div>
        <h2 className={`text-xl font-bold ${
          isLight ? 'text-gray-900' : isSpace ? 'text-white drop-shadow-lg' : 'text-white'
        } mb-1 flex items-center gap-2`}>
          <TrendingUp className={`w-5 h-5 ${
            isLight ? 'text-blue-600' : isSpace ? 'text-blue-400 drop-shadow' : 'text-blue-400'
          }`} />
          Stocks Market
          {autoRefreshEnabled && (
            <span className={`text-xs px-2 py-1 rounded-lg font-semibold ${
              isLight ? 'bg-green-100 text-green-700' : 'bg-green-500/20 text-green-400'
            }`}>
              Near-Live (Snapshot)
            </span>
          )}
        </h2>
        <p className={`${
          isLight ? 'text-gray-600' : isSpace ? 'text-gray-300' : 'text-gray-400'
        } text-xs`}>Search and analyze stocks with AI-powered predictions</p>
      </div>

      {/* Near-Live Mode Controls */}
      {searchQuery && predictions.length > 0 && (
        <div className={`p-3 rounded-lg border ${
          isLight ? 'bg-blue-50 border-blue-300' : 'bg-blue-500/10 border-blue-500/30'
        }`}>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoRefreshEnabled}
                  onChange={(e) => setAutoRefreshEnabled(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className={`text-sm font-semibold ${
                  isLight ? 'text-blue-700' : 'text-blue-300'
                }`}>Near-Live Mode</span>
              </label>
              <select
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
                disabled={!autoRefreshEnabled}
                className={`px-2 py-1 text-xs rounded ${
                  isLight ? 'bg-white border-blue-300' : 'bg-slate-700 border-blue-500/50'
                } border disabled:opacity-50`}
              >
                <option value={30}>30s</option>
                <option value={60}>60s</option>
                <option value={120}>2min</option>
                <option value={300}>5min</option>
              </select>
            </div>
            <div className="flex items-center gap-3">
              {lastRefreshTime && (
                <span className={`text-xs ${
                  isLight ? 'text-blue-600' : 'text-blue-400'
                }`}>
                  Last: {lastRefreshTime.toLocaleTimeString()}
                  {autoRefreshEnabled && nextRefreshIn !== null && (
                    <span className="ml-2">• Next: {nextRefreshIn}s</span>
                  )}
                </span>
              )}
            </div>
          </div>
          <p className={`text-xs mt-2 ${
            isLight ? 'text-blue-600' : 'text-blue-300'
          }`}>
            Updates every {refreshInterval}s using latest available market snapshot. Not tick-by-tick live price.
          </p>
        </div>
      )}

      <div className={`${
        isLight 
          ? 'bg-gradient-to-br from-gray-100/80 to-gray-200/80 backdrop-blur-sm rounded-lg p-3 border border-gray-300/50' 
          : isSpace
            ? 'bg-slate-900/95 backdrop-blur-md rounded-lg p-3 border border-purple-900/20'
            : 'bg-gradient-to-br from-slate-800/80 to-slate-900/80 backdrop-blur-sm rounded-lg p-3 border border-slate-700/50'
      }`}>
        {/* Progress indicator */}
        {progress && (
          <div className={`mb-3 p-3 ${
            isLight 
              ? 'bg-blue-100 border border-blue-300' 
              : isSpace
                ? 'bg-blue-900/20 border border-blue-900/40'
                : 'bg-blue-500/10 border border-blue-500/30'
          } rounded-lg`}>
            <div className="flex items-center gap-3">
              <Loader2 className={`w-5 h-5 animate-spin ${
                isLight ? 'text-blue-600' : 'text-blue-400'
              }`} />
              <div className="flex-1">
                <div className="flex justify-between mb-1">
                  <span className={`text-sm font-medium ${
                    isLight ? 'text-blue-700' : 'text-blue-300'
                  }`}>
                    {progress.description}
                  </span>
                  <span className={`text-sm ${
                    isLight ? 'text-blue-600' : 'text-blue-400'
                  }`}>
                    {progress.progress}%
                  </span>
                </div>
                <div className={`w-full ${
                  isLight ? 'bg-blue-200/50' : 'bg-blue-900/50'
                } rounded-full h-2`}>
                  <div 
                    className={`h-2 rounded-full transition-all duration-300 ${
                      isLight ? 'bg-blue-500' : 'bg-blue-500'
                    }`}
                    style={{ width: `${progress.progress}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div className="flex gap-2 mb-3">
          <div className="flex-1 relative">
            <Search className={`absolute left-2.5 top-1/2 transform -translate-y-1/2 ${
              isLight ? 'text-gray-500' : 'text-gray-400'
            } w-4 h-4 z-10 pointer-events-none`} />
            <SymbolAutocomplete
              value={searchQuery}
              onChange={setSearchQuery}
              onSelect={(symbol) => handlePredict(symbol, true, false)}
              placeholder="Enter stock symbol (e.g., AAPL, GOOGL, MSFT)"
              className="pl-8 pr-3 py-1.5 text-sm"
            />
          </div>
          {onHorizonChange && (
            <select
              value={horizon}
              onChange={(e) => onHorizonChange(e.target.value as any)}
              className={`px-2.5 py-1.5 text-sm ${
                isLight 
                  ? 'bg-white/80 border border-gray-300 text-gray-900 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500' 
                  : isSpace
                    ? 'bg-slate-800/50 border border-purple-800/50 text-white focus:outline-none focus:ring-1 focus:ring-purple-500 focus:border-purple-500'
                    : 'bg-slate-700/50 border border-slate-600 text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500'
              } rounded font-medium`}
            >
              <option value="intraday">📈 Intraday</option>
              <option value="short">📅 Short (5 days)</option>
              <option value="long">📆 Long (30 days)</option>
            </select>
          )}
          <button
            onClick={() => {
              if (searchQuery && !isRequestInProgress) {
                handlePredict(searchQuery, true, false);
              }
            }}
            disabled={loading || !searchQuery || isRequestInProgress}
            className={`px-3 py-1.5 ${
              isLight 
                ? 'bg-blue-500 hover:bg-blue-600 text-white' 
                : isSpace
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
            } text-sm font-semibold rounded transition-all disabled:opacity-50 flex items-center gap-1.5`}
          >
            {loading || isRequestInProgress ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            <span>Search</span>
          </button>
          {searchQuery && (
            <button
              onClick={() => {
                if (!isRequestInProgress) {
                  handlePredict(searchQuery, true, false);
                }
              }}
              disabled={loading || isRequestInProgress}
              className={`px-3 py-1.5 ${
                isLight 
                  ? 'bg-green-500 hover:bg-green-600 text-white' 
                  : isSpace
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : 'bg-green-500 hover:bg-green-600 text-white'
              } text-sm font-semibold rounded transition-all disabled:opacity-50 flex items-center gap-1.5`}
            >
              {loading || isRequestInProgress ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
              <span>Deep Analyze</span>
            </button>
          )}
          {searchQuery && (
            <button
              onClick={() => {
                if (!isRequestInProgress) {
                  handlePredict(searchQuery, true, false);
                }
              }}
              disabled={loading || isRequestInProgress}
              className={`px-3 py-1.5 ${
                isLight 
                  ? 'bg-purple-500 hover:bg-purple-600 text-white' 
                  : isSpace
                    ? 'bg-purple-600 hover:bg-purple-700 text-white'
                    : 'bg-purple-500 hover:bg-purple-600 text-white'
              } text-sm font-semibold rounded transition-all disabled:opacity-50 flex items-center gap-1.5`}
            >
              <Sparkles className="w-4 h-4" />
              <span>Complete Analysis</span>
            </button>
          )}
          {searchQuery && (
            <button
              onClick={() => {
                if (!isRequestInProgress) {
                  handlePredict(searchQuery, true, true);
                }
              }}
              disabled={loading || isRequestInProgress}
              className={`px-3 py-1.5 ${
                isLight 
                  ? 'bg-orange-500 hover:bg-orange-600 text-white' 
                  : isSpace
                    ? 'bg-orange-600 hover:bg-orange-700 text-white'
                    : 'bg-orange-500 hover:bg-orange-600 text-white'
              } text-sm font-semibold rounded transition-all disabled:opacity-50 flex items-center gap-1.5`}
            >
              <Zap className="w-4 h-4" />
              <span>Force Refresh</span>
            </button>
          )}
        </div>

        <div>
          <p className={`${
            isLight ? 'text-gray-700' : isSpace ? 'text-gray-300' : 'text-gray-300'
          } mb-3 font-medium flex items-center gap-2`}>
            <Sparkles className={`w-4 h-4 ${
              isLight ? 'text-blue-500' : isSpace ? 'text-blue-400 drop-shadow' : 'text-blue-400'
            }`} />
            Popular Stocks:
          </p>
          <div className="flex flex-wrap gap-2">
            {POPULAR_STOCKS.slice(0, 20).map((symbol) => (
              <button
                key={symbol}
                onClick={() => {
                  if (!isRequestInProgress) {
                    if (import.meta.env.DEV) {
                      console.log(`[TAB] Clicked: ${symbol}`);
                      console.log(`[API] /tools/predict will be called for ${symbol}`);
                    }
                    setSearchQuery(symbol);
                    handlePredict(symbol, true, false);
                  }
                }}
                disabled={isRequestInProgress}
                className={`px-3 py-1.5 ${
                  isLight 
                    ? 'bg-gray-200/50 text-gray-700 hover:bg-blue-500 hover:text-white' 
                    : isSpace
                      ? 'bg-slate-800/50 text-gray-300 hover:bg-white/10 hover:text-white drop-shadow'
                      : 'bg-slate-700/50 text-gray-300 hover:bg-blue-500 hover:text-white'
                } rounded-lg text-sm font-medium transition-all hover:scale-105`}
              >
                {symbol.replace('.NS', '')}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className={`${
          isLight 
            ? 'bg-red-100/80 border-2 border-red-300 rounded-xl p-4 space-y-2' 
            : isSpace
              ? 'bg-red-900/20 border-2 border-red-900/40 rounded-xl p-4 space-y-2'
              : 'bg-red-900/30 border-2 border-red-500/50 rounded-xl p-4 space-y-2'
        }`}>
          {/* Split multi-line errors into paragraphs */}
          {error.split('\n').map((line, idx) => (
            line.trim() && (
              <p key={idx} className={`${
                line.startsWith('•') 
                  ? isLight ? 'text-red-600 ml-2' : isSpace ? 'text-red-300 ml-2' : 'text-red-300 ml-2' 
                  : isLight ? 'text-red-700' : isSpace ? 'text-red-300' : 'text-red-400'
              } whitespace-normal`}>
                {line}
              </p>
            )
          ))}
        </div>
      )}

      {loading && (
        <div className={`${
          isLight 
            ? 'bg-blue-100/80 border border-blue-300 rounded-xl p-6 flex items-center justify-center gap-3' 
            : isSpace
              ? 'bg-blue-500/10 border border-blue-500/30 rounded-xl p-6 flex items-center justify-center gap-3'
              : 'bg-blue-500/10 border border-blue-500/30 rounded-xl p-6 flex items-center justify-center gap-3'
        }`}>
          <Loader2 className={`w-6 h-6 ${
            isLight ? 'text-blue-600 animate-spin' : 'text-blue-400 animate-spin'
          }`} />
          <span className={`${
            isLight ? 'text-blue-600 font-semibold' : 'text-blue-400 font-semibold'
          }`}>Loading predictions...</span>
        </div>
      )}

      {!loading && !error && predictions.length === 0 && searchQuery && (
        <div className={`${
          isLight 
            ? 'bg-yellow-100/80 border-2 border-yellow-300 rounded-xl p-4' 
            : isSpace
              ? 'bg-yellow-900/20 border-2 border-yellow-900/40 rounded-xl p-4'
              : 'bg-yellow-900/30 border-2 border-yellow-500/50 rounded-xl p-4'
        }`}>
          <p className={`${
            isLight ? 'text-yellow-700' : isSpace ? 'text-yellow-300' : 'text-yellow-400'
          }`}>No predictions found. Try searching for a different symbol or check if the backend is running.</p>
        </div>
      )}

      {predictions.length > 0 && (
        <div className={`${
          isLight 
            ? 'bg-gradient-to-br from-gray-100/80 to-gray-200/80 backdrop-blur-sm rounded-xl p-6 border border-gray-300/50' 
            : isSpace
              ? 'bg-slate-900/95 backdrop-blur-md rounded-xl p-6 border border-purple-900/20'
              : 'bg-gradient-to-br from-slate-800/80 to-slate-900/80 backdrop-blur-sm rounded-xl p-6 border border-slate-700/50'
        }`}>
          <h3 className={`text-xl font-bold ${
            isLight ? 'text-gray-900' : isSpace ? 'text-white drop-shadow-lg' : 'text-white'
          } mb-4 flex items-center gap-2`}>
            <TrendingUp className={`w-6 h-6 ${
              isLight ? 'text-green-500' : isSpace ? 'text-green-400 drop-shadow' : 'text-green-400'
            }`} />
            Predictions for {searchQuery}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {predictions.map((pred, index) => {
              const isPositive = (pred.predicted_return || 0) > 0;
              const isUnavailable = pred.unavailable || false;

              if (import.meta.env.DEV) {
                if (isUnavailable) {
                  console.log(`[RENDER] Unavailable card: ${pred.symbol} - ${pred.error || pred.reason || 'No error message'}`);
                } else {
                  console.log(`[RENDER] Success card: ${pred.symbol}`);
                }
              }
              
              return (
                <div
                  key={index}
                  className={`${
                    isLight 
                      ? 'bg-gradient-to-br from-gray-50/50 to-gray-100/30 rounded-xl p-5 border border-gray-300/50 hover:border-blue-500/50' 
                      : isSpace
                        ? 'bg-slate-800/50 rounded-xl p-5 border border-purple-800/50 hover:border-purple-500/50'
                        : 'bg-gradient-to-br from-slate-700/50 to-slate-600/30 rounded-xl p-5 border border-slate-600/50 hover:border-blue-500/50'
                  } transition-all ${
                    isUnavailable ? 'opacity-60' : ''
                  }`}
                >
                  {isUnavailable ? (
                    <div>
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <p className={`${
                            isLight ? 'text-gray-900' : isSpace ? 'text-white drop-shadow' : 'text-white'
                          } font-bold text-lg mb-1`}>{pred.symbol}</p>
                          <span className={`text-xs font-semibold px-2 py-1 rounded-lg ${
                            isLight ? 'bg-gray-100 text-gray-600' : 'bg-gray-500/20 text-gray-400'
                          }`}>
                            UNAVAILABLE
                          </span>
                        </div>
                      </div>
                      <div className={`p-3 rounded-lg ${
                        isLight ? 'bg-yellow-50 border border-yellow-200' : 'bg-yellow-500/10 border border-yellow-500/30'
                      }`}>
                        <p className={`text-sm ${
                          isLight ? 'text-yellow-800' : 'text-yellow-300'
                        }`}>
                          {pred.reason || 'Prediction unavailable for this symbol at the moment.'}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <>
                      <TrustGateWarning prediction={pred} className="mb-3" />
                      
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <p className={`${
                            isLight ? 'text-gray-900' : isSpace ? 'text-white drop-shadow' : 'text-white'
                          } font-bold text-lg mb-1`}>{pred.symbol}</p>
                          <span className={`text-xs font-semibold px-2 py-1 rounded-lg ${
                            pred.action === 'LONG' ? 
                              (isLight ? 'bg-green-100 text-green-700' : isSpace ? 'bg-green-900/20 text-green-400' : 'bg-green-500/20 text-green-400') :
                            pred.action === 'SHORT' ? 
                              (isLight ? 'bg-red-100 text-red-700' : isSpace ? 'bg-red-900/20 text-red-400' : 'bg-red-500/20 text-red-400') :
                              (isLight ? 'bg-yellow-100 text-yellow-700' : isSpace ? 'bg-yellow-900/20 text-yellow-400' : 'bg-yellow-500/20 text-yellow-400')
                          }`}>
                            {pred.action || 'HOLD'}
                          </span>
                        </div>
                        {getActionIcon(pred.action, isLight, isSpace)}
                      </div>

                      {pred.data_status && (
                        <DataStatusPanel dataStatus={pred.data_status} className="mb-3" />
                      )}
                      
                      <ModelOutputPanel prediction={pred} className="mb-3" />

                      <div className="space-y-2">
                        {pred.current_price && !pred.trust_gate_active && (
                          <div>
                            <div className="flex justify-between">
                              <span className={`${
                                isLight ? 'text-gray-600' : isSpace ? 'text-gray-300' : 'text-gray-400'
                              } text-sm`}>Model Reference Price:</span>
                              <span className={`${
                                isLight ? 'text-gray-900 font-semibold' : isSpace ? 'text-white font-semibold' : 'text-white font-semibold'
                              }`}>{formatUSDToINR(pred.current_price, pred.symbol)}</span>
                            </div>
                            <p className={`text-xs mt-1 ${
                              isLight ? 'text-gray-500' : isSpace ? 'text-gray-400' : 'text-gray-500'
                            }`}>Source: Yahoo Finance OHLC data snapshot</p>
                          </div>
                        )}
                        {pred.predicted_price && !pred.trust_gate_active && (
                          <div className="flex justify-between">
                            <span className={`${
                              isLight ? 'text-gray-600' : isSpace ? 'text-gray-300' : 'text-gray-400'
                            } text-sm`}>Predicted Price:</span>
                            <span className={`${
                              isLight ? 'text-gray-900 font-semibold' : isSpace ? 'text-white font-semibold' : 'text-white font-semibold'
                            }`}>{formatUSDToINR(pred.predicted_price, pred.symbol)}</span>
                          </div>
                        )}
                        {pred.predicted_return !== undefined && !pred.trust_gate_active && (
                          <div>
                            <div className="flex justify-between items-center">
                              <span className={`${
                                isLight ? 'text-gray-600' : isSpace ? 'text-gray-300' : 'text-gray-400'
                              } text-sm`}>Expected Return:</span>
                              <span className={`font-bold ${
                                isPositive ? 
                                  (isLight ? 'text-green-600' : isSpace ? 'text-green-400' : 'text-green-400') : 
                                  (isLight ? 'text-red-600' : isSpace ? 'text-red-400' : 'text-red-400')
                              }`}>
                                {isPositive ? '+' : ''}{pred.predicted_return.toFixed(2)}%
                              </span>
                            </div>
                            <p className={`text-xs mt-1 ${
                              isLight ? 'text-gray-500' : isSpace ? 'text-gray-400' : 'text-gray-500'
                            }`}>Model-based projection, not today's market move</p>
                          </div>
                        )}
                        {pred.trust_gate_active && (
                          <div className="p-2 bg-yellow-500/10 border border-yellow-500/30 rounded">
                            <p className="text-yellow-400 text-sm font-medium">Limited Output</p>
                            <p className="text-yellow-300 text-xs">Price targets disabled due to data quality</p>
                          </div>
                        )}
                      </div>

                      {pred.reason && (
                        <div className={`mt-3 pt-3 border-t ${
                          isLight ? 'border-gray-300/50' : isSpace ? 'border-purple-800/50' : 'border-slate-600/50'
                        }`}>
                          <p className={`${
                            isLight ? 'text-gray-700' : isSpace ? 'text-gray-300' : 'text-gray-300'
                          } text-xs leading-relaxed`}>{pred.reason}</p>
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Enhanced Analysis Results Section */}
      {predictions.length > 0 && (
        <div className={`${
          isLight 
            ? 'bg-gradient-to-br from-blue-100/30 to-indigo-200/30 backdrop-blur-sm rounded-xl p-6 border border-blue-300/50' 
            : isSpace
              ? 'bg-slate-900/95 backdrop-blur-md rounded-xl p-6 border border-blue-500/30'
              : 'bg-gradient-to-br from-slate-800/80 to-slate-900/80 backdrop-blur-sm rounded-xl p-6 border border-slate-600/50'
        }`}>          
          <h3 className={`text-xl font-bold ${
            isLight ? 'text-gray-900' : isSpace ? 'text-white drop-shadow-lg' : 'text-white'
          } mb-4 flex items-center gap-2`}>
            <BarChart3 className={`w-6 h-6 ${
              isLight ? 'text-blue-500' : isSpace ? 'text-blue-400 drop-shadow' : 'text-blue-400'
            }`} />
            Complete Analysis for {searchQuery}
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Analysis Summary Card */}
            <div className={`${
              isLight 
                ? 'bg-white/70 rounded-lg p-4 border border-gray-300/50' 
                : isSpace
                  ? 'bg-slate-800/70 rounded-lg p-4 border border-purple-800/50'
                  : 'bg-slate-700/70 rounded-lg p-4 border border-slate-600/50'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className={`w-5 h-5 ${
                  isLight ? 'text-blue-500' : isSpace ? 'text-blue-400' : 'text-blue-400'
                }`} />
                <h4 className={`font-semibold ${
                  isLight ? 'text-gray-800' : isSpace ? 'text-white' : 'text-white'
                }`}>Summary</h4>
              </div>
              <p className={`text-sm ${
                isLight ? 'text-gray-600' : isSpace ? 'text-gray-300' : 'text-gray-400'
              }`}>Comprehensive analysis including predictions, indicators, and market sentiment.</p>
            </div>
            
            {/* Confidence Score Card */}
            <div className={`${
              isLight 
                ? 'bg-white/70 rounded-lg p-4 border border-gray-300/50' 
                : isSpace
                  ? 'bg-slate-800/70 rounded-lg p-4 border border-purple-800/50'
                  : 'bg-slate-700/70 rounded-lg p-4 border border-slate-600/50'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className={`w-5 h-5 ${
                  isLight ? 'text-green-500' : isSpace ? 'text-green-400' : 'text-green-400'
                }`} />
                <h4 className={`font-semibold ${
                  isLight ? 'text-gray-800' : isSpace ? 'text-white' : 'text-white'
                }`}>Confidence</h4>
              </div>
              <p className={`text-sm ${
                isLight ? 'text-gray-600' : isSpace ? 'text-gray-300' : 'text-gray-400'
              }`}>Based on multiple indicators and models.</p>
            </div>
            
            {/* Market Sentiment Card */}
            <div className={`${
              isLight 
                ? 'bg-white/70 rounded-lg p-4 border border-gray-300/50' 
                : isSpace
                  ? 'bg-slate-800/70 rounded-lg p-4 border border-purple-800/50'
                  : 'bg-slate-700/70 rounded-lg p-4 border border-slate-600/50'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                <Newspaper className={`w-5 h-5 ${
                  isLight ? 'text-purple-500' : isSpace ? 'text-purple-400' : 'text-purple-400'
                }`} />
                <h4 className={`font-semibold ${
                  isLight ? 'text-gray-800' : isSpace ? 'text-white' : 'text-white'
                }`}>Sentiment</h4>
              </div>
              <p className={`text-sm ${
                isLight ? 'text-gray-600' : isSpace ? 'text-gray-300' : 'text-gray-400'
              }`}>Market sentiment and news analysis.</p>
            </div>
            
            {/* Technical Indicators Card */}
            <div className={`${
              isLight 
                ? 'bg-white/70 rounded-lg p-4 border border-gray-300/50' 
                : isSpace
                  ? 'bg-slate-800/70 rounded-lg p-4 border border-purple-800/50'
                  : 'bg-slate-700/70 rounded-lg p-4 border border-slate-600/50'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className={`w-5 h-5 ${
                  isLight ? 'text-yellow-500' : isSpace ? 'text-yellow-400' : 'text-yellow-400'
                }`} />
                <h4 className={`font-semibold ${
                  isLight ? 'text-gray-800' : isSpace ? 'text-white' : 'text-white'
                }`}>Indicators</h4>
              </div>
              <p className={`text-sm ${
                isLight ? 'text-gray-600' : isSpace ? 'text-gray-300' : 'text-gray-400'
              }`}>Technical analysis and trend indicators.</p>
            </div>
          </div>
          
          <div className={`mt-4 p-4 rounded-lg ${
            isLight ? 'bg-blue-50/50 border border-blue-300/30' : isSpace ? 'bg-blue-900/20 border border-blue-800/30' : 'bg-blue-500/10 border border-blue-500/30'
          }`}>
            <p className={`text-sm ${
              isLight ? 'text-blue-700' : isSpace ? 'text-blue-300' : 'text-blue-300'
            }`}>💡 Complete Analysis includes data fetching, indicator calculation, and comprehensive market insights. This enhanced view provides additional context beyond basic predictions.</p>
          </div>
        </div>
      )}

    </div>
  );
};

const getActionIcon = (action: string, isLight?: boolean, isSpace?: boolean) => {
  switch (action?.toUpperCase()) {
    case 'LONG':
    case 'BUY':
      return <TrendingUp className={`w-5 h-5 ${
        isLight ? 'text-green-600' : isSpace ? 'text-green-400' : 'text-green-400'
      }`} />;
    case 'SHORT':
    case 'SELL':
      return <TrendingDown className={`w-5 h-5 ${
        isLight ? 'text-red-600' : isSpace ? 'text-red-400' : 'text-red-400'
      }`} />;
    case 'HOLD':
    default:
      return <div className="w-5 h-5" />;
  }
};

export default StocksView;
