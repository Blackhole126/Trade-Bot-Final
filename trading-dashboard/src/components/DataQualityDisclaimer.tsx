import React, { useState } from 'react';
import { AlertTriangle, X, Info } from 'lucide-react';

interface DataQualityDisclaimerProps {
  onAccept: () => void;
  className?: string;
}

export const DataQualityDisclaimer: React.FC<DataQualityDisclaimerProps> = ({
  onAccept,
  className = ''
}) => {
  return (
    <div className={`fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4 ${className}`}>
      <div className="bg-slate-800 border border-red-500/50 rounded-xl p-6 max-w-md w-full">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-6 h-6 text-red-400 flex-shrink-0" />
          <h3 className="text-lg font-bold text-white">Data Quality Notice</h3>
        </div>
        
        <div className="space-y-3 text-gray-300 text-sm mb-6">
          <p>
            <strong className="text-white">This system shows data quality, not prediction accuracy.</strong>
          </p>
          
          <div className="bg-red-900/20 border border-red-500/30 rounded p-3">
            <p className="text-red-300 font-medium mb-2">Important Limitations:</p>
            <ul className="space-y-1 text-red-200 text-xs">
              <li>• Predictions may run on cached or delayed data</li>
              <li>• "Data Quality" refers to source reliability, not forecast accuracy</li>
              <li>• Backend data sources are not independently verified</li>
              <li>• This is a demonstration system, not production-grade</li>
            </ul>
          </div>
          
          <p>
            The system will clearly label data sources and warn about quality issues, 
            but <strong>you are responsible for verifying all information independently</strong>.
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={onAccept}
            className="flex-1 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-semibold transition-all"
          >
            I Understand
          </button>
        </div>
      </div>
    </div>
  );
};

interface DataQualityWarningBannerProps {
  onDismiss?: () => void;
  className?: string;
}

export const DataQualityWarningBanner: React.FC<DataQualityWarningBannerProps> = ({
  onDismiss,
  className = ''
}) => {
  const [dismissed, setDismissed] = useState(false);
  
  if (dismissed) return null;
  
  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };
  
  return (
    <div className={`bg-yellow-900/30 border border-yellow-500/50 rounded-lg p-3 ${className}`}>
      <div className="flex items-start gap-3">
        <Info className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-yellow-300 text-sm">
            <strong>Data Quality Indicators:</strong> The confidence levels shown refer to data source reliability, 
            not prediction accuracy. Always verify prices independently before making trading decisions.
          </p>
        </div>
        {onDismiss && (
          <button
            onClick={handleDismiss}
            className="text-yellow-400 hover:text-yellow-300 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};

export default DataQualityDisclaimer;