import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Bell, Plus, X, Trash2, AlertCircle, Loader2 } from 'lucide-react';
import { requestNotificationPermission } from '../services/alertsService';
import { useNotifications } from '../contexts/NotificationContext';
import SymbolAutocomplete from '../components/SymbolAutocomplete';
import { LocalStorageWarning } from '../components/LocalStorageWarning';

interface BackendAlert {
  id: string;
  symbol: string;
  alert_type: string;
  value?: number;
  enabled: boolean;
  created_at: string;
  triggered_at?: string;
  description?: string;
}

const AlertsPage = () => {
  const { addNotification } = useNotifications();
  const [alerts, setAlerts] = useState<BackendAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPriceAlertModal, setShowPriceAlertModal] = useState(false);
  const [showPredictionAlertModal, setShowPredictionAlertModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newPriceAlert, setNewPriceAlert] = useState({
    symbol: '',
    type: 'above' as 'above' | 'below',
    targetPrice: '',
  });
  const [newPredictionAlert, setNewPredictionAlert] = useState({
    symbol: '',
    action: 'LONG' as 'LONG' | 'SHORT' | 'HOLD',
  });
  const [browserNotificationPermission, setBrowserNotificationPermission] = useState<NotificationPermission>('default');

  useEffect(() => {
    loadAlerts();
    checkNotificationPermission();
  }, []);

  const loadAlerts = async () => {
    setLoading(true);
    setError(null);
    try {
      // Load from localStorage (backend does not support alerts)
      const stored = localStorage.getItem('alerts');
      setAlerts(stored ? JSON.parse(stored) : []);
    } catch (err: any) {
      setError('Failed to load alerts from local storage');
    } finally {
      setLoading(false);
    }
  };

  const checkNotificationPermission = async () => {
    if ('Notification' in window) {
      setBrowserNotificationPermission(Notification.permission);
    }
  };

  const handleRequestPermission = async () => {
    const granted = await requestNotificationPermission();
    if (granted) {
      setBrowserNotificationPermission('granted');
      addNotification({
        type: 'system',
        title: 'Notifications Enabled',
        message: 'You will now receive browser notifications for your alerts.',
      });
    }
  };

  const handleAddPriceAlert = async () => {
    if (!newPriceAlert.symbol) {
      setError('Please enter a symbol');
      return;
    }

    if (!newPriceAlert.targetPrice) {
      setError('Please enter a target price');
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const alertType = newPriceAlert.type === 'above' ? 'price_above' : 'price_below';
      const newAlert: BackendAlert = {
        id: Date.now().toString(),
        symbol: newPriceAlert.symbol.toUpperCase(),
        alert_type: alertType,
        value: parseFloat(newPriceAlert.targetPrice),
        enabled: true,
        created_at: new Date().toISOString(),
        description: `Price ${newPriceAlert.type} ${newPriceAlert.targetPrice}`
      };

      const updated = [...alerts, newAlert];
      localStorage.setItem('alerts', JSON.stringify(updated));
      setAlerts(updated);

      addNotification({
        type: 'price',
        title: 'Alert Created',
        message: `Alert set for ${newPriceAlert.symbol} ${newPriceAlert.type} ${newPriceAlert.targetPrice}`,
        symbol: newPriceAlert.symbol,
      });

      setNewPriceAlert({ symbol: '', type: 'above', targetPrice: '' });
      setShowPriceAlertModal(false);
    } catch (err: any) {
      setError(err.message || 'Failed to create alert');
    } finally {
      setCreating(false);
    }
  };

  const handleAddPredictionAlert = async () => {
    if (!newPredictionAlert.symbol) {
      setError('Please enter a symbol');
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const newAlert: BackendAlert = {
        id: Date.now().toString(),
        symbol: newPredictionAlert.symbol.toUpperCase(),
        alert_type: 'prediction_change',
        value: 0,
        enabled: true,
        created_at: new Date().toISOString(),
        description: `Prediction changes to ${newPredictionAlert.action}`
      };

      const updated = [...alerts, newAlert];
      localStorage.setItem('alerts', JSON.stringify(updated));
      setAlerts(updated);

      addNotification({
        type: 'prediction',
        title: 'Alert Created',
        message: `Alert set for ${newPredictionAlert.symbol} when prediction changes to ${newPredictionAlert.action}`,
        symbol: newPredictionAlert.symbol,
      });

      setNewPredictionAlert({ symbol: '', action: 'LONG' });
      setShowPredictionAlertModal(false);
    } catch (err: any) {
      setError(err.message || 'Failed to create alert');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteAlert = async (id: string) => {
    if (!confirm('Are you sure you want to delete this alert?')) return;

    setError(null);
    try {
      const updated = alerts.filter(a => a.id !== id);
      localStorage.setItem('alerts', JSON.stringify(updated));
      setAlerts(updated);
      addNotification({
        type: 'system',
        title: 'Alert Deleted',
        message: 'Alert removed successfully',
      });
    } catch (err: any) {
      setError(err.message || 'Failed to delete alert');
    }
  };

  const handleToggleAlert = async (id: string) => {
    const alert = alerts.find(a => a.id === id);
    if (!alert) return;

    setError(null);
    try {
      const updated = alerts.map(a => 
        a.id === id ? { ...a, enabled: !a.enabled } : a
      );
      localStorage.setItem('alerts', JSON.stringify(updated));
      setAlerts(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to update alert');
    }
  };

  return (
    <Layout>
      <div className="space-y-4">
        <LocalStorageWarning feature="Alerts" />
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">Alerts & Notifications</h1>
            <p className="text-gray-400 text-sm">Manage your price and prediction alerts</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowPriceAlertModal(true)}
              className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Price Alert
            </button>
            <button
              onClick={() => setShowPredictionAlertModal(true)}
              className="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Prediction Alert
            </button>
          </div>
        </div>

        {/* Browser Notification Permission */}
        {browserNotificationPermission !== 'granted' && (
          <div className="bg-yellow-900/30 border border-yellow-500/50 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-yellow-400 font-semibold mb-1">Enable Browser Notifications</p>
                <p className="text-yellow-300 text-sm mb-3">
                  Allow browser notifications to receive alerts even when the dashboard is not open.
                </p>
                <button
                  onClick={handleRequestPermission}
                  className="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white rounded-lg text-sm font-semibold transition-colors"
                >
                  Enable Notifications
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-red-400 font-semibold">Error</p>
                <p className="text-red-300 text-sm">{error}</p>
              </div>
              <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* All Alerts */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <div className="p-4 border-b border-slate-700">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Bell className="w-5 h-5 text-blue-400" />
              All Alerts ({alerts.length})
            </h2>
          </div>
          {loading ? (
            <div className="p-8 text-center text-gray-400">
              <Loader2 className="w-8 h-8 mx-auto mb-3 animate-spin" />
              <p>Loading alerts from backend...</p>
            </div>
          ) : alerts.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              <Bell className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No alerts set</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-700">
              {alerts.map((alert) => (
                <div key={alert.id} className="p-4 hover:bg-slate-700/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-white font-bold text-lg">{alert.symbol}</span>
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          alert.alert_type === 'price_above' ? 'bg-green-500/20 text-green-400' :
                          alert.alert_type === 'price_below' ? 'bg-red-500/20 text-red-400' :
                          'bg-purple-500/20 text-purple-400'
                        }`}>
                          {alert.alert_type.replace('_', ' ').toUpperCase()}
                        </span>
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          alert.enabled
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-gray-500/20 text-gray-400'
                        }`}>
                          {alert.enabled ? 'Active' : 'Inactive'}
                        </span>
                        {alert.triggered_at && (
                          <span className="px-2 py-1 rounded text-xs font-semibold bg-blue-500/20 text-blue-400">
                            Triggered
                          </span>
                        )}
                      </div>
                      <p className="text-gray-400 text-sm">
                        {alert.description || `${alert.alert_type} at ${alert.value}`}
                      </p>
                      <p className="text-gray-500 text-xs mt-1">
                        Created {new Date(alert.created_at).toLocaleString()}
                        {alert.triggered_at && ` • Triggered ${new Date(alert.triggered_at).toLocaleString()}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleToggleAlert(alert.id)}
                        className={`px-3 py-1.5 rounded text-sm transition-colors ${
                          alert.enabled
                            ? 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30'
                            : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                        }`}
                      >
                        {alert.enabled ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        onClick={() => handleDeleteAlert(alert.id)}
                        className="p-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Add Price Alert Modal */}
        {showPriceAlertModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-white">Add Price Alert</h3>
                <button
                  onClick={() => setShowPriceAlertModal(false)}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
                  <SymbolAutocomplete
                    value={newPriceAlert.symbol}
                    onChange={(symbol) => setNewPriceAlert({ ...newPriceAlert, symbol })}
                    placeholder="e.g., AAPL"
                    className="px-4 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Alert Type</label>
                  <select
                    value={newPriceAlert.type}
                    onChange={(e) => setNewPriceAlert({ ...newPriceAlert, type: e.target.value as any })}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="above">Price goes above</option>
                    <option value="below">Price goes below</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Target Price</label>
                  <input
                    type="number"
                    value={newPriceAlert.targetPrice}
                    onChange={(e) => setNewPriceAlert({ ...newPriceAlert, targetPrice: e.target.value })}
                    placeholder="0.00"
                    step="0.01"
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={handleAddPriceAlert}
                    disabled={creating}
                    className="flex-1 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
                  >
                    {creating && <Loader2 className="w-4 h-4 animate-spin" />}
                    {creating ? 'Creating...' : 'Create Alert'}
                  </button>
                  <button
                    onClick={() => setShowPriceAlertModal(false)}
                    className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-semibold transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Add Prediction Alert Modal */}
        {showPredictionAlertModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-white">Add Prediction Alert</h3>
                <button
                  onClick={() => setShowPredictionAlertModal(false)}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
                  <SymbolAutocomplete
                    value={newPredictionAlert.symbol}
                    onChange={(symbol) => setNewPredictionAlert({ ...newPredictionAlert, symbol })}
                    placeholder="e.g., AAPL"
                    className="px-4 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Alert When Prediction Changes To</label>
                  <select
                    value={newPredictionAlert.action}
                    onChange={(e) => setNewPredictionAlert({ ...newPredictionAlert, action: e.target.value as any })}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="LONG">LONG (Buy)</option>
                    <option value="SHORT">SHORT (Sell)</option>
                    <option value="HOLD">HOLD</option>
                  </select>
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={handleAddPredictionAlert}
                    disabled={creating}
                    className="flex-1 px-4 py-2 bg-purple-500 hover:bg-purple-600 disabled:bg-purple-400 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
                  >
                    {creating && <Loader2 className="w-4 h-4 animate-spin" />}
                    {creating ? 'Creating...' : 'Create Alert'}
                  </button>
                  <button
                    onClick={() => setShowPredictionAlertModal(false)}
                    className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-semibold transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default AlertsPage;




