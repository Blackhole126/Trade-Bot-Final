import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { usePortfolio } from '../contexts/PortfolioContext';
import { useScenario } from '../contexts/ScenarioContext';
import { useNotification } from '../contexts/NotificationContext';
import { TrendingUp, TrendingDown, Plus, AlertTriangle, RotateCcw, Trash2, Edit3, Play, Pause } from 'lucide-react';
import { formatUSDToINR, formatINRDirect } from '../utils/currencyConverter';
import SymbolAutocomplete from '../components/SymbolAutocomplete';

const ScenarioPortfolioPage = () => {
  const { showNotification } = useNotification();
  const { portfolioState } = usePortfolio();
  const {
    scenarios,
    activeScenario,
    isLoading,
    error,
    createScenario,
    loadScenario,
    updateHoldingPrice,
    addHolding,
    removeHolding,
    resetScenario,
    deleteScenario,
    updateScenarioMetadata,
    calculateScenarioMetrics
  } = useScenario();

  // Form states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newScenario, setNewScenario] = useState({ name: '', description: '' });
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingScenario, setEditingScenario] = useState({ id: '', name: '', description: '' });
  const [showPriceModal, setShowPriceModal] = useState(false);
  const [priceUpdate, setPriceUpdate] = useState({ symbol: '', newPrice: 0, notes: '' });
  const [showAddModal, setShowAddModal] = useState(false);
  const [newHolding, setNewHolding] = useState({ symbol: '', shares: 0, avgPrice: 0 });

  // Initialize with a default scenario if none exist
  useEffect(() => {
    if (scenarios.length === 0 && portfolioState.holdings.length > 0) {
      try {
        const scenarioId = createScenario(
          'Default Simulation',
          'Initial what-if scenario based on current portfolio',
          portfolioState.holdings
        );
      } catch (err) {
        // Silently fail - default scenario creation is optional
      }
    }
  }, [scenarios.length, portfolioState.holdings, createScenario]);

  const handleCreateScenario = () => {
    if (!newScenario.name.trim()) {
      showNotification('error', 'Invalid Input', 'Scenario name is required');
      return;
    }

    try {
      const scenarioId = createScenario(
        newScenario.name,
        newScenario.description,
        portfolioState.holdings
      );
      
      showNotification('success', 'Scenario Created', `Created scenario: ${newScenario.name}`);
      setNewScenario({ name: '', description: '' });
      setShowCreateModal(false);
    } catch (error: any) {
      showNotification('error', 'Create Failed', error.message || 'Failed to create scenario');
    }
  };

  const handleLoadScenario = (scenarioId: string) => {
    try {
      loadScenario(scenarioId);
      showNotification('success', 'Scenario Loaded', 'Scenario loaded successfully');
    } catch (error: any) {
      showNotification('error', 'Load Failed', error.message || 'Failed to load scenario');
    }
  };

  const handleUpdatePrice = () => {
    if (!activeScenario) {
      showNotification('error', 'No Active Scenario', 'Please select a scenario first');
      return;
    }

    if (!priceUpdate.symbol || priceUpdate.newPrice <= 0) {
      showNotification('error', 'Invalid Input', 'Valid symbol and price are required');
      return;
    }

    try {
      updateHoldingPrice(
        priceUpdate.symbol, 
        priceUpdate.newPrice, 
        priceUpdate.notes || `Manual price update to ${priceUpdate.newPrice}`
      );
      showNotification('success', 'Price Updated', `Updated ${priceUpdate.symbol} to ₹${priceUpdate.newPrice}`);
      setPriceUpdate({ symbol: '', newPrice: 0, notes: '' });
      setShowPriceModal(false);
    } catch (error: any) {
      showNotification('error', 'Update Failed', error.message || 'Failed to update price');
    }
  };

  const handleAddHolding = () => {
    if (!activeScenario) {
      showNotification('error', 'No Active Scenario', 'Please select a scenario first');
      return;
    }

    if (!newHolding.symbol || newHolding.shares <= 0 || newHolding.avgPrice <= 0) {
      showNotification('error', 'Invalid Input', 'Valid symbol, shares, and price are required');
      return;
    }

    try {
      addHolding({
        symbol: newHolding.symbol.toUpperCase(),
        shares: newHolding.shares,
        avgPrice: newHolding.avgPrice,
        stopLossPrice: null,
        side: 'long'
      });
      
      showNotification('success', 'Holding Added', `Added ${newHolding.shares} shares of ${newHolding.symbol}`);
      setNewHolding({ symbol: '', shares: 0, avgPrice: 0 });
      setShowAddModal(false);
    } catch (error: any) {
      showNotification('error', 'Add Failed', error.message || 'Failed to add holding');
    }
  };

  const handleRemoveHolding = (symbol: string) => {
    if (!activeScenario) return;
    
    try {
      removeHolding(symbol);
      showNotification('info', 'Holding Removed', `Removed ${symbol} from scenario`);
    } catch (error: any) {
      showNotification('error', 'Remove Failed', error.message || 'Failed to remove holding');
    }
  };

  const handleResetScenario = () => {
    if (!activeScenario) return;
    
    try {
      resetScenario();
      showNotification('success', 'Scenario Reset', 'Scenario reset to base values');
    } catch (error: any) {
      showNotification('error', 'Reset Failed', error.message || 'Failed to reset scenario');
    }
  };

  const handleDeleteScenario = (scenarioId: string) => {
    if (!window.confirm('Are you sure you want to delete this scenario? This cannot be undone.')) {
      return;
    }
    
    try {
      deleteScenario(scenarioId);
      showNotification('warning', 'Scenario Deleted', 'Scenario deleted successfully');
    } catch (error: any) {
      showNotification('error', 'Delete Failed', error.message || 'Failed to delete scenario');
    }
  };

  const calculateScenarioDifferences = () => {
    if (!activeScenario) return { valueDiff: 0, gainDiff: 0, gainPercentDiff: 0 };
    
    const baseValue = activeScenario.baseHoldings.reduce((sum, h) => sum + (h.shares * h.currentPrice), 0);
    const baseGain = activeScenario.baseHoldings.reduce((sum, h) => sum + ((h.currentPrice - h.avgPrice) * h.shares), 0);
    const baseGainPercent = baseValue > 0 ? (baseGain / baseValue) * 100 : 0;
    
    const currentValue = activeScenario.totalValue;
    const currentGain = activeScenario.totalGain;
    const currentGainPercent = activeScenario.totalGainPercent;
    
    return {
      valueDiff: currentValue - baseValue,
      gainDiff: currentGain - baseGain,
      gainPercentDiff: currentGainPercent - baseGainPercent
    };
  };

  const differences = calculateScenarioDifferences();

  return (
    <Layout>
      <div className="p-4 sm:p-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2">Scenario Portfolio</h1>
              <p className="text-gray-400 text-sm sm:text-base">
                What-if simulations for stress testing and analysis
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg text-sm sm:text-base font-medium flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              New Scenario
            </button>
          </div>

          {error && (
            <div className="bg-red-900/30 border border-red-800 rounded-lg p-3 mb-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
                <span className="text-red-200 text-sm">{error}</span>
              </div>
            </div>
          )}
        </div>

        {/* Scenario Selector */}
        <div className="mb-6">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
            <h2 className="text-lg font-semibold text-white mb-3">Scenarios</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {scenarios.map((scenario) => (
                <div
                  key={scenario.id}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    activeScenario?.id === scenario.id
                      ? 'border-purple-500 bg-purple-500/10'
                      : 'border-slate-600 hover:border-slate-500 bg-slate-700/50 hover:bg-slate-700'
                  }`}
                  onClick={() => handleLoadScenario(scenario.id)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-medium text-white text-sm truncate">{scenario.name}</h3>
                    {activeScenario?.id === scenario.id && (
                      <span className="px-2 py-1 bg-purple-500 text-white text-xs rounded">Active</span>
                    )}
                  </div>
                  <p className="text-gray-400 text-xs mb-2 line-clamp-2">{scenario.description}</p>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">
                      {scenario.simulatedHoldings.length} holdings
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteScenario(scenario.id);
                      }}
                      className="text-red-400 hover:text-red-300 p-1"
                      title="Delete scenario"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Active Scenario Dashboard */}
        {activeScenario && (
          <div className="space-y-6">
            {/* Scenario Info and Controls */}
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
                <div>
                  <h2 className="text-xl font-bold text-white">{activeScenario.name}</h2>
                  <p className="text-gray-400 text-sm">{activeScenario.description}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setShowPriceModal(true)}
                    className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded flex items-center gap-1"
                  >
                    <Play className="w-3 h-3" />
                    Update Price
                  </button>
                  <button
                    onClick={() => setShowAddModal(true)}
                    className="px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white text-sm rounded flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" />
                    Add Holding
                  </button>
                  <button
                    onClick={handleResetScenario}
                    disabled={isLoading}
                    className="px-3 py-1.5 bg-yellow-500 hover:bg-yellow-600 disabled:bg-yellow-400 text-white text-sm rounded flex items-center gap-1"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Reset
                  </button>
                </div>
              </div>

              {/* Scenario Metrics */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="bg-slate-700/50 rounded-lg p-3">
                  <p className="text-gray-400 text-xs mb-1">Scenario Value</p>
                  <p className="text-lg font-bold text-white">{formatINRDirect(activeScenario.totalValue)}</p>
                  <p className={`text-xs ${differences.valueDiff >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {differences.valueDiff >= 0 ? '+' : ''}{formatINRDirect(differences.valueDiff)} vs base
                  </p>
                </div>
                <div className="bg-slate-700/50 rounded-lg p-3">
                  <p className="text-gray-400 text-xs mb-1">Total Gain/Loss</p>
                  <p className={`text-lg font-bold ${activeScenario.totalGain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {activeScenario.totalGain >= 0 ? '+' : ''}{formatINRDirect(activeScenario.totalGain)}
                  </p>
                  <p className={`text-xs ${differences.gainDiff >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {differences.gainDiff >= 0 ? '+' : ''}{formatINRDirect(differences.gainDiff)} vs base
                  </p>
                </div>
                <div className="bg-slate-700/50 rounded-lg p-3">
                  <p className="text-gray-400 text-xs mb-1">Return %</p>
                  <p className={`text-lg font-bold ${activeScenario.totalGainPercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {activeScenario.totalGainPercent >= 0 ? '+' : ''}{(activeScenario.totalGainPercent || 0).toFixed(2)}%
                  </p>
                  <p className={`text-xs ${differences.gainPercentDiff >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {differences.gainPercentDiff >= 0 ? '+' : ''}{(differences.gainPercentDiff || 0).toFixed(2)}% vs base
                  </p>
                </div>
                <div className="bg-slate-700/50 rounded-lg p-3">
                  <p className="text-gray-400 text-xs mb-1">Last Updated</p>
                  <p className="text-white text-sm font-medium">
                    {activeScenario.lastUpdated?.toLocaleTimeString() || 'Never'}
                  </p>
                  <p className="text-gray-500 text-xs">Simulation Data</p>
                </div>
              </div>
            </div>

            {/* Scenario Holdings */}
            <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
              <div className="p-4 border-b border-slate-700">
                <h2 className="text-lg font-semibold text-white">Scenario Holdings</h2>
                <p className="text-gray-400 text-sm mt-1">
                  {activeScenario.simulatedHoldings.length} positions in this scenario
                </p>
              </div>
              
              {isLoading ? (
                <div className="p-8 text-center text-gray-400">Loading scenario...</div>
              ) : activeScenario.simulatedHoldings.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-700 sticky top-0">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium text-gray-300 uppercase">Symbol</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-300 uppercase">Shares</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-300 uppercase">Avg Price</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-300 uppercase">Current Price</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-300 uppercase">Value</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-300 uppercase">Gain/Loss</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-300 uppercase">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700">
                      {activeScenario.simulatedHoldings.map((holding) => {
                        const gain = (holding.currentPrice - holding.avgPrice) * holding.shares;
                        const gainPercent = ((holding.currentPrice - holding.avgPrice) / holding.avgPrice) * 100;
                        return (
                          <tr key={`${holding.symbol}-${holding.scenarioId}`} className="hover:bg-slate-700/50 transition-colors">
                            <td className="px-4 py-3">
                              <span className="text-white font-semibold">{holding.symbol}</span>
                              {holding.notes && (
                                <p className="text-gray-400 text-xs mt-1">{holding.notes}</p>
                              )}
                            </td>
                            <td className="px-4 py-3 text-gray-300">{holding.shares}</td>
                            <td className="px-4 py-3 text-gray-300">{formatUSDToINR(holding.avgPrice, holding.symbol)}</td>
                            <td className="px-4 py-3 text-white">{formatUSDToINR(holding.currentPrice, holding.symbol)}</td>
                            <td className="px-4 py-3 text-white">{formatUSDToINR(holding.value, holding.symbol)}</td>
                            <td className="px-4 py-3">
                              <div className="flex items-center space-x-2">
                                {gain >= 0 ? (
                                  <TrendingUp className="w-4 h-4 text-green-400" />
                                ) : (
                                  <TrendingDown className="w-4 h-4 text-red-400" />
                                )}
                                <span className={gain >= 0 ? 'text-green-400' : 'text-red-400'}>
                                  {formatUSDToINR(gain, holding.symbol)} ({gainPercent >= 0 ? '+' : ''}{(gainPercent || 0).toFixed(2)}%)
                                </span>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <button
                                onClick={() => handleRemoveHolding(holding.symbol)}
                                className="px-2 py-1 bg-red-500 hover:bg-red-600 text-white text-xs rounded transition-colors"
                                title="Remove from scenario"
                              >
                                Remove
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-8 text-center text-gray-400">
                  <p className="mb-2">No holdings in this scenario</p>
                  <p className="text-sm text-gray-500">Add positions to start your simulation</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Modals */}
        {/* Create Scenario Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 max-w-md w-full">
              <h3 className="text-xl font-semibold text-white mb-4">Create New Scenario</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Scenario Name</label>
                  <input
                    type="text"
                    value={newScenario.name}
                    onChange={(e) => setNewScenario({ ...newScenario, name: e.target.value })}
                    placeholder="e.g., Bull Market Simulation"
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Description</label>
                  <textarea
                    value={newScenario.description}
                    onChange={(e) => setNewScenario({ ...newScenario, description: e.target.value })}
                    placeholder="Describe your what-if scenario..."
                    rows={3}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={handleCreateScenario}
                    disabled={isLoading || !newScenario.name.trim()}
                    className="flex-1 px-4 py-2 bg-purple-500 hover:bg-purple-600 disabled:bg-purple-400 text-white rounded font-medium"
                  >
                    {isLoading ? 'Creating...' : 'Create Scenario'}
                  </button>
                  <button
                    onClick={() => {
                      setShowCreateModal(false);
                      setNewScenario({ name: '', description: '' });
                    }}
                    className="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white rounded font-medium"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Update Price Modal */}
        {showPriceModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 max-w-md w-full">
              <h3 className="text-xl font-semibold text-white mb-4">Update Holding Price</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
                  <select
                    value={priceUpdate.symbol}
                    onChange={(e) => setPriceUpdate({ ...priceUpdate, symbol: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select a holding</option>
                    {activeScenario?.simulatedHoldings.map(holding => (
                      <option key={holding.symbol} value={holding.symbol}>
                        {holding.symbol} (Current: ₹{holding.currentPrice.toFixed(2)})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">New Price</label>
                  <input
                    type="number"
                    value={priceUpdate.newPrice || ''}
                    onChange={(e) => setPriceUpdate({ ...priceUpdate, newPrice: parseFloat(e.target.value) || 0 })}
                    placeholder="Enter new price"
                    step="0.01"
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Notes (Optional)</label>
                  <input
                    type="text"
                    value={priceUpdate.notes}
                    onChange={(e) => setPriceUpdate({ ...priceUpdate, notes: e.target.value })}
                    placeholder="Reason for price change"
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={handleUpdatePrice}
                    disabled={isLoading || !priceUpdate.symbol || priceUpdate.newPrice <= 0}
                    className="flex-1 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 text-white rounded font-medium"
                  >
                    {isLoading ? 'Updating...' : 'Update Price'}
                  </button>
                  <button
                    onClick={() => {
                      setShowPriceModal(false);
                      setPriceUpdate({ symbol: '', newPrice: 0, notes: '' });
                    }}
                    className="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white rounded font-medium"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Add Holding Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 max-w-md w-full">
              <h3 className="text-xl font-semibold text-white mb-4">Add Holding to Scenario</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
                  <SymbolAutocomplete
                    value={newHolding.symbol}
                    onChange={(symbol) => setNewHolding({ ...newHolding, symbol })}
                    placeholder="e.g., AAPL, TCS.NS"
                    className="px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Shares</label>
                  <input
                    type="number"
                    value={newHolding.shares || ''}
                    onChange={(e) => setNewHolding({ ...newHolding, shares: parseInt(e.target.value) || 0 })}
                    placeholder="Number of shares"
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Average Price</label>
                  <input
                    type="number"
                    value={newHolding.avgPrice || ''}
                    onChange={(e) => setNewHolding({ ...newHolding, avgPrice: parseFloat(e.target.value) || 0 })}
                    placeholder="Purchase price per share"
                    step="0.01"
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={handleAddHolding}
                    disabled={isLoading || !newHolding.symbol || newHolding.shares <= 0 || newHolding.avgPrice <= 0}
                    className="flex-1 px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-green-400 text-white rounded font-medium"
                  >
                    {isLoading ? 'Adding...' : 'Add to Scenario'}
                  </button>
                  <button
                    onClick={() => {
                      setShowAddModal(false);
                      setNewHolding({ symbol: '', shares: 0, avgPrice: 0 });
                    }}
                    className="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white rounded font-medium"
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

export default ScenarioPortfolioPage;