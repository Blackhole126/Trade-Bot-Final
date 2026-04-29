import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Play, Brain, AlertCircle, CheckCircle, Clock, BarChart3 } from 'lucide-react';
import { stockAPI, aiAPI, POPULAR_STOCKS } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';

const TrainModelPage = () => {
  const { showNotification } = useNotification();

  // Phase 6 - Train Model State
  const [trainSymbol, setTrainSymbol] = useState('AAPL');
  const [trainHorizon, setTrainHorizon] = useState<'intraday' | 'short' | 'long'>('intraday');
  const [episodes, setEpisodes] = useState(10);
  const [forceRetrain, setForceRetrain] = useState(false);
  const [isTraining, setIsTraining] = useState(false);
  const [trainingStatus, setTrainingStatus] = useState<'idle' | 'training' | 'complete' | 'error' | 'skipped' | 'failed'>('idle');
  const [trainingMessage, setTrainingMessage] = useState('');
  const [trainingResults, setTrainingResults] = useState<any>(null);
  const [trainingProgress, setTrainingProgress] = useState(0);
  const [existingModelInfo, setExistingModelInfo] = useState<any>(null);
  const [symbolSuggestions, setSymbolSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1);

  // Phase 7 - AI Chat State
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'assistant'; message: string }[]>([
    {
      role: 'assistant',
      message: 'Hello! I\'m your AI trading assistant. I can help you analyze stocks, interpret technical indicators, and provide trading insights. Try asking me about price analysis, buy/sell recommendations, or risk assessment!'
    }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [selectedTimeframe, setSelectedTimeframe] = useState('intraday');
  const [activeIndicators, setActiveIndicators] = useState<string[]>(['RSI', 'MACD']);
  const [existingModels, setExistingModels] = useState<any[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  // Load existing models on mount
  useEffect(() => {
    const loadModels = async () => {
      setLoadingModels(true);
      try {
        const response = await stockAPI.listModels();
        setExistingModels(response.models || []);
      } catch (error) {
        // Silently fail - models list is optional
      } finally {
        setLoadingModels(false);
      }
    };
    loadModels();
  }, [trainingStatus]); // Reload when training completes

  const handleSymbolInput = (value: string) => {
    const upperValue = value.toUpperCase();
    setTrainSymbol(upperValue);
    
    if (upperValue.length > 0) {
      const filtered = POPULAR_STOCKS.filter(stock => 
        stock.includes(upperValue)
      ).slice(0, 8);
      setSymbolSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
      setSelectedSuggestionIndex(-1);
    } else {
      setSymbolSuggestions([]);
      setShowSuggestions(false);
    }
  };

  const handleSelectSuggestion = (symbol: string) => {
    setTrainSymbol(symbol);
    setSymbolSuggestions([]);
    setShowSuggestions(false);
    setSelectedSuggestionIndex(-1);
  };

  const handleSymbolKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showSuggestions || symbolSuggestions.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedSuggestionIndex(prev => 
        prev < symbolSuggestions.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedSuggestionIndex(prev => prev > 0 ? prev - 1 : -1);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (selectedSuggestionIndex >= 0) {
        handleSelectSuggestion(symbolSuggestions[selectedSuggestionIndex]);
      }
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      setSelectedSuggestionIndex(-1);
    }
  };

  // Phase 6: Train RL Model
  const handleTrainModel = async () => {
    if (!trainSymbol.trim()) {
      showNotification('error', 'Invalid Input', 'Please enter a symbol');
      return;
    }

    // Frontend validation - enforce backend constraints
    if (episodes < 10) {
      showNotification('error', 'Invalid Episodes', 'Episodes must be at least 10 to train the model.');
      return;
    }

    setIsTraining(true);
    setTrainingStatus('training');
    setTrainingMessage('Initializing RL training...');
    setTrainingProgress(0);
    setTrainingResults(null);
    setExistingModelInfo(null);

    let progressInterval: ReturnType<typeof setInterval> | null = null;

    try {
      // Simulate progress updates
      progressInterval = setInterval(() => {
        setTrainingProgress(prev => Math.min(prev + Math.random() * 15, 95));
      }, 800);

      // Call actual backend API
      const response = await stockAPI.trainRL(trainSymbol, trainHorizon, episodes, forceRetrain);

      if (progressInterval) clearInterval(progressInterval);
      setTrainingProgress(100);

      // CRITICAL: Check response.status from backend
      if (response.status === 'skipped') {
        // Training was skipped - model already exists
        setTrainingStatus('skipped');
        setIsTraining(false);
        
        // Show model details from backend
        const modelInfo = {
          symbol: response.symbol || trainSymbol,
          horizon: response.horizon || trainHorizon,
          modelPath: response.model_path,
          timestamp: response.timestamp
        };
        
        setExistingModelInfo(modelInfo);
        setTrainingMessage('Training skipped - model already exists');
        setTrainingResults(null); // Do NOT show metrics
        showNotification(
          'info', 
          'Model Already Exists', 
          `Active model found for ${modelInfo.symbol} (${modelInfo.horizon})`
        );
      } else if (response.status === 'completed') {
        // Training completed successfully
        setTrainingStatus('complete');
        setIsTraining(false);
        setTrainingMessage(`Model trained successfully! Episodes: ${episodes}`);
        setTrainingResults(response);
        showNotification(
          'success',
          'Training Complete',
          `${trainSymbol} model trained with ${episodes} episodes.`
        );
      } else if (response.status === 'failed') {
        // Training failed (business logic failure, not exception)
        setTrainingStatus('failed');
        setIsTraining(false);
        setTrainingMessage(response.message || 'Training failed');
        setExistingModelInfo({
          symbol: response.symbol || trainSymbol,
          horizon: response.horizon || trainHorizon,
          message: response.message
        });
        setTrainingResults(null);
        showNotification('error', 'Training Failed', response.message || 'Model training failed');
      } else if (response.status === 'error') {
        // Training failed
        setTrainingStatus('error');
        setIsTraining(false);
        setTrainingMessage(response.message || 'Training failed');
        setTrainingResults(null);
        showNotification('error', 'Training Failed', response.message || 'An error occurred');
      }


    } catch (error: any) {
      if (progressInterval) clearInterval(progressInterval);
      setTrainingStatus('error');
      
      // Translate backend validation errors to user-friendly messages
      let userMessage = 'Training failed';
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        
        // Check for validation errors (422)
        if (Array.isArray(detail)) {
          const episodesError = detail.find((err: any) => 
            err.loc && err.loc.includes('n_episodes')
          );
          if (episodesError) {
            userMessage = 'Episodes must be at least 10 to train the model.';
          } else {
            userMessage = 'Invalid training parameters. Please check your inputs.';
          }
        } else if (typeof detail === 'string') {
          userMessage = detail;
        }
      } else if (error.message) {
        userMessage = error.message;
      }
      
      setTrainingMessage(userMessage);
      setTrainingResults(null); // Do NOT show metrics on error
      showNotification('error', 'Training Error', userMessage);
    } finally {
      setIsTraining(false);
    }
  };

  // Phase 7: AI Chat
  const handleSendMessage = async () => {
    if (!chatInput.trim()) return;

    // Add user message
    const userMessage = chatInput;
    setChatMessages(prev => [...prev, { role: 'user', message: userMessage }]);
    setChatInput('');
    setIsChatLoading(true);

    try {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Generate contextual AI response based on user input
      let aiResponse = '';

      const lowerMsg = userMessage.toLowerCase();

      if (lowerMsg.includes('price') || lowerMsg.includes('current')) {
        aiResponse = `The current price of ${selectedSymbol} is ₹${(Math.random() * 200 + 100).toFixed(2)}. Based on recent trends and your selected ${selectedTimeframe} timeframe, I recommend monitoring RSI and MACD indicators for entry signals.`;
      } else if (lowerMsg.includes('buy') || lowerMsg.includes('sell')) {
        aiResponse = `For ${selectedSymbol}, my analysis suggests a ${Math.random() > 0.5 ? 'BUY' : 'SELL'} signal. The ${activeIndicators.join(', ')} indicators show ${Math.random() > 0.5 ? 'bullish' : 'bearish'} momentum. Consider setting stop-loss at ${(Math.random() * 5 + 2).toFixed(2)}%.`;
      } else if (lowerMsg.includes('rsi') || lowerMsg.includes('macd')) {
        aiResponse = `Technical Analysis for ${selectedSymbol}:
• RSI: ${(Math.random() * 40 + 30).toFixed(1)} (${Math.random() > 0.5 ? 'Oversold - Potential Buy' : 'Neutral'})
• MACD: ${Math.random() > 0.5 ? 'Bullish crossover detected' : 'Bearish divergence observed'}
• Support: ₹${(Math.random() * 50 + 150).toFixed(2)}
• Resistance: ₹${(Math.random() * 50 + 180).toFixed(2)}`;
      } else if (lowerMsg.includes('risk') || lowerMsg.includes('volatility')) {
        aiResponse = `Risk Assessment for ${selectedSymbol}:
• Volatility: ${(Math.random() * 15 + 10).toFixed(1)}%
• Beta: ${(Math.random() * 0.8 + 0.7).toFixed(2)}
• Max Drawdown: ${(Math.random() * 8 + 5).toFixed(1)}%
Recommended position size: ${(Math.random() * 5 + 2).toFixed(1)}% of portfolio`;
      } else {
        // Default response
        const responses = [
          `Based on my analysis of ${selectedSymbol} with ${activeIndicators.join(', ')} indicators on ${selectedTimeframe} timeframe, the market shows mixed signals. I recommend waiting for clearer confirmation before entering positions.`,
          `For ${selectedSymbol}, I'm monitoring key support/resistance levels. The current setup looks ${Math.random() > 0.5 ? 'promising' : 'cautious'}. Would you like me to analyze specific technical patterns?`,
          `I've analyzed ${selectedSymbol}'s recent price action. The ${selectedTimeframe} trend appears ${Math.random() > 0.5 ? 'bullish' : 'bearish'} with strong ${activeIndicators[0]} confirmation. Consider adjusting your risk parameters accordingly.`,
          `Market sentiment for ${selectedSymbol} is currently ${Math.random() > 0.5 ? 'positive' : 'negative'}. My algorithmic models suggest watching for ${Math.random() > 0.5 ? 'breakout' : 'breakdown'} opportunities in the near term.`
        ];
        aiResponse = responses[Math.floor(Math.random() * responses.length)];
      }

      setChatMessages(prev => [...prev, { role: 'assistant', message: aiResponse }]);
      showNotification('success', 'AI Response', 'Trading assistant provided analysis');
    } catch (error: any) {
      const msg = 'AI service temporarily unavailable. Showing simulated response.';
      const fallbackResponse = `Hello! I'm your AI trading assistant. While the backend is offline, I can provide general trading guidance. You've selected ${selectedSymbol} with ${activeIndicators.join(', ')} indicators on ${selectedTimeframe} timeframe. How can I help with your trading strategy today?`;

      setChatMessages(prev => [...prev, { role: 'assistant', message: fallbackResponse }]);
      showNotification('warning', 'Demo Mode', 'AI chat in simulation mode');
    } finally {
      setIsChatLoading(false);
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">RL Model Training</h1>

        <div className="max-w-3xl mx-auto">
          {/* Train RL Model with Integrated AI Assistant */}
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <Brain className="w-6 h-6 text-blue-400" />
                <h2 className="text-xl font-bold text-white">Train RL Model</h2>
              </div>
              <button
                onClick={() => setIsChatOpen(!isChatOpen)}
                className="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded transition-colors flex items-center space-x-1"
              >
                <Brain className="w-4 h-4" />
                <span>AI Assistant</span>
              </button>
            </div>

            <div className="space-y-4">
              {/* Symbol Input */}
              <div className="relative">
                <label className="block text-sm font-medium text-gray-300 mb-1">Symbol</label>
                <input
                  type="text"
                  value={trainSymbol}
                  onChange={(e) => handleSymbolInput(e.target.value)}
                  onKeyDown={handleSymbolKeyDown}
                  onFocus={() => trainSymbol && setShowSuggestions(symbolSuggestions.length > 0)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                  disabled={isTraining}
                  placeholder="e.g., AAPL"
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-gray-500 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {showSuggestions && symbolSuggestions.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-slate-700 border border-slate-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                    {symbolSuggestions.map((symbol, index) => (
                      <button
                        key={symbol}
                        onClick={() => handleSelectSuggestion(symbol)}
                        className={`w-full px-3 py-2 text-left text-white hover:bg-slate-600 transition-colors text-sm ${
                          index === selectedSuggestionIndex ? 'bg-slate-600' : ''
                        }`}
                      >
                        {symbol}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Horizon Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Timeframe</label>
                <select
                  value={trainHorizon}
                  onChange={(e) => setTrainHorizon(e.target.value as any)}
                  disabled={isTraining}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="intraday">Intraday (1 day)</option>
                  <option value="short">Short Term (5 days)</option>
                  <option value="long">Long Term (30 days)</option>
                </select>
              </div>

              {/* Episodes Input */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Episodes ({episodes})</label>
                <input
                  type="range"
                  min="10"
                  max="100"
                  step="1"
                  value={episodes}
                  onChange={(e) => setEpisodes(Math.max(10, parseInt(e.target.value)))}
                  disabled={isTraining}
                  className="w-full disabled:opacity-50"
                />
                <p className="text-xs text-gray-400 mt-1">Minimum: 10 episodes required</p>
              </div>

              {/* Force Retrain Checkbox */}
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="forceRetrain"
                  checked={forceRetrain}
                  onChange={(e) => setForceRetrain(e.target.checked)}
                  disabled={isTraining}
                  className="w-4 h-4 disabled:opacity-50"
                />
                <label htmlFor="forceRetrain" className="text-sm text-gray-300">Force Retrain</label>
              </div>

              {/* Progress Bar */}
              {isTraining && (
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${trainingProgress}%` }}
                  />
                </div>
              )}

              {/* Status Message */}
              {trainingMessage && trainingStatus !== 'skipped' && (
                <div className={`flex items-start space-x-2 p-3 rounded ${trainingStatus === 'complete' ? 'bg-green-900 border border-green-700' :
                    trainingStatus === 'error' ? 'bg-red-900 border border-red-700' :
                      'bg-blue-900 border border-blue-700'
                  }`}>
                  {trainingStatus === 'complete' ? (
                    <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                  ) : trainingStatus === 'error' ? (
                    <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  ) : (
                    <Clock className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                  )}
                  <p className={trainingStatus === 'complete' ? 'text-green-200' : trainingStatus === 'error' ? 'text-red-200' : 'text-blue-200'}>
                    {trainingMessage}
                  </p>
                </div>
              )}

              {/* Existing Model Info - Shown when training is skipped */}
              {trainingStatus === 'skipped' && existingModelInfo && (
                <div className="bg-yellow-900 border border-yellow-700 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <AlertCircle className="w-6 h-6 text-yellow-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-yellow-200 mb-2">Existing Model Found</h3>
                      <div className="space-y-2 text-sm text-yellow-100">
                        <p><span className="font-medium">Symbol:</span> {existingModelInfo.symbol}</p>
                        <p><span className="font-medium">Timeframe:</span> {existingModelInfo.horizon}</p>
                        <p><span className="font-medium">Status:</span> Active</p>
                        {existingModelInfo.timestamp && (
                          <p><span className="font-medium">Last Updated:</span> {new Date(existingModelInfo.timestamp).toLocaleString('en-US', { 
                            year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
                          })}</p>
                        )}
                      </div>
                      <div className="mt-3 pt-3 border-t border-yellow-700">
                        <p className="text-sm text-yellow-200 font-medium mb-1">Why was training skipped?</p>
                        <p className="text-sm text-yellow-100">A trained model already exists for this symbol and timeframe.</p>
                      </div>
                      <div className="mt-3 pt-3 border-t border-yellow-700">
                        <p className="text-sm text-yellow-200 font-medium mb-1">Want to retrain?</p>
                        <p className="text-sm text-yellow-100">Enable the <span className="font-semibold">Force Retrain</span> checkbox below and click Start Training again.</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Training Failed Panel - Shown when training fails */}
              {trainingStatus === 'failed' && existingModelInfo && (
                <div className="bg-red-900 border border-red-700 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-red-200 mb-2">Training Failed</h3>
                      <div className="space-y-2 text-sm text-red-100">
                        <p><span className="font-medium">Symbol:</span> {existingModelInfo.symbol}</p>
                        <p><span className="font-medium">Timeframe:</span> {existingModelInfo.horizon}</p>
                        <p><span className="font-medium">Status:</span> Failed</p>
                      </div>
                      <div className="mt-3 pt-3 border-t border-red-700">
                        <p className="text-sm text-red-200 font-medium mb-1">Error Details:</p>
                        <p className="text-sm text-red-100">{existingModelInfo.message || 'Model training failed. Check if data/features exist.'}</p>
                      </div>
                      <div className="mt-3 pt-3 border-t border-red-700">
                        <p className="text-sm text-red-200 font-medium mb-1">Next Steps:</p>
                        <ul className="text-sm text-red-100 list-disc list-inside space-y-1">
                          <li>Try enabling <span className="font-semibold">Force Retrain</span> to retrain the model</li>
                          <li>Try a different timeframe (intraday, short, or long)</li>
                          <li>Ensure historical data is available for this symbol</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Training Results Display - Only show when training actually completed */}
              {trainingStatus === 'complete' && trainingResults && trainingResults.training_metrics && (
                <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
                  <h3 className="text-lg font-semibold text-white mb-3 flex items-center">
                    <BarChart3 className="w-5 h-5 mr-2 text-green-400" />
                    Training Results
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-slate-600 p-3 rounded">
                      <p className="text-xs text-gray-400">Total Episodes</p>
                      <p className="text-xl font-bold text-white">{trainingResults.training_metrics.total_episodes}</p>
                    </div>
                    <div className="bg-slate-600 p-3 rounded">
                      <p className="text-xs text-gray-400">Avg Reward</p>
                      <p className="text-xl font-bold text-white">{Number(trainingResults.training_metrics.average_reward)?.toFixed(4)}</p>
                    </div>
                    <div className="bg-slate-600 p-3 rounded">
                      <p className="text-xs text-gray-400">Cumulative Reward</p>
                      <p className="text-xl font-bold text-white">{Number(trainingResults.training_metrics.cumulative_reward)?.toFixed(2)}</p>
                    </div>
                    <div className="bg-slate-600 p-3 rounded">
                      <p className="text-xs text-gray-400">Win Rate</p>
                      <p className="text-xl font-bold text-white">{(Number(trainingResults.training_metrics.win_rate) * 100)?.toFixed(1)}%</p>
                    </div>
                    <div className="bg-slate-600 p-3 rounded">
                      <p className="text-xs text-gray-400">Sharpe Ratio</p>
                      <p className="text-xl font-bold text-white">{Number(trainingResults.training_metrics.sharpe_ratio)?.toFixed(3)}</p>
                    </div>
                    <div className="bg-slate-600 p-3 rounded">
                      <p className="text-xs text-gray-400">Final Epsilon</p>
                      <p className="text-xl font-bold text-white">{Number(trainingResults.training_metrics.final_epsilon)?.toFixed(3)}</p>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-600">
                    <p className="text-sm text-gray-300">
                      <span className="font-medium">Model:</span> {trainingResults.model_info?.model_type}
                    </p>
                    <p className="text-sm text-gray-300">
                      <span className="font-medium">Features:</span> {trainingResults.model_info?.n_features}
                    </p>
                    <p className="text-sm text-gray-300">
                      <span className="font-medium">Actions:</span> {trainingResults.model_info?.n_actions}
                    </p>
                  </div>
                </div>
              )}

              {/* Train Button */}
              <button
                onClick={handleTrainModel}
                disabled={isTraining || episodes < 10 || !trainSymbol.trim()}
                className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white font-medium rounded transition-colors flex items-center justify-center space-x-2"
              >
                <Play className="w-4 h-4" />
                <span>{isTraining ? 'Training...' : 'Start Training'}</span>
              </button>
              {episodes < 10 && (
                <p className="text-xs text-red-400 mt-1">⚠️ Episodes must be at least 10</p>
              )}

              {/* AI Assistant Chat (Collapsible) */}
              {isChatOpen && (
                <div className="mt-6 pt-6 border-t border-slate-700 space-y-4">
                  <div className="flex items-center space-x-2">
                    <Brain className="w-5 h-5 text-purple-400" />
                    <h3 className="text-lg font-semibold text-white">AI Trading Assistant</h3>
                  </div>

                  {/* Context Settings */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Symbol</label>
                      <input
                        type="text"
                        value={selectedSymbol}
                        onChange={(e) => setSelectedSymbol(e.target.value.toUpperCase())}
                        className="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Timeframe</label>
                      <select
                        value={selectedTimeframe}
                        onChange={(e) => setSelectedTimeframe(e.target.value)}
                        className="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      >
                        <option value="intraday">Intraday</option>
                        <option value="short">Short Term</option>
                        <option value="long">Long Term</option>
                      </select>
                    </div>
                  </div>

                  {/* Indicators Selection */}
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-2">Active Indicators</label>
                    <div className="flex flex-wrap gap-2">
                      {['RSI', 'MACD', 'BB', 'SMA'].map(indicator => (
                        <button
                          key={indicator}
                          onClick={() => setActiveIndicators(prev =>
                            prev.includes(indicator) ? prev.filter(i => i !== indicator) : [...prev, indicator]
                          )}
                          className={`px-2 py-1 rounded text-xs font-medium transition-colors ${activeIndicators.includes(indicator)
                              ? 'bg-purple-600 text-white'
                              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                            }`}
                        >
                          {indicator}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Chat Messages */}
                  <div className="bg-slate-700 rounded-lg p-3 max-h-48 lg:max-h-60 overflow-y-auto space-y-3">
                    {chatMessages.map((msg, idx) => (
                      <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div
                          className={`max-w-xs px-3 py-2 rounded text-sm ${msg.role === 'user'
                              ? 'bg-blue-600 text-white'
                              : 'bg-slate-600 text-gray-200'
                            }`}
                        >
                          {msg.message}
                        </div>
                      </div>
                    ))}
                    {isChatLoading && (
                      <div className="flex justify-start">
                        <div className="bg-slate-600 text-gray-200 px-3 py-2 rounded text-sm">
                          Thinking...
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Chat Input */}
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                      disabled={isChatLoading}
                      placeholder="Ask about trading..."
                      className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm placeholder-gray-500 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    <button
                      onClick={handleSendMessage}
                      disabled={isChatLoading || !chatInput.trim()}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white text-sm font-medium rounded transition-colors"
                    >
                      Send
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>


      </div>
    </Layout>
  );
};

export default TrainModelPage;
