import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { stockAPI } from '../services/api';
import { validateApiResponsePrice, validatePrice, getPriceSourceInfo } from '../utils/priceValidator';
import { calculatePortfolioMetrics } from '../utils/portfolioCalculations';

// Portfolio Types
export type PortfolioType = 'seed' | 'tree' | 'sky' | 'scenario';

export interface PortfolioInfo {
  id: PortfolioType;
  name: string;
  description: string;
  scope: string;
  color: string;
  icon: string;
}

export interface PortfolioHolding {
  symbol: string;
  shares: number;
  avgPrice: number;
  currentPrice: number;
  value: number;
  stopLossPrice?: number | null;
  side?: 'long' | 'short';
}

export interface PortfolioState {
  selectedPortfolio: PortfolioType;
  holdings: PortfolioHolding[];
  totalValue: number;
  totalGain: number;
  totalGainPercent: number;
  lastUpdated: Date | null;
}

interface PortfolioContextType {
  // State
  portfolioState: PortfolioState;
  availablePortfolios: PortfolioInfo[];
  isLoading: boolean;
  error: string | null;
  
  // Actions
  selectPortfolio: (portfolioId: PortfolioType) => void;
  addHolding: (holding: Omit<PortfolioHolding, 'currentPrice' | 'value'>) => Promise<void>;
  removeHolding: (symbol: string) => void;
  updateHoldingPrice: (symbol: string, newPrice: number) => void;
  refreshPortfolio: (options?: { shouldPredict?: boolean }) => Promise<void>;
  clearPortfolio: () => void;
  updateHoldingStopLoss: (symbol: string, stopLossPrice: number | null) => void;
  clearAllPortfolioData: () => void;  // Add this method
}

const PortfolioContext = createContext<PortfolioContextType | undefined>(undefined);

// Portfolio Definitions
export const PORTFOLIO_DEFINITIONS: Record<PortfolioType, PortfolioInfo> = {
  seed: {
    id: 'seed',
    name: 'Seed Portfolio',
    description: 'Beginner Learning',
    scope: 'Small positions to understand basic concepts',
    color: 'from-green-500 to-emerald-500',
    icon: '🌱'
  },
  tree: {
    id: 'tree',
    name: 'Tree Portfolio',
    description: 'Practice & Discipline',
    scope: 'Medium complexity for behavioral learning',
    color: 'from-blue-500 to-cyan-500',
    icon: '🌳'
  },
  sky: {
    id: 'sky',
    name: 'Sky Portfolio',
    description: 'Advanced Analysis',
    scope: 'Complex positions for multi-factor analysis',
    color: 'from-purple-500 to-pink-500',
    icon: '🌤️'
  },
  scenario: {
    id: 'scenario',
    name: 'Scenario Portfolio',
    description: 'What-if Simulation',
    scope: 'Hypothetical situations for stress testing',
    color: 'from-orange-500 to-red-500',
    icon: '🔮'
  }
};

