import React, { createContext, useContext, useState, useEffect } from 'react';
import { config } from '../config';

interface BackendStatusState {
  isOnline: boolean;
  isOffline: boolean;
  status: 'ONLINE' | 'OFFLINE' | 'CHECKING';
}

interface BackendStatusContextType extends BackendStatusState {
  checkStatus: () => Promise<void>;
}

const BackendStatusContext = createContext<BackendStatusContextType | undefined>(undefined);

export const BackendStatusProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<BackendStatusState>({
    isOnline: true,   // optimistic: assume online until a hard connection failure
    isOffline: false,
    status: 'CHECKING'
  });

  const checkStatus = async () => {
    const controller = new AbortController();
    // 5-second ping. If it doesn't respond in 5s the backend is busy with ML analysis.
    // We do NOT mark it OFFLINE for a timeout — only for a true connection refusal.
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
      const response = await fetch(`${config.API_BASE_URL}/api/health`, { signal: controller.signal });
      clearTimeout(timeoutId);
      const isOnline = response.ok;
      setState({
        isOnline,
        isOffline: !isOnline,
        status: isOnline ? 'ONLINE' : 'OFFLINE'
      });
    } catch (e: any) {
      clearTimeout(timeoutId);
      const isAbort = e?.name === 'AbortError';
      const isNetworkRefused =
        !isAbort &&
        (e?.message?.includes('ERR_CONNECTION_REFUSED') ||
          e?.message?.includes('ECONNREFUSED'));

      if (isAbort || !isNetworkRefused) {
        // Timeout or ambiguous error → backend is BUSY (ML analysis, cold start…)
        // Keep as online/checking — DO NOT flash "System Offline"
        setState(prev => ({ ...prev, status: 'CHECKING' }));
      } else {
        // True connection refused = process is not running
        setState({ isOnline: false, isOffline: true, status: 'OFFLINE' });
      }
    }
  };

  useEffect(() => {
    checkStatus();
    // Poll every 60 s — false positives during ML analysis are very disruptive.
    const interval = setInterval(checkStatus, 60000);
    return () => {
      clearInterval(interval);
    };
  }, []);

  return (
    <BackendStatusContext.Provider value={{ ...state, checkStatus }}>
      {children}
    </BackendStatusContext.Provider>
  );
};

export const useBackendStatus = (): BackendStatusContextType => {
  const context = useContext(BackendStatusContext);
  if (!context) {
    throw new Error('useBackendStatus must be used within BackendStatusProvider');
  }
  return context;
};