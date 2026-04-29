import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { AppNotification } from '../types/alerts';
import { notificationsService, notificationSettingsService, NotificationSettings } from '../services/alertsService';

interface NotificationContextType {
  notifications: AppNotification[];
  unreadCount: number;
  settings: NotificationSettings;
  addNotification: (notification: Omit<AppNotification, 'id' | 'timestamp' | 'read'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  deleteNotification: (id: string) => void;
  clearAll: () => void;
  updateSettings: (settings: Partial<NotificationSettings>) => void;
  refreshNotifications: () => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [settings, setSettings] = useState<NotificationSettings>(notificationSettingsService.get());

  const refreshNotifications = useCallback(() => {
    const all = notificationsService.getAll();
    setNotifications(all);
  }, []);

  useEffect(() => {
    refreshNotifications();
    
    // Refresh every 30 seconds to check for new notifications (conservative - doesn't make API calls)
    // This only reads from localStorage, so it's safe to refresh frequently
    const interval = setInterval(refreshNotifications, 30000);
    return () => clearInterval(interval);
  }, [refreshNotifications]);

  const addNotification = useCallback((notification: Omit<AppNotification, 'id' | 'timestamp' | 'read'>) => {
    const newNotif = notificationsService.add(notification);
    refreshNotifications();
    return newNotif;
  }, [refreshNotifications]);

  const markAsRead = useCallback((id: string) => {
    notificationsService.markAsRead(id);
    refreshNotifications();
  }, [refreshNotifications]);

  const markAllAsRead = useCallback(() => {
    notificationsService.markAllAsRead();
    refreshNotifications();
  }, [refreshNotifications]);

  const deleteNotification = useCallback((id: string) => {
    notificationsService.delete(id);
    refreshNotifications();
  }, [refreshNotifications]);

  const clearAll = useCallback(() => {
    notificationsService.clearAll();
    refreshNotifications();
  }, [refreshNotifications]);

  const updateSettings = useCallback((newSettings: Partial<NotificationSettings>) => {
    const updated = notificationSettingsService.update(newSettings);
    setSettings(updated);
  }, []);

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        settings,
        addNotification,
        markAsRead,
        markAllAsRead,
        deleteNotification,
        clearAll,
        updateSettings,
        refreshNotifications,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
};

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within NotificationProvider');
  }
  
  return {
    showNotification: (type: 'success' | 'error' | 'warning' | 'info', title: string, message: string) => {
      // Map generic notification types to AppNotification types
      let mappedType: 'price' | 'prediction' | 'stop-loss' | 'system' = 'system';
      if (type === 'success' || type === 'info') {
        mappedType = 'system';
      } else if (type === 'warning') {
        mappedType = 'stop-loss';
      } else if (type === 'error') {
        mappedType = 'system';
      }
      
      context.addNotification({
        type: mappedType,
        title,
        message,
      });
    },
  };
};

