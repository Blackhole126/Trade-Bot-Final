/**
 * Portfolio Calculation Helper
 * 
 * CRITICAL: This is the SINGLE SOURCE OF TRUTH for all portfolio calculations.
 * All portfolio math MUST use these functions. No inline calculations allowed.
 * 
 * Mathematical Rules (MANDATORY):
 * - costBasis = shares × avgPrice
 * - marketValue = shares × currentPrice
 * - unrealizedValue = marketValue - costBasis
 * - unrealizedPercent = (unrealizedValue / costBasis) × 100 (only if valid)
 * 
 * Semantic Correctness Rules:
 * - Percentage is only meaningful when cost basis is substantial
 * - MIN_VALID_COST_BASIS ensures educational safety
 * - Extreme percentages from tiny positions are suppressed, not capped
 */

// Minimum cost basis for meaningful percentage calculation
// Below this threshold, percentage returns are educationally misleading
const MIN_VALID_COST_BASIS = 100; // ₹100 minimum for meaningful percentage

export interface HoldingMetrics {
  costBasis: number;
  marketValue: number;
  unrealizedValue: number;
  unrealizedPercent: number | null;
}

export interface PortfolioMetrics {
  totalCostBasis: number;
  totalMarketValue: number;
  totalUnrealizedValue: number;
  totalUnrealizedPercent: number | null;
  holdingCount: number;
}

/**
 * Calculate metrics for a single holding
 * @param shares - Number of shares held
 * @param avgPrice - Average purchase price per share
 * @param currentPrice - Current market price per share
 * @returns Calculated metrics with safe percentage handling
 */
export function calculateHoldingMetrics(
  shares: number,
  avgPrice: number,
  currentPrice: number
): HoldingMetrics {
  // Validate inputs
  if (shares < 0) {
    throw new Error(`Invalid shares: ${shares}. Must be >= 0`);
  }
  if (avgPrice < 0) {
    throw new Error(`Invalid avgPrice: ${avgPrice}. Must be >= 0`);
  }
  if (currentPrice < 0) {
    throw new Error(`Invalid currentPrice: ${currentPrice}. Must be >= 0`);
  }

  // Step 1: Calculate cost basis (what was originally invested)
  const costBasis = shares * avgPrice;

  // Step 2: Calculate market value (current worth)
  const marketValue = shares * currentPrice;

  // Step 3: Calculate unrealized P&L (gain/loss in currency)
  const unrealizedValue = marketValue - costBasis;

  // Step 4: Calculate percentage (SEMANTIC CORRECTNESS: only if cost basis is meaningful)
  let unrealizedPercent: number | null = null;
  
  // Percentage is only valid when:
  // 1. Cost basis meets minimum threshold (educational safety)
  // 2. Shares > 0
  // 3. Current price > 0
  if (costBasis >= MIN_VALID_COST_BASIS && shares > 0 && currentPrice > 0) {
    unrealizedPercent = (unrealizedValue / costBasis) * 100;
    unrealizedPercent = Math.round(unrealizedPercent * 100) / 100;
    // NO CAPPING - if invalid, suppress entirely
  }

  return {
    costBasis,
    marketValue,
    unrealizedValue,
    unrealizedPercent
  };
}

/**
 * Calculate aggregate metrics for entire portfolio
 * @param holdings - Array of holdings with shares, avgPrice, currentPrice
 * @returns Aggregated portfolio metrics
 */
export function calculatePortfolioMetrics(
  holdings: Array<{ shares: number; avgPrice: number; currentPrice: number }>
): PortfolioMetrics {
  let totalCostBasis = 0;
  let totalMarketValue = 0;

  // Sum up all holdings
  for (const holding of holdings) {
    const metrics = calculateHoldingMetrics(
      holding.shares,
      holding.avgPrice,
      holding.currentPrice
    );
    
    totalCostBasis += metrics.costBasis;
    totalMarketValue += metrics.marketValue;
  }

  // Calculate total unrealized P&L
  const totalUnrealizedValue = totalMarketValue - totalCostBasis;

  // Calculate total percentage (SEMANTIC CORRECTNESS: only if meaningful)
  let totalUnrealizedPercent: number | null = null;
  
  if (totalCostBasis >= MIN_VALID_COST_BASIS) {
    totalUnrealizedPercent = (totalUnrealizedValue / totalCostBasis) * 100;
    totalUnrealizedPercent = Math.round(totalUnrealizedPercent * 100) / 100;
    // NO CAPPING - if invalid, suppress entirely
  }

  return {
    totalCostBasis,
    totalMarketValue,
    totalUnrealizedValue,
    totalUnrealizedPercent,
    holdingCount: holdings.length
  };
}

/**
 * Format percentage for display
 * @param percent - Percentage value or null
 * @returns Formatted string for UI display
 */
export function formatPercentage(percent: number | null): string {
  if (percent === null) {
    return '—';
  }
  
  const sign = percent >= 0 ? '+' : '';
  return `${sign}${percent.toFixed(2)}%`;
}

/**
 * Validate that portfolio totals match sum of holdings
 * This is a self-check function to ensure calculation integrity
 */
export function validatePortfolioIntegrity(
  holdings: Array<{ shares: number; avgPrice: number; currentPrice: number }>,
  reportedTotalValue: number,
  reportedTotalGain: number
): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  const calculated = calculatePortfolioMetrics(holdings);
  
  // Check total market value
  const valueDiff = Math.abs(calculated.totalMarketValue - reportedTotalValue);
  if (valueDiff > 0.01) {
    errors.push(
      `Total market value mismatch: calculated ${calculated.totalMarketValue.toFixed(2)}, ` +
      `reported ${reportedTotalValue.toFixed(2)}`
    );
  }
  
  // Check total unrealized gain
  const gainDiff = Math.abs(calculated.totalUnrealizedValue - reportedTotalGain);
  if (gainDiff > 0.01) {
    errors.push(
      `Total unrealized gain mismatch: calculated ${calculated.totalUnrealizedValue.toFixed(2)}, ` +
      `reported ${reportedTotalGain.toFixed(2)}`
    );
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}
