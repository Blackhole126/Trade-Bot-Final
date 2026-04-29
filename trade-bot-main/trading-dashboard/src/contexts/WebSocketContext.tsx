import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { websocketService, PriceUpdate, PortfolioUpdate, NotificationUpdate } from '../services/websocket';
import { useAuth } from './AuthContext';

interface WebSocketContextType {
  isConnected: boolean;
  subscribeToPrices: (symbols: string[]) => void;
  unsubscribeFromPrices: (symbols: string[]) => void;
  onPriceUpdate: (callback: (update: PriceUpdate) => void) => () => void;
  onPortfolioUpdate: (callback: (update: PortfolioUpdate) => void) => () => void;
  onNotification: (callback: (update: NotificationUpdate) => void) => () => void;
  connectionStatus: {
    connected: boolean;
    reconnectAttempts: number;
    subscribedSymbols: string[];
  };
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider = ({ children }: { children: ReactNode }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState({
    connected: false,
    reconnectAttempts: 0,
    subscribedSymbols: [] as string[],
  });
  const { user } = useAuth();

  useEffect(() => {
    // DISABLED: WebSocket connection disabled
    // Reason: Backend does NOT support Socket.IO or WebSockets
    // All real-time updates use REST API polling instead (see DashboardPage.tsx)
    // 
    // Previous attempt to connect was causing unwanted connection attempts to:
    // ws://127.0.0.1:8000/socket.io/?EIO=4&transport=websocket
    // 
    // To re-enable WebSocket support in future, uncomment code below
    // and ensure backend has Socket.IO middleware configured.
    
    // const shouldConnect = false; // WebSockets not supported by backend
    // if (!shouldConnect) return;
    
    // const connect = () => {
    //   try {
    //     const authToken = user?.token || localStorage.getItem('token');
    //     websocketService.connect(authToken && authToken !== 'no-auth-required' ? authToken : undefined);
    //   } catch (error) {
    //     // Silently fail
    //   }
    // };
    
    // const unsubscribeStatus = websocketService.onConnectionStatus((connected) => {
    //   setIsConnected(connected);
    //   setConnectionStatus(websocketService.getConnectionStatus());
    // });
    
    // const connectTimer = setTimeout(() => {
    //   connect();
    // }, 1000);

    // Cleanup on unmount
    return () => {
      // Cleanup code removed - WebSocket disabled
    };
  }, [user]);

  const subscribeToPrices = useCallback((_symbols: string[]) => {
    // WebSocket disabled - no real-time price updates
    // Use REST API polling instead (see dashboard refresh interval)
  }, []);

  const unsubscribeFromPrices = useCallback((_symbols: string[]) => {
    // WebSocket disabled
  }, []);

  const onPriceUpdate = useCallback((_callback: (update: PriceUpdate) => void) => {
    // WebSocket disabled - callback will never be triggered
    return () => {}; // Return no-op unsubscribe function
  }, []);

  const onPortfolioUpdate = useCallback((_callback: (update: PortfolioUpdate) => void) => {
    // WebSocket disabled - callback will never be triggered
    return () => {}; // Return no-op unsubscribe function
  }, []);

  const onNotification = useCallback((_callback: (update: NotificationUpdate) => void) => {
    // WebSocket disabled - callback will never be triggered
    return () => {}; // Return no-op unsubscribe function
  }, []);

  return (
    <WebSocketContext.Provider
      value={{
        isConnected,
        subscribeToPrices,
        unsubscribeFromPrices,
        onPriceUpdate,
        onPortfolioUpdate,
        onNotification,
        connectionStatus,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

