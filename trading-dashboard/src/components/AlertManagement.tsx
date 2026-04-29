import React, { useState, useEffect } from 'react';
import { alertAPI } from '../services/api';
import { Alert, AlertCreateRequest, NewAlertType, ALERT_TYPE_LABELS, ALERT_TYPE_DESCRIPTIONS } from '../types/alerts';
import { Bell, X, Plus, Edit2, Trash2, Eye, EyeOff, Check, AlertCircle } from 'lucide-react';

interface AlertManagementProps {
  isDarkMode?: boolean;
  onAlertsLoaded?: (alerts: Alert[]) => void;
}

const AlertManagement: React.FC<AlertManagementProps> = ({ isDarkMode = false, onAlertsLoaded }) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState<AlertCreateRequest>({
    symbol: '',
    alert_type: 'price_above',
    value: undefined,
    enabled: true,
    notification_channels: ['browser'],
    description: ''
  });

  // Load alerts on mount
  useEffect(() => {
    loadAlerts();
  }, []);

  // Notify parent when alerts change
  useEffect(() => {
    if (onAlertsLoaded) {
      onAlertsLoaded(alerts);
    }
  }, [alerts, onAlertsLoaded]);

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const response = await alertAPI.list();
      if (response.success) {
        setAlerts(response.alerts || []);
      }
    } catch (err: any) {
      setError(`Failed to load alerts: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      // Validate form
      if (!formData.symbol.trim()) {
        throw new Error('Symbol is required');
      }

      // For price alerts, value is required
      if ((formData.alert_type === 'price_above' || formData.alert_type === 'price_below') && !formData.value) {
        throw new Error(`Value is required for ${formData.alert_type} alerts`);
      }

      if (editingId) {
        // Update existing alert
        const response = await alertAPI.update(editingId, formData);
        if (response.success) {
          setSuccess(`Alert updated successfully`);
          setEditingId(null);
          setFormData({
            symbol: '',
            alert_type: 'price_above',
            value: undefined,
            enabled: true,
            notification_channels: ['browser'],
            description: ''
          });
          setShowForm(false);
          loadAlerts();
        }
      } else {
        // Create new alert
        const response = await alertAPI.create(formData);
        if (response.success) {
          setSuccess(`Alert created for ${formData.symbol}`);
          setFormData({
            symbol: '',
            alert_type: 'price_above',
            value: undefined,
            enabled: true,
            notification_channels: ['browser'],
            description: ''
          });
          setShowForm(false);
          loadAlerts();
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to save alert');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (alert: Alert) => {
    setEditingId(alert.id);
    setFormData({
      symbol: alert.symbol,
      alert_type: alert.alert_type,
      value: alert.value,
      enabled: alert.enabled,
      notification_channels: alert.notification_channels as any,
      description: alert.description
    });
    setShowForm(true);
  };

  const handleDelete = async (alertId: string) => {
    if (!window.confirm('Are you sure you want to delete this alert?')) return;

    setError(null);
    try {
      const response = await alertAPI.delete(alertId);
      if (response.success) {
        setSuccess('Alert deleted successfully');
        loadAlerts();
      }
    } catch (err: any) {
      setError(`Failed to delete alert: ${err.message}`);
    }
  };

  const handleToggle = async (alert: Alert) => {
    try {
      const response = await alertAPI.update(alert.id, { enabled: !alert.enabled });
      if (response.success) {
        loadAlerts();
      }
    } catch (err: any) {
      setError(`Failed to toggle alert: ${err.message}`);
    }
  };

  const bgColor = isDarkMode ? 'bg-gray-900' : 'bg-white';
  const borderColor = isDarkMode ? 'border-gray-700' : 'border-gray-200';
  const textColor = isDarkMode ? 'text-gray-100' : 'text-gray-900';
  const inputBg = isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-300';
  const labelText = isDarkMode ? 'text-gray-300' : 'text-gray-700';

  return (
    <div className={`${bgColor} rounded-lg border ${borderColor} p-6 w-full max-w-4xl`}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Bell className={`w-6 h-6 ${isDarkMode ? 'text-yellow-400' : 'text-yellow-600'}`} />
          <h2 className={`text-2xl font-bold ${textColor}`}>Trading Alerts</h2>
        </div>
        <button
          onClick={() => {
            setShowForm(!showForm);
            setEditingId(null);
            setFormData({
              symbol: '',
              alert_type: 'price_above',
              value: undefined,
              enabled: true,
              notification_channels: ['browser'],
              description: ''
            });
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition ${
            isDarkMode
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-blue-500 hover:bg-blue-600 text-white'
          }`}
        >
          <Plus className="w-4 h-4" />
          New Alert
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className={`mb-4 p-4 rounded-lg flex items-start gap-3 ${
          isDarkMode ? 'bg-red-900/20 border border-red-700' : 'bg-red-50 border border-red-200'
        }`}>
          <AlertCircle className={`w-5 h-5 flex-shrink-0 ${isDarkMode ? 'text-red-400' : 'text-red-600'}`} />
          <p className={isDarkMode ? 'text-red-300' : 'text-red-700'}>{error}</p>
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div className={`mb-4 p-4 rounded-lg flex items-start gap-3 ${
          isDarkMode ? 'bg-green-900/20 border border-green-700' : 'bg-green-50 border border-green-200'
        }`}>
          <Check className={`w-5 h-5 flex-shrink-0 ${isDarkMode ? 'text-green-400' : 'text-green-600'}`} />
          <p className={isDarkMode ? 'text-green-300' : 'text-green-700'}>{success}</p>
        </div>
      )}

      {/* Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className={`mb-6 p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            {/* Symbol */}
            <div>
              <label className={`block text-sm font-medium ${labelText} mb-1`}>Symbol *</label>
              <input
                type="text"
                placeholder="e.g., RELIANCE.NS"
                value={formData.symbol}
                onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                className={`w-full px-3 py-2 border rounded-lg ${inputBg} ${textColor} placeholder-gray-500`}
              />
            </div>

            {/* Alert Type */}
            <div>
              <label className={`block text-sm font-medium ${labelText} mb-1`}>Alert Type *</label>
              <select
                value={formData.alert_type}
                onChange={(e) => setFormData({ ...formData, alert_type: e.target.value as NewAlertType })}
                className={`w-full px-3 py-2 border rounded-lg ${inputBg} ${textColor}`}
              >
                {Object.entries(ALERT_TYPE_LABELS).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
              <p className={`text-xs mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                {ALERT_TYPE_DESCRIPTIONS[formData.alert_type]}
              </p>
            </div>

            {/* Value */}
            {(formData.alert_type === 'price_above' || formData.alert_type === 'price_below' || formData.alert_type === 'confidence_high' || formData.alert_type === 'gain_loss') && (
              <div>
                <label className={`block text-sm font-medium ${labelText} mb-1`}>
                  {formData.alert_type === 'confidence_high' ? 'Confidence Threshold (%)' : formData.alert_type === 'gain_loss' ? 'Gain/Loss (%)' : 'Price (₹)'} *
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.value ?? ''}
                  onChange={(e) => setFormData({ ...formData, value: e.target.value ? parseFloat(e.target.value) : undefined })}
                  className={`w-full px-3 py-2 border rounded-lg ${inputBg} ${textColor}`}
                />
              </div>
            )}

            {/* Enabled */}
            <div>
              <label className={`block text-sm font-medium ${labelText} mb-1`}>Status</label>
              <select
                value={formData.enabled ? 'enabled' : 'disabled'}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.value === 'enabled' })}
                className={`w-full px-3 py-2 border rounded-lg ${inputBg} ${textColor}`}
              >
                <option value="enabled">✅ Enabled</option>
                <option value="disabled">❌ Disabled</option>
              </select>
            </div>
          </div>

          {/* Description */}
          <div className="mb-4">
            <label className={`block text-sm font-medium ${labelText} mb-1`}>Description</label>
            <textarea
              placeholder="Optional note about this alert..."
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={2}
              className={`w-full px-3 py-2 border rounded-lg ${inputBg} ${textColor} placeholder-gray-500 resize-none`}
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                loading
                  ? isDarkMode ? 'bg-gray-700 text-gray-400' : 'bg-gray-300 text-gray-500'
                  : isDarkMode ? 'bg-green-600 hover:bg-green-700 text-white' : 'bg-green-500 hover:bg-green-600 text-white'
              }`}
            >
              {loading ? 'Saving...' : editingId ? 'Update Alert' : 'Create Alert'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowForm(false);
                setEditingId(null);
                setFormData({
                  symbol: '',
                  alert_type: 'price_above',
                  value: undefined,
                  enabled: true,
                  notification_channels: ['browser'],
                  description: ''
                });
              }}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                isDarkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-gray-300 hover:bg-gray-400 text-gray-800'
              }`}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Alerts List */}
      <div>
        <h3 className={`text-lg font-semibold ${textColor} mb-4`}>
          {alerts.length === 0 ? 'No alerts yet' : `Active Alerts (${alerts.length})`}
        </h3>

        {loading && alerts.length === 0 && (
          <p className={isDarkMode ? 'text-gray-400' : 'text-gray-500'}>Loading alerts...</p>
        )}

        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-4 rounded-lg border ${borderColor} ${
                !alert.enabled ? (isDarkMode ? 'bg-gray-800/50' : 'bg-gray-100/50') : ''
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`font-semibold ${textColor}`}>{alert.symbol}</span>
                    <span className={`text-xs px-2 py-1 rounded ${
                      isDarkMode ? 'bg-blue-900/30 text-blue-300' : 'bg-blue-100 text-blue-700'
                    }`}>
                      {ALERT_TYPE_LABELS[alert.alert_type]}
                    </span>
                    {!alert.enabled && (
                      <span className={`text-xs px-2 py-1 rounded ${
                        isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-300 text-gray-700'
                      }`}>
                        Disabled
                      </span>
                    )}
                  </div>
                  {alert.value !== undefined && (
                    <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      Threshold: {alert.alert_type === 'confidence_high' || alert.alert_type === 'gain_loss' ? `${alert.value}%` : `₹${alert.value}`}
                    </p>
                  )}
                  {alert.description && (
                    <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>{alert.description}</p>
                  )}
                  {alert.last_triggered && (
                    <p className={`text-xs mt-2 ${isDarkMode ? 'text-green-400' : 'text-green-600'}`}>
                      Last triggered: {new Date(alert.last_triggered).toLocaleString()}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggle(alert)}
                    className={`p-2 rounded-lg transition ${
                      alert.enabled
                        ? isDarkMode ? 'bg-green-900/30 hover:bg-green-900/50 text-green-400' : 'bg-green-100 hover:bg-green-200 text-green-600'
                        : isDarkMode ? 'bg-gray-700 hover:bg-gray-600 text-gray-300' : 'bg-gray-300 hover:bg-gray-400 text-gray-700'
                    }`}
                    title={alert.enabled ? 'Disable' : 'Enable'}
                  >
                    {alert.enabled ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => handleEdit(alert)}
                    className={`p-2 rounded-lg transition ${
                      isDarkMode ? 'bg-blue-900/30 hover:bg-blue-900/50 text-blue-400' : 'bg-blue-100 hover:bg-blue-200 text-blue-600'
                    }`}
                    title="Edit"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(alert.id)}
                    className={`p-2 rounded-lg transition ${
                      isDarkMode ? 'bg-red-900/30 hover:bg-red-900/50 text-red-400' : 'bg-red-100 hover:bg-red-200 text-red-600'
                    }`}
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AlertManagement;
