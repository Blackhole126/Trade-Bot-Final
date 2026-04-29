import { useState, useEffect } from 'react';
import { Activity, CheckCircle, XCircle, AlertCircle, RefreshCw, Server, Zap } from 'lucide-react';
import { stockAPI, authAPI, riskAPI, tradeAPI, alertAPI } from '../services/api';
import { config } from '../config';

interface EndpointTest {
  name: string;
  endpoint: string;
  method: string;
  status: 'pending' | 'success' | 'error' | 'testing';
  responseTime?: number;
  error?: string;
  response?: any;
}

const APIDebugger = () => {
  const [tests, setTests] = useState<EndpointTest[]>([]);
  const [testing, setTesting] = useState(false);
  const [backendUrl, setBackendUrl] = useState(config.API_BASE_URL);

  const endpoints: Omit<EndpointTest, 'status'>[] = [
    { name: 'Root Info', endpoint: '/', method: 'GET' },
    { name: 'Health Check', endpoint: '/tools/health', method: 'GET' },
    { name: 'Auth Status', endpoint: '/auth/status', method: 'GET' },
    { name: 'Predict', endpoint: '/tools/predict', method: 'POST' },
    { name: 'Scan All', endpoint: '/tools/scan_all', method: 'POST' },
    { name: 'Analyze', endpoint: '/tools/analyze', method: 'POST' },
    { name: 'Feedback', endpoint: '/tools/feedback', method: 'POST' },
    { name: 'Train RL', endpoint: '/tools/train_rl', method: 'POST' },
    { name: 'Fetch Data', endpoint: '/tools/fetch_data', method: 'POST' },
    { name: 'List Alerts', endpoint: '/api/alerts/list', method: 'GET' },
    { name: 'Risk Assess', endpoint: '/api/risk/assess', method: 'POST' },
  ];

  useEffect(() => {
    setTests(endpoints.map(e => ({ ...e, status: 'pending' })));
  }, []);

  const testEndpoint = async (test: EndpointTest): Promise<EndpointTest> => {
    const startTime = Date.now();
    
    try {
      let response;
      
      switch (test.endpoint) {
        case '/':
          response = await stockAPI.checkConnection();
          break;
        case '/tools/health':
          response = await stockAPI.health();
          break;
        case '/auth/status':
          response = await authAPI.checkStatus();
          break;
        case '/tools/predict':
          response = await stockAPI.predict(['AAPL'], 'intraday');
          break;
        case '/tools/scan_all':
          response = await stockAPI.scanAll(['AAPL', 'GOOGL'], 'intraday', 0.3);
          break;
        case '/tools/analyze':
          response = await stockAPI.analyze('AAPL', ['intraday'], 2.0, 1.0, 5.0);
          break;
        case '/tools/feedback':
          response = await stockAPI.feedback('AAPL', 'LONG', 'Test feedback', 5.0);
          break;
        case '/tools/train_rl':
          response = await stockAPI.trainRL('AAPL', 'intraday', 10, false);
          break;
        case '/tools/fetch_data':
          response = await stockAPI.fetchData(['AAPL'], '1mo', false, false);
          break;
        case '/api/alerts/list':
          response = await alertAPI.list();
          break;
        case '/api/risk/assess':
          response = await riskAPI.assess({
            symbol: 'AAPL',
            position_size: 100,
            entry_price: 150,
            stop_loss_price: 145,
            capital_at_risk_pct: 1
          });
          break;
        default:
          throw new Error('Unknown endpoint');
      }

      const responseTime = Date.now() - startTime;
      
      return {
        ...test,
        status: 'success',
        responseTime,
        response: response
      };
    } catch (error: any) {
      const responseTime = Date.now() - startTime;
      
      return {
        ...test,
        status: 'error',
        responseTime,
        error: error.message || 'Unknown error'
      };
    }
  };

  const runAllTests = async () => {
    setTesting(true);
    
    for (let i = 0; i < tests.length; i++) {
      setTests(prev => prev.map((t, idx) => 
        idx === i ? { ...t, status: 'testing' } : t
      ));
      
      const result = await testEndpoint(tests[i]);
      
      setTests(prev => prev.map((t, idx) => 
        idx === i ? result : t
      ));
      
      // Small delay between tests
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    setTesting(false);
  };

  const getStatusIcon = (status: EndpointTest['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-400" />;
      case 'testing':
        return <RefreshCw className="w-5 h-5 text-blue-400 animate-spin" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-400" />;
    }
  };

  const successCount = tests.filter(t => t.status === 'success').length;
  const errorCount = tests.filter(t => t.status === 'error').length;
  const avgResponseTime = tests
    .filter(t => t.responseTime)
    .reduce((sum, t) => sum + (t.responseTime || 0), 0) / tests.filter(t => t.responseTime).length;

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Server className="w-6 h-6 text-blue-400" />
          <div>
            <h2 className="text-xl font-bold text-white">API Integration Debugger</h2>
            <p className="text-sm text-gray-400">Backend: {backendUrl}</p>
          </div>
        </div>
        <button
          onClick={runAllTests}
          disabled={testing}
          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white rounded-lg font-semibold transition-colors flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${testing ? 'animate-spin' : ''}`} />
          {testing ? 'Testing...' : 'Run All Tests'}
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-slate-700/50 rounded-lg p-4">
          <div className="text-gray-400 text-sm mb-1">Total Endpoints</div>
          <div className="text-2xl font-bold text-white">{tests.length}</div>
        </div>
        <div className="bg-green-900/20 rounded-lg p-4">
          <div className="text-gray-400 text-sm mb-1">Success</div>
          <div className="text-2xl font-bold text-green-400">{successCount}</div>
        </div>
        <div className="bg-red-900/20 rounded-lg p-4">
          <div className="text-gray-400 text-sm mb-1">Errors</div>
          <div className="text-2xl font-bold text-red-400">{errorCount}</div>
        </div>
        <div className="bg-blue-900/20 rounded-lg p-4">
          <div className="text-gray-400 text-sm mb-1">Avg Response</div>
          <div className="text-2xl font-bold text-blue-400">
            {avgResponseTime ? `${avgResponseTime.toFixed(0)}ms` : '-'}
          </div>
        </div>
      </div>

      {/* Endpoint Tests */}
      <div className="space-y-2">
        {tests.map((test, idx) => (
          <div
            key={idx}
            className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/50"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 flex-1">
                {getStatusIcon(test.status)}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white">{test.name}</span>
                    <span className="text-xs px-2 py-0.5 bg-slate-600 rounded text-gray-300">
                      {test.method}
                    </span>
                  </div>
                  <div className="text-sm text-gray-400 font-mono">{test.endpoint}</div>
                </div>
              </div>
              {test.responseTime && (
                <div className="text-sm text-gray-400">
                  {test.responseTime}ms
                </div>
              )}
            </div>
            
            {test.error && (
              <div className="mt-3 p-3 bg-red-900/20 border border-red-700/50 rounded text-sm text-red-300">
                <strong>Error:</strong> {test.error}
              </div>
            )}
            
            {test.response && test.status === 'success' && (
              <details className="mt-3">
                <summary className="cursor-pointer text-sm text-blue-400 hover:text-blue-300">
                  View Response
                </summary>
                <pre className="mt-2 p-3 bg-slate-900 rounded text-xs text-gray-300 overflow-auto max-h-40">
                  {JSON.stringify(test.response, null, 2)}
                </pre>
              </details>
            )}
          </div>
        ))}
      </div>

      {/* Connection Tips */}
      <div className="mt-6 p-4 bg-blue-900/20 border border-blue-700/50 rounded-lg">
        <div className="flex items-start gap-3">
          <Zap className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-300">
            <strong>Integration Tips:</strong>
            <ul className="mt-2 space-y-1 list-disc list-inside">
              <li>Ensure backend is running: <code className="bg-slate-700 px-1 rounded">python api_server.py</code></li>
              <li>Check backend URL in config: <code className="bg-slate-700 px-1 rounded">{backendUrl}</code></li>
              <li>Verify CORS is enabled on backend</li>
              <li>Check browser console for detailed error messages</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default APIDebugger;