export const PortfolioProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [selectedPortfolio, setSelectedPortfolio] = useState<PortfolioType>('seed');
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([]);
  const [totalValue, setTotalValue] = useState(0);
  const [totalGain, setTotalGain] = useState(0);
  const [totalGainPercent, setTotalGainPercent] = useState(0);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshTime, setLastRefreshTime] = useState<number>(0);

  // Load portfolio data on mount - NO auto-refresh
  useEffect(() => {
    const loadData = async () => {
      await loadPortfolioFromStorage(selectedPortfolio);
      // No automatic refresh - let user explicitly trigger if needed
    };
    
    loadData();
  }, [selectedPortfolio]);

  const loadPortfolioFromStorage = async (portfolioId: PortfolioType) => {
  try {
    const res = await fetch("http://127.0.0.1:8000/portfolio");
    const data = await res.json();

    console.log("[PORTFOLIO CONTEXT] Loaded from backend:", data);

    setHoldings(data.holdings || []);
    setTotalValue(data.total_value || 0);
    setTotalGain(data.total_gain || 0);
    setTotalGainPercent(data.total_gain_percent || 0);
    setLastUpdated(new Date());

  } catch (err) {
    console.error("Failed to initialize portfolio:", err);
    setError("Failed to initialize portfolio data");
  }
};


 const savePortfolioToBackend = async (holdings: PortfolioHolding[]) => {
  try {
    await fetch("http://127.0.0.1:8000/portfolio/update", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        holdings,
        total_value: totalValue,
        total_gain: totalGain,
        total_gain_percent: totalGainPercent,
      }),
    });

    console.log("✅ Portfolio saved to backend");
  } catch (err) {
    console.error("❌ Backend save failed", err);
    setError("Failed to save portfolio");
  }
};

  const recalculatePortfolioMetrics = (holdingsToCalculate: PortfolioHolding[]) => {
    // Use centralized calculation helper
    const metrics = calculatePortfolioMetrics(holdingsToCalculate);
    
    // Update state with calculated values
    setTotalValue(metrics.totalMarketValue);
    setTotalGain(metrics.totalUnrealizedValue);
    setTotalGainPercent(metrics.totalUnrealizedPercent || 0);
  };

  const selectPortfolio = (portfolioId: PortfolioType) => {
    setSelectedPortfolio(portfolioId);
    // Will trigger useEffect to load the selected portfolio
  };

  const addHolding = async (holding: Omit<PortfolioHolding, 'currentPrice' | 'value'>) => {
    setIsLoading(true);
    setError(null);
    
    // Validate input data
    if (holding.shares <= 0) {
      throw new Error(`Invalid quantity: ${holding.shares}`);
    }
    if (holding.avgPrice <= 0) {
      throw new Error(`Invalid average price: ${holding.avgPrice}`);
    }
    
    try {
      // Fetch current price from backend using stockAPI
      const data = await stockAPI.predict([holding.symbol], 'intraday');
      
      console.log('[ADD HOLDING] Raw API response:', data);
      let currentPrice = holding.avgPrice;
      if (data.predictions && data.predictions.length > 0) {
        const prediction = data.predictions.find((p: any) => !p.error);
        console.log('[ADD HOLDING] Found prediction:', prediction);
        if (prediction) {
          try {
            currentPrice = validateApiResponsePrice(prediction, holding.symbol);
            console.log(`[ADD HOLDING] ${holding.symbol} price set to: ${currentPrice} (${getPriceSourceInfo(currentPrice, holding.symbol)})`);
          } catch (priceError: any) {
            console.error(`[ADD HOLDING] Price validation failed for ${holding.symbol}:`, priceError);
            setError(`Cannot add holding: ${priceError.message || 'Unknown error'}`);
            throw priceError; // Re-throw to prevent adding invalid holding
          }
        }
      }
      
      // CRITICAL VALIDATION: Ensure quantity is not being multiplied by any factor
      if (holding.shares > 100000) { // Arbitrarily high number that shouldn't occur in normal usage
        console.warn(`Warning: Quantity seems unusually high: ${holding.shares} for ${holding.symbol}`);
      }
      
      const newHolding: PortfolioHolding = {
        ...holding,
        currentPrice,
        value: holding.shares * currentPrice,
        stopLossPrice: holding.stopLossPrice || null,
        side: holding.side || 'long'
      };
      
      const updatedHoldings = [...holdings, newHolding];
      setHoldings(updatedHoldings);
      savePortfolioToBackend(updatedHoldings);
      recalculatePortfolioMetrics(updatedHoldings);
      setLastUpdated(new Date());
      
    } catch (err) {
      console.error('Failed to add holding:', err);
      setError('Failed to fetch current price. Using average price.');
      
      // Fallback: use average price
      // CRITICAL VALIDATION: Ensure quantity is not being multiplied by any factor
      if (holding.shares > 100000) { // Arbitrarily high number that shouldn't occur in normal usage
        console.warn(`Warning: Quantity seems unusually high: ${holding.shares} for ${holding.symbol}`);
      }
      
      const newHolding: PortfolioHolding = {
        ...holding,
        currentPrice: holding.avgPrice,
        value: holding.shares * holding.avgPrice,
        stopLossPrice: holding.stopLossPrice || null,
        side: holding.side || 'long'
      };
      
      const updatedHoldings = [...holdings, newHolding];
      setHoldings(updatedHoldings);
      savePortfolioToBackend(updatedHoldings);
      await savePortfolioToBackend(updatedHoldings); // ✅ FIX
      recalculatePortfolioMetrics(updatedHoldings);
      setLastUpdated(new Date());
    } finally {
      // Ensure loading state is only reset after a reasonable delay to prevent flickering
      setTimeout(() => {
        setIsLoading(false);
      }, 300); // Small delay to prevent rapid state changes
    }
  };

  const removeHolding = (symbol: string) => {
    const updatedHoldings = holdings.filter(h => h.symbol !== symbol);
    setHoldings(updatedHoldings);
    savePortfolioToBackend(updatedHoldings);
    recalculatePortfolioMetrics(updatedHoldings);
    setLastUpdated(new Date());
  };

  const updateHoldingPrice = (symbol: string, newPrice: number) => {
    const updatedHoldings = holdings.map(h => 
      h.symbol === symbol 
        ? { 
            ...h, 
            currentPrice: newPrice, 
            value: h.shares * newPrice
          } 
        : h
    );
    setHoldings(updatedHoldings);
    savePortfolioToBackend(updatedHoldings);
    recalculatePortfolioMetrics(updatedHoldings);
  };

  const refreshPortfolio = async (options: { shouldPredict?: boolean } = {}) => {
    const { shouldPredict = true } = options;
    const now = Date.now();
    // Prevent refresh if last refresh was less than 1 second ago to avoid rapid state changes
    if (now - lastRefreshTime < 1000) {
      return;
    }
    
    setLastRefreshTime(now);
    setIsLoading(true);
    setError(null);
    
    try {
      // Refresh all holdings with current prices
      const symbols = holdings.map(h => h.symbol);
      if (symbols.length === 0) {
        // Even if no holdings, still use timeout to prevent rapid state changes
        setTimeout(() => {
          setIsLoading(false);
        }, 300);
        return;
      }
      
      // Only fetch predictions if explicitly requested
      if (!shouldPredict) {
        console.log('[PORTFOLIO REFRESH] Skipping prediction fetch - not requested');
        setIsLoading(false);
        return;
      }
      
      const data = await stockAPI.predict(symbols, 'intraday');
      
      if (data.predictions) {
        console.log('[PORTFOLIO REFRESH] Raw API response:', data);
        const updatedHoldings = holdings.map(holding => {
          const prediction = data.predictions.find((p: any) => p.symbol === holding.symbol && !p.error);
          console.log(`[PORTFOLIO REFRESH] Processing ${holding.symbol}`, { prediction, originalPrice: holding.currentPrice });
          if (prediction) {
            try {
              const newPrice = validateApiResponsePrice(prediction, holding.symbol);
              console.log(`[PORTFOLIO REFRESH] ${holding.symbol} price updated from ${holding.currentPrice} to ${newPrice} (${getPriceSourceInfo(newPrice, holding.symbol)})`);
              
              // CRITICAL VALIDATION: Ensure quantity is not being multiplied by any factor
              if (holding.shares > 100000) { // Arbitrarily high number that shouldn't occur in normal usage
                console.warn(`Warning: Quantity seems unusually high: ${holding.shares} for ${holding.symbol}`);
              }
              
              return {
                ...holding,
                currentPrice: newPrice,
                value: holding.shares * newPrice,
                stopLossPrice: holding.stopLossPrice,
                side: holding.side
              };
            } catch (priceError) {
              console.error(`[PORTFOLIO REFRESH] Price validation failed for ${holding.symbol}:`, priceError);
              // Keep original holding if price validation fails
              return holding;
            }
          }
          console.log(`[PORTFOLIO REFRESH] ${holding.symbol} no prediction found, keeping ${holding.currentPrice}`);
          return holding;
        });
        
        setHoldings(updatedHoldings);
        savePortfolioToBackend(updatedHoldings);
        recalculatePortfolioMetrics(updatedHoldings);
      }
      
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to refresh portfolio:', err);
      setError('Failed to refresh portfolio prices');
    } finally {
      // Ensure loading state is only reset after a reasonable delay to prevent flickering
      setTimeout(() => {
        setIsLoading(false);
      }, 300); // Small delay to prevent rapid state changes
    }
  };

  const clearPortfolio = () => {
    setHoldings([]);
    setTotalValue(0);
    setTotalGain(0);
    setTotalGainPercent(0);
    setLastUpdated(new Date());
    savePortfolioToStorage(selectedPortfolio, []);
  };

  // Utility function to clear all portfolio data from localStorage
  const clearAllPortfolioData = () => {
    const portfolioTypes: PortfolioType[] = ['seed', 'tree', 'sky', 'scenario'];
    portfolioTypes.forEach(type => {
      const key = `portfolio_${type}_holdings`;
      localStorage.removeItem(key);
      console.log(`[PORTFOLIO CONTEXT] Cleared localStorage for: ${key}`);
    });
    // Also clear holdings state
    setHoldings([]);
    setTotalValue(0);
    setTotalGain(0);
    setTotalGainPercent(0);
    setLastUpdated(new Date());
  };

  const updateHoldingStopLoss = (symbol: string, stopLossPrice: number | null) => {
    const updatedHoldings = holdings.map(h => 
      h.symbol === symbol 
        ? { ...h, stopLossPrice: stopLossPrice || null }
        : h
    );
    setHoldings(updatedHoldings);
    savePortfolioToBackend(updatedHoldings);
    recalculatePortfolioMetrics(updatedHoldings);
  };

  const portfolioState: PortfolioState = {
    selectedPortfolio,
    holdings,
    totalValue,
    totalGain,
    totalGainPercent,
    lastUpdated
  };

  const value: PortfolioContextType = {
    portfolioState,
    availablePortfolios: Object.values(PORTFOLIO_DEFINITIONS),
    isLoading,
    error,
    selectPortfolio,
    addHolding,
    removeHolding,
    updateHoldingPrice,
    refreshPortfolio,
    clearPortfolio,
    updateHoldingStopLoss,
    clearAllPortfolioData
  };

  return (
    <PortfolioContext.Provider value={value}>
      {children}
    </PortfolioContext.Provider>
  );
};

export const usePortfolio = (): PortfolioContextType => {
  const context = useContext(PortfolioContext);
  if (context === undefined) {
    throw new Error('usePortfolio must be used within a PortfolioProvider');
  }
  return context;
};