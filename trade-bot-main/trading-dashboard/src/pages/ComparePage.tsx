import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { GitCompare, Plus, X, TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import { stockAPI, POPULAR_STOCKS, type PredictionItem } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import SymbolAutocomplete from '../components/SymbolAutocomplete';

const ComparePage = () => {
  const { showNotification } = useNotification();
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [predictions, setPredictions] = useState<PredictionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);

  const handleAddSymbol = (symbol: string) => {
    const normalized = symbol.trim().toUpperCase();
    if (normalized && !selectedSymbols.includes(normalized) && selectedSymbols.length < 4) {
      setSelectedSymbols([...selectedSymbols, normalized]);
      setNewSymbol('');
      setShowAddModal(false);
      showNotification('success', 'Symbol Added', `${normalized} added to comparison.`);
    }
  };

  const handleRemoveSymbol = (symbol: string) => {
    setSelectedSymbols(selectedSymbols.filter(s => s !== symbol));
    showNotification('info', 'Symbol Removed', `${symbol} removed from comparison.`);
  };

  useEffect(() => {
    if (selectedSymbols.length > 0) {
      loadPredictions();
    } else {
      setPredictions([]);
    }
  }, [selectedSymbols]);

  const loadPredictions = async () => {
    setLoading(true);
    try {
      const response = await stockAPI.predict(selectedSymbols, 'intraday');
      if (response.predictions) {
        const valid = response.predictions.filter((p: PredictionItem) => !p.error);
        setPredictions(valid);
        showNotification('success', 'Comparison Loaded', `Compared ${valid.length} symbols. Ready for analysis.`);
      } else {
        showNotification('warning', 'No Predictions', 'Could not load predictions for selected symbols.');
        setPredictions([]);
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to load predictions';
      setPredictions([]);
      showNotification('error', 'Comparison Failed', msg);
    } finally {
      setLoading(false);
    }
  };

  const chartData = predictions.map(p => ({
    symbol: p.symbol,
    return: p.predicted_return || 0,
    confidence: (p.confidence || 0) * 100,
    price: p.predicted_price || p.current_price || 0,
  }));

  return (
    <Layout>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1 flex items-center gap-2">
              <GitCompare className="w-6 h-6" />
              Compare Stocks
            </h1>
            <p className="text-gray-400 text-sm">Compare up to 4 stocks side-by-side</p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            disabled={selectedSymbols.length >= 4}
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Stock
          </button>
        </div>

        {/* Selected Symbols */}
        {selectedSymbols.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {selectedSymbols.map(symbol => (
              <div
                key={symbol}
                className="flex items-center gap-2 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg"
              >
                <span className="text-white font-semibold">{symbol}</span>
                <button
                  onClick={() => handleRemoveSymbol(symbol)}
                  className="text-gray-400 hover:text-red-400 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading...</div>
        ) : predictions.length === 0 ? (
          <div className="text-center py-12">
            <GitCompare className="w-16 h-16 text-gray-500 mx-auto mb-4 opacity-50" />
            <p className="text-gray-400">Add stocks to compare</p>
          </div>
        ) : (
          <>
            {/* Comparison Table */}
            <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-700">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">Symbol</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">Action</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">Price</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">Predicted Return</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700">
                    {predictions.map((pred) => {
                      const isPositive = (pred.predicted_return || 0) > 0;
                      return (
                        <tr key={pred.symbol} className="hover:bg-slate-700/50">
                          <td className="px-4 py-3">
                            <span className="text-white font-bold">{pred.symbol}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded text-xs font-semibold ${
                              pred.action === 'LONG' ? 'bg-green-500/20 text-green-400' :
                              pred.action === 'SHORT' ? 'bg-red-500/20 text-red-400' :
                              'bg-yellow-500/20 text-yellow-400'
                            }`}>
                              {pred.action === 'LONG' ? 'BUY' : pred.action === 'SHORT' ? 'SELL' : pred.action}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-white">
                            ${(pred.predicted_price || pred.current_price || 0).toFixed(2)}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1">
                              {isPositive ? (
                                <TrendingUp className="w-4 h-4 text-green-400" />
                              ) : (
                                <TrendingDown className="w-4 h-4 text-red-400" />
                              )}
                              <span className={isPositive ? 'text-green-400' : 'text-red-400'}>
                                {isPositive ? '+' : ''}{(pred.predicted_return || 0).toFixed(2)}%
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-sm font-semibold ${
                              (pred.confidence || 0) > 0.7 ? 'text-green-400' :
                              (pred.confidence || 0) > 0.5 ? 'text-yellow-400' :
                              'text-red-400'
                            }`}>
                              {((pred.confidence || 0) * 100).toFixed(0)}%
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Comparison Chart */}
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Visual Comparison</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.15} />
                  <XAxis dataKey="symbol" stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                  <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1E293B',
                      border: '1px solid #475569',
                      borderRadius: '8px',
                    }}
                  />
                  <Legend />
                  <Bar dataKey="return" fill="#3B82F6" name="Predicted Return (%)" />
                  <Bar dataKey="confidence" fill="#10B981" name="Confidence (%)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}

        {/* Add Symbol Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-white">Add Stock to Compare</h3>
                <button
                  onClick={() => {
                    setShowAddModal(false);
                    setNewSymbol('');
                  }}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
                  <SymbolAutocomplete
                    value={newSymbol}
                    onChange={setNewSymbol}
                    onSelect={handleAddSymbol}
                    placeholder="e.g., AAPL, TCS.NS"
                    excludeSymbols={selectedSymbols}
                    maxSuggestions={6}
                    className="px-4 py-2"
                  />
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => handleAddSymbol(newSymbol)}
                    disabled={!newSymbol || selectedSymbols.includes(newSymbol.toUpperCase()) || selectedSymbols.length >= 4}
                    className="flex-1 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors"
                  >
                    Add
                  </button>
                  <button
                    onClick={() => {
                      setShowAddModal(false);
                      setNewSymbol('');
                    }}
                    className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-semibold transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default ComparePage;




