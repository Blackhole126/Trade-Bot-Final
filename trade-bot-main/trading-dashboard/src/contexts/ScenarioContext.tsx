import React, { createContext, useContext, useState, ReactNode } from 'react';
import { PortfolioHolding } from './PortfolioContext';
import { validatePrice } from '../utils/priceValidator';

// Scenario Types
export interface ScenarioHolding extends PortfolioHolding {
  // Extended with scenario-specific fields
  scenarioId?: string;
  simulatedPrice?: number;
  notes?: string;
}

export interface ScenarioState {
  id: string;
  name: string;
  description: string;
  baseHoldings: ScenarioHolding[]; // Original holdings for reference
  simulatedHoldings: ScenarioHolding[]; // Current scenario state
  totalValue: number;
  totalGain: number;
  totalGainPercent: number;
  lastUpdated: Date | null;
  isActive: boolean;
}

interface ScenarioContextType {
  // State
  scenarios: ScenarioState[];
  activeScenario: ScenarioState | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  createScenario: (name: string, description: string, baseHoldings: PortfolioHolding[]) => string;
  loadScenario: (scenarioId: string) => void;
  updateHoldingPrice: (symbol: string, newPrice: number, notes?: string) => void;
  addHolding: (holding: Omit<ScenarioHolding, 'currentPrice' | 'value' | 'scenarioId'>) => void;
  removeHolding: (symbol: string) => void;
  resetScenario: () => void;
  deleteScenario: (scenarioId: string) => void;
  updateScenarioMetadata: (scenarioId: string, name?: string, description?: string) => void;
  calculateScenarioMetrics: () => void;
}

const ScenarioContext = createContext<ScenarioContextType | undefined>(undefined);

