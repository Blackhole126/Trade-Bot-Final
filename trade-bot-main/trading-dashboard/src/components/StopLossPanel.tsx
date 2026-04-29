import { useState, useEffect } from 'react';
import { Shield, X, AlertCircle } from 'lucide-react';

export interface StopLossState {
  price: number;
  side: 'BUY' | 'SELL';
  isActive: boolean;
}

interface StopLossPanelProps {
  symbol: string;
  currentPrice: number;
  timeframe: string;
  isVisible: boolean;
  stopLossState: StopLossState | null;
  onClose: () => void;
  onStopLossChange: (state: StopLossState | null) => void;
}

const StopLossPanel = ({
  symbol,
  currentPrice,
  timeframe: _timeframe,
  isVisible,
  stopLossState,
  onClose,
  onStopLossChange,
}: StopLossPanelProps) => {
  const [priceInput, setPriceInput] = useState<string>('');
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [validationError, setValidationError] = useState<string | null>(null);

  // Sync with external state
  useEffect(() => {
    if (stopLossState) {
      setPriceInput(stopLossState.price.toString());
      setSide(stopLossState.side);
    } else {
      setPriceInput('');
      setSide('BUY');
    }
    setValidationError(null);
  }, [stopLossState]);

  // Validate stop-loss price based on side
  const validatePrice = (price: number, tradeSide: 'BUY' | 'SELL'): string | null => {
    if (isNaN(price) || price <= 0) {
      return 'Price must be a positive number';
    }

    if (tradeSide === 'BUY' && price >= currentPrice) {
      return 'Stop-loss must be below current price for BUY orders';
    }

    if (tradeSide === 'SELL' && price <= currentPrice) {
      return 'Stop-loss must be above current price for SELL orders';
    }

    return null;
  };

  const handlePriceChange = (value: string) => {
    setPriceInput(value);
    setValidationError(null);

    const numValue = parseFloat(value);
    if (!isNaN(numValue) && numValue > 0) {
      const error = validatePrice(numValue, side);
      if (error) {
        setValidationError(error);
      }
    }
  };

  const handleSideChange = (newSide: 'BUY' | 'SELL') => {
    setSide(newSide);
    setValidationError(null);

    if (priceInput) {
      const numValue = parseFloat(priceInput);
      if (!isNaN(numValue) && numValue > 0) {
        const error = validatePrice(numValue, newSide);
        if (error) {
          setValidationError(error);
        }
      }
    }
  };

  const handleApply = () => {
    const numValue = parseFloat(priceInput);
    
    if (!priceInput || isNaN(numValue) || numValue <= 0) {
      setValidationError('Please enter a valid stop-loss price');
      return;
    }

    const error = validatePrice(numValue, side);
    if (error) {
      setValidationError(error);
      return;
    }

    // Apply stop-loss
    onStopLossChange({
      price: numValue,
      side,
      isActive: true,
    });
  };

  const handleRemove = () => {
    onStopLossChange(null);
    setPriceInput('');
    setValidationError(null);
  };

  if (!isVisible) return null;

  return (
    <div className="absolute top-16 right-4 w-80 bg-slate-800/95 backdrop-blur-sm rounded-lg border border-slate-700 shadow-2xl z-50">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-red-400" />
          <h3 className="text-sm font-semibold text-white">Stop-Loss</h3>
          <span className="text-xs text-gray-400">({symbol})</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-slate-700 rounded transition-colors"
        >
          <X className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      {/* Content */}
      <div className="p-3 space-y-3">
        {/* Side Selection */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-2">
            Trade Side
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => handleSideChange('BUY')}
              className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
                side === 'BUY'
                  ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                  : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
              }`}
            >
              BUY
            </button>
            <button
              onClick={() => handleSideChange('SELL')}
              className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
                side === 'SELL'
                  ? 'bg-red-500/20 text-red-400 border border-red-500/50'
                  : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
              }`}
            >
              SELL
            </button>
          </div>
        </div>

        {/* Current Price Display */}
        <div className="bg-slate-900/50 rounded p-2">
          <div className="text-xs text-gray-400 mb-1">Current Price</div>
          <div className="text-lg font-bold text-white">
            ${currentPrice.toFixed(2)}
          </div>
        </div>

        {/* Price Input */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-2">
            Stop-Loss Price
          </label>
          <input
            type="number"
            step="0.01"
            value={priceInput}
            onChange={(e) => handlePriceChange(e.target.value)}
            placeholder="Enter stop-loss price"
            className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {validationError && (
            <div className="flex items-center gap-1.5 mt-1.5 text-xs text-red-400">
              <AlertCircle className="w-3 h-3 flex-shrink-0" />
              <span>{validationError}</span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          {stopLossState?.isActive ? (
            <>
              <button
                onClick={handleApply}
                className="flex-1 px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm font-medium transition-colors"
              >
                Update
              </button>
              <button
                onClick={handleRemove}
                className="px-3 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded text-sm font-medium transition-colors border border-red-500/50"
              >
                Remove
              </button>
            </>
          ) : (
            <button
              onClick={handleApply}
              className="w-full px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm font-medium transition-colors"
            >
              Apply Stop-Loss
            </button>
          )}
        </div>

        {/* Info */}
        {stopLossState?.isActive && (
          <div className="bg-blue-500/10 border border-blue-500/30 rounded p-2">
            <div className="text-xs text-blue-400">
              Stop-loss active at ${stopLossState.price.toFixed(2)} for {stopLossState.side}
            </div>
          </div>
        )}
      </div>

      {/* Backend API Contract Note */}
      <div className="border-t border-slate-700 p-2 bg-slate-900/50">
        <div className="text-xs text-gray-500 italic">
          {/* TODO: Backend API endpoint: POST /api/risk/stop-loss */}
          {/* Payload: { symbol, stopLossPrice, side, timeframe, source: "manual" } */}
        </div>
      </div>
    </div>
  );
};

export default StopLossPanel;

