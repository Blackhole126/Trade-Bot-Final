import { PriceAlert, PredictionAlert, AppNotification } from '../types/alerts';

const STORAGE_KEYS = {
  PRICE_ALERTS: 'price_alerts',
  PREDICTION_ALERTS: 'prediction_alerts',
  NOTIFICATIONS: 'notifications',
  NOTIFICATION_SETTINGS: 'notification_settings',
};

export interface NotificationSettings {
  browserNotifications: boolean;
  priceAlerts: boolean;
  predictionAlerts: boolean;
  stopLossAlerts: boolean;
  systemNotifications: boolean;
}

const defaultSettings: NotificationSettings = {
  browserNotifications: true,
  priceAlerts: true,
  predictionAlerts: true,
  stopLossAlerts: true,
  systemNotifications: true,
};

// Price Alerts
export const priceAlertsService = {
  getAll: (): PriceAlert[] => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.PRICE_ALERTS);
      if (!stored) return [];
      const alerts = JSON.parse(stored);
      return alerts.map((a: any) => ({
        ...a,
        createdAt: new Date(a.createdAt),
        triggeredAt: a.triggeredAt ? new Date(a.triggeredAt) : undefined,
      }));
    } catch {
      return [];
    }
  },

  add: (alert: Omit<PriceAlert, 'id' | 'createdAt' | 'triggeredAt' | 'notificationSent'>): PriceAlert => {
    const alerts = priceAlertsService.getAll();
    const newAlert: PriceAlert = {
      ...alert,
      id: `price_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`,
      createdAt: new Date(),
      triggeredAt: undefined,
      notificationSent: false,
    };
    alerts.push(newAlert);
    localStorage.setItem(STORAGE_KEYS.PRICE_ALERTS, JSON.stringify(alerts));
    return newAlert;
  },

  update: (id: string, updates: Partial<PriceAlert>): PriceAlert | null => {
    const alerts = priceAlertsService.getAll();
    const index = alerts.findIndex(a => a.id === id);
    if (index === -1) return null;
    alerts[index] = { ...alerts[index], ...updates };
    localStorage.setItem(STORAGE_KEYS.PRICE_ALERTS, JSON.stringify(alerts));
    return alerts[index];
  },

  delete: (id: string): boolean => {
    const alerts = priceAlertsService.getAll();
    const filtered = alerts.filter(a => a.id !== id);
    localStorage.setItem(STORAGE_KEYS.PRICE_ALERTS, JSON.stringify(filtered));
    return filtered.length < alerts.length;
  },

  checkAlerts: (symbol: string, currentPrice: number, previousPrice?: number): PriceAlert[] => {
    const alerts = priceAlertsService.getAll();
    const triggered: PriceAlert[] = [];

    alerts.forEach(alert => {
      if (!alert.isActive || alert.symbol !== symbol) return;

      let shouldTrigger = false;

      if (alert.type === 'above' && alert.targetPrice && currentPrice >= alert.targetPrice) {
        shouldTrigger = true;
      } else if (alert.type === 'below' && alert.targetPrice && currentPrice <= alert.targetPrice) {
        shouldTrigger = true;
      } else if (alert.type === 'change' && alert.changePercent && previousPrice) {
        const changePercent = ((currentPrice - previousPrice) / previousPrice) * 100;
        if (Math.abs(changePercent) >= Math.abs(alert.changePercent!)) {
          shouldTrigger = true;
        }
      }

      if (shouldTrigger && !alert.notificationSent) {
        triggered.push(alert);
        priceAlertsService.update(alert.id, {
          triggeredAt: new Date(),
          notificationSent: true,
          isActive: false,
        });
      }
    });

    return triggered;
  },
};

