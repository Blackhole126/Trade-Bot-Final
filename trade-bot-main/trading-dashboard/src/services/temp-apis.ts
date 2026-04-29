import api from './api';

// Trading History API
export const historyAPI = {
  /**
   * Fetch trading history from backend
   * 
   * Backend endpoint: GET /api/trades/history
   * 
   * Response: { trades: Array<TradeHistoryItem> }
   */
  getHistory: async (page: number = 1, limit: number = 20, filters?: any) => {
    try {
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('limit', limit.toString());
      
      if (filters) {
        if (filters.startDate) params.append('startDate', filters.startDate);
        if (filters.endDate) params.append('endDate', filters.endDate);
        if (filters.symbols) params.append('symbols', filters.symbols.join(','));
        if (filters.types) params.append('types', filters.types.join(','));
      }
      
      const queryString = params.toString();
      const url = queryString ? `/api/trades/history?${queryString}` : '/api/trades/history';
      
      const response = await api.get(url);
      return response.data;
    } catch (error: any) {
      // If endpoint doesn't exist, return empty data
      if (error.response?.status === 404) {
        return { trades: [], total: 0, page: 1, totalPages: 1, message: 'Trade history API not available' };
      }
      throw error;
    }
  },

  /**
   * Add trade to history
   * 
   * Backend endpoint: POST /api/trades/history
   * 
   * Payload: { symbol: string, type: string, shares: number, price: number, total: number, date: string, status: string }
   * 
   * Response: { success: boolean }
   */
  addTrade: async (tradeData: any) => {
    try {
      const response = await api.post('/api/trades/history', tradeData);
      return response.data;
    } catch (error: any) {
      // If endpoint doesn't exist, return mock response
      if (error.response?.status === 404) {
        return { success: true, message: 'Trade added to history (mock mode)' };
      }
      throw error;
    }
  },
};

// User Settings API
export const userAPI = {
  /**
   * Fetch user settings from backend
   * 
   * Backend endpoint: GET /api/user/settings
   * 
   * Response: { settings: any }
   */
  getSettings: async () => {
    try {
      const response = await api.get('/api/user/settings');
      return response.data;
    } catch (error: any) {
      // If endpoint doesn't exist, return empty data
      if (error.response?.status === 404) {
        return { settings: {}, message: 'User settings API not available' };
      }
      throw error;
    }
  },

  /**
   * Save user settings to backend
   * 
   * Backend endpoint: PUT /api/user/settings
   * 
   * Payload: { settings: any }
   * 
   * Response: { success: boolean }
   */
  saveSettings: async (settings: any) => {
    try {
      const response = await api.put('/api/user/settings', settings);
      return response.data;
    } catch (error: any) {
      // If endpoint doesn't exist, return mock response
      if (error.response?.status === 404) {
        return { success: true, message: 'Settings saved (mock mode)' };
      }
      throw error;
    }
  },
};

// Educational API
export const educationalAPI = {
  /**
   * Fetch learning modules from backend
   * 
   * Backend endpoint: GET /api/education/modules
   * 
   * Response: { modules: Array<EducationalModule>, userProgress: any }
   */
  getModules: async () => {
    try {
      const response = await api.get('/api/education/modules');
      return response.data;
    } catch (error: any) {
      // If endpoint doesn't exist, return empty data
      if (error.response?.status === 404) {
        return { modules: [], userProgress: {}, message: 'Education API not available' };
      }
      throw error;
    }
  },

  /**
   * Fetch user progress from backend
   * 
   * Backend endpoint: GET /api/education/progress
   * 
   * Response: { progress: any }
   */
  getProgress: async () => {
    try {
      const response = await api.get('/api/education/progress');
      return response.data;
    } catch (error: any) {
      // If endpoint doesn't exist, return empty data
      if (error.response?.status === 404) {
        return { progress: {}, message: 'Education progress API not available' };
      }
      throw error;
    }
  },

  /**
   * Save user progress to backend
   * 
   * Backend endpoint: POST /api/education/progress
   * 
   * Payload: { moduleId: string, lessonId: string, completed: boolean }
   * 
   * Response: { success: boolean }
   */
  saveProgress: async (moduleId: string, lessonId: string, completed: boolean) => {
    try {
      const response = await api.post('/api/education/progress', {
        moduleId,
        lessonId,
        completed
      });
      return response.data;
    } catch (error: any) {
      // If endpoint doesn't exist, return mock response
      if (error.response?.status === 404) {
        return { success: true, message: 'Progress saved (mock mode)' };
      }
      throw error;
    }
  },
};