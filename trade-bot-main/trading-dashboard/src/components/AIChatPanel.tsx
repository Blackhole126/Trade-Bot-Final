import { useState, useRef, useEffect } from 'react';
import { Send, X, Minimize2, Bot, User, Loader2, Sparkles, AlertCircle, Zap, TrendingUp, BarChart3, HelpCircle } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useLocation } from 'react-router-dom';
import { useAssetType } from '../contexts/AssetTypeContext';
import { FeatureUnavailable } from './FeatureUnavailable';

interface AIChatPanelProps {
  onClose: () => void;
  onMinimize: () => void;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  error?: boolean;
}

const QUICK_ACTIONS = [
  { label: 'Understanding Trends', icon: BarChart3, prompt: 'Explain how market trends form and what they indicate for educational purposes' },
  { label: 'Learning Strategies', icon: TrendingUp, prompt: 'Describe different investment approaches and their educational value' },
  { label: 'Indicator Education', icon: Zap, prompt: 'Explain how technical indicators work and their role in analysis' },
  { label: 'Risk Principles', icon: HelpCircle, prompt: 'What are the fundamental principles of risk management in markets?' },
];

const AIChatPanel = ({ onClose, onMinimize }: AIChatPanelProps) => {
  const { theme } = useTheme();
  const location = useLocation();
  const { assetType } = useAssetType();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const isLight = theme === 'light';
  const isSpace = theme === 'space';

  // Get context from URL or current page
  const getContext = () => {
    const context: { symbol?: string; timeframe?: string; activeIndicators?: string[] } = {};
    
    // Try to get symbol from URL params
    const urlParams = new URLSearchParams(location.search);
    const symbol = urlParams.get('q') || urlParams.get('symbol');
    if (symbol) {
      context.symbol = symbol;
    }
    
    // Add asset type to context
    if (assetType) {
      context.activeIndicators = context.activeIndicators || [];
      context.activeIndicators.push(`AssetType: ${assetType}`);
    }
    
    return context;
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleSend = async (messageContent?: string, contextOverride?: typeof getContext extends () => infer R ? R : never) => {
    const content = messageContent || input.trim();
    if (!content || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!messageContent) setInput('');
    setIsLoading(true);
    setError(null);

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    try {
      // Get context for the request
      const context = contextOverride || getContext();

      // Backend API call
      const response = await aiAPI.chat(content, context);
      
      // Check if feature is disabled
      if (response.feature_status === 'disabled') {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.message || 'AI Chat is currently in placeholder mode. Please use the prediction and analysis tools for trading insights.',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
        setError('AI Chat feature is currently disabled');
      } else {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.message || response.content || 'I received your message.',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error: any) {
      if (error.name === 'AbortError' || abortControllerRef.current?.signal.aborted) {
        return;
      }
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `I encountered a technical issue while processing your question. As your learning mentor, I'm here to explain market concepts and help you understand financial patterns. Please rephrase your question or try again.\n\nTechnical note: ${error.message || 'Connection issue'}`,
        timestamp: new Date(),
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
      setError(error.message || 'Failed to get response');
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleQuickAction = (prompt: string) => {
    handleSend(prompt);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSend();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getThemeClasses = () => {
    if (isLight) {
      return {
        bg: 'bg-white',
        bgSecondary: 'bg-gray-50',
        border: 'border-gray-200',
        text: 'text-gray-900',
        textSecondary: 'text-gray-600',
        textTertiary: 'text-gray-400',
        input: 'bg-gray-100 border-gray-300 text-gray-900 placeholder-gray-500',
        messageUser: 'bg-blue-500 text-white',
        messageBot: 'bg-gray-100 text-gray-900',
        header: 'bg-white border-gray-200',
      };
    }
    if (isSpace) {
      return {
        bg: 'bg-slate-900/95 backdrop-blur-sm',
        bgSecondary: 'bg-slate-800/60',
        border: 'border-purple-900/30',
        text: 'text-white',
        textSecondary: 'text-gray-300',
        textTertiary: 'text-gray-400',
        input: 'bg-slate-800/60 backdrop-blur-sm border-purple-900/30 text-white placeholder-gray-300',
        messageUser: 'bg-blue-500 text-white',
        messageBot: 'bg-slate-700/80 text-gray-100',
        header: 'bg-slate-900/95 backdrop-blur-sm border-purple-900/30',
      };
    }
    return {
      bg: 'bg-slate-800/95 backdrop-blur-sm',
      bgSecondary: 'bg-slate-700/50',
      border: 'border-slate-700',
      text: 'text-white',
      textSecondary: 'text-gray-300',
      textTertiary: 'text-gray-400',
      input: 'bg-slate-700/50 border-slate-600 text-white placeholder-gray-400',
      messageUser: 'bg-blue-500 text-white',
      messageBot: 'bg-slate-700 text-gray-100',
      header: 'bg-slate-800/95 backdrop-blur-sm border-slate-700',
    };
  };

  const themeClasses = getThemeClasses();

  return (
    <div className={`fixed inset-0 sm:inset-auto sm:bottom-24 sm:right-6 sm:w-[420px] sm:h-[650px] h-full sm:rounded-xl ${themeClasses.bg} ${themeClasses.border} border shadow-2xl z-50 flex flex-col`}>
      {/* Header */}
      <div className={`flex items-center justify-between p-4 border-b ${themeClasses.header} ${themeClasses.border}`}>
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center relative shadow-lg ${
            isSpace ? 'shadow-blue-500/50' : ''
          }`}>
            {!imageError ? (
              <img
                src="/jarvis-logo.png"
                alt="AI"
                className="w-6 h-6 object-contain"
                onError={() => setImageError(true)}
              />
            ) : (
              <Bot className="w-5 h-5 text-white" />
            )}
            {isLoading && (
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-pulse border-2 border-white"></div>
            )}
          </div>
          <div>
            <h3 className={`text-sm font-semibold ${themeClasses.text} flex items-center gap-1`}>
              Market Learning Mentor
              {isSpace && <Sparkles className="w-3 h-3 text-purple-400" />}
            </h3>
            <p className={`text-xs ${themeClasses.textTertiary}`}>
              {isLoading ? 'Analyzing...' : 'Educational guidance'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onMinimize}
            className={`p-1.5 hover:bg-opacity-20 rounded transition-colors ${themeClasses.textSecondary}`}
            title="Minimize"
          >
            <Minimize2 className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className={`p-1.5 hover:bg-opacity-20 rounded transition-colors ${themeClasses.textSecondary}`}
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className={`flex-1 overflow-y-auto p-4 space-y-4 ${themeClasses.bgSecondary}`}>
        <FeatureUnavailable
          feature="AI Chat"
          reason="This feature requires backend support and is not enabled."
          suggestion="Backend does not implement /api/ai/chat endpoint. AI chat requires server-side implementation."
          mode="info"
        />
      </div>

      {/* Input - Disabled */}
      <div className={`border-t ${themeClasses.header} ${themeClasses.border} p-3 sm:p-4 flex-shrink-0`}>
        <form onSubmit={(e) => e.preventDefault()} className="flex gap-2">
          <input
            type="text"
            value=""
            placeholder="AI Chat is currently unavailable"
            className={`flex-1 px-4 py-2.5 rounded-lg ${themeClasses.input} focus:outline-none text-sm transition-all cursor-not-allowed opacity-50`}
            disabled
          />
          <button
            type="submit"
            disabled
            className={`px-4 py-2.5 bg-blue-500 text-white rounded-lg transition-all opacity-50 cursor-not-allowed flex items-center justify-center`}
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default AIChatPanel;