export const ScenarioProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [scenarios, setScenarios] = useState<ScenarioState[]>([]);
  const [activeScenario, setActiveScenario] = useState<ScenarioState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createScenario = (name: string, description: string, baseHoldings: PortfolioHolding[]): string => {
    setIsLoading(true);
    setError(null);
    
    try {
      const scenarioId = `scenario_${Date.now()}`;
      
      // Create deep copy of base holdings for scenario
      const scenarioHoldings: ScenarioHolding[] = baseHoldings.map(holding => ({
        ...holding,
        scenarioId,
        simulatedPrice: holding.currentPrice, // Start with current price
        notes: 'Base scenario'
      }));
      
      const newScenario: ScenarioState = {
        id: scenarioId,
        name,
        description,
        baseHoldings: [...baseHoldings],
        simulatedHoldings: scenarioHoldings,
        totalValue: 0,
        totalGain: 0,
        totalGainPercent: 0,
        lastUpdated: new Date(),
        isActive: true
      };
      
      // Calculate initial metrics
      calculateMetrics(newScenario);
      
      setScenarios(prev => [...prev, newScenario]);
      setActiveScenario(newScenario);
      
      console.log(`[SCENARIO] Created new scenario: ${name} (${scenarioId})`);
      
      return scenarioId;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to create scenario';
      setError(errorMsg);
      console.error('Failed to create scenario:', err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const loadScenario = (scenarioId: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const scenario = scenarios.find(s => s.id === scenarioId);
      if (!scenario) {
        throw new Error(`Scenario not found: ${scenarioId}`);
      }
      
      // Mark as active
      const updatedScenarios = scenarios.map(s => 
        s.id === scenarioId 
          ? { ...s, isActive: true, lastUpdated: new Date() }
          : { ...s, isActive: false }
      );
      
      setScenarios(updatedScenarios);
      setActiveScenario(scenario);
      
      console.log(`[SCENARIO] Loaded scenario: ${scenario.name} (${scenarioId})`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load scenario';
      setError(errorMsg);
      console.error('Failed to load scenario:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const updateHoldingPrice = (symbol: string, newPrice: number, notes?: string) => {
    if (!activeScenario) {
      setError('No active scenario');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Validate new price
      const validation = validatePrice(newPrice, symbol);
      if (!validation.valid) {
        throw new Error(`Invalid price for ${symbol}: ${validation.error}`);
      }
      
      // Update the simulated holding
      const updatedHoldings = activeScenario.simulatedHoldings.map(holding => {
        if (holding.symbol === symbol) {
          const newValue = holding.shares * newPrice;
          return {
            ...holding,
            simulatedPrice: newPrice,
            currentPrice: newPrice, // Update currentPrice for consistency
            value: newValue,
            notes: notes || `Price updated to ${newPrice}`
          };
        }
        return holding;
      });
      
      // Check if holding was found
      const holdingExists = activeScenario.simulatedHoldings.some(h => h.symbol === symbol);
      if (!holdingExists) {
        throw new Error(`Holding not found: ${symbol}`);
      }
      
      // Update scenario with new holdings
      const updatedScenario = {
        ...activeScenario,
        simulatedHoldings: updatedHoldings,
        lastUpdated: new Date()
      };
      
      // Recalculate metrics
      calculateMetrics(updatedScenario);
      
      // Update state
      setScenarios(prev => prev.map(s => 
        s.id === activeScenario.id ? updatedScenario : s
      ));
      setActiveScenario(updatedScenario);
      
      console.log(`[SCENARIO] Updated ${symbol} price to ${newPrice} in scenario ${activeScenario.name}`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to update holding price';
      setError(errorMsg);
      console.error('Failed to update holding price:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const addHolding = (holding: Omit<ScenarioHolding, 'currentPrice' | 'value' | 'scenarioId'>) => {
    if (!activeScenario) {
      setError('No active scenario');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Validate input data
      if (holding.shares <= 0) {
        throw new Error(`Invalid quantity: ${holding.shares}`);
      }
      if (holding.avgPrice <= 0) {
        throw new Error(`Invalid average price: ${holding.avgPrice}`);
      }
      
      // Validate current price
      const validation = validatePrice(holding.avgPrice, holding.symbol);
      if (!validation.valid) {
        throw new Error(`Invalid price for ${holding.symbol}: ${validation.error}`);
      }
      
      // Check if holding already exists
      const exists = activeScenario.simulatedHoldings.some(h => h.symbol === holding.symbol);
      if (exists) {
        throw new Error(`Holding already exists: ${holding.symbol}`);
      }
      
      const newHolding: ScenarioHolding = {
        ...holding,
        scenarioId: activeScenario.id,
        currentPrice: holding.avgPrice,
        simulatedPrice: holding.avgPrice,
        value: holding.shares * holding.avgPrice,
        notes: 'Added in simulation'
      };
      
      const updatedScenario = {
        ...activeScenario,
        simulatedHoldings: [...activeScenario.simulatedHoldings, newHolding],
        lastUpdated: new Date()
      };
      
      // Recalculate metrics
      calculateMetrics(updatedScenario);
      
      // Update state
      setScenarios(prev => prev.map(s => 
        s.id === activeScenario.id ? updatedScenario : s
      ));
      setActiveScenario(updatedScenario);
      
      console.log(`[SCENARIO] Added holding ${holding.symbol} to scenario ${activeScenario.name}`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to add holding';
      setError(errorMsg);
      console.error('Failed to add holding:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const removeHolding = (symbol: string) => {
    if (!activeScenario) {
      setError('No active scenario');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Check if holding exists
      const holdingExists = activeScenario.simulatedHoldings.some(h => h.symbol === symbol);
      if (!holdingExists) {
        throw new Error(`Holding not found: ${symbol}`);
      }
      
      const updatedHoldings = activeScenario.simulatedHoldings.filter(h => h.symbol !== symbol);
      
      const updatedScenario = {
        ...activeScenario,
        simulatedHoldings: updatedHoldings,
        lastUpdated: new Date()
      };
      
      // Recalculate metrics
      calculateMetrics(updatedScenario);
      
      // Update state
      setScenarios(prev => prev.map(s => 
        s.id === activeScenario.id ? updatedScenario : s
      ));
      setActiveScenario(updatedScenario);
      
      console.log(`[SCENARIO] Removed holding ${symbol} from scenario ${activeScenario.name}`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to remove holding';
      setError(errorMsg);
      console.error('Failed to remove holding:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const resetScenario = () => {
    if (!activeScenario) {
      setError('No active scenario');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Reset to base holdings
      const resetScenario = {
        ...activeScenario,
        simulatedHoldings: activeScenario.baseHoldings.map(holding => ({
          ...holding,
          scenarioId: activeScenario.id,
          simulatedPrice: holding.currentPrice,
          notes: 'Reset to base'
        })),
        lastUpdated: new Date()
      };
      
      // Recalculate metrics
      calculateMetrics(resetScenario);
      
      // Update state
      setScenarios(prev => prev.map(s => 
        s.id === activeScenario.id ? resetScenario : s
      ));
      setActiveScenario(resetScenario);
      
      console.log(`[SCENARIO] Reset scenario ${activeScenario.name} to base state`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to reset scenario';
      setError(errorMsg);
      console.error('Failed to reset scenario:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteScenario = (scenarioId: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const scenarioExists = scenarios.some(s => s.id === scenarioId);
      if (!scenarioExists) {
        throw new Error(`Scenario not found: ${scenarioId}`);
      }
      
      const updatedScenarios = scenarios.filter(s => s.id !== scenarioId);
      setScenarios(updatedScenarios);
      
      // If deleted scenario was active, clear active scenario
      if (activeScenario?.id === scenarioId) {
        setActiveScenario(null);
      }
      
      console.log(`[SCENARIO] Deleted scenario ${scenarioId}`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete scenario';
      setError(errorMsg);
      console.error('Failed to delete scenario:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const updateScenarioMetadata = (scenarioId: string, name?: string, description?: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const updatedScenarios = scenarios.map(scenario => {
        if (scenario.id === scenarioId) {
          return {
            ...scenario,
            name: name !== undefined ? name : scenario.name,
            description: description !== undefined ? description : scenario.description,
            lastUpdated: new Date()
          };
        }
        return scenario;
      });
      
      setScenarios(updatedScenarios);
      
      // Update active scenario if it's the one being updated
      if (activeScenario?.id === scenarioId) {
        setActiveScenario(updatedScenarios.find(s => s.id === scenarioId) || null);
      }
      
      console.log(`[SCENARIO] Updated metadata for scenario ${scenarioId}`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to update scenario metadata';
      setError(errorMsg);
      console.error('Failed to update scenario metadata:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const calculateMetrics = (scenario: ScenarioState) => {
    console.log('[SCENARIO] Calculating metrics for scenario:', scenario.name);
    
    let totalInvested = 0;
    let totalValue = 0;
    let totalProfit = 0;
    
    scenario.simulatedHoldings.forEach(holding => {
      // Validate position data
      if (holding.shares <= 0) {
        throw new Error(`Invalid quantity for ${holding.symbol}: ${holding.shares}`);
      }
      if (holding.avgPrice <= 0) {
        throw new Error(`Invalid avgPrice for ${holding.symbol}: ${holding.avgPrice}`);
      }
      if (holding.currentPrice <= 0) {
        throw new Error(`Invalid currentPrice for ${holding.symbol}: ${holding.currentPrice}`);
      }
      
      const investedValue = holding.shares * holding.avgPrice;
      const currentValue = holding.shares * holding.currentPrice;
      const profit = currentValue - investedValue;
      
      totalInvested += investedValue;
      totalValue += currentValue;
      totalProfit += profit;
    });
    
    const totalReturnPercent = (totalInvested > 0) ? (totalProfit / totalInvested) * 100 : 0;
    
    // Update scenario with calculated metrics
    scenario.totalValue = totalValue;
    scenario.totalGain = totalProfit;
    scenario.totalGainPercent = totalReturnPercent;
  };

  const calculateScenarioMetrics = () => {
    if (!activeScenario) {
      setError('No active scenario');
      return;
    }
    
    try {
      const updatedScenario = { ...activeScenario };
      calculateMetrics(updatedScenario);
      
      // Update state
      setScenarios(prev => prev.map(s => 
        s.id === activeScenario.id ? updatedScenario : s
      ));
      setActiveScenario(updatedScenario);
      
      console.log(`[SCENARIO] Recalculated metrics for ${activeScenario.name}`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to calculate metrics';
      setError(errorMsg);
      console.error('Failed to calculate metrics:', err);
    }
  };

  const value: ScenarioContextType = {
    scenarios,
    activeScenario,
    isLoading,
    error,
    createScenario,
    loadScenario,
    updateHoldingPrice,
    addHolding,
    removeHolding,
    resetScenario,
    deleteScenario,
    updateScenarioMetadata,
    calculateScenarioMetrics
  };

  return (
    <ScenarioContext.Provider value={value}>
      {children}
    </ScenarioContext.Provider>
  );
};

export const useScenario = (): ScenarioContextType => {
  const context = useContext(ScenarioContext);
  if (context === undefined) {
    throw new Error('useScenario must be used within a ScenarioProvider');
  }
  return context;
};