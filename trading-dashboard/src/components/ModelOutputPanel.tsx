import React from 'react';
import { PredictionItem } from '../types';

interface ModelOutputPanelProps {
  prediction: PredictionItem;
  className?: string;
}

export const ModelOutputPanel: React.FC<ModelOutputPanelProps> = ({ prediction, className = '' }) => {
  const getDirectionalBias = () => {
    if (prediction.action === 'LONG') return 'Bullish';
    if (prediction.action === 'SHORT') return 'Bearish';
    return 'Neutral';
  };

  const getBiasColor = () => {
    if (prediction.action === 'LONG') return 'text-green-600';
    if (prediction.action === 'SHORT') return 'text-red-600';
    return 'text-gray-600';
  };

  return (
    <div className={`bg-gray-50 border rounded-lg p-3 ${className}`}>
      <h4 className="font-medium text-gray-900 mb-2">MODEL OUTPUT</h4>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Directional Bias:</span>
          <span className={getBiasColor()}>{getDirectionalBias()}</span>
        </div>
        {prediction.model_agreement && (
          <div className="flex justify-between">
            <span className="text-gray-600">Model Agreement:</span>
            <span className="text-gray-900">{prediction.model_agreement}</span>
          </div>
        )}
        {prediction.signal_strength !== undefined && (
          <div className="flex justify-between">
            <span className="text-gray-600">Signal Strength:</span>
            <span className="text-gray-900">{prediction.signal_strength}/100</span>
          </div>
        )}
      </div>
    </div>
  );
};