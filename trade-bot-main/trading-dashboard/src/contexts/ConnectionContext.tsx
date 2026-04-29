import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { stockAPI } from '../services/api';
import { useBackendStatus } from './BackendStatusContext';

interface ConnectionState {
  isConnected: boolean;
  isChecking: boolean;
  error: string | null;
  lastCheck: Date | null;
  backendUrl: string;
}

interface ConnectionContextType {
  connectionState: ConnectionState;
  checkConnection: () => Promise<void>;
  forceCheck: () => Promise<void>;
}

const ConnectionContext = createContext<ConnectionContextType | undefined>(undefined);

export const ConnectionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isOnline, isOffline, status } = useBackendStatus();
  const [connectionState, setConnectionState] = useState<ConnectionState>({
    isConnected: true,
    isChecking: true,
    error: null,
    lastCheck: null,
    backendUrl: import.meta.env.VITE_API_BASE_BACKEND_URL || 'https://trade-bot-api.onrender.com',
  });

  // Sync with centralized backend status
  useEffect(() => {
    setConnectionState(prev => ({
      ...prev,
      isConnected: isOnline,
      isChecking: status === 'CHECKING',
      error: isOffline ? 'Backend is offline' : null,
      lastCheck: new Date(),
    }));
  }, [isOnline, isOffline, status]);

  const checkConnection = useCallback(async (isForceCheck = false) => {
    // Delegate to centralized backend status
    // This prevents duplicate checks
    return;
  }, []);

  const forceCheck = useCallback(async () => {
    // Delegate to centralized backend status
    return;
  }, []);

  return (
    <ConnectionContext.Provider value={{ connectionState, checkConnection, forceCheck }}>
      {children}
    </ConnectionContext.Provider>
  );
};

export const useConnection = () => {
  const context = useContext(ConnectionContext);
  if (context === undefined) {
    throw new Error('useConnection must be used within a ConnectionProvider');
  }
  return context;
};
