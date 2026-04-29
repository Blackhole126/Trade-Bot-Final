import { useState } from 'react';
import { useConnection } from '../contexts/ConnectionContext';
import { X, Wifi, WifiOff, Loader2 } from 'lucide-react';

interface BackendConnectionBannerProps {
  className?: string;
}

const BackendConnectionBanner = ({ className = '' }: BackendConnectionBannerProps) => {
  const { connectionState, forceCheck } = useConnection();
  const [isDismissed, setIsDismissed] = useState(false);

  // Reset dismissal when connection is restored
  if (connectionState.isConnected && isDismissed) {
    setIsDismissed(false);
  }

  // Don't show banner if connection is good or if user dismissed it
  if (connectionState.isConnected || isDismissed) {
    return null;
  }

  const connectionStatus = connectionState.isChecking ? 'checking' : 'disconnected';

  return (
    <div className={`${className} fixed top-0 left-0 lg:left-64 right-0 z-[60] animate-slideDown`}>
      <div className="bg-red-900/95 border-b-2 border-red-500 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 mt-0.5">
              {connectionStatus === 'checking' ? (
                <Loader2 className="w-5 h-5 text-yellow-400 animate-spin" />
              ) : (
                <WifiOff className="w-5 h-5 text-red-400" />
              )}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-3">
                <div className="flex-1">
                  <h3 className="text-red-100 font-bold text-sm mb-1">
                    {connectionStatus === 'checking' ? 'Checking Backend Connection...' : 'Backend Server Offline'}
                  </h3>
                  <p className="text-red-200 text-xs mb-2">
                    {connectionState.error || 'Unable to connect to the backend server. Some features may not work.'}
                  </p>
                  
                  <div className="bg-red-950/50 rounded-lg p-2.5 mt-2 border border-red-800/50">
                    <p className="text-red-300 text-xs font-medium mb-1.5">Backend URL:</p>
                    <code className="text-xs text-red-200 bg-red-900/50 px-2 py-1 rounded block">
                      {connectionState.backendUrl}
                    </code>
                    
                    <div className="mt-2 space-y-1.5">
                      <p className="text-red-300 text-xs font-medium">To start the backend server:</p>
                      <div className="space-y-1">
                        <code className="text-xs text-green-300 bg-red-900/50 px-2 py-1 rounded block">
                          cd backend && python api_server.py
                        </code>
                        <p className="text-red-400 text-xs mt-1">
                          Or use: <code className="text-yellow-300">START_BACKEND_NOW.bat</code>
                        </p>
                      </div>
                    </div>
                    
                    {connectionState.lastCheck && (
                      <p className="text-red-400 text-xs mt-2">
                        Last check: {connectionState.lastCheck.toLocaleTimeString()}
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={forceCheck}
                    disabled={connectionState.isChecking}
                    className="px-3 py-1.5 bg-red-700 hover:bg-red-600 text-white text-xs font-semibold rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                  >
                    {connectionState.isChecking ? (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>Checking...</span>
                      </>
                    ) : (
                      <>
                        <Wifi className="w-3 h-3" />
                        <span>Retry</span>
                      </>
                    )}
                  </button>
                  
                  <button
                    onClick={() => setIsDismissed(true)}
                    className="p-1.5 text-red-300 hover:text-red-100 hover:bg-red-800/50 rounded transition-colors"
                    title="Dismiss (will reappear if connection fails again)"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BackendConnectionBanner;

