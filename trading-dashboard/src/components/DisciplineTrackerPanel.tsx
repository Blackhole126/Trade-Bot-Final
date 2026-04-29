import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

interface PreMarketSetup {
  date: string;
  capital_allocated: number;
  max_risk_per_trade: number;
  max_risk_absolute: number;
  instruments_allowed: string[];
  max_trades: number;
  min_rr_ratio: number;
  market_regime: string;
  volatility_level: string;
  mental_state_ok: boolean;
  declaration_signed: boolean;
}

interface TradeEntry {
  trade_number: number;
  symbol: string;
  direction: string;
  setup_type: string;
  entry_reason: string;
  entry_price: number;
  stop_loss: number;
  target_zone_min: number;
  target_zone_max: number;
  position_size: number;
  risk_amount: number;
  rr_ratio: number;
  pre_entry_checklist_completed: boolean;
}

interface DisciplineScore {
  overall_score: number;
  checklist_compliance: number;
  stop_loss_adherence: number;
  exit_discipline: number;
  grade: string;
}

const DisciplineTrackerPanel: React.FC = () => {
  const [preMarketSetup, setPreMarketSetup] = useState<PreMarketSetup | null>(null);
  const [showPreMarketForm, setShowPreMarketForm] = useState(false);
  const [disciplineScore, setDisciplineScore] = useState<DisciplineScore | null>(null);
  const [runningStats, setRunningStats] = useState({
    total_trades: 0,
    winners: 0,
    losers: 0,
    net_pnl: 0
  });

  // Pre-market form state
  const [formData, setFormData] = useState({
    capital: 100000,
    max_risk_percent: 0.005,
    market_regime: 'NORMAL',
    volatility_level: 'NORMAL',
    declaration_signed: false
  });

  useEffect(() => {
    // Check if pre-market setup exists for today
    checkPreMarketStatus();
    fetchDisciplineScore();
    
    // Auto-refresh score every 30 seconds
    const interval = setInterval(fetchDisciplineScore, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkPreMarketStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/discipline/pre-market/check`);
      if (response.data.status === 'success' && response.data.setup) {
        setPreMarketSetup(response.data.setup);
      } else {
        setShowPreMarketForm(true);
      }
    } catch (error) {
      setShowPreMarketForm(true);
    }
  };

  const fetchDisciplineScore = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/discipline/score`);
      if (response.data.status === 'success') {
        setDisciplineScore(response.data.score);
      }
    } catch (error) {
      console.error('Failed to fetch discipline score:', error);
    }
  };

  const handlePreMarketSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const response = await axios.post(`${API_BASE_URL}/discipline/pre-market`, {
        date: new Date().toISOString().split('T')[0],
        capital: formData.capital,
        max_risk_percent: formData.max_risk_percent,
        market_regime: formData.market_regime,
        volatility_level: formData.volatility_level,
        declaration_signed: formData.declaration_signed
      });

      if (response.data.status === 'success') {
        setPreMarketSetup(response.data.setup);
        setShowPreMarketForm(false);
        alert('✅ Pre-market setup initialized successfully');
      }
    } catch (error: any) {
      alert(`❌ Error: ${error.response?.data?.detail || error.message}`);
    }
  };

  const getGradeColor = (grade: string) => {
    if (grade.includes('A')) return 'text-green-500';
    if (grade.includes('B')) return 'text-blue-500';
    if (grade.includes('C')) return 'text-yellow-500';
    if (grade.includes('D')) return 'text-orange-500';
    return 'text-red-500';
  };

  if (showPreMarketForm) {
    return (
      <div className="bg-gray-900 border-2 border-yellow-500 rounded-lg p-6 max-w-4xl mx-auto">
        <h2 className="text-2xl font-bold text-yellow-500 mb-4">
          ⚠️ PRE-MARKET SETUP REQUIRED
        </h2>
        
        <p className="text-gray-300 mb-6">
          Complete your pre-market declaration before trading. This is MANDATORY.
        </p>

        <form onSubmit={handlePreMarketSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Capital Allocated (₹)
              </label>
              <input
                type="number"
                value={formData.capital}
                onChange={(e) => setFormData({...formData, capital: Number(e.target.value)})}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Max Risk Per Trade (%)
              </label>
              <select
                value={formData.max_risk_percent}
                onChange={(e) => setFormData({...formData, max_risk_percent: Number(e.target.value)})}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              >
                <option value={0.005}>0.5% (Conservative)</option>
                <option value={0.008}>0.8% (Moderate)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Market Regime
              </label>
              <select
                value={formData.market_regime}
                onChange={(e) => setFormData({...formData, market_regime: e.target.value})}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              >
                <option value="BULL">Bull</option>
                <option value="BEAR">Bear</option>
                <option value="SIDEWAYS">Sideways</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Volatility Level
              </label>
              <select
                value={formData.volatility_level}
                onChange={(e) => setFormData({...formData, volatility_level: e.target.value})}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              >
                <option value="LOW">Low (VIX < 12)</option>
                <option value="NORMAL">Normal (12-18)</option>
                <option value="HIGH">High (> 18)</option>
                <option value="EXTREME">Extreme (> 25) - NO TRADING</option>
              </select>
            </div>
          </div>

          <div className="border-t border-gray-700 pt-4 mt-4">
            <h3 className="text-lg font-semibold text-white mb-3">Mental State Check</h3>
            
            <label className="flex items-center space-x-3 mb-2">
              <input
                type="checkbox"
                checked={true}
                readOnly
                className="w-5 h-5 accent-green-500"
              />
              <span className="text-gray-300">I slept 7+ hours last night</span>
            </label>

            <label className="flex items-center space-x-3 mb-2">
              <input
                type="checkbox"
                checked={true}
                readOnly
                className="w-5 h-5 accent-green-500"
              />
              <span className="text-gray-300">I am emotionally balanced and calm</span>
            </label>

            <label className="flex items-center space-x-3 mb-4">
              <input
                type="checkbox"
                checked={true}
                readOnly
                className="w-5 h-5 accent-green-500"
              />
              <span className="text-gray-300">I am focused on process, not profits</span>
            </label>
          </div>

          <div className="bg-yellow-900/30 border border-yellow-500 rounded p-4 mt-4">
            <p className="text-yellow-200 font-semibold mb-2">Declaration:</p>
            <p className="text-yellow-100 text-sm italic">
              "I am here to validate my system, not to make money. I will follow my rules without exception.
              Losses are acceptable if rules were followed. Profits are irrelevant if rules were broken."
            </p>
          </div>

          <label className="flex items-center space-x-3 mt-4">
            <input
              type="checkbox"
              checked={formData.declaration_signed}
              onChange={(e) => setFormData({...formData, declaration_signed: e.target.checked})}
              className="w-5 h-5 accent-red-500"
              required
            />
            <span className="text-white font-semibold">
              I have read and agree to this declaration
            </span>
          </label>

          <button
            type="submit"
            disabled={!formData.declaration_signed}
            className={`w-full py-3 px-6 rounded font-bold mt-4 ${
              formData.declaration_signed
                ? 'bg-green-600 hover:bg-green-500 text-white'
                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            }`}
          >
            ✓ Initialize Pre-Market Setup
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-green-500 rounded-lg p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-green-500">
          📊 DISCIPLINE TRACKER
        </h2>
        
        {disciplineScore && (
          <div className="text-right">
            <div className={`text-3xl font-bold ${getGradeColor(disciplineScore.grade)}`}>
              {disciplineScore.overall_score.toFixed(1)}%
            </div>
            <div className={`text-sm font-semibold ${getGradeColor(disciplineScore.grade)}`}>
              Grade: {disciplineScore.grade}
            </div>
          </div>
        )}
      </div>

      {/* Pre-Market Summary */}
      {preMarketSetup && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 rounded p-3">
            <div className="text-xs text-gray-400 mb-1">Capital</div>
            <div className="text-lg font-bold text-white">
              ₹{(preMarketSetup.capital_allocated / 1000).toFixed(0)}K
            </div>
          </div>

          <div className="bg-gray-800 rounded p-3">
            <div className="text-xs text-gray-400 mb-1">Max Risk/Trade</div>
            <div className="text-lg font-bold text-red-400">
              ₹{preMarketSetup.max_risk_absolute.toFixed(0)}
            </div>
            <div className="text-xs text-gray-500">
              {(preMarketSetup.max_risk_per_trade * 100).toFixed(1)}%
            </div>
          </div>

          <div className="bg-gray-800 rounded p-3">
            <div className="text-xs text-gray-400 mb-1">Max Trades</div>
            <div className="text-lg font-bold text-white">
              {preMarketSetup.max_trades}
            </div>
          </div>

          <div className="bg-gray-800 rounded p-3">
            <div className="text-xs text-gray-400 mb-1">Min R:R</div>
            <div className="text-lg font-bold text-green-400">
              1:{preMarketSetup.min_rr_ratio}
            </div>
          </div>
        </div>
      )}

      {/* Discipline Metrics */}
      {disciplineScore && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-800 rounded p-3">
            <div className="text-xs text-gray-400 mb-1">Checklist Compliance</div>
            <div className="text-lg font-bold text-blue-400">
              {disciplineScore.checklist_compliance.toFixed(0)}%
            </div>
          </div>

          <div className="bg-gray-800 rounded p-3">
            <div className="text-xs text-gray-400 mb-1">Stop-Loss Adherence</div>
            <div className="text-lg font-bold text-green-400">
              {disciplineScore.stop_loss_adherence.toFixed(0)}%
            </div>
          </div>

          <div className="bg-gray-800 rounded p-3">
            <div className="text-xs text-gray-400 mb-1">Exit Discipline</div>
            <div className="text-lg font-bold text-purple-400">
              {disciplineScore.exit_discipline.toFixed(0)}%
            </div>
          </div>
        </div>
      )}

      {/* Running Stats */}
      <div className="border-t border-gray-700 pt-4">
        <h3 className="text-lg font-semibold text-white mb-3">Running Statistics</h3>
        
        <div className="grid grid-cols-4 gap-4">
          <div>
            <div className="text-xs text-gray-400">Total Trades</div>
            <div className="text-xl font-bold text-white">{runningStats.total_trades}</div>
          </div>

          <div>
            <div className="text-xs text-gray-400">Winners</div>
            <div className="text-xl font-bold text-green-400">{runningStats.winners}</div>
          </div>

          <div>
            <div className="text-xs text-gray-400">Losers</div>
            <div className="text-xl font-bold text-red-400">{runningStats.losers}</div>
          </div>

          <div>
            <div className="text-xs text-gray-400">Net P&L</div>
            <div className={`text-xl font-bold ${runningStats.net_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              ₹{runningStats.net_pnl.toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mt-6 flex gap-3">
        <button className="flex-1 bg-blue-600 hover:bg-blue-500 text-white py-2 px-4 rounded">
          📝 Log Trade Entry
        </button>
        
        <button className="flex-1 bg-green-600 hover:bg-green-500 text-white py-2 px-4 rounded">
          ✅ Log Trade Exit
        </button>
        
        <button className="flex-1 bg-purple-600 hover:bg-purple-500 text-white py-2 px-4 rounded">
          📊 View Full Report
        </button>
      </div>

      {/* Warning Messages */}
      {disciplineScore && disciplineScore.overall_score < 75 && (
        <div className="mt-4 bg-red-900/30 border border-red-500 rounded p-3">
          <p className="text-red-200 font-semibold">
            ⚠️ WARNING: Discipline score below 75%. Consider stopping trading for the day.
          </p>
        </div>
      )}
    </div>
  );
};

export default DisciplineTrackerPanel;
