import React from 'react';
import { WifiOff } from 'lucide-react';
import { useBackendStatus } from '../contexts/BackendStatusContext';

export const GlobalOfflineIndicator: React.FC = () => {
  const { status } = useBackendStatus();

  // Only show indicator if backend is actually offline/unreachable
  if (status !== 'OFFLINE') {
    return null;
  }

  return (
    <div
      className={`fixed top-0 left-0 right-0 z-50 bg-red-600 text-white px-4 py-3 shadow-lg`}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <WifiOff className="w-5 h-5" />
          
          <div>
            <p className="font-semibold">
              🔴 Backend Offline
            </p>
          </div>
        </div>

        <div className="text-sm opacity-90">
          Check connection to https://trade-bot-api.onrender.com
        </div>
      </div>
    </div>
  );
};
