import { useState, useEffect } from 'react';
import { stockAPI } from '../services/api';
import { CheckCircle2, XCircle, AlertCircle, Loader2, Server, WifiOff } from 'lucide-react';

interface ServerStatusIndicatorProps {
  className?: string;
  showDetails?: boolean;
}

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'error' | 'checking';
  timestamp?: string;
  system?: {
    cpu_usage_percent?: number;
    memory_percent?: number;
    memory_available_gb?: number;
  };
  mcp_adapter?: {
    status?: string;
    error?: string;
  };
  models?: {
    available?: boolean;
    total_trained?: number;
  };
}

const ServerStatusIndicator = ({ className = '', showDetails = false }: ServerStatusIndicatorProps) => {
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking');
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [lastCheck, setLastCheck] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  const checkServerStatus = async () => {
    setConnectionStatus('checking');
    setError(null);

    try {
      // Check connection first (uses same endpoint as health check base)
      const connectionCheck = await stockAPI.checkConnection();
      
      if (!connectionCheck.connected) {
        setConnectionStatus('disconnected');
        setError(connectionCheck.error || 'Backend server is not reachable');
        setHealthStatus(null);
        setLastCheck(new Date());
        return;
      }

      // If connected, get health status (only if connection check passed)
      // This makes 2 requests total, but only every 2 minutes = ~1 request per minute
      try {
        const health = await stockAPI.health();
        setHealthStatus(health);
        setConnectionStatus('connected');
        setError(null);
      } catch (healthError: any) {
        // Connection works but health check failed - still mark as connected
        setConnectionStatus('connected');
        setError(healthError.message || 'Health check failed');
        setHealthStatus({
          status: 'error',
          timestamp: new Date().toISOString(),
        });
      }
      
      setLastCheck(new Date());
    } catch (err: any) {
      setConnectionStatus('disconnected');
      setError(err.message || 'Unable to connect to backend server');
      setHealthStatus(null);
      setLastCheck(new Date());
    }
  };

  useEffect(() => {
    // Initial check
    checkServerStatus();

    // Check every 120 seconds (2 minutes) to reduce API calls and avoid rate limits
    const interval = setInterval(() => {
      checkServerStatus();
    }, 120000);

    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return healthStatus?.status === 'healthy' ? (
          <CheckCircle2 className="w-4 h-4 text-green-400" />
        ) : (
          <AlertCircle className="w-4 h-4 text-yellow-400" />
        );
      case 'disconnected':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'checking':
        return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
      default:
        return <Server className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return healthStatus?.status === 'healthy' ? 'Live' : 'Degraded';
      case 'disconnected':
        return 'Offline';
      case 'checking':
        return 'Checking...';
      default:
        return 'Unknown';
    }
  };

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return healthStatus?.status === 'healthy' 
          ? 'bg-green-500/20 border-green-500/50 text-green-400' 
          : 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400';
      case 'disconnected':
        return 'bg-red-500/20 border-red-500/50 text-red-400';
      case 'checking':
        return 'bg-blue-500/20 border-blue-500/50 text-blue-400';
      default:
        return 'bg-gray-500/20 border-gray-500/50 text-gray-400';
    }
  };

  return (
    <div className={`${className}`}>
      <div
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all cursor-pointer hover:opacity-80 ${getStatusColor()}`}
        onClick={checkServerStatus}
        title={error || 'Click to refresh status'}
      >
        {getStatusIcon()}
        <span className="hidden sm:inline">{getStatusText()}</span>
        {connectionStatus === 'checking' && (
          <span className="hidden sm:inline ml-1">...</span>
        )}
      </div>

      {showDetails && connectionStatus === 'connected' && healthStatus && (
        <div className="mt-2 p-3 bg-slate-800/50 rounded-lg border border-slate-700 text-xs space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Status:</span>
            <span className={`font-semibold ${
              healthStatus.status === 'healthy' ? 'text-green-400' : 'text-yellow-400'
            }`}>
              {healthStatus.status?.toUpperCase()}
            </span>
          </div>
          
          {healthStatus.system && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">CPU:</span>
                <span className="text-gray-300">{healthStatus.system.cpu_usage_percent?.toFixed(1)}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Memory:</span>
                <span className="text-gray-300">
                  {healthStatus.system.memory_percent?.toFixed(1)}% 
                  {healthStatus.system.memory_available_gb && ` (${healthStatus.system.memory_available_gb.toFixed(1)} GB free)`}
                </span>
              </div>
            </>
          )}
          
          {healthStatus.mcp_adapter && (
            <div className="flex items-center justify-between">
              <span className="text-gray-400">MCP Adapter:</span>
              <span className={`${
                healthStatus.mcp_adapter.status === 'ready' ? 'text-green-400' : 'text-yellow-400'
              }`}>
                {healthStatus.mcp_adapter.status || 'unknown'}
              </span>
            </div>
          )}
          
          {healthStatus.models && (
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Models:</span>
              <span className="text-gray-300">
                {healthStatus.models.total_trained || 0} trained
              </span>
            </div>
          )}
          
          {lastCheck && (
            <div className="pt-2 mt-2 border-t border-slate-700 text-gray-500">
              Last check: {lastCheck.toLocaleTimeString()}
            </div>
          )}
        </div>
      )}

      {showDetails && error && connectionStatus === 'disconnected' && (
        <div className="mt-2 p-3 bg-red-900/20 rounded-lg border border-red-500/30 text-xs">
          <div className="flex items-start gap-2">
            <WifiOff className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-red-400 font-semibold mb-1">Connection Failed</p>
              <p className="text-red-300">{error}</p>
              <p className="text-red-400/70 mt-2 text-xs">
                Make sure the backend server is running:<br />
                <code className="bg-red-900/30 px-1 rounded">cd backend && python api_server.py</code>
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ServerStatusIndicator;


