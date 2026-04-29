import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import PortfolioSelector from '../components/PortfolioSelector';
import { usePortfolio } from '../contexts/PortfolioContext';
import { useNotification } from '../contexts/NotificationContext';
import { TimeoutError, type PredictionItem } from '../services/api';
import { TrendingUp, TrendingDown, Plus, AlertTriangle, CheckCircle, BookOpen, RotateCcw, Info } from 'lucide-react';
import { formatUSDToINR, formatINRDirect } from '../utils/currencyConverter';
import testResponsiveDesign from '../utils/testResponsive';
import { config } from '../config';
import { calculateHoldingMetrics, formatPercentage } from '../utils/portfolioCalculations';
import { LocalStorageWarning } from '../components/LocalStorageWarning';
import axios from 'axios';

const PortfolioPage = () => {
  const { showNotification } = useNotification();
  const {
    portfolioState,
    availablePortfolios,
    isLoading,
    error,
    addHolding,
    removeHolding,
    refreshPortfolio,
    clearPortfolio,
    updateHoldingStopLoss
  } = usePortfolio();

  const [showAddModal, setShowAddModal] = useState(false);
  const [newPosition, setNewPosition] = useState({ symbol: '', shares: 0, avgPrice: 0 });
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // Risk assessment state - CLIENT-SIDE ONLY (backend does not support risk/trade APIs)
  const [riskAssessment, setRiskAssessment] = useState<any>(null);
  const [showRiskModal, setShowRiskModal] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [riskChecking, setRiskChecking] = useState(false);
  const [riskError, setRiskError] = useState<string | null>(null);
  const [pendingTrade, setPendingTrade] = useState<any>(null);
  // Stop-loss state
  const [stopLossPrice, setStopLossPrice] = useState<number>(0);
  const [stopLossError, setStopLossError] = useState<string | null>(null);
  const [tradeExecutionMode, setTradeExecutionMode] = useState<'market' | 'limit'>('market');
  const [limitPrice, setLimitPrice] = useState<number>(0);
  const [quantity, setQuantity] = useState<number>(0);

  // Calculate risk percentage
  const calculateRiskPercentage = (entryPrice: number, stopLossPrice: number, quantity: number, portfolioValue: number) => {
    const riskPerUnit = Math.abs(entryPrice - stopLossPrice);
    const totalRisk = riskPerUnit * quantity;
    const riskPercent = (totalRisk / portfolioValue) * 100;
    return { riskPerUnit, totalRisk, riskPercent };
  };

  // Available stocks list - US + Indian stocks
  const availableStocks = [
    // US Stocks
    'AAPL', 'GOOGL', 'MSFT', 'TSLA', 'META', 'AMZN', 'NVDA', 'AMD', 'INTC', 'NFLX',
    'IBM', 'ORACLE', 'CISCO', 'UBER', 'COIN', 'PYPL', 'SHOP', 'SQ', 'DDOG', 'NET',
    // Indian Stocks - Banking & Finance
    'SBIN.NS', 'AXISBANK.NS', 'ICICIBANK.NS', 'KOTAKBANK.NS', 'HDFC.NS', 'BAJAJFINSV.NS',
    // Indian Stocks - IT & Tech
    'TCS.NS', 'INFY.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS',
    // Indian Stocks - Automobiles
    'TATAMOTORS.NS', 'M&M.NS', 'MARUTI.NS', 'BAJAJ-AUTO.NS', 'EICHERMOT.NS',
    // Indian Stocks - Steel & Metal
    'TATASTEEL.NS', 'JSWSTEEL.NS', 'HINDALCO.NS', 'NMDC.NS',
    // Indian Stocks - Energy
    'GAIL.NS', 'POWERGRID.NS', 'NTPC.NS', 'COAL.NS', 'BPCL.NS',
    // Indian Stocks - Infrastructure & Transport
    'ADANIPORTS.NS', 'ADANIGREEN.NS', 'ADANITRANS.NS', 'LT.NS',
    // Indian Stocks - Consumer & Others
    'ASIANPAINT.NS', 'ULTRACEMCO.NS', 'SUNPHARMA.NS', 'NESTLEIND.NS', 'BRITANNIA.NS',
    'HINDUNILVR.NS', 'ITC.NS'
  ];

  const handleSymbolInput = (value: string) => {
    const upperValue = value.toUpperCase();
    setNewPosition({ ...newPosition, symbol: upperValue });

    // Filter suggestions based on input
    if (upperValue.length > 0) {
      const filtered = availableStocks.filter(stock =>
        stock.includes(upperValue)
      );
      setSuggestions(filtered.slice(0, 6)); // Show max 6 suggestions
    } else {
      setSuggestions([]);
    }
  };

  const handleSelectSuggestion = (symbol: string) => {
    setNewPosition({ ...newPosition, symbol });
    setSuggestions([]);
  };

  useEffect(() => {
    // Portfolio data is automatically managed by the PortfolioContext
    // No need to manually load here since context handles it
    // Just trigger a refresh to ensure fresh data (without predictions)
    refreshPortfolio({ shouldPredict: false });

    // Run responsive design tests
    testResponsiveDesign();

    // Refresh every 120 seconds (2 minutes) to reduce API calls and avoid rate limits
    // Only refresh prices, not predictions
    const interval = setInterval(() => {
      refreshPortfolio({ shouldPredict: false });
    }, 120000);

    return () => clearInterval(interval);
  }, [refreshPortfolio]);

  // Use the portfolio state from context instead of local state
  const loadPortfolio = async () => {
    // This function is no longer needed since the PortfolioContext manages all portfolio state
    // The context handles loading, refreshing, and state management
    // We just use the data from the context
    refreshPortfolio();
  };



  const handleAddPosition = async () => {
    if (newPosition.symbol && newPosition.shares > 0 && newPosition.avgPrice > 0) {
      try {
        await addHolding({
          symbol: newPosition.symbol.toUpperCase(),
          shares: newPosition.shares,
          avgPrice: newPosition.avgPrice
        });

        setNewPosition({ symbol: '', shares: 0, avgPrice: 0 });
        setShowAddModal(false);
        showNotification('success', 'Position Added', `Added ${newPosition.shares} shares of ${newPosition.symbol}`);
      } catch (error: any) {
        showNotification('error', 'Add Failed', error.message || 'Failed to add position');
      }
    }
  };

  const handleRemovePosition = (symbol: string) => {
    removeHolding(symbol);
    showNotification('info', 'Position Removed', `Removed ${symbol} from portfolio`);
  };

  const handleRefresh = async () => {
    try {
      await refreshPortfolio();
      showNotification('success', 'Portfolio Refreshed', 'Prices updated successfully');
    } catch (error: any) {
      showNotification('error', 'Refresh Failed', error.message || 'Failed to refresh portfolio');
    }
  };

  const handleClearPortfolio = () => {
    clearPortfolio();
    showNotification('warning', 'Portfolio Cleared', 'All positions removed');
  };

  // Assess risk before executing trade - CLIENT-SIDE CALCULATION
  const handleAssessRisk = async (holding: any, action: 'ADD' | 'REDUCE') => {
    setRiskChecking(false);
    setRiskError(null);
    setStopLossError(null);
    setPendingTrade({ holding, action });

    // Initialize stop-loss price (5% below current price for long positions)
    const initialStopLoss = holding.currentPrice * 0.95;
    setStopLossPrice(initialStopLoss);

    // Initialize quantity and limit price
    setQuantity(holding.shares);
    setLimitPrice(holding.currentPrice);

    // CLIENT-SIDE RISK CALCULATION (backend does not support risk API)
    const positionSize = holding.shares * holding.currentPrice;
    const riskAmount = Math.abs(holding.currentPrice - initialStopLoss) * holding.shares;
    const riskPercent = (riskAmount / positionSize) * 100;
    const riskScore = riskPercent > 10 ? 8 : riskPercent > 5 ? 5 : 3;

    setRiskAssessment({
      risk_score: riskScore,
      risk_level: riskScore > 5 ? 'High Risk' : 'Medium Risk',
      recommendation: riskScore > 5 ? 'Proceed with caution' : 'Risk acceptable'
    });
    setShowRiskModal(true);
  };

  // Validate stop-loss price
  const validateStopLoss = (price: number, currentPrice: number, action: string, avgPrice: number) => {
    if (price <= 0) {
      return 'Stop-loss price must be greater than 0';
    }

    // For long positions (ADD)
    if (action === 'ADD') {
      if (price >= currentPrice) {
        return 'Stop-loss must be below current market price for long positions';
      }
      if (price >= avgPrice) {
        return 'Stop-loss should be below entry price for long positions (recommended)';
      }
    }

    // For short positions (REDUCE) - we need to be careful here
    // For a REDUCE action, typically you want to sell if price goes down (for long positions)
    // Or cover if price goes up (for short positions)
    if (action === 'REDUCE') {
      // For reducing a long position, stop-loss should be below current price
      if (pendingTrade?.holding.side === 'long' || !pendingTrade?.holding.side) {
        if (price >= currentPrice) {
          return 'Stop-loss must be below current market price to reduce long position';
        }
      }
      // For reducing a short position, stop-loss should be above current price
      else if (pendingTrade?.holding.side === 'short') {
        if (price <= currentPrice) {
          return 'Stop-loss must be above current market price to reduce short position';
        }
      }
    }

    return null;
  };

  // Update risk assessment when stop-loss changes - CLIENT-SIDE
  const updateRiskAssessment = async (newStopLoss: number) => {
    if (!pendingTrade) return;

    const { holding, action } = pendingTrade;
    const error = validateStopLoss(newStopLoss, holding.currentPrice, action, holding.avgPrice);

    if (error) {
      setStopLossError(error);
      return;
    }

    setStopLossError(null);

    // CLIENT-SIDE RISK RECALCULATION
    const positionSize = holding.shares * holding.currentPrice;
    const riskAmount = Math.abs(holding.currentPrice - newStopLoss) * holding.shares;
    const riskPercent = (riskAmount / positionSize) * 100;
    const riskScore = riskPercent > 10 ? 8 : riskPercent > 5 ? 5 : 3;

    setRiskAssessment({
      risk_score: riskScore,
      risk_level: riskScore > 5 ? 'High Risk' : 'Medium Risk',
      recommendation: riskScore > 5 ? 'Proceed with caution' : 'Risk acceptable'
    });
  };

  // Execute trade after confirmation - REAL TRADE EXECUTION
  const handleExecuteTrade = async () => {
    if (!pendingTrade) return;

    const { holding, action } = pendingTrade;

    // Validate stop-loss before execution
    const error = validateStopLoss(stopLossPrice, holding.currentPrice, action, holding.avgPrice);
    if (error) {
      showNotification('error', 'Invalid Stop-Loss', error);
      return;
    }

    setRiskChecking(true);

    try {
      // Determine order parameters
      const side = action === 'ADD' ? 'BUY' : 'SELL';
      const orderType = tradeExecutionMode.toUpperCase();
      const price = tradeExecutionMode === 'limit' ? limitPrice : 0;
      const execQuantity = quantity > 0 ? quantity : holding.shares;

      // Validate quantity
      if (execQuantity <= 0) {
        showNotification('error', 'Invalid Quantity', 'Quantity must be greater than 0');
        return;
      }

      // For SELL orders, ensure we have enough shares
      if (side === 'SELL' && execQuantity > holding.shares) {
        showNotification('error', 'Insufficient Shares', `You only have ${holding.shares} shares of ${holding.symbol}`);
        return;
      }

      // Call the actual trade execution API
      const response = await axios.post(
        `${config.API_BASE_URL}/api/order`,
        {
          symbol: holding.symbol,
          side: side,
          quantity: execQuantity,
          order_type: orderType,
          price: price || undefined,
          stop_loss: stopLossPrice || undefined
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
          withCredentials: false,
        }
      );

      const result = response.data;

      if (result.success || result.status === 'executed') {
        // Update local portfolio state
        if (side === 'BUY') {
          // Update the holding with new quantity and average price
          await addHolding({
            symbol: holding.symbol,
            shares: execQuantity,
            avgPrice: tradeExecutionMode === 'limit' ? limitPrice : holding.currentPrice
          });
        } else {
          // For SELL, remove or reduce the position
          if (execQuantity >= holding.shares) {
            await removeHolding(holding.symbol);
          }
        }

        // Update stop-loss if provided
        if (stopLossPrice > 0) {
          await updateHoldingStopLoss(holding.symbol, stopLossPrice);
        }

        showNotification(
          'success',
          `Trade Executed Successfully!`,
          `${side} ${execQuantity} ${holding.symbol} @ ${orderType} ₹${(tradeExecutionMode === 'limit' ? limitPrice : holding.currentPrice).toFixed(2)}. Order ID: ${result.order_id || 'N/A'}`
        );
      } else {
        throw new Error(result.message || 'Trade execution failed');
      }

      // Close modals and reset state
      setShowConfirmModal(false);
      setShowRiskModal(false);
      setPendingTrade(null);
      setRiskAssessment(null);
      setStopLossPrice(0);
      setStopLossError(null);
      setQuantity(0);
      setLimitPrice(0);
    } catch (error: any) {
      console.error('Trade execution error:', error);
      const msg = error.response?.data?.detail || error.response?.data?.message || error.message || 'Failed to execute trade';
      showNotification('error', 'Trade Execution Failed', msg);
    } finally {
      setRiskChecking(false);
    }
  };

  return (
    <Layout>
      <div className="space-y-4 w-full">
        <LocalStorageWarning feature="Portfolio" />
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
          <div className="w-full sm:w-auto">
            <h1 className="text-2xl sm:text-3xl font-bold text-white mb-1">Position Tracker</h1>
            <p className="text-gray-400 text-xs sm:text-sm">Exposure monitoring and risk awareness</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            <button
              onClick={handleRefresh}
              disabled={isLoading}
              className="flex-1 sm:flex-none px-3 py-1.5 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 text-white text-xs sm:text-sm font-semibold rounded transition-colors flex items-center justify-center sm:justify-start gap-1.5"
            >
              <RotateCcw className={`w-4 h-4 flex-shrink-0 ${isLoading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Update Prices</span>
              <span className="sm:hidden">Update</span>
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex-1 sm:flex-none px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white text-xs sm:text-sm font-semibold rounded transition-colors flex items-center justify-center sm:justify-start gap-1.5"
            >
              <Plus className="w-4 h-4 flex-shrink-0" />
              <span className="hidden sm:inline">Add Holding</span>
              <span className="sm:hidden">Add</span>
            </button>
          </div>
        </div>

        <div className="mb-4">
          <PortfolioSelector />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <div className="bg-slate-800 rounded-lg p-3 sm:p-4 border border-slate-700">
            <p className="text-gray-400 text-xs mb-1">Tracked Value</p>
            <p className="text-xl sm:text-2xl font-bold text-white truncate">{formatINRDirect(portfolioState.totalValue)}</p>
            <p className="text-gray-500 text-xs mt-1">Current Exposure</p>
          </div>
          <div className="bg-slate-800 rounded-lg p-3 sm:p-4 border border-slate-700">
            <p className="text-gray-400 text-xs mb-1">Unrealized Change</p>
            <p className={`text-xl sm:text-2xl font-bold truncate ${portfolioState.totalGain >= 0 ? 'text-blue-400' : 'text-blue-400'}`}>
              {portfolioState.totalGain >= 0 ? '+' : ''}{formatINRDirect(portfolioState.totalGain)}
            </p>
            <p className={`text-xs mt-1 text-gray-400`}>
              {portfolioState.totalGain >= 0 ? '+' : ''}{(portfolioState.totalGainPercent || 0).toFixed(2)}%
            </p>
          </div>
          <div className="bg-slate-800 rounded-lg p-3 sm:p-4 border border-slate-700">
            <p className="text-gray-400 text-xs mb-1">Active Holdings</p>
            <p className="text-xl sm:text-2xl font-bold text-white">{portfolioState.holdings.length}</p>
            <p className="text-gray-500 text-xs mt-1">Tracked Assets</p>
          </div>
          <div className="bg-slate-800 rounded-lg p-3 sm:p-4 border border-slate-700">
            <p className="text-gray-400 text-xs mb-1">Last Updated</p>
            <p className="text-white text-sm font-medium truncate">
              {portfolioState.lastUpdated
                ? portfolioState.lastUpdated.toLocaleTimeString()
                : 'Never'}
            </p>
            <p className="text-gray-500 text-xs mt-1">Price Data</p>
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <div className="p-3 sm:p-4 border-b border-slate-700 flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-sm sm:text-base font-semibold text-white">Current Holdings</h2>
            {portfolioState.holdings.length > 0 && (
              <button
                onClick={handleClearPortfolio}
                className="text-xs text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-500/10 transition-colors"
              >
                Clear Tracker
              </button>
            )}
          </div>
          {isLoading ? (
            <div className="p-8 text-center text-gray-400">Loading holdings...</div>
          ) : error ? (
            <div className="p-8 text-center text-red-400">
              <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
              <p className="text-xs sm:text-sm">{error}</p>
              <button
                onClick={handleRefresh}
                className="mt-3 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded text-xs sm:text-sm"
              >
                Retry
              </button>
            </div>
          ) : portfolioState.holdings.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs sm:text-sm">
                <thead className="bg-slate-700 sticky top-0">
                  <tr>
                    <th className="px-2 sm:px-3 py-2 text-left font-medium text-gray-300 uppercase whitespace-nowrap">Symbol</th>
                    <th className="px-2 sm:px-3 py-2 text-left font-medium text-gray-300 uppercase whitespace-nowrap">Shares</th>
                    <th className="px-2 sm:px-3 py-2 text-left font-medium text-gray-300 uppercase whitespace-nowrap">Avg Price</th>
                    <th className="px-2 sm:px-3 py-2 text-left font-medium text-gray-300 uppercase whitespace-nowrap">Curr Price</th>
                    <th className="px-2 sm:px-3 py-2 text-left font-medium text-gray-300 uppercase whitespace-nowrap">Stop-Loss</th>
                    <th className="px-2 sm:px-3 py-2 text-left font-medium text-gray-300 uppercase whitespace-nowrap">Market Value</th>
                    <th className="px-2 sm:px-3 py-2 text-left font-medium text-gray-300 uppercase whitespace-nowrap">Unrealized</th>
                    <th className="px-2 sm:px-3 py-2 text-left font-medium text-gray-300 uppercase text-center whitespace-nowrap">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {portfolioState.holdings.map((holding, index) => {
                    const metrics = calculateHoldingMetrics(holding.shares, holding.avgPrice, holding.currentPrice);
                    return (
                      <tr key={index} className="hover:bg-slate-700/50 transition-colors">
                        <td className="px-2 sm:px-3 py-2 sm:py-3 whitespace-nowrap">
                          <span className="text-white font-semibold text-xs sm:text-sm">{holding.symbol}</span>
                        </td>
                        <td className="px-2 sm:px-3 py-2 sm:py-3 whitespace-nowrap text-gray-300">{holding.shares}</td>
                        <td className="px-2 sm:px-3 py-2 sm:py-3 whitespace-nowrap text-gray-300">{formatUSDToINR(holding.avgPrice || 0, holding.symbol)}</td>
                        <td className="px-2 sm:px-3 py-2 sm:py-3 whitespace-nowrap text-white">{formatUSDToINR(holding.currentPrice || 0, holding.symbol)}</td>
                        <td className="px-2 sm:px-3 py-2 sm:py-3 whitespace-nowrap text-white">
                          {holding.stopLossPrice ? (
                            <div className="flex flex-col">
                              <span>{formatUSDToINR(holding.stopLossPrice, holding.symbol)}</span>
                              <span className="text-xs text-gray-400">({((holding.stopLossPrice - holding.avgPrice) / holding.avgPrice * 100).toFixed(1)}%)</span>
                            </div>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-2 sm:px-3 py-2 sm:py-3 whitespace-nowrap text-white text-xs sm:text-sm">{formatUSDToINR(holding.shares * holding.currentPrice, holding.symbol)}</td>
                        <td className="px-2 sm:px-3 py-2 sm:py-3 whitespace-nowrap">
                          <div className="flex items-center space-x-1 sm:space-x-2 text-xs sm:text-sm">
                            {metrics.unrealizedValue >= 0 ? (
                              <TrendingUp className="w-3 h-3 sm:w-4 sm:h-4 text-blue-400 flex-shrink-0" />
                            ) : (
                              <TrendingDown className="w-3 h-3 sm:w-4 sm:h-4 text-blue-400 flex-shrink-0" />
                            )}
                            <span className="text-gray-300">
                              {formatUSDToINR(metrics.unrealizedValue, holding.symbol)} ({formatPercentage(metrics.unrealizedPercent)})
                            </span>
                          </div>
                        </td>
                        <td className="px-1 sm:px-3 py-2 sm:py-3 whitespace-nowrap">
                          <div className="flex gap-0.5 sm:gap-1 justify-end">
                            <button
                              onClick={() => handleAssessRisk(holding, 'ADD')}
                              disabled={riskChecking}
                              className="px-1.5 sm:px-2.5 py-0.5 sm:py-1 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 text-white text-xs rounded transition-colors flex-shrink-0"
                              title="Increase Exposure (Simulated)"
                            >
                              <span className="hidden sm:inline">Increase</span>
                              <span className="sm:hidden">+</span>
                            </button>
                            <button
                              onClick={() => handleAssessRisk(holding, 'REDUCE')}
                              disabled={riskChecking}
                              className="px-1.5 sm:px-2.5 py-0.5 sm:py-1 bg-purple-500 hover:bg-purple-600 disabled:bg-purple-400 text-white text-xs rounded transition-colors flex-shrink-0"
                              title="Decrease Exposure (Simulated)"
                            >
                              <span className="hidden sm:inline">Decrease</span>
                              <span className="sm:hidden">−</span>
                            </button>
                            <button
                              onClick={() => handleRemovePosition(holding.symbol)}
                              className="px-1.5 sm:px-2.5 py-0.5 sm:py-1 bg-slate-600 hover:bg-slate-700 text-white text-xs rounded transition-colors flex-shrink-0"
                              title="Remove from Tracker"
                            >
                              <span className="hidden sm:inline">Remove</span>
                              <span className="sm:hidden">×</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-6 sm:p-8 text-center text-gray-400">
              <BookOpen className="w-12 h-12 sm:w-12 sm:h-12 mx-auto mb-3 text-slate-600" />
              <p className="mb-2 text-sm sm:text-base">No holdings tracked yet</p>
              <p className="text-xs sm:text-sm text-gray-500 mb-4">Add holdings to monitor exposure and understand risk allocation</p>
              <button
                onClick={() => setShowAddModal(true)}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-xs sm:text-sm font-medium"
              >
                Add First Holding
              </button>
            </div>
          )}
        </div>

        {showAddModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-lg p-4 sm:p-6 border border-slate-700 max-w-md w-full max-h-[90vh] overflow-y-auto">
              <h3 className="text-lg sm:text-xl font-semibold text-white mb-4">Add Holding to Tracker</h3>
              <div className="space-y-3 sm:space-y-4">
                <div className="relative">
                  <label className="block text-xs sm:text-sm font-medium text-gray-300 mb-2">Symbol</label>
                  <input
                    type="text"
                    value={newPosition.symbol}
                    onChange={(e) => handleSymbolInput(e.target.value)}
                    placeholder="e.g., AAPL, TCS.NS"
                    className="w-full px-3 sm:px-4 py-1.5 sm:py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-xs sm:text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />

                  {/* Suggestions Dropdown */}
                  {suggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-slate-700 border border-slate-600 rounded-lg shadow-lg z-10 max-h-48 overflow-y-auto">
                      {suggestions.map((stock) => (
                        <button
                          key={stock}
                          type="button"
                          onClick={() => handleSelectSuggestion(stock)}
                          className="w-full px-3 sm:px-4 py-1.5 sm:py-2 text-left text-white text-xs sm:text-sm hover:bg-slate-600 transition-colors first:rounded-t-lg last:rounded-b-lg border-b border-slate-600 last:border-b-0"
                        >
                          {stock}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <div>
                  <label className="block text-xs sm:text-sm font-medium text-gray-300 mb-2">Shares</label>
                  <input
                    type="number"
                    value={newPosition.shares || ''}
                    onChange={(e) => setNewPosition({ ...newPosition, shares: parseFloat(e.target.value) || 0 })}
                    placeholder="Number of shares"
                    className="w-full px-3 sm:px-4 py-1.5 sm:py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs sm:text-sm font-medium text-gray-300 mb-2">Average Price</label>
                  <input
                    type="number"
                    value={newPosition.avgPrice || ''}
                    onChange={(e) => setNewPosition({ ...newPosition, avgPrice: parseFloat(e.target.value) || 0 })}
                    placeholder="Purchase price per share"
                    step="0.01"
                    className="w-full px-3 sm:px-4 py-1.5 sm:py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
                  <button
                    onClick={handleAddPosition}
                    disabled={isLoading}
                    className="flex-1 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 text-white text-xs sm:text-sm rounded-lg font-medium"
                  >
                    {isLoading ? 'Adding...' : 'Add to Tracker'}
                  </button>
                  <button
                    onClick={() => {
                      setShowAddModal(false);
                      setNewPosition({ symbol: '', shares: 0, avgPrice: 0 });
                    }}
                    className="flex-1 px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white text-xs sm:text-sm rounded-lg"
                  >
                    Cancel
                  </button>
                </div>

                <div className="bg-yellow-900/20 border border-yellow-800 rounded-lg p-2 sm:p-3 mt-4">
                  <div className="flex items-start gap-2">
                    <Info className="w-3 h-3 sm:w-4 sm:h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-yellow-200 text-xs font-medium mb-1">Risk Monitoring Tool</p>
                      <p className="text-yellow-300 text-xs">
                        This tracker helps you understand exposure allocation. All data is for educational purposes only.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Risk Assessment Modal */}
        {showRiskModal && riskAssessment && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-lg p-4 sm:p-6 border border-slate-700 max-w-md w-full">
              <div className="flex items-center gap-2 sm:gap-3 mb-4">
                {riskAssessment.risk_score > 5 ? (
                  <AlertTriangle className="w-5 h-5 sm:w-6 sm:h-6 text-red-500 flex-shrink-0" />
                ) : (
                  <CheckCircle className="w-5 h-5 sm:w-6 sm:h-6 text-green-500 flex-shrink-0" />
                )}
                <h3 className="text-lg sm:text-xl font-semibold text-white">
                  Risk Assessment
                </h3>
              </div>

              <div className="space-y-3 sm:space-y-4">
                <div className="bg-slate-700/50 rounded-lg p-3 sm:p-4">
                  <p className="text-gray-300 text-xs sm:text-sm mb-1">Risk Score</p>
                  <p className={`text-xl sm:text-2xl font-bold ${riskAssessment.risk_score > 5 ? 'text-red-400' : 'text-green-400'
                    }`}>
                    {(riskAssessment.risk_score || 0).toFixed(1)} / 10
                  </p>
                  <p className="text-gray-400 text-xs mt-2">
                    {riskAssessment.risk_level || 'Medium Risk'}
                  </p>
                </div>

                <div className="bg-slate-700/50 rounded-lg p-3 sm:p-4">
                  <p className="text-gray-300 text-xs sm:text-sm mb-2">Recommendation</p>
                  <p className="text-white text-xs sm:text-sm">
                    {riskAssessment.recommendation || 'Proceed with caution'}
                  </p>
                </div>

                {riskAssessment.risk_score > 5 && (
                  <div className="bg-red-900/30 border border-red-800 rounded-lg p-2 sm:p-3">
                    <p className="text-red-200 text-xs sm:text-sm">
                      ⚠️ High Risk Alert: Risk score exceeds 5%. Confirm to proceed or cancel.
                    </p>
                  </div>
                )}

                {/* Order Type and Quantity */}
                <div className="bg-slate-700/50 rounded-lg p-3 sm:p-4">
                  <label className="block text-gray-300 text-xs sm:text-sm mb-2">Order Type</label>
                  <div className="flex gap-2 mb-3">
                    <button
                      type="button"
                      onClick={() => setTradeExecutionMode('market')}
                      className={`flex-1 px-3 py-2 rounded-lg font-semibold text-xs sm:text-sm transition-colors ${tradeExecutionMode === 'market'
                        ? 'bg-blue-500 text-white'
                        : 'bg-slate-600 text-gray-300 hover:bg-slate-500'
                        }`}
                    >
                      Market Order
                    </button>
                    <button
                      type="button"
                      onClick={() => setTradeExecutionMode('limit')}
                      className={`flex-1 px-3 py-2 rounded-lg font-semibold text-xs sm:text-sm transition-colors ${tradeExecutionMode === 'limit'
                        ? 'bg-blue-500 text-white'
                        : 'bg-slate-600 text-gray-300 hover:bg-slate-500'
                        }`}
                    >
                      Limit Order
                    </button>
                  </div>

                  {/* Limit Price Input (only for limit orders) */}
                  {tradeExecutionMode === 'limit' && (
                    <div className="mb-3">
                      <label className="block text-gray-300 text-xs sm:text-sm mb-1">Limit Price</label>
                      <input
                        type="number"
                        value={limitPrice || ''}
                        onChange={(e) => setLimitPrice(parseFloat(e.target.value) || 0)}
                        step="0.05"
                        className="w-full px-3 py-1.5 bg-slate-600 border border-slate-500 rounded text-white text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Enter limit price"
                      />
                      <p className="text-gray-400 text-xs mt-1">
                        Current: ₹{pendingTrade?.holding.currentPrice.toFixed(2)}
                      </p>
                    </div>
                  )}

                  {/* Quantity Input */}
                  <div>
                    <label className="block text-gray-300 text-xs sm:text-sm mb-1">Quantity</label>
                    <input
                      type="number"
                      value={quantity || ''}
                      onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
                      className="w-full px-3 py-1.5 bg-slate-600 border border-slate-500 rounded text-white text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Number of shares"
                      max={pendingTrade?.action === 'REDUCE' ? pendingTrade?.holding.shares : undefined}
                    />
                    <p className="text-gray-400 text-xs mt-1">
                      Available: {pendingTrade?.holding.shares} shares
                    </p>
                  </div>
                </div>

                {/* Stop-Loss Input */}
                <div className="bg-slate-700/50 rounded-lg p-3 sm:p-4">
                  <label className="block text-gray-300 text-xs sm:text-sm mb-2">Stop-Loss Price (Optional)</label>
                  <input
                    type="number"
                    value={stopLossPrice || ''}
                    onChange={(e) => {
                      const newPrice = parseFloat(e.target.value) || 0;
                      setStopLossPrice(newPrice);
                      updateRiskAssessment(newPrice);
                    }}
                    step="0.01"
                    className="w-full px-3 py-1.5 bg-slate-600 border border-slate-500 rounded text-white text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter stop-loss price (optional)"
                  />
                  {stopLossError && (
                    <p className="text-red-400 text-xs mt-1">{stopLossError}</p>
                  )}
                  <p className="text-gray-400 text-xs mt-1">
                    Current: ₹{pendingTrade?.holding.currentPrice.toFixed(2)}
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
                  <button
                    onClick={() => {
                      const error = validateStopLoss(stopLossPrice, pendingTrade.holding.currentPrice, pendingTrade.action, pendingTrade.holding.avgPrice);
                      if (error) {
                        showNotification('error', 'Invalid Stop-Loss', error);
                        return;
                      }
                      setShowConfirmModal(true);
                    }}
                    disabled={riskChecking || !!stopLossError}
                    className="flex-1 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 text-white text-xs sm:text-sm rounded-lg font-semibold flex items-center justify-center gap-2"
                  >
                    {riskChecking && (
                      <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    )}
                    {riskChecking ? 'Processing...' : 'Proceed to Confirm'}
                  </button>
                  <button
                    onClick={() => {
                      setShowRiskModal(false);
                      setPendingTrade(null);
                      setRiskAssessment(null);
                      setStopLossPrice(0);
                      setStopLossError(null);
                      setRiskChecking(false);
                    }}
                    className="flex-1 px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white text-xs sm:text-sm rounded-lg font-semibold"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Trade Confirmation Modal */}
        {showConfirmModal && pendingTrade && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-lg p-4 sm:p-6 border border-slate-700 max-w-md w-full">
              <h3 className="text-lg sm:text-xl font-semibold text-white mb-4">
                Confirm Exposure Change
              </h3>

              <div className="space-y-2 sm:space-y-3 mb-4 text-xs sm:text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-300">Symbol:</span>
                  <span className="text-white font-semibold">{pendingTrade.holding.symbol}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Action:</span>
                  <span className={`font-semibold ${pendingTrade.action === 'ADD' ? 'text-blue-400' : 'text-purple-400'
                    }`}>
                    {pendingTrade.action === 'ADD' ? 'BUY' : 'SELL'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Order Type:</span>
                  <span className="text-white font-semibold">{tradeExecutionMode.toUpperCase()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Quantity:</span>
                  <span className="text-white">{quantity || pendingTrade.holding.shares} shares</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Price:</span>
                  <span className="text-white">
                    {tradeExecutionMode === 'limit'
                      ? `₹${limitPrice.toFixed(2)} (Limit)`
                      : `₹${(pendingTrade.holding.currentPrice || 0).toFixed(2)} (Market)`}
                  </span>
                </div>
                {stopLossPrice > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-300">Stop-Loss:</span>
                    <span className="text-white">₹{stopLossPrice.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between border-t border-slate-700 pt-2 sm:pt-3">
                  <span className="text-gray-300 font-semibold">Total Value:</span>
                  <span className="text-white font-bold">
                    ₹{((quantity || pendingTrade.holding.shares) * (tradeExecutionMode === 'limit' ? limitPrice : (pendingTrade.holding.currentPrice || 0))).toFixed(2)}
                  </span>
                </div>
              </div>

              <div className="bg-yellow-900/30 border border-yellow-800 rounded-lg p-2 sm:p-3 mb-4">
                <p className="text-yellow-200 text-xs sm:text-sm">
                  📋 Please review the order details carefully before confirming. This will execute a real trade in the market.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
                <button
                  onClick={handleExecuteTrade}
                  disabled={riskChecking}
                  className="flex-1 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 text-white text-xs sm:text-sm rounded-lg font-semibold flex items-center justify-center gap-2"
                >
                  {riskChecking && (
                    <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  )}
                  {riskChecking ? 'Processing...' : 'Confirm Change'}
                </button>
                <button
                  onClick={() => {
                    setShowConfirmModal(false);
                    setShowRiskModal(true);
                  }}
                  className="flex-1 px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white text-xs sm:text-sm rounded-lg font-semibold"
                >
                  Back
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default PortfolioPage;
