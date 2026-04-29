import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { stockAPI } from '../services/api';
import { useBackendStatus } from './BackendStatusContext';

interface HealthStatus {
  healthy: boolean;
  status: string;
  timestamp: Date;
  message?: string;
}

interface HealthContextType {
  health: HealthStatus;
  isPolling: boolean;
  lastHealthCheck: Date | null;
  checkHealth: () => Promise<void>;
}

const HealthContext = createContext<HealthContextType | undefined>(undefined);

export const HealthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isOnline, isOffline } = useBackendStatus();
  const [health, setHealth] = useState<HealthStatus>({
    healthy: true,
    status: 'unknown',
    timestamp: new Date(),
  });
  const [isPolling, setIsPolling] = useState(false);
  const [lastHealthCheck, setLastHealthCheck] = useState<Date | null>(null);

  const checkHealth = useCallback(async () => {
    // Skip if backend is offline (centralized check already failed)
    if (isOffline) {
      setHealth({
        healthy: false,
        status: 'offline',
        timestamp: new Date(),
        message: 'Backend is offline',
      });
      return;
    }

    try {
      setIsPolling(true);
      const result = await stockAPI.health();
      
      setHealth({
        healthy: result.status === 'ok' || result.status === 'healthy' || result.healthy === true,
        status: result.status || 'unknown',
        timestamp: new Date(),
        message: result.message,
      });
      setLastHealthCheck(new Date());
    } catch (error: any) {
      setHealth({
        healthy: false,
        status: 'error',
        timestamp: new Date(),
        message: error.message || 'Health check failed',
      });
      setLastHealthCheck(new Date());
    } finally {
      setIsPolling(false);
    }
  }, [isOffline]);

  // Poll health status only when backend is online
  useEffect(() => {
    if (!isOnline) return;

    checkHealth();

    const interval = setInterval(() => {
      if (isOnline) {
        checkHealth();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [checkHealth, isOnline]);

  return (
    <HealthContext.Provider value={{ health, isPolling, lastHealthCheck, checkHealth }}>
      {children}
    </HealthContext.Provider>
  );
};

export const useHealth = (): HealthContextType => {
  const context = useContext(HealthContext);
  if (!context) {
    throw new Error('useHealth must be used within HealthProvider');
  }
  return context;
};
