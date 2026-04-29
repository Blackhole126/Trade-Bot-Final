import React, { useState } from 'react';
import { usePortfolio } from '../contexts/PortfolioContext';
import { useTheme } from '../contexts/ThemeContext';
import { ChevronDown, BookOpen, Target, TrendingUp, Zap } from 'lucide-react';

const PortfolioSelector = () => {
  const { 
    portfolioState, 
    availablePortfolios, 
    selectPortfolio 
  } = usePortfolio();
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const [isOpen, setIsOpen] = useState(false);
  
  const selectedPortfolioInfo = availablePortfolios.find(
    p => p.id === portfolioState.selectedPortfolio
  );

  const getPortfolioIcon = (icon: string) => {
    switch(icon) {
      case '🌱': return <BookOpen className="w-4 h-4" />;
      case '🌳': return <Target className="w-4 h-4" />;
      case '🌤️': return <TrendingUp className="w-4 h-4" />;
      case '🔮': return <Zap className="w-4 h-4" />;
      default: return <BookOpen className="w-4 h-4" />;
    }
  };

  return (
    <div className="relative mt-4">
      {/* Selected Portfolio Display */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors group min-w-[280px] ${
          isLight 
            ? 'bg-white border border-gray-300 hover:bg-gray-50 text-gray-900' 
            : 'bg-slate-800 border border-slate-600 hover:bg-slate-700 text-white'
        }`}
      >
        <div className={`flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br ${selectedPortfolioInfo?.color} text-white text-lg`}>
          {getPortfolioIcon(selectedPortfolioInfo?.icon || '🌱')}
        </div>
        
        <div className="flex-1 text-left">
          <div className="flex items-center gap-2">
            <span className={`font-semibold text-sm ${isLight ? 'text-gray-900' : 'text-white'}`}>
              {selectedPortfolioInfo?.name}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded ${
              isLight 
                ? 'bg-gray-100 text-gray-600' 
                : 'bg-slate-700 text-gray-400'
            }`}>
              {selectedPortfolioInfo?.description}
            </span>
          </div>
          <p className={`text-xs mt-0.5 ${isLight ? 'text-gray-600' : 'text-gray-400'}`}>
            {selectedPortfolioInfo?.scope}
          </p>
        </div>
        
        <ChevronDown className={`w-4 h-4 transition-transform ${
          isLight ? 'text-gray-500' : 'text-gray-400'
        } ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          
          {/* Portfolio Options */}
          <div className={`absolute top-full left-0 right-0 mt-2 rounded-lg shadow-xl z-50 overflow-hidden ${
            isLight 
              ? 'bg-white border border-gray-200' 
              : 'bg-slate-800 border border-slate-600'
          }`}>
            <div className="p-2">
              <p className={`text-xs px-2 py-1.5 ${
                isLight ? 'text-gray-500' : 'text-gray-400'
              }`}>
                Educational Portfolios
              </p>
              
              <div className="space-y-1">
                {availablePortfolios.map((portfolio) => (
                  <button
                    key={portfolio.id}
                    onClick={() => {
                      selectPortfolio(portfolio.id);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                      portfolioState.selectedPortfolio === portfolio.id
                        ? isLight 
                          ? 'bg-blue-50 border border-blue-200' 
                          : 'bg-blue-500/20 border border-blue-500/30'
                        : isLight
                          ? 'hover:bg-gray-100' 
                          : 'hover:bg-slate-700'
                    }`}
                  >
                    <div className={`flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br ${portfolio.color} text-white text-lg flex-shrink-0`}>
                      {getPortfolioIcon(portfolio.icon)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`font-medium text-sm ${
                          isLight ? 'text-gray-900' : 'text-white'
                        }`}>
                          {portfolio.name}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          isLight 
                            ? 'bg-gray-100 text-gray-600' 
                            : 'bg-slate-700 text-gray-400'
                        }`}>
                          {portfolio.description}
                        </span>
                      </div>
                      <p className={`text-xs mt-1 truncate ${
                        isLight ? 'text-gray-600' : 'text-gray-400'
                      }`}>
                        {portfolio.scope}
                      </p>
                    </div>
                    
                    {portfolioState.selectedPortfolio === portfolio.id && (
                      <div className="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0"></div>
                    )}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Disclaimer */}
            <div className={`border-t p-3 ${
              isLight 
                ? 'bg-gray-50 border-gray-200' 
                : 'bg-slate-800/50 border-slate-700'
            }`}>
              <div className="flex items-start gap-2">
                <div className="w-2 h-2 rounded-full bg-yellow-400/80 mt-1.5 flex-shrink-0"></div>
                <p className={`text-xs leading-relaxed ${
                  isLight ? 'text-yellow-700' : 'text-yellow-200'
                }`}>
                  <span className="font-semibold">Educational Simulation:</span> All portfolios are for learning purposes only. No real money is involved. Past performance does not guarantee future results.
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default PortfolioSelector;