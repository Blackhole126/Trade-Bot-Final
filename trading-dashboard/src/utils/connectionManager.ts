/**
 * Connection Manager
 * Manages backend connection state and provides utilities for connection handling
 */

import { stockAPI } from '../services/api';

let connectionState = {
  isOnline: true,
  lastCheck: Date.now(),
  retryCount: 0,
};

const MAX_RETRY_COUNT = 3;
const RETRY_DELAY = 2000; // 2 seconds

/**
 * Check backend connection with retry logic
 */
export const checkBackendConnection = async (retries: number = MAX_RETRY_COUNT): Promise<boolean> => {
  try {
    const result = await stockAPI.checkConnection();
    if (result.connected) {
      connectionState.isOnline = true;
      connectionState.lastCheck = Date.now();
      connectionState.retryCount = 0;
      return true;
    } else {
      connectionState.isOnline = false;
      if (retries > 0) {
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
        return checkBackendConnection(retries - 1);
      }
      return false;
    }
  } catch (error) {
    connectionState.isOnline = false;
    if (retries > 0) {
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
      return checkBackendConnection(retries - 1);
    }
    return false;
  }
};

/**
 * Get current connection state
 */
export const getConnectionState = () => {
  return { ...connectionState };
};

/**
 * Reset connection state
 */
export const resetConnectionState = () => {
  connectionState = {
    isOnline: true,
    lastCheck: Date.now(),
    retryCount: 0,
  };
};