// Prediction Alerts
export const predictionAlertsService = {
  getAll: (): PredictionAlert[] => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.PREDICTION_ALERTS);
      if (!stored) return [];
      const alerts = JSON.parse(stored);
      return alerts.map((a: any) => ({
        ...a,
        createdAt: new Date(a.createdAt),
        triggeredAt: a.triggeredAt ? new Date(a.triggeredAt) : undefined,
      }));
    } catch {
      return [];
    }
  },

  add: (alert: Omit<PredictionAlert, 'id' | 'createdAt' | 'triggeredAt'>): PredictionAlert => {
    const alerts = predictionAlertsService.getAll();
    const newAlert: PredictionAlert = {
      ...alert,
      id: `pred_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`,
      createdAt: new Date(),
      triggeredAt: undefined,
    };
    alerts.push(newAlert);
    localStorage.setItem(STORAGE_KEYS.PREDICTION_ALERTS, JSON.stringify(alerts));
    return newAlert;
  },

  update: (id: string, updates: Partial<PredictionAlert>): PredictionAlert | null => {
    const alerts = predictionAlertsService.getAll();
    const index = alerts.findIndex(a => a.id === id);
    if (index === -1) return null;
    alerts[index] = { ...alerts[index], ...updates };
    localStorage.setItem(STORAGE_KEYS.PREDICTION_ALERTS, JSON.stringify(alerts));
    return alerts[index];
  },

  delete: (id: string): boolean => {
    const alerts = predictionAlertsService.getAll();
    const filtered = alerts.filter(a => a.id !== id);
    localStorage.setItem(STORAGE_KEYS.PREDICTION_ALERTS, JSON.stringify(filtered));
    return filtered.length < alerts.length;
  },

  checkAlerts: (symbol: string, currentAction: 'LONG' | 'SHORT' | 'HOLD', previousAction?: 'LONG' | 'SHORT' | 'HOLD'): PredictionAlert[] => {
    const alerts = predictionAlertsService.getAll();
    const triggered: PredictionAlert[] = [];

    alerts.forEach(alert => {
      if (!alert.isActive || alert.symbol !== symbol) return;
      if (alert.action !== currentAction && (!previousAction || alert.previousAction !== previousAction)) {
        triggered.push(alert);
        predictionAlertsService.update(alert.id, {
          triggeredAt: new Date(),
          isActive: false,
        });
      }
    });

    return triggered;
  },
};

// Notifications
export const notificationsService = {
  getAll: (): AppNotification[] => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.NOTIFICATIONS);
      if (!stored) return [];
      const notifications = JSON.parse(stored);
      return notifications.map((n: any) => ({
        ...n,
        timestamp: new Date(n.timestamp),
      }));
    } catch {
      return [];
    }
  },

  add: (notification: Omit<AppNotification, 'id' | 'timestamp' | 'read'>): AppNotification => {
    const notifications = notificationsService.getAll();
    const newNotification: AppNotification = {
      ...notification,
      id: `notif_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`,
      timestamp: new Date(),
      read: false,
    };
    notifications.unshift(newNotification); // Add to beginning
    // Keep only last 100 notifications
    const limited = notifications.slice(0, 100);
    localStorage.setItem(STORAGE_KEYS.NOTIFICATIONS, JSON.stringify(limited));
    
    // Send browser notification if enabled
    const settings = notificationSettingsService.get();
    if (settings.browserNotifications && 'Notification' in window && Notification.permission === 'granted') {
      new Notification(newNotification.title, {
        body: newNotification.message,
        icon: '/jarvis-logo.png',
        tag: newNotification.id,
      });
    }
    
    return newNotification;
  },

  markAsRead: (id: string): boolean => {
    const notifications = notificationsService.getAll();
    const index = notifications.findIndex(n => n.id === id);
    if (index === -1) return false;
    notifications[index].read = true;
    localStorage.setItem(STORAGE_KEYS.NOTIFICATIONS, JSON.stringify(notifications));
    return true;
  },

  markAllAsRead: (): void => {
    const notifications = notificationsService.getAll();
    notifications.forEach(n => n.read = true);
    localStorage.setItem(STORAGE_KEYS.NOTIFICATIONS, JSON.stringify(notifications));
  },

  delete: (id: string): boolean => {
    const notifications = notificationsService.getAll();
    const filtered = notifications.filter(n => n.id !== id);
    localStorage.setItem(STORAGE_KEYS.NOTIFICATIONS, JSON.stringify(filtered));
    return filtered.length < notifications.length;
  },

  clearAll: (): void => {
    localStorage.removeItem(STORAGE_KEYS.NOTIFICATIONS);
  },

  getUnreadCount: (): number => {
    return notificationsService.getAll().filter(n => !n.read).length;
  },
};

// Notification Settings
export const notificationSettingsService = {
  get: (): NotificationSettings => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.NOTIFICATION_SETTINGS);
      if (!stored) return defaultSettings;
      return { ...defaultSettings, ...JSON.parse(stored) };
    } catch {
      return defaultSettings;
    }
  },

  update: (settings: Partial<NotificationSettings>): NotificationSettings => {
    const current = notificationSettingsService.get();
    const updated = { ...current, ...settings };
    localStorage.setItem(STORAGE_KEYS.NOTIFICATION_SETTINGS, JSON.stringify(updated));
    
    // Request browser notification permission if enabling
    if (updated.browserNotifications && 'Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
    
    return updated;
  },
};

// Request browser notification permission
export const requestNotificationPermission = async (): Promise<boolean> => {
  if (!('Notification' in window)) {
    return false;
  }
  
  if (Notification.permission === 'granted') {
    return true;
  }
  
  if (Notification.permission === 'default') {
    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }
  
  return false;
};

