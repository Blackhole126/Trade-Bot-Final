import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, RefreshCw, Power, Terminal } from 'lucide-react';
import { useConnection } from '../contexts/ConnectionContext';
import { useTheme } from '../contexts/ThemeContext';

interface BackendStatusProps {
  className?: string;
}

export const BackendStatus: React.FC<BackendStatusProps> = ({ className = '' }) => {
  const { connectionState, forceCheck } = useConnection();
  const { theme } = useTheme();
  const [isRestarting, setIsRestarting] = useState(false);
  const [showRestartModal, setShowRestartModal] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);

  const isLight = theme === 'light';
  const isSpace = theme === 'space';

  const handleRestartClick = () => {
    setShowRestartModal(true);
  };

  const handleRestartConfirm = async () => {
    setIsRestarting(true);
    setShowRestartModal(false);
    
    // Copy the restart command to clipboard
    const restartCommand = `cd "d:\\blackhole projects\\blackhole-infevers trade\\Multi-Asset Trading Dashboard\\backend" && python api_server.py`;
    
    try {
      await navigator.clipboard.writeText(restartCommand);
      setCopySuccess(true);
      
      alert(
        '✅ Command copied to clipboard!\n\n' +
        'Instructions:\n' +
        '1. Open a new PowerShell/Terminal window\n' +
        '2. Paste the command (Ctrl+V)\n' +
        '3. Press Enter to start the backend\n' +
        '4. Wait 3-5 seconds for server to start\n' +
        '5. Come back and click "Check Connection"'
      );
    } catch (err) {
      alert(
        '⚠️ Unable to copy automatically.\n\n' +
        'Run this command manually in a terminal:\n\n' +
        restartCommand
      );
    }

    // Wait a moment then check connection again
    setTimeout(async () => {
      await forceCheck();
      setIsRestarting(false);
      setCopySuccess(false);
    }, 3000);
  };

  const handleCheckConnection = async () => {
    await forceCheck();
  };

  const isOnline = connectionState.isConnected;

  return (
    <>
      {/* Status Button/Badge with Green Dot */}
      <button
        onClick={isOnline ? handleCheckConnection : handleRestartClick}
        className={`
          flex items-center gap-2 px-3 py-2 rounded-lg font-medium text-sm
          transition-all duration-200 cursor-pointer shadow-sm
          ${isOnline
            ? isLight
              ? 'bg-green-50 text-green-700 hover:bg-green-100 border border-green-200'
              : isSpace
                ? 'bg-green-900/40 text-green-300 border border-green-800'
                : 'bg-green-900/40 text-green-300 border border-green-800'
            : isLight
              ? 'bg-red-50 text-red-700 hover:bg-red-100 border border-red-200'
              : isSpace
                ? 'bg-red-900/40 text-red-300 border border-red-800'
                : 'bg-red-900/40 text-red-300 border border-red-800'
          }
          ${className}
        `}
        disabled={isRestarting || connectionState.isChecking}
        title={isOnline ? 'Click to verify connection' : 'Click to restart backend'}
      >
        {/* Green/Red Dot Indicator */}
        <div className="flex items-center">
          <div
            className={`
              w-2 h-2 rounded-full
              ${isOnline
                ? 'bg-green-500 animate-pulse'
                : 'bg-red-500 animate-pulse'
              }
            `}
          />
        </div>

        {isOnline ? (
          <>
            <span className="font-semibold">Backend Online (Live)</span>
            {connectionState.isChecking && <RefreshCw size={14} className="animate-spin ml-1" />}
          </>
        ) : (
          <>
            <span className="font-semibold">Backend Offline</span>
            {connectionState.isChecking && <RefreshCw size={14} className="animate-spin ml-1" />}
          </>
        )}
      </button>

      {/* Restart Modal */}
      {showRestartModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className={`rounded-lg shadow-xl max-w-md w-full mx-4 ${
            isLight ? 'bg-white' : isSpace ? 'bg-slate-800' : 'bg-slate-800'
          }`}>
            {/* Header */}
            <div className={`px-6 py-4 border-b ${
              isLight
                ? 'bg-red-50 border-red-200'
                : isSpace
                  ? 'bg-red-900/30 border-red-800'
                  : 'bg-red-900/30 border-red-800'
            }`}>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
                <h2 className={`text-lg font-bold ${
                  isLight ? 'text-red-900' : 'text-red-100'
                }`}>
                  Backend Server Offline
                </h2>
              </div>
            </div>

            {/* Content */}
            <div className="p-6">
              <p className={`mb-4 font-medium ${
                isLight ? 'text-gray-700' : 'text-gray-300'
              }`}>
                The backend server is offline. Click below to copy the restart command.
              </p>
            
              <div className={`p-4 rounded-lg mb-4 overflow-x-auto ${
                isLight
                  ? 'bg-gray-100 border border-gray-300'
                  : isSpace
                    ? 'bg-gray-900 border border-gray-700'
                    : 'bg-gray-900 border border-gray-700'
              }`}>
                <code className={`text-xs font-mono block whitespace-pre-wrap break-words ${
                  isLight ? 'text-gray-800' : 'text-gray-200'
                }`}>
                  cd "d:\blackhole projects\blackhole-infevers trade\Multi-Asset Trading Dashboard\backend" && python api_server.py
                </code>
              </div>
            
              <div className={`rounded-lg p-3 mb-4 ${
                isLight
                  ? 'bg-blue-50 border border-blue-200'
                  : isSpace
                    ? 'bg-blue-900/30 border border-blue-800'
                    : 'bg-blue-900/30 border border-blue-800'
              }`}>
                <p className={`text-sm ${
                  isLight ? 'text-blue-900' : 'text-blue-200'
                }`}>
                  <span className="font-semibold">📋 Steps:</span><br/>
                  1️⃣ Click "Copy & Restart" button below<br/>
                  2️⃣ Open PowerShell or Terminal<br/>
                  3️⃣ Paste (Ctrl+V) and press Enter<br/>
                  4️⃣ Wait for "Application startup complete"<br/>
                  5️⃣ Come back and button will turn green!
                </p>
              </div>
            
              {copySuccess && (
                <div className={`rounded-lg p-3 mb-4 ${
                  isLight
                    ? 'bg-green-50 border border-green-200'
                    : isSpace
                      ? 'bg-green-900/30 border border-green-800'
                      : 'bg-green-900/30 border border-green-800'
                }`}>
                  <p className={`text-sm ${
                    isLight ? 'text-green-900' : 'text-green-200'
                  }`}>
                    ✅ Command copied to clipboard!
                  </p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className={`px-6 py-4 flex gap-3 border-t ${
              isLight
                ? 'bg-gray-50 border-gray-200'
                : isSpace
                  ? 'bg-gray-700/50 border-gray-700'
                  : 'bg-gray-700/50 border-gray-700'
            }`}>
              <button
                onClick={() => setShowRestartModal(false)}
                className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                  isLight
                    ? 'border border-gray-300 text-gray-700 hover:bg-gray-100'
                    : isSpace
                      ? 'border border-gray-600 text-gray-300 hover:bg-gray-700'
                      : 'border border-gray-600 text-gray-300 hover:bg-gray-700'
                }`}
              >
                Cancel
              </button>
              <button
                onClick={handleRestartConfirm}
                className="flex-1 px-4 py-2 rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
              >
                <Terminal size={16} />
                Copy & Restart
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default BackendStatus;
