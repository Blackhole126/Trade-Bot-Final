import { useState, useRef, useEffect } from 'react';
import { Bell, X, Check, Trash2, Settings } from 'lucide-react';
import { useNotifications } from '../contexts/NotificationContext';
import { useTheme } from '../contexts/ThemeContext';

const NotificationCenter = () => {
  const { notifications, unreadCount, markAsRead, markAllAsRead, deleteNotification, clearAll } = useNotifications();
  const { theme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const isLight = theme === 'light';
  const isSpace = theme === 'space';

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`relative p-2 rounded-lg transition-colors ${
          isLight
            ? 'text-gray-700 hover:bg-gray-100'
            : isSpace
              ? 'text-white/90 hover:bg-white/10'
              : 'text-gray-300 hover:bg-slate-800'
        }`}
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className={`absolute right-0 top-full mt-2 w-80 md:w-96 max-h-96 overflow-y-auto rounded-lg shadow-2xl z-50 ${
          isLight
            ? 'bg-white border border-gray-200'
            : isSpace
              ? 'bg-slate-900/95 backdrop-blur-md border border-purple-900/20'
              : 'bg-slate-800 border border-slate-700'
        }`}>
          <div className={`p-4 border-b ${
            isLight ? 'border-gray-200' : isSpace ? 'border-purple-900/20' : 'border-slate-700'
          }`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className={`font-semibold ${
                isLight ? 'text-gray-900' : 'text-white'
              }`}>
                Notifications
              </h3>
              <div className="flex items-center gap-2">
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className={`text-xs px-2 py-1 rounded transition-colors ${
                      isLight
                        ? 'text-blue-600 hover:bg-blue-50'
                        : 'text-blue-400 hover:bg-blue-500/20'
                    }`}
                  >
                    Mark all read
                  </button>
                )}
                <button
                  onClick={() => setIsOpen(false)}
                  className={`p-1 rounded transition-colors ${
                    isLight
                      ? 'text-gray-600 hover:bg-gray-100'
                      : 'text-gray-400 hover:bg-slate-700'
                  }`}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            {unreadCount > 0 && (
              <p className={`text-xs ${
                isLight ? 'text-gray-600' : 'text-gray-400'
              }`}>
                {unreadCount} unread notification{unreadCount !== 1 ? 's' : ''}
              </p>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-8 text-center">
                <Bell className={`w-12 h-12 mx-auto mb-2 ${
                  isLight ? 'text-gray-400' : 'text-gray-500'
                }`} />
                <p className={`text-sm ${
                  isLight ? 'text-gray-600' : 'text-gray-400'
                }`}>
                  No notifications
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-700">
                {notifications.map((notification) => (
                  <div
                    key={notification.id}
                    className={`p-3 hover:bg-slate-700/50 transition-colors cursor-pointer ${
                      !notification.read ? (isLight ? 'bg-blue-50' : 'bg-blue-500/10') : ''
                    }`}
                    onClick={() => {
                      if (!notification.read) {
                        markAsRead(notification.id);
                      }
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`flex-shrink-0 w-2 h-2 rounded-full mt-2 ${
                        !notification.read ? 'bg-blue-500' : 'bg-transparent'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <p className={`font-semibold text-sm ${
                              isLight ? 'text-gray-900' : 'text-white'
                            }`}>
                              {notification.title}
                            </p>
                            <p className={`text-xs mt-1 ${
                              isLight ? 'text-gray-600' : 'text-gray-400'
                            }`}>
                              {notification.message}
                            </p>
                            {notification.symbol && (
                              <span className={`inline-block mt-1 px-2 py-0.5 text-xs rounded ${
                                isLight
                                  ? 'bg-gray-100 text-gray-700'
                                  : 'bg-slate-700 text-gray-300'
                              }`}>
                                {notification.symbol}
                              </span>
                            )}
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteNotification(notification.id);
                            }}
                            className={`p-1 rounded transition-colors flex-shrink-0 ${
                              isLight
                                ? 'text-gray-600 hover:bg-gray-200'
                                : 'text-gray-400 hover:bg-slate-600'
                            }`}
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                        <p className={`text-xs mt-2 ${
                          isLight ? 'text-gray-500' : 'text-gray-500'
                        }`}>
                          {new Date(notification.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {notifications.length > 0 && (
            <div className={`p-3 border-t ${
              isLight ? 'border-gray-200' : isSpace ? 'border-purple-900/20' : 'border-slate-700'
            }`}>
              <button
                onClick={clearAll}
                className={`w-full text-xs px-3 py-2 rounded transition-colors ${
                  isLight
                    ? 'text-red-600 hover:bg-red-50'
                    : 'text-red-400 hover:bg-red-500/20'
                }`}
              >
                Clear all notifications
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default NotificationCenter;

