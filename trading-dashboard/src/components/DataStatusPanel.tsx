import React from 'react';
import { DataStatus } from '../types';

interface DataStatusPanelProps {
  dataStatus: DataStatus;
  className?: string;
}

export const DataStatusPanel: React.FC<DataStatusPanelProps> = ({ dataStatus, className = '' }) => {
  const getSourceLabel = (source: string) => {
    switch (source) {
      case 'REALTIME_YAHOO_FINANCE': return 'Real-time Yahoo Finance';
      case 'CACHED_YAHOO_FINANCE': return 'Cached Yahoo Finance';
      case 'FALLBACK_PROVIDER': return 'Fallback Provider';
      case 'INVALID': return 'Invalid Data';
      default: return source;
    }
  };

  const getContextLabel = (context: string) => {
    switch (context) {
      case 'NORMAL': return 'Normal';
      case 'HIGH_VOLATILITY': return 'High Volatility';
      case 'EVENT_WINDOW': return 'Event Window';
      case 'MARKET_CLOSED': return 'Market Closed';
      default: return context;
    }
  };

  const formatFreshness = (seconds: number) => {
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
  };

  const getStatusColor = () => {
    if (dataStatus.data_source === 'REALTIME_YAHOO_FINANCE') return 'text-green-600';
    if (dataStatus.data_source === 'CACHED_YAHOO_FINANCE' && dataStatus.data_freshness_seconds < 300) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className={`bg-gray-50 border rounded-lg p-3 ${className}`}>
      <h4 className="font-medium text-gray-900 mb-2">DATA STATUS</h4>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Source:</span>
          <span className={getStatusColor()}>{getSourceLabel(dataStatus.data_source)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Last Updated:</span>
          <span className="text-gray-900">{formatFreshness(dataStatus.data_freshness_seconds)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Market Context:</span>
          <span className="text-gray-900">{getContextLabel(dataStatus.market_context)}</span>
        </div>
      </div>
    </div>
  );
};