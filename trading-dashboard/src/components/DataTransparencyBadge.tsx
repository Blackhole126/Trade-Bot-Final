import React from 'react';
import { AlertTriangle, CheckCircle, Clock, Wifi, WifiOff, Info, Eye } from 'lucide-react';
import { MarketDataValidation } from '../utils/marketDataValidator';

interface DataTransparencyBadgeProps {
  validation: MarketDataValidation;
  symbol?: string;
  compact?: boolean;
  className?: string;
}

export const DataTransparencyBadge: React.FC<DataTransparencyBadgeProps> = ({
  validation,
  symbol,
  compact = false,
  className = ''
}) => {
  const getStatusIcon = () => {
    if (!validation.isValid) {
      return <AlertTriangle className="w-3 h-3 text-red-400" />;
    }
    
    if (!validation.isReal) {
      return <Eye className="w-3 h-3 text-yellow-400" />;
    }
    
    if (validation.confidence === 'HIGH') {
      return <Wifi className="w-3 h-3 text-green-400" />;
    }
    
    if (validation.confidence === 'MEDIUM') {
      return <Clock className="w-3 h-3 text-yellow-400" />;
    }
    
    return <WifiOff className="w-3 h-3 text-red-400" />;
  };

  const getStatusColor = () => {
    if (!validation.isValid) return 'border-red-500/50 bg-red-500/10';
    if (!validation.isReal) return 'border-yellow-500/50 bg-yellow-500/10';
    if (validation.confidence === 'HIGH') return 'border-green-500/50 bg-green-500/10';
    if (validation.confidence === 'MEDIUM') return 'border-yellow-500/50 bg-yellow-500/10';
    return 'border-red-500/50 bg-red-500/10';
  };

  const getStatusText = () => {
    if (!validation.isValid) return 'INVALID';
    if (!validation.isReal) return 'SIMULATED';
    
    if (validation.dataAge !== undefined) {
      if (validation.dataAge < 1) return 'LIVE';
      if (validation.dataAge < 15) return `${validation.dataAge}min delay`;
      return `${validation.dataAge}min old`;
    }
    
    return validation.source.toUpperCase();
  };

  const getTooltipContent = () => {
    const parts = [];
    
    if (symbol) {
      parts.push(`Symbol: ${symbol}`);
    }
    
    parts.push(`Source: ${validation.source}`);
    parts.push(`Confidence: ${validation.confidence}`);
    
    if (validation.timestamp) {
      parts.push(`Updated: ${new Date(validation.timestamp).toLocaleString()}`);
    }
    
    if (validation.warnings.length > 0) {
      parts.push(`Warnings: ${validation.warnings.join(', ')}`);
    }
    
    if (validation.errors.length > 0) {
      parts.push(`Errors: ${validation.errors.join(', ')}`);
    }
    
    return parts.join('\n');
  };

  if (compact) {
    return (
      <div 
        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium border ${getStatusColor()} ${className}`}
        title={getTooltipContent()}
      >
        {getStatusIcon()}
        <span>{getStatusText()}</span>
      </div>
    );
  }

  return (
    <div className={`p-2 rounded-lg border ${getStatusColor()} ${className}`}>
      <div className="flex items-center gap-2 mb-1">
        {getStatusIcon()}
        <span className="text-xs font-semibold">{getStatusText()}</span>
      </div>
      
      <div className="text-xs text-gray-400 space-y-1">
        <div>Source: {validation.source}</div>
        {validation.timestamp && (
          <div>Updated: {new Date(validation.timestamp).toLocaleTimeString()}</div>
        )}
        {validation.warnings.length > 0 && (
          <div className="text-yellow-400">⚠ {validation.warnings.join(', ')}</div>
        )}
        {validation.errors.length > 0 && (
          <div className="text-red-400">✗ {validation.errors.join(', ')}</div>
        )}
      </div>
    </div>
  );
};

interface DataIntegrityWarningProps {
  validation: MarketDataValidation;
  onRefresh?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export const DataIntegrityWarning: React.FC<DataIntegrityWarningProps> = ({
  validation,
  onRefresh,
  onDismiss,
  className = ''
}) => {
  if (validation.isValid && validation.isReal && validation.confidence !== 'LOW') {
    return null;
  }

  const getSeverityColor = () => {
    if (!validation.isValid) return 'bg-red-900/30 border-red-500/50';
    if (!validation.isReal) return 'bg-yellow-900/30 border-yellow-500/50';
    return 'bg-orange-900/30 border-orange-500/50';
  };

  const getSeverityIcon = () => {
    if (!validation.isValid) return <AlertTriangle className="w-5 h-5 text-red-400" />;
    if (!validation.isReal) return <Info className="w-5 h-5 text-yellow-400" />;
    return <Clock className="w-5 h-5 text-orange-400" />;
  };

  const getTitle = () => {
    if (!validation.isValid) return 'Invalid Market Data';
    if (!validation.isReal) return 'Simulated Data Warning';
    return 'Data Quality Notice';
  };

  const getMessage = () => {
    if (!validation.isValid) {
      return 'The displayed market data contains errors and should not be used for trading decisions.';
    }
    
    if (!validation.isReal) {
      return 'This data is simulated or cached and does not reflect real market conditions.';
    }
    
    return 'The market data may be stale or have quality issues that could affect accuracy.';
  };

  return (
    <div className={`rounded-xl p-4 border-2 ${getSeverityColor()} ${className}`}>
      <div className="flex items-start gap-3">
        {getSeverityIcon()}
        <div className="flex-1">
          <h3 className="font-semibold text-white mb-2">{getTitle()}</h3>
          <p className="text-gray-300 text-sm mb-3">{getMessage()}</p>
          
          {validation.warnings.length > 0 && (
            <div className="mb-3">
              <p className="text-yellow-400 text-sm font-medium mb-1">Warnings:</p>
              <ul className="text-yellow-300 text-sm space-y-1">
                {validation.warnings.map((warning, index) => (
                  <li key={index}>• {warning}</li>
                ))}
              </ul>
            </div>
          )}
          
          {validation.errors.length > 0 && (
            <div className="mb-3">
              <p className="text-red-400 text-sm font-medium mb-1">Errors:</p>
              <ul className="text-red-300 text-sm space-y-1">
                {validation.errors.map((error, index) => (
                  <li key={index}>• {error}</li>
                ))}
              </ul>
            </div>
          )}
          
          <div className="flex items-center gap-2 flex-wrap">
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm transition-all hover:scale-105"
              >
                Refresh Data
              </button>
            )}
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="px-3 py-1.5 bg-gray-500 hover:bg-gray-600 text-white rounded-lg text-sm transition-all hover:scale-105"
              >
                Dismiss
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataTransparencyBadge;