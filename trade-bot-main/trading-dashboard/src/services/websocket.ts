/**
 * WebSocket Service for Real-time Updates
 * Handles real-time price updates, portfolio changes, and notifications
 */

import { io, Socket } from 'socket.io-client';
import { config } from '../config';

export interface PriceUpdate {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: number;
}

export interface PortfolioUpdate {
  totalValue: number;
  dailyChange: number;
  dailyChangePercent: number;
  timestamp: number;
}

export interface NotificationUpdate {
  id: string;
  type: 'price_alert' | 'prediction' | 'order' | 'system';
  message: string;
  data?: any;
  timestamp: number;
}

type PriceUpdateCallback = (update: PriceUpdate) => void;
type PortfolioUpdateCallback = (update: PortfolioUpdate) => void;
type NotificationUpdateCallback = (update: NotificationUpdate) => void;
type ConnectionStatusCallback = (connected: boolean) => void;

class WebSocketService {
  private socket: Socket | null = null;
  private connected: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 2; // Reduced attempts to avoid spam
  private reconnectDelay: number = 2000;
  private connectionFailed: boolean = false; // Track if connection permanently failed

  private priceUpdateCallbacks: Set<PriceUpdateCallback> = new Set();
  private portfolioUpdateCallbacks: Set<PortfolioUpdateCallback> = new Set();
  private notificationCallbacks: Set<NotificationUpdateCallback> = new Set();
  private connectionStatusCallbacks: Set<ConnectionStatusCallback> = new Set();
  private subscribedSymbols: Set<string> = new Set();

  connect(token?: string): void {
    // Don't try to connect if we've already failed or already connected
    if (this.connectionFailed || this.socket?.connected) {
      return;
    }

    try {
      const socketUrl = config.API_BASE_URL;

      this.socket = io(socketUrl, {
        transports: ['websocket', 'polling'],
        reconnection: false, // Disable auto-reconnection to prevent spam
        reconnectionDelay: this.reconnectDelay,
        reconnectionAttempts: 0, // No auto-reconnect
        timeout: 5000, // 5 second timeout
        auth: token ? { token } : undefined,
        autoConnect: false, // Don't auto-connect
      });

      this.setupEventHandlers();
      this.socket.connect(); // Manual connect
    } catch (error) {
      // Silently fail - backend WebSocket not available yet
      this.connectionFailed = true;
      this.handleConnectionError();
    }
  }

  private setupEventHandlers(): void {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      // Only log in development
      if (import.meta.env.DEV) {
        console.log('[WebSocket] Connected');
      }
      this.connected = true;
      this.reconnectAttempts = 0;
      this.connectionFailed = false;
      this.notifyConnectionStatus(true);

      if (this.subscribedSymbols.size > 0) {
        this.subscribeToPrices(Array.from(this.subscribedSymbols));
      }
    });

    this.socket.on('disconnect', (reason) => {
      // Only log in development
      if (import.meta.env.DEV) {
        console.log('[WebSocket] Disconnected:', reason);
      }
      this.connected = false;
      this.notifyConnectionStatus(false);
    });

    this.socket.on('connect_error', () => {
      // Silently handle connection errors - backend may not have WebSocket server yet
      this.reconnectAttempts++;
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        this.connectionFailed = true;
        if (this.socket) {
          this.socket.disconnect();
          this.socket = null;
        }
      }
      this.handleConnectionError();
    });

    this.socket.on('reconnect_attempt', () => {
      // Suppressed - no auto-reconnect enabled
    });

    this.socket.on('reconnect_failed', () => {
      // Suppressed - no auto-reconnect enabled
      this.connectionFailed = true;
      this.notifyConnectionStatus(false);
    });

    this.socket.on('price_update', (update: PriceUpdate) => {
      this.priceUpdateCallbacks.forEach(callback => {
        try {
          callback(update);
        } catch (error) {
          console.error('Error in price update callback:', error);
        }
      });
    });

    this.socket.on('portfolio_update', (update: PortfolioUpdate) => {
      this.portfolioUpdateCallbacks.forEach(callback => {
        try {
          callback(update);
        } catch (error) {
          console.error('Error in portfolio update callback:', error);
        }
      });
    });

    this.socket.on('notification', (update: NotificationUpdate) => {
      this.notificationCallbacks.forEach(callback => {
        try {
          callback(update);
        } catch (error) {
          console.error('Error in notification callback:', error);
        }
      });
    });
  }

  private handleConnectionError(): void {
    this.connected = false;
    this.notifyConnectionStatus(false);
    
    // Don't attempt reconnection - wait for backend to be ready
    // User can refresh page when backend WebSocket is available
  }

  subscribeToPrices(symbols: string[]): void {
    if (!this.socket || !this.connected) {
      symbols.forEach(symbol => this.subscribedSymbols.add(symbol));
      return;
    }

    try {
      symbols.forEach(symbol => {
        if (!this.subscribedSymbols.has(symbol)) {
          this.subscribedSymbols.add(symbol);
          this.socket?.emit('subscribe_prices', { symbols: [symbol] });
        }
      });
    } catch (error) {
      console.error('Error subscribing to prices:', error);
    }
  }

  unsubscribeFromPrices(symbols: string[]): void {
    if (!this.socket || !this.connected) {
      symbols.forEach(symbol => this.subscribedSymbols.delete(symbol));
      return;
    }

    try {
      symbols.forEach(symbol => {
        if (this.subscribedSymbols.has(symbol)) {
          this.subscribedSymbols.delete(symbol);
          this.socket?.emit('unsubscribe_prices', { symbols: [symbol] });
        }
      });
    } catch (error) {
      console.error('Error unsubscribing from prices:', error);
    }
  }

  onPriceUpdate(callback: PriceUpdateCallback): () => void {
    this.priceUpdateCallbacks.add(callback);
    return () => this.priceUpdateCallbacks.delete(callback);
  }

  onPortfolioUpdate(callback: PortfolioUpdateCallback): () => void {
    this.portfolioUpdateCallbacks.add(callback);
    return () => this.portfolioUpdateCallbacks.delete(callback);
  }

  onNotification(callback: NotificationUpdateCallback): () => void {
    this.notificationCallbacks.add(callback);
    return () => this.notificationCallbacks.delete(callback);
  }

  onConnectionStatus(callback: ConnectionStatusCallback): () => void {
    this.connectionStatusCallbacks.add(callback);
    return () => this.connectionStatusCallbacks.delete(callback);
  }

  private notifyConnectionStatus(connected: boolean): void {
    this.connectionStatusCallbacks.forEach(callback => {
      try {
        callback(connected);
      } catch (error) {
        console.error('Error in connection status callback:', error);
      }
    });
  }

  emit(event: string, data?: any): void {
    if (this.socket && this.connected) {
      this.socket.emit(event, data);
    }
    // Silently fail if not connected - no warning spam
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
      this.subscribedSymbols.clear();
      this.notifyConnectionStatus(false);
    }
  }

  isConnected(): boolean {
    return this.connected && (this.socket?.connected ?? false);
  }

  getConnectionStatus(): {
    connected: boolean;
    reconnectAttempts: number;
    subscribedSymbols: string[];
  } {
    return {
      connected: this.connected,
      reconnectAttempts: this.reconnectAttempts,
      subscribedSymbols: Array.from(this.subscribedSymbols),
    };
  }
}

export const websocketService = new WebSocketService();

