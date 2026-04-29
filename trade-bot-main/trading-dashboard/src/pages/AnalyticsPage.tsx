import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { stockAPI, TimeoutError, type PredictionItem, POPULAR_STOCKS } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, AreaChart, Area } from 'recharts';
import { Brain, Cpu, TrendingUp, Zap, BarChart3, Plus, X, Search } from 'lucide-react';
import SymbolAutocomplete from '../components/SymbolAutocomplete';

const AnalyticsPage = () => {
  const { showNotification } = useNotification();
  const [analyticsSymbols, setAnalyticsSymbols] = useState<string[]>([]);
  const [analytics, setAnalytics] = useState<{
    predictions: PredictionItem[];
    buyCount: number;
    sellCount: number;
    holdCount: number;
    avgConfidence: number;
    avgReturn: number;
    totalReturn: number;
    ensembleStats: { aligned: number; priceAgreement: number; totalPredictions: number };
    modelPerformance: Record<string, { count: number; avgReturn: number }>;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<'7d' | '30d' | '90d'>('30d');
  const [features, setFeatures] = useState<Record<string, unknown> | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [chartType, setChartType] = useState<'bar' | 'line' | 'area'>('bar');
  const [showAddModal, setShowAddModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Load symbols from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('analytics_symbols');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setAnalyticsSymbols(parsed);
        }
      }
    } catch (error) {
      // Silently fail - start with empty array
    }
  }, []);

  // Load analytics when symbols change
  useEffect(() => {
    if (analyticsSymbols.length > 0) {
      loadAnalytics();
      // Refresh every 120 seconds (2 minutes) to reduce API calls and avoid rate limits
      const interval = setInterval(() => {
        loadAnalytics();
      }, 120000);
      return () => clearInterval(interval);
    } else {
      // Clear analytics when no symbols
      setAnalytics(null);
      setError(null);
    }
  }, [analyticsSymbols, selectedPeriod]);

  // Persist symbols to localStorage
  useEffect(() => {
    localStorage.setItem('analytics_symbols', JSON.stringify(analyticsSymbols));
  }, [analyticsSymbols]);

  const loadAnalytics = async () => {
    if (analyticsSymbols.length === 0) {
      return; // Don't call backend with empty array
    }
    setLoading(true);
    try {
      const response = await stockAPI.scanAll(analyticsSymbols, 'intraday', 0.3);
      
      // Check for errors in metadata
      if (response.metadata?.error) {
        throw new Error(response.metadata.error);
      }
      
      // Backend returns: { metadata, shortlist, all_predictions }
      // Filter out predictions with errors
      const allPredictions = response.all_predictions || response.shortlist || [];
      const predictions = allPredictions.filter((p: PredictionItem) => !p.error);
      
      // Process analytics data - backend uses LONG/SHORT/HOLD
      const buyCount = predictions.filter((p: PredictionItem) => p.action === 'LONG').length;
      const sellCount = predictions.filter((p: PredictionItem) => p.action === 'SHORT').length;
      const holdCount = predictions.filter((p: PredictionItem) => p.action === 'HOLD').length;
      
      // Calculate additional analytics
      const totalReturn = predictions.reduce((sum: number, p: PredictionItem) => sum + (p.predicted_return || 0), 0);
      const avgReturn = predictions.length > 0 ? totalReturn / predictions.length : 0;
      
      // Extract ensemble details
      const ensembleStats = {
        aligned: predictions.filter((p: PredictionItem) => p.ensemble_details?.models_align).length,
        priceAgreement: predictions.filter((p: PredictionItem) => p.ensemble_details?.price_agreement).length,
        totalPredictions: predictions.length
      };
      
      // Extract individual model performance
      const modelPerformance: any = {
        random_forest: { count: 0, avgReturn: 0 },
        lightgbm: { count: 0, avgReturn: 0 },
        xgboost: { count: 0, avgReturn: 0 },
        dqn: { count: 0, avgReturn: 0 }
      };
      
      predictions.forEach((p: PredictionItem) => {
        const ind = p.individual_predictions || {};
        if (ind.random_forest) {
          modelPerformance.random_forest.count++;
          modelPerformance.random_forest.avgReturn += (ind.random_forest as any)?.return || 0;
        }
        if (ind.lightgbm) {
          modelPerformance.lightgbm.count++;
          modelPerformance.lightgbm.avgReturn += (ind.lightgbm as any)?.return || 0;
        }
        if (ind.xgboost) {
          modelPerformance.xgboost.count++;
          modelPerformance.xgboost.avgReturn += (ind.xgboost as any)?.return || 0;
        }
        if (ind.dqn) {
          modelPerformance.dqn.count++;
        }
      });
      
      Object.keys(modelPerformance).forEach(key => {
        if (modelPerformance[key].count > 0) {
          modelPerformance[key].avgReturn = modelPerformance[key].avgReturn / modelPerformance[key].count;
        }
      });
      
      setAnalytics({
        predictions,
        buyCount,
        sellCount,
        holdCount,
        avgConfidence: predictions.length > 0 
          ? predictions.reduce((sum: number, p: PredictionItem) => sum + (p.confidence || 0), 0) / predictions.length 
          : 0,
        avgReturn,
        totalReturn,
        ensembleStats,
        modelPerformance
      });
      
      // Load features for first prediction if available
      if (predictions.length > 0 && !selectedSymbol) {
        loadFeaturesForSymbol(predictions[0].symbol);
      }
      setLoading(false);
      setError(null);
      showNotification('success', 'Analytics Updated', `Analyzed ${predictions.length} symbols.`);
    } catch (error: unknown) {
      // Handle TimeoutError - backend is still processing
      if (error instanceof TimeoutError) {
        setError(null);
        return;
      }
      
      // Handle actual errors
      const err = error instanceof Error ? error : new Error(String(error));
      setAnalytics(null);
      const msg = err.message || 'Failed to load analytics';
      setError(msg);
      setLoading(false);
    }
  };

  const loadFeaturesForSymbol = async (symbol: string) => {
    try {
      setSelectedSymbol(symbol);
      const response = await stockAPI.fetchData([symbol], '2y', true);
      if (response.data && response.data[symbol] && response.data[symbol].features) {
        setFeatures(response.data[symbol].features);
      }
    } catch (error) {
      // Silently fail - features are optional
    }
  };

  // Only use real data, no mock fallback
  const performanceData = analytics?.predictions
    ? analytics.predictions.slice(0, 10).map((p: any) => ({
        name: p.symbol || 'N/A',
        value: p.predicted_return || 0,
        confidence: (p.confidence || 0) * 100,
        price: p.predicted_price || p.current_price || 0
      }))
    : [];

  const pieData = analytics
    ? [
        { name: 'Uptrend', value: analytics.buyCount, color: '#3B82F6' },
        { name: 'Downtrend', value: analytics.sellCount, color: '#8B5CF6' },
        { name: 'Neutral', value: analytics.holdCount, color: '#6B7280' },
      ]
    : [];

  const handleAddSymbol = (symbol: string) => {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) return;
    if (analyticsSymbols.includes(normalized)) {
      showNotification('warning', 'Already Added', `${normalized} is already in analytics`);
      return;
    }
    setAnalyticsSymbols([...analyticsSymbols, normalized]);
    setShowAddModal(false);
    setSearchQuery('');
    showNotification('success', 'Asset Added', `${normalized} added to analytics`);
  };

  const handleRemoveSymbol = (symbol: string) => {
    setAnalyticsSymbols(analyticsSymbols.filter(s => s !== symbol));
    showNotification('info', 'Asset Removed', `${symbol} removed from analytics`);
  };

  const handleClearAll = () => {
    if (confirm('Remove all assets from analytics?')) {
      setAnalyticsSymbols([]);
      setAnalytics(null);
      showNotification('info', 'Analytics Cleared', 'All assets removed');
    }
  };

  return (
    <Layout>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white mb-1">Market Observation Analytics</h1>
            <p className="text-gray-400">Analysis of selected assets</p>
          </div>
          <div className="flex gap-2">
            {analyticsSymbols.length > 0 && (
              <button
                onClick={handleClearAll}
                className="px-3 py-2 bg-slate-700 hover:bg-slate-600 border border-slate-600 rounded-lg text-gray-300 text-sm transition-colors"
              >
                Clear All
              </button>
            )}
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add Asset
            </button>
          </div>
        </div>

        {/* Selected Symbols Display */}
        {analyticsSymbols.length > 0 && (
          <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
            <p className="text-gray-400 text-xs mb-2">Analyzing {analyticsSymbols.length} asset{analyticsSymbols.length !== 1 ? 's' : ''}:</p>
            <div className="flex flex-wrap gap-2">
              {analyticsSymbols.map(symbol => (
                <div key={symbol} className="flex items-center gap-2 bg-slate-700 px-3 py-1 rounded-lg">
                  <span className="text-white text-sm font-medium">{symbol}</span>
                  <button
                    onClick={() => handleRemoveSymbol(symbol)}
                    className="text-gray-400 hover:text-red-400 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Add Asset Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 max-w-md w-full">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-white">Add Asset to Analytics</h3>
                <button
                  onClick={() => {
                    setShowAddModal(false);
                    setSearchQuery('');
                  }}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="mb-4">
                <SymbolAutocomplete
                  value={searchQuery}
                  onChange={setSearchQuery}
                  onSelect={handleAddSymbol}
                  placeholder="Search symbol (e.g., AAPL, RELIANCE.NS)"
                  excludeSymbols={analyticsSymbols}
                  className="px-4 py-2"
                />
              </div>
              <button
                onClick={() => handleAddSymbol(searchQuery)}
                disabled={!searchQuery.trim()}
                className="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors"
              >
                Add to Analytics
              </button>
            </div>
          </div>
        )}

        {analyticsSymbols.length === 0 ? (
          <div className="bg-slate-800 rounded-lg p-12 border border-slate-700 text-center">
            <BarChart3 className="w-16 h-16 mx-auto mb-4 text-slate-600" />
            <h2 className="text-xl font-semibold text-white mb-2">No assets under analysis</h2>
            <p className="text-gray-400 mb-6">Add assets to observe market behavior and model performance</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-semibold transition-colors inline-flex items-center gap-2"
            >
              <Plus className="w-5 h-5" />
              Add Asset to Analytics
            </button>
          </div>
        ) : loading ? (
          <div className="text-center py-8 text-gray-400">Loading analytics...</div>
        ) : error ? (
          <div className="bg-red-900 border border-red-700 rounded-lg p-4 text-red-200">
            <p className="font-semibold mb-1">Error Loading Analytics</p>
            <p className="text-sm">{error}</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                <p className="text-gray-400 text-xs mb-1">Total Predictions</p>
                <p className="text-xl font-bold text-white">{analytics?.predictions?.length || 0}</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                <p className="text-gray-400 text-xs mb-1">Uptrend</p>
                <p className="text-xl font-bold text-blue-400">{analytics?.buyCount || 0}</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                <p className="text-gray-400 text-xs mb-1">Downtrend</p>
                <p className="text-xl font-bold text-purple-400">{analytics?.sellCount || 0}</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                <p className="text-gray-400 text-xs mb-1">Avg Confidence</p>
                <p className="text-xl font-bold text-blue-400">
                  {analytics ? (analytics.avgConfidence * 100).toFixed(1) : 0}%
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-blue-400" />
                    Performance Trend
                  </h2>
                  <div className="flex gap-2 bg-slate-700 rounded-lg p-1">
                    <button
                      onClick={() => setChartType('bar')}
                      className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                        chartType === 'bar' 
                          ? 'bg-blue-500 text-white' 
                          : 'text-gray-300 hover:text-white'
                      }`}
                    >
                      Bar
                    </button>
                    <button
                      onClick={() => setChartType('line')}
                      className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                        chartType === 'line' 
                          ? 'bg-blue-500 text-white' 
                          : 'text-gray-300 hover:text-white'
                      }`}
                    >
                      Line
                    </button>
                    <button
                      onClick={() => setChartType('area')}
                      className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                        chartType === 'area' 
                          ? 'bg-blue-500 text-white' 
                          : 'text-gray-300 hover:text-white'
                      }`}
                    >
                      Area
                    </button>
                  </div>
                </div>
                {performanceData.length > 0 ? (
                  <div style={{ width: '100%', height: 300, minWidth: 0, minHeight: 300 }}>
                    <ResponsiveContainer width="100%" height={300} minWidth={0}>
                    {chartType === 'bar' ? (
                      <BarChart data={performanceData} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={true} vertical={false} />
                        <XAxis 
                          type="number" 
                          stroke="#9CA3AF" 
                          tick={{ fill: '#9CA3AF', fontSize: 12 }}
                          tickFormatter={(value) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`}
                        />
                        <YAxis 
                          type="category" 
                          dataKey="name" 
                          stroke="#9CA3AF" 
                          tick={{ fill: '#9CA3AF', fontSize: 12 }}
                          width={80}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#1E293B', 
                            border: '1px solid #475569',
                            borderRadius: '8px',
                            padding: '12px'
                          }}
                          labelStyle={{ color: '#E2E8F0', fontWeight: 'bold' }}
                          formatter={(value: any) => [`${value >= 0 ? '+' : ''}${value.toFixed(2)}%`, 'Return']}
                        />
                        <Bar 
                          dataKey="value" 
                          radius={[0, 8, 8, 0]}
                        >
                          {performanceData.map((entry: any, index: number) => (
                            <Cell 
                              key={`cell-${index}`} 
                              fill={entry.value >= 0 ? '#10B981' : '#EF4444'} 
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    ) : chartType === 'line' ? (
                      <LineChart data={performanceData}>
                        <defs>
                          <linearGradient id="lineGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis 
                          dataKey="name" 
                          stroke="#9CA3AF" 
                          tick={{ fill: '#9CA3AF', fontSize: 12 }}
                        />
                        <YAxis 
                          stroke="#9CA3AF"
                          tick={{ fill: '#9CA3AF', fontSize: 12 }}
                          tickFormatter={(value) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#1E293B', 
                            border: '1px solid #475569',
                            borderRadius: '8px',
                            padding: '12px'
                          }}
                          labelStyle={{ color: '#E2E8F0', fontWeight: 'bold' }}
                          formatter={(value: any) => [`${value >= 0 ? '+' : ''}${value.toFixed(2)}%`, 'Return']}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="value" 
                          stroke="#3B82F6" 
                          strokeWidth={3}
                          dot={{ fill: '#3B82F6', r: 5 }}
                          activeDot={{ r: 7 }}
                        />
                      </LineChart>
                    ) : (
                      <AreaChart data={performanceData}>
                        <defs>
                          <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis 
                          dataKey="name" 
                          stroke="#9CA3AF" 
                          tick={{ fill: '#9CA3AF', fontSize: 12 }}
                        />
                        <YAxis 
                          stroke="#9CA3AF"
                          tick={{ fill: '#9CA3AF', fontSize: 12 }}
                          tickFormatter={(value) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#1E293B', 
                            border: '1px solid #475569',
                            borderRadius: '8px',
                            padding: '12px'
                          }}
                          labelStyle={{ color: '#E2E8F0', fontWeight: 'bold' }}
                          formatter={(value: any) => [`${value >= 0 ? '+' : ''}${value.toFixed(2)}%`, 'Return']}
                        />
                        <Area 
                          type="monotone" 
                          dataKey="value" 
                          stroke="#3B82F6" 
                          strokeWidth={3}
                          fill="url(#areaGradient)"
                        />
                      </AreaChart>
                    )}
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-[300px] text-gray-400">
                    <div className="text-center">
                      <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No performance data available</p>
                    </div>
                  </div>
                )}
              </div>

              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                  <Brain className="w-5 h-5 text-purple-400" />
                  Trend Distribution
                </h2>
                {pieData.length > 0 && pieData.some(d => d.value > 0) ? (
                  <div className="flex flex-col items-center" style={{ width: '100%', minWidth: 0 }}>
                    <div style={{ width: '100%', height: 250, minWidth: 0, minHeight: 250 }}>
                      <ResponsiveContainer width="100%" height={250} minWidth={0}>
                      <PieChart>
                        <Pie
                          data={pieData.filter(d => d.value > 0)}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, percent, value }) => 
                            value > 0 && percent !== undefined ? `${name}\n${(percent * 100).toFixed(0)}%` : ''
                          }
                          outerRadius={90}
                          innerRadius={40}
                          fill="#8884d8"
                          dataKey="value"
                          paddingAngle={2}
                        >
                          {pieData.filter(d => d.value > 0).map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#1E293B', 
                            border: '1px solid #475569',
                            borderRadius: '8px',
                            padding: '12px'
                          }}
                          formatter={(value: any) => [value, 'Signals']}
                        />
                      </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="mt-4 flex flex-wrap justify-center gap-4">
                      {pieData.filter(d => d.value > 0).map((entry, index) => (
                        <div key={index} className="flex items-center gap-2">
                          <div 
                            className="w-4 h-4 rounded-full" 
                            style={{ backgroundColor: entry.color }}
                          ></div>
                          <span className="text-sm text-gray-300">
                            {entry.name}: {entry.value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-[300px] text-gray-400">
                    <div className="text-center">
                      <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No signal data available</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold text-white mb-4">Observation Results</h2>
              <div className="space-y-3">
                {analytics?.predictions?.slice(0, 5).map((pred: PredictionItem, index: number) => (
                  <div 
                    key={index} 
                    className="flex items-center justify-between p-3 bg-slate-700 rounded-lg hover:bg-slate-600 transition-colors cursor-pointer"
                    onClick={() => loadFeaturesForSymbol(pred.symbol)}
                  >
                    <div>
                      <p className="text-white font-semibold">{pred.symbol}</p>
                      <p className="text-gray-400 text-sm">
                        {pred.action === 'LONG' ? 'UPTREND' : pred.action === 'SHORT' ? 'DOWNTREND' : 'NEUTRAL'}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-white font-semibold">
                        ${pred.predicted_price?.toFixed(2) || pred.current_price?.toFixed(2) || 'N/A'}
                      </p>
                      <p className="text-gray-400 text-sm">
                        {((pred.confidence || 0) * 100).toFixed(1)}% confidence
                      </p>
                      {pred.predicted_return !== undefined && (
                        <p className={`text-xs ${pred.predicted_return > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {pred.predicted_return > 0 ? '+' : ''}{pred.predicted_return.toFixed(2)}%
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Ensemble Statistics */}
            {analytics?.ensembleStats && (
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                  <Brain className="w-5 h-5 text-purple-400" />
                  Ensemble Statistics
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <p className="text-gray-400 text-sm mb-1">Models Aligned</p>
                    <p className="text-2xl font-bold text-green-400">
                      {analytics.ensembleStats.aligned}/{analytics.ensembleStats.totalPredictions}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {((analytics.ensembleStats.aligned / analytics.ensembleStats.totalPredictions) * 100).toFixed(1)}% agreement
                    </p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <p className="text-gray-400 text-sm mb-1">Price Agreement</p>
                    <p className="text-2xl font-bold text-blue-400">
                      {analytics.ensembleStats.priceAgreement}/{analytics.ensembleStats.totalPredictions}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {((analytics.ensembleStats.priceAgreement / analytics.ensembleStats.totalPredictions) * 100).toFixed(1)}% consensus
                    </p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <p className="text-gray-400 text-sm mb-1">Average Return</p>
                    <p className={`text-2xl font-bold ${analytics.avgReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {analytics.avgReturn >= 0 ? '+' : ''}{analytics.avgReturn.toFixed(2)}%
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Across all predictions</p>
                  </div>
                </div>
              </div>
            )}

            {/* Model Performance Comparison */}
            {analytics?.modelPerformance && (
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-blue-400" />
                  Individual Model Performance
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(analytics.modelPerformance).map(([model, stats]: [string, any]) => (
                    <div key={model} className="bg-slate-700/50 rounded-lg p-4">
                      <p className="text-gray-400 text-xs mb-2 capitalize">{model.replace('_', ' ')}</p>
                      <p className="text-white font-semibold text-lg">{stats.count} predictions</p>
                      {stats.avgReturn !== undefined && (
                        <p className={`text-sm font-medium mt-1 ${stats.avgReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {stats.avgReturn >= 0 ? '+' : ''}{stats.avgReturn.toFixed(2)}% avg
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Features Display */}
            {features && selectedSymbol && (
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                    <Zap className="w-5 h-5 text-yellow-400" />
                    Technical Features - {selectedSymbol}
                  </h2>
                  <button
                    onClick={() => {
                      setFeatures(null);
                      setSelectedSymbol(null);
                    }}
                    className="text-gray-400 hover:text-white text-sm"
                  >
                    Close
                  </button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-h-96 overflow-y-auto">
                  {Object.entries(features).slice(0, 50).map(([key, value]: [string, any]) => (
                    <div key={key} className="bg-slate-700/50 rounded p-3">
                      <p className="text-xs text-gray-400 mb-1 truncate">{key}</p>
                      <p className="text-sm text-white font-medium">
                        {typeof value === 'number' ? value.toFixed(4) : String(value)}
                      </p>
                    </div>
                  ))}
                </div>
                {Object.keys(features).length > 50 && (
                  <p className="text-xs text-gray-500 mt-3 text-center">
                    Showing 50 of {Object.keys(features).length} features
                  </p>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  );
};

export default AnalyticsPage;

