import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import APIDebugger from '../components/APIDebugger';
import { Activity, Server, Wifi, WifiOff, Database, Cpu, HardDrive } from 'lucide-react';
import { stockAPI } from '../services/api';
import { config } from '../config';

const DebugPage = () => {
  const [connectionStatus, setConnectionStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  const [healthData, setHealthData] = useState<any>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  useEffect(() => {
    checkConnection();
    
    if (autoRefresh) {
      const interval = setInterval(checkConnection, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const checkConnection = async () => {
    setConnectionStatus('checking');
    try {
      const result = await stockAPI.checkConnection();
      setConnectionStatus(result.connected ? 'connected' : 'disconnected');
      
      // Fetch health data if connected
      if (result.connected) {
        try {
          const health = await stockAPI.health();
          setHealthData(health);
        } catch (error) {
          console.error('Health check failed:', error);
        }
      }
    } catch (error) {
      setConnectionStatus('disconnected');
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">System Diagnostics</h1>
          <p className="text-gray-400 text-sm">
            Monitor backend connection, test API endpoints, and view system health
          </p>
        </div>

        {/* Connection Status Card */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              {connectionStatus === 'connected' ? (
                <Wifi className="w-6 h-6 text-green-400" />
              ) : connectionStatus === 'disconnected' ? (
                <WifiOff className="w-6 h-6 text-red-400" />
              ) : (
                <Activity className="w-6 h-6 text-yellow-400 animate-pulse" />
              )}
              <div>
                <h2 className="text-lg font-semibold text-white">Backend Connection</h2>
                <p className="text-sm text-gray-400">{config.API_BASE_URL}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-gray-400">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="rounded"
                />
                Auto-refresh
              </label>
              <button
                onClick={checkConnection}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-semibold transition-colors"
              >
                Refresh
              </button>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className={`p-4 rounded-lg ${
              connectionStatus === 'connected' ? 'bg-green-900/20 border border-green-700/50' :
              connectionStatus === 'disconnected' ? 'bg-red-900/20 border border-red-700/50' :
              'bg-yellow-900/20 border border-yellow-700/50'
            }`}>
              <div className="text-sm text-gray-400 mb-1">Status</div>
              <div className={`text-lg font-bold ${
                connectionStatus === 'connected' ? 'text-green-400' :
                connectionStatus === 'disconnected' ? 'text-red-400' :
                'text-yellow-400'
              }`}>
                {connectionStatus === 'connected' ? 'Connected' :
                 connectionStatus === 'disconnected' ? 'Disconnected' :
                 'Checking...'}
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-700/50">
              <div className="text-sm text-gray-400 mb-1">Backend URL</div>
              <div className="text-sm font-mono text-white truncate">
                {config.API_BASE_URL}
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-700/50">
              <div className="text-sm text-gray-400 mb-1">Environment</div>
              <div className="text-sm font-semibold text-white">
                {import.meta.env.DEV ? 'Development' : 'Production'}
              </div>
            </div>
          </div>
        </div>

        {/* System Health */}
        {healthData && (
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
            <div className="flex items-center gap-3 mb-4">
              <Server className="w-6 h-6 text-blue-400" />
              <h2 className="text-lg font-semibold text-white">System Health</h2>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-700/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Cpu className="w-4 h-4 text-blue-400" />
                  <div className="text-sm text-gray-400">CPU Usage</div>
                </div>
                <div className="text-2xl font-bold text-white">
                  {healthData.system?.cpu_usage_percent?.toFixed(1)}%
                </div>
              </div>

              <div className="bg-slate-700/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Database className="w-4 h-4 text-green-400" />
                  <div className="text-sm text-gray-400">Memory</div>
                </div>
                <div className="text-2xl font-bold text-white">
                  {healthData.system?.memory_percent?.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {healthData.system?.memory_used_gb?.toFixed(1)} / {healthData.system?.memory_total_gb?.toFixed(1)} GB
                </div>
              </div>

              <div className="bg-slate-700/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <HardDrive className="w-4 h-4 text-purple-400" />
                  <div className="text-sm text-gray-400">Disk</div>
                </div>
                <div className="text-2xl font-bold text-white">
                  {healthData.system?.disk_percent?.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {healthData.system?.disk_free_gb?.toFixed(1)} GB free
                </div>
              </div>

              <div className="bg-slate-700/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="w-4 h-4 text-yellow-400" />
                  <div className="text-sm text-gray-400">Models</div>
                </div>
                <div className="text-2xl font-bold text-white">
                  {healthData.models?.total_trained || 0}
                </div>
                <div className="text-xs text-gray-400 mt-1">Trained models</div>
              </div>
            </div>
          </div>
        )}

        {/* API Debugger */}
        <APIDebugger />

        {/* Troubleshooting Guide */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Troubleshooting Guide</h2>
          
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-white mb-2">Backend Not Running</h3>
              <div className="text-sm text-gray-400 space-y-1">
                <p>1. Navigate to backend directory:</p>
                <code className="block bg-slate-900 p-2 rounded font-mono text-xs">
                  cd "d:\blackhole projects\blackhole-infevers trade\Multi-Asset Trading Dashboard\backend"
                </code>
                <p className="mt-2">2. Start the backend server:</p>
                <code className="block bg-slate-900 p-2 rounded font-mono text-xs">
                  python api_server.py
                </code>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-white mb-2">Connection Refused</h3>
              <div className="text-sm text-gray-400">
                <p>• Verify backend is running on port 8000</p>
                <p>• Check firewall settings</p>
                <p>• Ensure no other service is using port 8000</p>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-white mb-2">CORS Errors</h3>
              <div className="text-sm text-gray-400">
                <p>• Backend CORS is configured for all origins (*)</p>
                <p>• Check browser console for specific CORS errors</p>
                <p>• Verify backend is running with correct CORS middleware</p>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-white mb-2">Slow Response Times</h3>
              <div className="text-sm text-gray-400">
                <p>• First prediction request trains models (60-90 seconds)</p>
                <p>• Subsequent requests use cached models (faster)</p>
                <p>• Check system resources (CPU, Memory)</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default DebugPage;
