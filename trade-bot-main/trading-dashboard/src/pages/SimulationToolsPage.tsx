import { useState } from 'react';
import Layout from '../components/Layout';
import { Activity, Shield, AlertTriangle, Loader2 } from 'lucide-react';
import { tradeAPI, riskAPI } from '../services/api';
import SymbolAutocomplete from '../components/SymbolAutocomplete';

const SimulationToolsPage = () => {
  // Trade Execution State
  const [tradeForm, setTradeForm] = useState({
    symbol: '',
    quantity: '',
    entryPrice: '',
    stopLossPrice: '',
    side: 'BUY' as 'BUY' | 'SELL'
  });
  const [tradeExecuting, setTradeExecuting] = useState(false);
  const [tradeResult, setTradeResult] = useState<any>(null);
  const [tradeError, setTradeError] = useState<string | null>(null);

  // Risk Assessment State
  const [riskForm, setRiskForm] = useState({
    symbol: '',
    quantity: '',
    entryPrice: '',
    stopLossPrice: ''
  });
  const [riskAssessing, setRiskAssessing] = useState(false);
  const [riskResult, setRiskResult] = useState<any>(null);
  const [riskError, setRiskError] = useState<string | null>(null);

  const handleTradeExecution = async () => {
    if (!tradeForm.symbol || !tradeForm.quantity || !tradeForm.entryPrice || !tradeForm.stopLossPrice) {
      setTradeError('All fields are required');
      return;
    }

    setTradeExecuting(true);
    setTradeError(null);
    setTradeResult(null);

    try {
      const result = await tradeAPI.execute(
        tradeForm.symbol.toUpperCase(),
        tradeForm.side,
        parseInt(tradeForm.quantity),
        parseFloat(tradeForm.entryPrice),
        parseFloat(tradeForm.stopLossPrice)
      );
      setTradeResult(result);
    } catch (err: any) {
      setTradeError(err.message || 'Execution failed');
    } finally {
      setTradeExecuting(false);
    }
  };

  const handleRiskAssessment = async () => {
    if (!riskForm.symbol || !riskForm.quantity || !riskForm.entryPrice || !riskForm.stopLossPrice) {
      setRiskError('All fields are required');
      return;
    }

    setRiskAssessing(true);
    setRiskError(null);
    setRiskResult(null);

    try {
      const result = await riskAPI.assess({
        symbol: riskForm.symbol.toUpperCase(),
        position_size: parseFloat(riskForm.entryPrice) * parseInt(riskForm.quantity),
        entry_price: parseFloat(riskForm.entryPrice),
        stop_loss_price: parseFloat(riskForm.stopLossPrice),
        capital_at_risk_pct: 0.02
      });
      setRiskResult(result);
    } catch (err: any) {
      setRiskError(err.message || 'Assessment failed');
    } finally {
      setRiskAssessing(false);
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Simulation Tools</h1>
          <p className="text-gray-400 text-sm">Educational simulation endpoints — No real trades executed</p>
        </div>

        {/* Trade Execution Simulator */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-blue-400" />
            <h2 className="text-xl font-semibold text-white">Simulated Execution — Educational Only</h2>
          </div>
          
          <div className="bg-yellow-900/20 border border-yellow-700 rounded-lg p-3 mb-4">
            <p className="text-yellow-300 text-sm">⚠️ This is a simulation tool. No real trades are executed.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
              <SymbolAutocomplete
                value={tradeForm.symbol}
                onChange={(symbol) => setTradeForm({ ...tradeForm, symbol })}
                placeholder="e.g., AAPL"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Side</label>
              <select
                value={tradeForm.side}
                onChange={(e) => setTradeForm({ ...tradeForm, side: e.target.value as any })}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Quantity</label>
              <input
                type="number"
                value={tradeForm.quantity}
                onChange={(e) => setTradeForm({ ...tradeForm, quantity: e.target.value })}
                placeholder="100"
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Entry Price</label>
              <input
                type="number"
                step="0.01"
                value={tradeForm.entryPrice}
                onChange={(e) => setTradeForm({ ...tradeForm, entryPrice: e.target.value })}
                placeholder="150.00"
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Stop Loss Price</label>
              <input
                type="number"
                step="0.01"
                value={tradeForm.stopLossPrice}
                onChange={(e) => setTradeForm({ ...tradeForm, stopLossPrice: e.target.value })}
                placeholder="145.00"
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <button
            onClick={handleTradeExecution}
            disabled={tradeExecuting}
            className="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
          >
            {tradeExecuting && <Loader2 className="w-4 h-4 animate-spin" />}
            {tradeExecuting ? 'Simulating...' : 'Simulate Execution'}
          </button>

          {tradeError && (
            <div className="mt-4 bg-red-900/30 border border-red-700 rounded-lg p-4">
              <p className="text-red-400 font-semibold">Error</p>
              <p className="text-red-300 text-sm">{tradeError}</p>
            </div>
          )}

          {tradeResult && (
            <div className="mt-4 bg-green-900/30 border border-green-700 rounded-lg p-4">
              <p className="text-green-400 font-semibold mb-2">Simulation Complete</p>
              <div className="space-y-1 text-sm">
                <p className="text-gray-300"><span className="text-gray-400">Order ID:</span> {tradeResult.order_id}</p>
                <p className="text-gray-300"><span className="text-gray-400">Symbol:</span> {tradeResult.symbol}</p>
                <p className="text-gray-300"><span className="text-gray-400">Side:</span> {tradeResult.side}</p>
                <p className="text-gray-300"><span className="text-gray-400">Quantity:</span> {tradeResult.quantity}</p>
                <p className="text-gray-300"><span className="text-gray-400">Execution Price:</span> ₹{tradeResult.execution_price}</p>
                <p className="text-gray-300"><span className="text-gray-400">Position Size:</span> ₹{tradeResult.position_size?.toFixed(2)}</p>
                <p className="text-gray-300"><span className="text-gray-400">Risk Amount:</span> ₹{tradeResult.risk_amount?.toFixed(2)}</p>
                <p className="text-gray-300"><span className="text-gray-400">Risk %:</span> {tradeResult.risk_percentage?.toFixed(2)}%</p>
                <p className="text-gray-300"><span className="text-gray-400">Status:</span> {tradeResult.status}</p>
              </div>
            </div>
          )}
        </div>

        {/* Risk Assessment Panel */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-purple-400" />
            <h2 className="text-xl font-semibold text-white">Risk Assessment Panel</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
              <SymbolAutocomplete
                value={riskForm.symbol}
                onChange={(symbol) => setRiskForm({ ...riskForm, symbol })}
                placeholder="e.g., AAPL"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Quantity</label>
              <input
                type="number"
                value={riskForm.quantity}
                onChange={(e) => setRiskForm({ ...riskForm, quantity: e.target.value })}
                placeholder="100"
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Entry Price</label>
              <input
                type="number"
                step="0.01"
                value={riskForm.entryPrice}
                onChange={(e) => setRiskForm({ ...riskForm, entryPrice: e.target.value })}
                placeholder="150.00"
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Stop Loss Price</label>
              <input
                type="number"
                step="0.01"
                value={riskForm.stopLossPrice}
                onChange={(e) => setRiskForm({ ...riskForm, stopLossPrice: e.target.value })}
                placeholder="145.00"
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>

          <button
            onClick={handleRiskAssessment}
            disabled={riskAssessing}
            className="w-full px-4 py-2 bg-purple-500 hover:bg-purple-600 disabled:bg-purple-400 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
          >
            {riskAssessing && <Loader2 className="w-4 h-4 animate-spin" />}
            {riskAssessing ? 'Assessing...' : 'Assess Risk'}
          </button>

          {riskError && (
            <div className="mt-4 bg-red-900/30 border border-red-700 rounded-lg p-4">
              <p className="text-red-400 font-semibold">Error</p>
              <p className="text-red-300 text-sm">{riskError}</p>
            </div>
          )}

          {riskResult && (
            <div className={`mt-4 border rounded-lg p-4 ${
              riskResult.recommendation === 'ACCEPTABLE' 
                ? 'bg-green-900/30 border-green-700' 
                : 'bg-red-900/30 border-red-700'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                {riskResult.recommendation === 'ACCEPTABLE' ? (
                  <Shield className="w-5 h-5 text-green-400" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                )}
                <p className={`font-semibold ${
                  riskResult.recommendation === 'ACCEPTABLE' ? 'text-green-400' : 'text-red-400'
                }`}>
                  Risk Level: {riskResult.recommendation}
                </p>
              </div>
              <div className="space-y-1 text-sm">
                <p className="text-gray-300"><span className="text-gray-400">Symbol:</span> {riskResult.symbol}</p>
                <p className="text-gray-300"><span className="text-gray-400">Position Size:</span> ₹{riskResult.position_size?.toFixed(2)}</p>
                <p className="text-gray-300"><span className="text-gray-400">Risk Amount:</span> ₹{riskResult.risk_amount?.toFixed(2)}</p>
                <p className="text-gray-300"><span className="text-gray-400">Risk %:</span> {riskResult.risk_percentage?.toFixed(2)}%</p>
                <p className="text-gray-300"><span className="text-gray-400">Max Capital at Risk:</span> ₹{riskResult.max_capital_at_risk?.toFixed(2)}</p>
                {riskResult.suggestions && riskResult.suggestions.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-700">
                    <p className="text-gray-400 font-medium mb-1">Suggestions:</p>
                    {riskResult.suggestions.map((suggestion: string, idx: number) => (
                      <p key={idx} className="text-gray-300 text-xs">• {suggestion}</p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default SimulationToolsPage;
