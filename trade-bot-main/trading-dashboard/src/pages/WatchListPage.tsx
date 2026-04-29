import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Star, Plus, X, TrendingUp, TrendingDown } from 'lucide-react';
import { stockAPI, POPULAR_STOCKS } from '../services/api';
import { formatUSDToINR } from '../utils/currencyConverter';
import SymbolAutocomplete from '../components/SymbolAutocomplete';

const WatchListPage = () => {
  const [watchlist, setWatchlist] = useState<string[]>(() => {
    const saved = localStorage.getItem('watchlist');
    return saved ? JSON.parse(saved) : []; // No mock data - empty by default
  });
  const [predictions, setPredictions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');

  const handleAddToWatchlist = (symbol: string) => {
    const normalized = symbol.trim().toUpperCase();
    if (normalized && !watchlist.includes(normalized)) {
      setWatchlist([...watchlist, normalized]);
      setNewSymbol('');
    }
  };

  useEffect(() => {
    localStorage.setItem('watchlist', JSON.stringify(watchlist));
    if (watchlist.length > 0) {
      loadWatchlistData();
    }
  }, [watchlist]);

  const loadWatchlistData = async () => {
    setLoading(true);
    try {
      const response = await stockAPI.predict(watchlist, 'intraday');

      // Check for errors in metadata
      if (response.metadata?.error) {
        throw new Error(response.metadata.error);
      }

      if (response.predictions) {
        // Filter out predictions with errors
        const validPredictions = response.predictions.filter((p: any) => !p.error);
        setPredictions(validPredictions);
      } else {
        setPredictions([]);
      }
    } catch (error: any) {
      setPredictions([]);
    } finally {
      setLoading(false);
    }
  };

  const removeFromWatchlist = (symbol: string) => {
    setWatchlist(watchlist.filter((s) => s !== symbol));
  };

  return (
    <Layout>
      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-bold text-white mb-1">Watch List</h1>
          <p className="text-gray-400 text-xs">Monitor your favorite stocks</p>
        </div>

        <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
          <div className="flex items-center gap-2 mb-3">
            <div className="flex-1">
              <SymbolAutocomplete
                value={newSymbol}
                onChange={setNewSymbol}
                onSelect={handleAddToWatchlist}
                placeholder="e.g., AAPL, TCS.NS"
                excludeSymbols={watchlist}
                className="px-3 py-1.5 text-sm"
              />
            </div>
            <button
              onClick={() => handleAddToWatchlist(newSymbol)}
              className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-sm font-semibold rounded transition-colors flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>Add</span>
            </button>
          </div>

          <div className="mb-4">
            <p className="text-gray-300 mb-2 text-sm">Quick Add:</p>
            <div className="flex flex-wrap gap-2">
              {POPULAR_STOCKS.slice(0, 10).map((symbol) => (
                <button
                  key={symbol}
                  onClick={() => {
                    if (!watchlist.includes(symbol)) {
                      setWatchlist([...watchlist, symbol]);
                    }
                  }}
                  disabled={watchlist.includes(symbol)}
                  className={`px-3 py-1 rounded-lg text-sm transition-colors ${watchlist.includes(symbol)
                    ? 'bg-slate-600 text-gray-400 cursor-not-allowed'
                    : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                    }`}
                >
                  {symbol}
                </button>
              ))}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-8 text-gray-400">Loading...</div>
        ) : predictions.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {predictions.map((pred, index) => {
              const symbol = watchlist[index];
              return (
                <div key={symbol} className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-2">
                      <Star className="w-5 h-5 text-yellow-400 fill-yellow-400" />
                      <h3 className="text-xl font-bold text-white">{symbol}</h3>
                    </div>
                    <button
                      onClick={() => removeFromWatchlist(symbol)}
                      className="p-1 hover:bg-slate-700 rounded transition-colors"
                    >
                      <X className="w-4 h-4 text-gray-400" />
                    </button>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Price</span>
                      <span className="text-white font-semibold">
                        {formatUSDToINR(pred.predicted_price || pred.current_price || 0, pred.symbol)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Action</span>
                      <div className="flex items-center space-x-2">
                        {(pred.action === 'LONG' || pred.action === 'BUY') ? (
                          <TrendingUp className="w-4 h-4 text-green-400" />
                        ) : (pred.action === 'SHORT' || pred.action === 'SELL') ? (
                          <TrendingDown className="w-4 h-4 text-red-400" />
                        ) : null}
                        <span
                          className={`font-semibold ${pred.action === 'LONG' || pred.action === 'BUY'
                            ? 'text-green-400'
                            : pred.action === 'SHORT' || pred.action === 'SELL'
                              ? 'text-red-400'
                              : 'text-yellow-400'
                            }`}
                        >
                          {pred.action === 'LONG' ? 'BUY' : pred.action === 'SHORT' ? 'SELL' : pred.action || 'HOLD'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Confidence</span>
                      <span className="text-white font-semibold">
                        {((pred.confidence || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                    {pred.predicted_return !== undefined && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-400">Return</span>
                        <span className={`font-semibold ${pred.predicted_return > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {pred.predicted_return > 0 ? '+' : ''}{(pred.predicted_return || 0).toFixed(2)}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">No stocks in watchlist</div>
        )}
      </div>
    </Layout>
  );
};

export default WatchListPage;

