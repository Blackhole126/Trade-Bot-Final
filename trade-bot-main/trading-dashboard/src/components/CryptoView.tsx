import { useState, useEffect } from 'react';
import { Search, Coins, Loader2, Zap, BarChart3 } from 'lucide-react';
import { POPULAR_CRYPTO } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

interface CryptoViewProps {
  onSearch: (symbol: string, isUserInitiated?: boolean) => void;
  onAnalyze?: (symbol: string) => void;
  predictions: any[];
  loading: boolean;
  error: string | null;
  horizon?: 'intraday' | 'short' | 'long';
  onHorizonChange?: (horizon: 'intraday' | 'short' | 'long') => void;
}

const CryptoView = ({ onSearch, onAnalyze, predictions, loading, error, horizon = 'intraday', onHorizonChange }: CryptoViewProps) => {
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const isSpace = theme === 'space';
  const [searchQuery, setSearchQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  
  // Generate suggestions based on search query
  useEffect(() => {
    if (searchQuery && searchQuery.length > 0) {
      const query = searchQuery.toUpperCase();
      const filtered = POPULAR_CRYPTO.filter(symbol => 
        symbol.toUpperCase().includes(query)
      ).slice(0, 8);
      setSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  }, [searchQuery]);
  

  return (
    <div className="space-y-4">
      <div>
        <h2 className={`text-xl font-bold ${
          isLight ? 'text-gray-900' : isSpace ? 'text-white drop-shadow-lg' : 'text-white'
        } mb-1 flex items-center gap-2`}>
          <Coins className={`w-5 h-5 ${
            isLight ? 'text-yellow-600' : isSpace ? 'text-yellow-400 drop-shadow' : 'text-yellow-400'
          }`} />
          Cryptocurrency Market
        </h2>
        <p className={`${
          isLight ? 'text-gray-600' : isSpace ? 'text-gray-300' : 'text-gray-400'
        } text-xs`}>Track and analyze cryptocurrencies with real-time predictions</p>
      </div>

      <div className={`${
        isLight 
          ? 'bg-gradient-to-br from-yellow-100/20 to-orange-100/20 backdrop-blur-sm rounded-lg p-3 border border-yellow-300/30' 
          : isSpace
            ? 'bg-slate-900/95 backdrop-blur-md rounded-lg p-3 border border-purple-900/20'
            : 'bg-gradient-to-br from-yellow-900/20 to-orange-900/20 backdrop-blur-sm rounded-lg p-3 border border-yellow-500/30'
      }`}>
        <div className="flex gap-2 mb-3">
          <div className="flex-1 relative">
            <Search className={`absolute left-2.5 top-1/2 transform -translate-y-1/2 ${
              isLight ? 'text-gray-500' : 'text-gray-400'
            } w-4 h-4 z-10`} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
              onFocus={() => {
                if (suggestions.length > 0) {
                  setShowSuggestions(true);
                }
              }}
              onBlur={() => {
                setTimeout(() => setShowSuggestions(false), 200);
              }}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && searchQuery) {
                  setShowSuggestions(false);
                  onSearch(searchQuery, true);
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  setShowSuggestions(false);
                }
              }}
              placeholder="Enter crypto symbol (e.g., BTC-USD, ETH-USD, SOL-USD)"
              className={`w-full pl-8 pr-3 py-1.5 text-sm ${
                isLight 
                  ? 'bg-white/80 border border-gray-300 rounded text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-yellow-500' 
                  : isSpace
                    ? 'bg-slate-800/50 border border-purple-800/50 rounded text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-purple-500'
                    : 'bg-slate-700/50 border border-slate-600 rounded text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-yellow-500'
              }`}
            />
            
            {/* Suggestions Dropdown */}
            {showSuggestions && suggestions.length > 0 && (
              <div className={`absolute top-full left-0 right-0 mt-1 ${
                isLight 
                  ? 'bg-white border border-gray-300 rounded-lg shadow-xl z-50 max-h-64 overflow-y-auto' 
                  : isSpace
                    ? 'bg-slate-800 border border-purple-800/50 rounded-lg shadow-xl z-50 max-h-64 overflow-y-auto'
                    : 'bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 max-h-64 overflow-y-auto'
              }`}>
                {suggestions.map((symbol) => (
                  <button
                    key={symbol}
                    type="button"
                    onClick={() => {
                      setSearchQuery(symbol);
                      setShowSuggestions(false);
                      onSearch(symbol, true);
                    }}
                    onMouseDown={(e) => e.preventDefault()}
                    className={`w-full text-left px-4 py-2 text-sm ${
                      isLight 
                        ? 'text-gray-700 hover:bg-gray-100 hover:text-gray-900' 
                        : isSpace
                          ? 'text-gray-300 hover:bg-white/10 hover:text-white drop-shadow'
                          : 'text-gray-300 hover:bg-slate-700 hover:text-white'
                    } transition-colors`}
                  >
                    <span className="font-medium">{symbol}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          {onHorizonChange && (
            <select
              value={horizon}
              onChange={(e) => onHorizonChange(e.target.value as any)}
              className={`px-2.5 py-1.5 text-sm ${
                isLight 
                  ? 'bg-white/80 border border-gray-300 rounded text-gray-900 focus:outline-none focus:ring-1 focus:ring-yellow-500 font-medium' 
                  : isSpace
                    ? 'bg-slate-800/50 border border-purple-800/50 rounded text-white focus:outline-none focus:ring-1 focus:ring-purple-500 font-medium'
                    : 'bg-slate-700/50 border border-slate-600 rounded text-white focus:outline-none focus:ring-1 focus:ring-yellow-500 font-medium'
              }`}
            >
              <option value="intraday">📈 Intraday</option>
              <option value="short">📅 Short (5 days)</option>
              <option value="long">📆 Long (30 days)</option>
            </select>
          )}
          <button
            onClick={() => {
              if (searchQuery) {
                onSearch(searchQuery, true);
              }
            }}
            disabled={loading || !searchQuery}
            className={`px-3 py-1.5 ${
              isLight 
                ? 'bg-yellow-500 hover:bg-yellow-600 text-white' 
                : isSpace
                  ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                  : 'bg-yellow-500 hover:bg-yellow-600 text-white'
            } text-sm font-semibold rounded transition-all disabled:opacity-50 flex items-center gap-1.5`}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            <span>Search</span>
          </button>
          {searchQuery && onAnalyze && (
            <button
              onClick={() => {
                if (onAnalyze) {
                  onAnalyze(searchQuery);
                }
              }}
              disabled={loading}
              className={`px-3 py-1.5 ${
                isLight 
                  ? 'bg-green-500 hover:bg-green-600 text-white' 
                  : isSpace
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : 'bg-green-500 hover:bg-green-600 text-white'
              } text-sm font-semibold rounded transition-all disabled:opacity-50 flex items-center gap-1.5`}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
              <span>Deep Analyze</span>
            </button>
          )}
        </div>

        <div>
          <p className={`${
            isLight ? 'text-gray-700' : isSpace ? 'text-gray-300' : 'text-gray-300'
          } mb-3 font-medium flex items-center gap-2`}>
            <Zap className={`w-4 h-4 ${
              isLight ? 'text-yellow-600' : isSpace ? 'text-yellow-400 drop-shadow' : 'text-yellow-400'
            }`} />
            Popular Cryptocurrencies:
          </p>
          <div className="flex flex-wrap gap-2">
            {POPULAR_CRYPTO.slice(0, 20).map((symbol) => (
              <button
                key={symbol}
                onClick={() => {
                  onSearch(symbol, true);
                }}
                className={`px-3 py-1.5 ${
                  isLight 
                    ? 'bg-gray-200/50 text-gray-700 hover:bg-yellow-500 hover:text-white' 
                    : isSpace
                      ? 'bg-slate-800/50 text-gray-300 hover:bg-white/10 hover:text-white drop-shadow'
                      : 'bg-slate-700/50 text-gray-300 hover:bg-yellow-500 hover:text-white'
                } rounded-lg text-sm font-medium transition-all hover:scale-105`}
              >
                {symbol.replace('-USD', '')}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className={`${
          isLight 
            ? 'bg-red-100/80 border-2 border-red-300 rounded-xl p-4' 
            : isSpace
              ? 'bg-red-900/20 border-2 border-red-900/40 rounded-xl p-4'
              : 'bg-red-900/30 border-2 border-red-500/50 rounded-xl p-4'
        }`}>
          <p className={`${
            isLight ? 'text-red-700' : isSpace ? 'text-red-300' : 'text-red-400'
          }`}>{error}</p>
        </div>
      )}

      {loading && (
        <div className={`${
          isLight 
            ? 'bg-gray-100/80 rounded-xl p-8 border border-gray-300/50 text-center' 
            : isSpace
              ? 'bg-slate-900/95 backdrop-blur-md rounded-xl p-8 border border-purple-900/20 text-center'
              : 'bg-slate-800/80 rounded-xl p-8 border border-slate-700/50 text-center'
        }`}>
          <Loader2 className={`w-12 h-12 ${
            isLight ? 'text-yellow-600 animate-spin' : 'text-yellow-400 animate-spin'
          } mx-auto mb-4`} />
          <p className={`${
            isLight ? 'text-gray-600' : isSpace ? 'text-gray-300' : 'text-gray-400'
          }`}>Fetching crypto predictions from backend...</p>
          <p className={`${
            isLight ? 'text-gray-500 text-sm mt-2' : isSpace ? 'text-gray-400 text-sm mt-2' : 'text-gray-500 text-sm mt-2'
          }`}>This may take 60-90 seconds for first-time predictions</p>
        </div>
      )}

      {!loading && predictions.length === 0 && !error && (
        <div className={`${
          isLight 
            ? 'bg-gray-100/80 rounded-xl p-8 border border-gray-300/50 text-center' 
            : isSpace
              ? 'bg-slate-900/95 backdrop-blur-md rounded-xl p-8 border border-purple-900/20 text-center'
              : 'bg-slate-800/80 rounded-xl p-8 border border-slate-700/50 text-center'
        }`}>
          <Coins className={`w-16 h-16 ${
            isLight ? 'text-yellow-600 mx-auto mb-4 opacity-50' : 'text-yellow-400 mx-auto mb-4 opacity-50'
          }`} />
          <h3 className={`text-xl font-bold ${
            isLight ? 'text-gray-900' : isSpace ? 'text-white drop-shadow-lg' : 'text-white'
          } mb-2`}>Ready to Search Cryptocurrencies</h3>
          <p className={`${
            isLight ? 'text-gray-600 mb-4' : isSpace ? 'text-gray-300 mb-4' : 'text-gray-400 mb-4'
          }`}>Enter a crypto symbol (e.g., BTC-USD) above or click a popular crypto to get AI-powered predictions</p>
          <div className="flex flex-wrap justify-center gap-2 mt-4">
            {POPULAR_CRYPTO.slice(0, 10).map((symbol) => (
              <button
                key={symbol}
                onClick={() => onSearch(symbol, true)}
                className={`px-4 py-2 ${
                  isLight 
                    ? 'bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-600 rounded-lg text-sm font-medium transition-all border border-yellow-500/30' 
                    : isSpace
                      ? 'bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 rounded-lg text-sm font-medium transition-all border border-purple-500/30'
                      : 'bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 rounded-lg text-sm font-medium transition-all border border-yellow-500/30'
                }`}
              >
                {symbol.replace('-USD', '')}
              </button>
            ))}
          </div>
        </div>
      )}

      {predictions.length > 0 && (
        <div className={`${
          isLight 
            ? 'bg-gray-100/80 rounded-xl p-6 border border-gray-300/50' 
            : isSpace
              ? 'bg-slate-900/95 backdrop-blur-md rounded-xl p-6 border border-purple-900/20'
              : 'bg-slate-800/80 rounded-xl p-6 border border-slate-700/50'
        }`}>
          <h3 className={`text-xl font-bold ${
            isLight ? 'text-gray-900' : isSpace ? 'text-white drop-shadow-lg' : 'text-white'
          } mb-4 flex items-center gap-2`}>
            <Coins className={`w-5 h-5 ${
              isLight ? 'text-yellow-600' : isSpace ? 'text-yellow-400 drop-shadow' : 'text-yellow-400'
            }`} />
            Crypto Predictions
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {predictions.map((pred, index) => {
              const symbol = pred.symbol?.replace('-USD', '') || pred.symbol;
              const isUnavailable = pred.unavailable || pred.error;
              return (
                <div key={index} className={`${
                  isLight 
                    ? 'bg-gradient-to-br from-yellow-100/20 to-orange-100/10 rounded-lg p-4 border border-yellow-300/30' 
                    : isSpace
                      ? 'bg-slate-800/50 rounded-lg p-4 border border-purple-800/50'
                      : 'bg-gradient-to-br from-yellow-900/20 to-orange-900/10 rounded-lg p-4 border border-yellow-500/30'
                }`}>
                  {isUnavailable ? (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Coins className={`w-5 h-5 ${
                            isLight ? 'text-yellow-600' : isSpace ? 'text-yellow-400 drop-shadow' : 'text-yellow-400'
                          }`} />
                          <span className={`font-bold text-lg ${
                            isLight ? 'text-gray-900' : isSpace ? 'text-white drop-shadow' : 'text-white'
                          }`}>{symbol}</span>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          isLight ? 'bg-gray-100 text-gray-600' : 'bg-gray-500/20 text-gray-400'
                        }`}>
                          UNAVAILABLE
                        </span>
                      </div>
                      <div className={`p-3 rounded-lg ${
                        isLight ? 'bg-yellow-50 border border-yellow-200' : 'bg-yellow-500/10 border border-yellow-500/30'
                      }`}>
                        <p className={`text-sm ${
                          isLight ? 'text-yellow-800' : 'text-yellow-300'
                        }`}>
                          {pred.reason || pred.error || 'Prediction unavailable for this symbol at the moment.'}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Coins className={`w-5 h-5 ${
                            isLight ? 'text-yellow-600' : isSpace ? 'text-yellow-400 drop-shadow' : 'text-yellow-400'
                          }`} />
                          <span className={`font-bold text-lg ${
                            isLight ? 'text-gray-900' : isSpace ? 'text-white drop-shadow' : 'text-white'
                          }`}>{symbol}</span>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          pred.action === 'LONG' ? 
                            (isLight ? 'bg-green-100 text-green-700' : isSpace ? 'bg-green-900/20 text-green-400' : 'bg-green-500/20 text-green-400') :
                          pred.action === 'SHORT' ? 
                            (isLight ? 'bg-red-100 text-red-700' : isSpace ? 'bg-red-900/20 text-red-400' : 'bg-red-500/20 text-red-400') :
                            (isLight ? 'bg-yellow-100 text-yellow-700' : isSpace ? 'bg-yellow-900/20 text-yellow-400' : 'bg-yellow-500/20 text-yellow-400')
                        }`}>
                          {pred.action || 'HOLD'}
                        </span>
                      </div>
                      <div className="space-y-1">
                        <p className={`text-sm ${
                          isLight ? 'text-gray-600' : isSpace ? 'text-gray-300' : 'text-gray-400'
                        }`}>Current: ${pred.current_price?.toFixed(2) || 'N/A'}</p>
                        <p className={`font-semibold ${
                          isLight ? 'text-gray-900' : isSpace ? 'text-white' : 'text-white'
                        }`}>Predicted: ${pred.predicted_price?.toFixed(2) || 'N/A'}</p>
                        <p className={`text-sm font-semibold ${
                          (pred.predicted_return || 0) > 0 ? 
                            (isLight ? 'text-green-600' : isSpace ? 'text-green-400' : 'text-green-400') : 
                            (isLight ? 'text-red-600' : isSpace ? 'text-red-400' : 'text-red-400')
                        }`}>
                          {(pred.predicted_return || 0) > 0 ? '+' : ''}{pred.predicted_return?.toFixed(2) || 0}%
                        </p>
                        <p className={`text-xs ${
                          isLight ? 'text-gray-600' : isSpace ? 'text-gray-400' : 'text-gray-400'
                        }`}>Confidence: {((pred.confidence || 0) * 100).toFixed(0)}%</p>
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
};

export default CryptoView;
