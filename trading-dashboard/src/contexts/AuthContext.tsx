import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI } from '../services/api';
import { config } from '../config';
import { getUserStorage } from '../utils/userStorage';

interface User {
  username: string;
  token: string;
}

interface AuthContextType {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  signup: (username: string, password: string, email: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  _isProvider: boolean; // Internal flag to check if we're inside a provider
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Initialize user from isolated sessionStorage (tab-specific)
const initializeUser = (): User | null => {
  const token = sessionStorage.getItem('token');
  const username = sessionStorage.getItem('username');

  // If we have a tab-specific session, use it
  if (token && token !== 'no-auth-required' && username) {
    return { username, token };
  }

  // ❌ REMOVED: Fallback to localStorage - this causes cross-tab data contamination
  // Each tab should maintain its own session without interference from other tabs
  return null;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Check if backend auth is disabled (open access mode)
  // In open access mode, we allow anonymous users
  const [authEnabled, setAuthEnabled] = useState<boolean | null>(null); // null = not checked yet
  const [user, setUser] = useState<User | null>(initializeUser);

  const checkAuthStatus = useCallback(async () => {
    try {
      const data = await authAPI.checkStatus();

      if (data.auth_status === 'disabled') {
        setAuthEnabled(false);
        const anonymousUser = { username: 'anonymous', token: 'no-auth-required' };
        setUser(anonymousUser);
        sessionStorage.setItem('token', 'no-auth-required');
        sessionStorage.setItem('username', 'anonymous');
        // ❌ REMOVED: localStorage.setItem - using sessionStorage only for tab isolation
      } else {
        setAuthEnabled(true);
        // STRICT ISOLATION: Use ONLY sessionStorage for tab-specific isolation
        const sessionToken = sessionStorage.getItem('token');
        const sessionUsername = sessionStorage.getItem('username');

        if (sessionToken && sessionUsername && sessionToken !== 'no-auth-required') {
          setUser({ username: sessionUsername, token: sessionToken });
        } else {
          setUser(null);
        }
      }
    } catch (_error) {
      // Backend unreachable or error: require login. Do NOT set anonymous user.
      setAuthEnabled(true);
      setUser(null);
      // ❌ REMOVED: localStorage cleanup - not using localStorage anymore
    }
  }, []);

  useEffect(() => {
    // Check backend auth status on mount
    checkAuthStatus();
  }, [checkAuthStatus]);

  // Cross-tab communication: detect when other tabs change auth state
  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      // Only care about sessionStorage changes (tab-specific)
      // Note: storage events only fire for localStorage changes from other tabs
      // For sessionStorage, each tab is already isolated, which is what we want
      console.log('[AUTH CONTEXT] Storage event detected:', event.key);
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  // When auth is enabled and we have no valid user, ensure state is clean
  useEffect(() => {
    if (authEnabled === true && user?.token === 'no-auth-required') {
      setUser(null);
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('username');
    }
  }, [authEnabled, user?.token]);

  const login = useCallback(async (username: string, password: string) => {
    // If auth is disabled, allow any login or skip login
    if (authEnabled === false) {
      const userData = {
        username: username || 'anonymous',
        token: 'no-auth-required'
      };
      setUser(userData);
      sessionStorage.setItem('token', 'no-auth-required');
      sessionStorage.setItem('username', userData.username);
      // ❌ REMOVED: localStorage - prevents cross-tab data contamination
      return;
    }

    // Only try to login via API if auth is enabled
    if (authEnabled === true) {
      try {
        const response = await authAPI.login(username, password);

        if (response.success && response.token) {
          const userData = {
            username: response.username || username,
            token: response.token
          };
          setUser(userData);
          sessionStorage.setItem('token', response.token);
          sessionStorage.setItem('username', response.username || username);
          // ❌ REMOVED: localStorage - using sessionStorage only for tab isolation
        } else {
          throw new Error(response.error || 'Login failed');
        }
      } catch (error: any) {
        // Handle axios errors
        if (error.response?.data?.detail) {
          throw new Error(error.response.data.detail);
        }
        throw new Error(error.message || 'Login failed. Please check your credentials.');
      }
    }
  }, [authEnabled]);

  const signup = async (username: string, password: string, email: string) => {
    if (!authEnabled) {
      await login(username, password);
      return;
    }
    try {
      const response = await authAPI.signup(username, password, email);
      if (!response.success) {
        throw new Error((response as any).message || 'Signup failed');
      }
      const r = response as { token?: string; username?: string };
      if (r.token && r.token !== 'no-auth-required') {
        const userData = { username: r.username || username, token: r.token };
        setUser(userData);
        sessionStorage.setItem('token', r.token);
        sessionStorage.setItem('username', r.username || username);
        // ❌ REMOVED: localStorage - using sessionStorage only for tab isolation
      } else {
        await login(username, password);
      }
    } catch (error: any) {
      throw new Error(error.message || 'Signup failed');
    }
  };

  const logout = () => {
    // Clear this user's scoped data from sessionStorage
    if (user?.username) {
      const userStorage = getUserStorage(user.username);
      userStorage.clearUserData();
    }
    setUser(null);
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('username');
    // ❌ REMOVED: localStorage cleanup - not using localStorage anymore
  };

  return (
    <AuthContext.Provider value={{ user, login, signup, logout, isAuthenticated: !!user, _isProvider: true }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): Omit<AuthContextType, '_isProvider'> => {
  const context = useContext(AuthContext);
  if (!context || !context._isProvider) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  // Remove internal flag before returning
  const { _isProvider, ...publicContext } = context;
  return publicContext;
};

