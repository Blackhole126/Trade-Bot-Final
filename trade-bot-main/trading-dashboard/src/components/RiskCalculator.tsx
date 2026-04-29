import { useState } from 'react';
import { Calculator, TrendingUp, TrendingDown, AlertTriangle, Info } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

interface RiskCalculatorProps {
  symbol?: string;
  currentPrice?: number;
  onCalculate?: (result: RiskCalculationResult) => void;
}

export interface RiskCalculationResult {
  positionSize: number;
  riskAmount: number;
  rewardAmount: number;
  riskRewardRatio: number;
  stopLossPrice: number;
  takeProfitPrice: number;
  sharesToBuy: number;
  maxLoss: number;
  maxProfit: number;
}

const RiskCalculator = ({ symbol, currentPrice, onCalculate }: RiskCalculatorProps) => {
  const { theme } = useTheme();
  const [accountSize, setAccountSize] = useState<string>('10000');
  const [riskPercent, setRiskPercent] = useState<string>('2');
  const [entryPrice, setEntryPrice] = useState<string>(currentPrice?.toFixed(2) || '');
  const [stopLoss, setStopLoss] = useState<string>('');
  const [takeProfit, setTakeProfit] = useState<string>('');
  const [riskReward, setRiskReward] = useState<string>('2');
  const [calculateMode, setCalculateMode] = useState<'stopLoss' | 'riskReward'>('stopLoss');
  const [result, setResult] = useState<RiskCalculationResult | null>(null);

  const isLight = theme === 'light';
  const isSpace = theme === 'space';

  const calculate = () => {
    try {
      const account = parseFloat(accountSize);
      const risk = parseFloat(riskPercent) / 100;
      const entry = parseFloat(entryPrice);
      const stop = parseFloat(stopLoss);
      const profit = parseFloat(takeProfit);
      const rr = parseFloat(riskReward);

      if (!account || !risk || !entry) {
        alert('Please fill in Account Size, Risk %, and Entry Price');
        return;
      }

      let calculatedStopLoss: number;
      let calculatedTakeProfit: number;

      if (calculateMode === 'stopLoss' && stop) {
        calculatedStopLoss = stop;
        calculatedTakeProfit = profit || entry + (entry - stop) * rr;
      } else if (calculateMode === 'riskReward' && rr) {
        const riskAmount = entry * (risk * 0.01); // 1% of entry price as risk
        calculatedStopLoss = entry - riskAmount;
        calculatedTakeProfit = entry + (riskAmount * rr);
      } else {
        alert('Please provide Stop Loss or Risk/Reward ratio');
        return;
      }

      const riskPerShare = Math.abs(entry - calculatedStopLoss);
      const rewardPerShare = Math.abs(calculatedTakeProfit - entry);
      const riskAmount = account * risk;
      const sharesToBuy = Math.floor(riskAmount / riskPerShare);
      const positionSize = sharesToBuy * entry;
      const rewardAmount = sharesToBuy * rewardPerShare;
      const riskRewardRatio = riskPerShare > 0 ? rewardPerShare / riskPerShare : 0;
      const maxLoss = sharesToBuy * riskPerShare;
      const maxProfit = sharesToBuy * rewardPerShare;

      const calculationResult: RiskCalculationResult = {
        positionSize,
        riskAmount,
        rewardAmount,
        riskRewardRatio,
        stopLossPrice: calculatedStopLoss,
        takeProfitPrice: calculatedTakeProfit,
        sharesToBuy,
        maxLoss,
        maxProfit,
      };

      setResult(calculationResult);
      if (onCalculate) {
        onCalculate(calculationResult);
      }
    } catch (error) {
      console.error('Calculation error:', error);
      alert('Error in calculation. Please check your inputs.');
    }
  };

  return (
    <div className={`rounded-lg border p-4 sm:p-6 ${
      isLight 
        ? 'bg-white border-gray-200' 
        : isSpace 
          ? 'bg-slate-800/60 backdrop-blur-sm border-purple-900/30' 
          : 'bg-slate-800 border-slate-700'
    }`}>
      <div className="flex items-center gap-2 mb-4">
        <Calculator className={`w-5 h-5 ${isSpace ? 'text-purple-400' : 'text-blue-400'}`} />
        <h3 className={`text-lg font-semibold ${isLight ? 'text-gray-900' : 'text-white'}`}>
          Risk Calculator
        </h3>
      </div>

      {/* Mode Toggle */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setCalculateMode('stopLoss')}
          className={`px-3 py-1.5 rounded text-sm transition-colors ${
            calculateMode === 'stopLoss'
              ? 'bg-blue-500 text-white'
              : isLight
                ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          Use Stop Loss
        </button>
        <button
          onClick={() => setCalculateMode('riskReward')}
          className={`px-3 py-1.5 rounded text-sm transition-colors ${
            calculateMode === 'riskReward'
              ? 'bg-blue-500 text-white'
              : isLight
                ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          Use Risk/Reward
        </button>
      </div>

      {/* Input Fields */}
      <div className="space-y-4">
        <div>
          <label className={`block text-sm font-medium mb-1.5 ${
            isLight ? 'text-gray-700' : 'text-gray-300'
          }`}>
            Account Size ($)
          </label>
          <input
            type="number"
            value={accountSize}
            onChange={(e) => setAccountSize(e.target.value)}
            className={`w-full px-3 py-2 rounded ${
              isLight
                ? 'bg-gray-50 border-gray-300 text-gray-900'
                : 'bg-slate-700 border-slate-600 text-white'
            } border focus:outline-none focus:ring-2 focus:ring-blue-500`}
            placeholder="10000"
          />
        </div>

        <div>
          <label className={`block text-sm font-medium mb-1.5 ${
            isLight ? 'text-gray-700' : 'text-gray-300'
          }`}>
            Risk Per Trade (%)
          </label>
          <input
            type="number"
            value={riskPercent}
            onChange={(e) => setRiskPercent(e.target.value)}
            className={`w-full px-3 py-2 rounded ${
              isLight
                ? 'bg-gray-50 border-gray-300 text-gray-900'
                : 'bg-slate-700 border-slate-600 text-white'
            } border focus:outline-none focus:ring-2 focus:ring-blue-500`}
            placeholder="2"
          />
          <p className={`text-xs mt-1 ${isLight ? 'text-gray-500' : 'text-gray-400'}`}>
            Recommended: 1-2% per trade
          </p>
        </div>

        <div>
          <label className={`block text-sm font-medium mb-1.5 ${
            isLight ? 'text-gray-700' : 'text-gray-300'
          }`}>
            Entry Price ($)
          </label>
          <input
            type="number"
            step="0.01"
            value={entryPrice}
            onChange={(e) => setEntryPrice(e.target.value)}
            className={`w-full px-3 py-2 rounded ${
              isLight
                ? 'bg-gray-50 border-gray-300 text-gray-900'
                : 'bg-slate-700 border-slate-600 text-white'
            } border focus:outline-none focus:ring-2 focus:ring-blue-500`}
            placeholder={currentPrice?.toFixed(2) || "100.00"}
          />
          {symbol && (
            <p className={`text-xs mt-1 ${isLight ? 'text-gray-500' : 'text-gray-400'}`}>
              Symbol: {symbol}
            </p>
          )}
        </div>

        {calculateMode === 'stopLoss' ? (
          <>
            <div>
              <label className={`block text-sm font-medium mb-1.5 ${
                isLight ? 'text-gray-700' : 'text-gray-300'
              }`}>
                Stop Loss ($)
              </label>
              <input
                type="number"
                step="0.01"
                value={stopLoss}
                onChange={(e) => setStopLoss(e.target.value)}
                className={`w-full px-3 py-2 rounded ${
                  isLight
                    ? 'bg-gray-50 border-gray-300 text-gray-900'
                    : 'bg-slate-700 border-slate-600 text-white'
                } border focus:outline-none focus:ring-2 focus:ring-blue-500`}
                placeholder="95.00"
              />
            </div>
            <div>
              <label className={`block text-sm font-medium mb-1.5 ${
                isLight ? 'text-gray-700' : 'text-gray-300'
              }`}>
                Take Profit ($) <span className="text-xs text-gray-400">(Optional)</span>
              </label>
              <input
                type="number"
                step="0.01"
                value={takeProfit}
                onChange={(e) => setTakeProfit(e.target.value)}
                className={`w-full px-3 py-2 rounded ${
                  isLight
                    ? 'bg-gray-50 border-gray-300 text-gray-900'
                    : 'bg-slate-700 border-slate-600 text-white'
                } border focus:outline-none focus:ring-2 focus:ring-blue-500`}
                placeholder="110.00"
              />
            </div>
            <div>
              <label className={`block text-sm font-medium mb-1.5 ${
                isLight ? 'text-gray-700' : 'text-gray-300'
              }`}>
                Risk/Reward Ratio
              </label>
              <input
                type="number"
                step="0.1"
                value={riskReward}
                onChange={(e) => setRiskReward(e.target.value)}
                className={`w-full px-3 py-2 rounded ${
                  isLight
                    ? 'bg-gray-50 border-gray-300 text-gray-900'
                    : 'bg-slate-700 border-slate-600 text-white'
                } border focus:outline-none focus:ring-2 focus:ring-blue-500`}
                placeholder="2"
                disabled={!!takeProfit}
              />
              {takeProfit && (
                <p className={`text-xs mt-1 ${isLight ? 'text-gray-500' : 'text-gray-400'}`}>
                  Auto-calculated from Stop Loss and Take Profit
                </p>
              )}
            </div>
          </>
        ) : (
          <div>
            <label className={`block text-sm font-medium mb-1.5 ${
              isLight ? 'text-gray-700' : 'text-gray-300'
            }`}>
              Risk/Reward Ratio
            </label>
            <input
              type="number"
              step="0.1"
              value={riskReward}
              onChange={(e) => setRiskReward(e.target.value)}
              className={`w-full px-3 py-2 rounded ${
                isLight
                  ? 'bg-gray-50 border-gray-300 text-gray-900'
                  : 'bg-slate-700 border-slate-600 text-white'
              } border focus:outline-none focus:ring-2 focus:ring-blue-500`}
              placeholder="2"
            />
          </div>
        )}

        <button
          onClick={calculate}
          className="w-full px-4 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors font-medium"
        >
          Calculate Position Size
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className={`mt-6 p-4 rounded-lg ${
          isLight ? 'bg-blue-50 border border-blue-200' : 'bg-slate-900/50 border border-slate-700'
        }`}>
          <h4 className={`font-semibold mb-3 flex items-center gap-2 ${
            isLight ? 'text-gray-900' : 'text-white'
          }`}>
            <Info className="w-4 h-4" />
            Calculation Results
          </h4>
          
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className={isLight ? 'text-gray-600' : 'text-gray-400'}>Shares to Buy:</span>
              <p className={`font-semibold ${isLight ? 'text-gray-900' : 'text-white'}`}>
                {result.sharesToBuy}
              </p>
            </div>
            <div>
              <span className={isLight ? 'text-gray-600' : 'text-gray-400'}>Position Size:</span>
              <p className={`font-semibold ${isLight ? 'text-gray-900' : 'text-white'}`}>
                ${result.positionSize.toFixed(2)}
              </p>
            </div>
            <div>
              <span className={isLight ? 'text-gray-600' : 'text-gray-400'}>Stop Loss:</span>
              <p className={`font-semibold text-red-400 flex items-center gap-1`}>
                <TrendingDown className="w-3 h-3" />
                ${result.stopLossPrice.toFixed(2)}
              </p>
            </div>
            <div>
              <span className={isLight ? 'text-gray-600' : 'text-gray-400'}>Take Profit:</span>
              <p className={`font-semibold text-green-400 flex items-center gap-1`}>
                <TrendingUp className="w-3 h-3" />
                ${result.takeProfitPrice.toFixed(2)}
              </p>
            </div>
            <div>
              <span className={isLight ? 'text-gray-600' : 'text-gray-400'}>Risk Amount:</span>
              <p className={`font-semibold text-red-400`}>
                ${result.riskAmount.toFixed(2)}
              </p>
            </div>
            <div>
              <span className={isLight ? 'text-gray-600' : 'text-gray-400'}>Reward Amount:</span>
              <p className={`font-semibold text-green-400`}>
                ${result.rewardAmount.toFixed(2)}
              </p>
            </div>
            <div className="col-span-2">
              <span className={isLight ? 'text-gray-600' : 'text-gray-400'}>Risk/Reward Ratio:</span>
              <p className={`font-semibold ${
                result.riskRewardRatio >= 2 ? 'text-green-400' : 
                result.riskRewardRatio >= 1 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {result.riskRewardRatio.toFixed(2)}:1
                {result.riskRewardRatio < 1 && (
                  <AlertTriangle className="w-4 h-4 inline ml-1" />
                )}
              </p>
            </div>
            <div>
              <span className={isLight ? 'text-gray-600' : 'text-gray-400'}>Max Loss:</span>
              <p className="font-semibold text-red-400">
                ${result.maxLoss.toFixed(2)}
              </p>
            </div>
            <div>
              <span className={isLight ? 'text-gray-600' : 'text-gray-400'}>Max Profit:</span>
              <p className="font-semibold text-green-400">
                ${result.maxProfit.toFixed(2)}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RiskCalculator;

