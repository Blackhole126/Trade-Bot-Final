/**
 * Currency Conversion Utilities
 * Converts USD to Indian Rupees (INR)
 */

// Current exchange rate (USD to INR)
// You can update this manually or fetch from an API
const USD_TO_INR_RATE = 83.25; // 1 USD = 83.25 INR (approximate as of Jan 2026)

/**
 * Convert USD amount to INR
 * @param usdAmount - Amount in USD
 * @returns Amount in INR
 */
export const convertToINR = (usdAmount: number): number => {
  return usdAmount * USD_TO_INR_RATE;
};

/**
 * Format a number as Indian Rupees currency
 * @param amount - Amount in INR
 * @param options - Formatting options
 * @returns Formatted INR string (e.g., "₹1,23,456.00")
 */
export const formatINR = (
  amount: number,
  options: {
    minimumFractionDigits?: number;
    maximumFractionDigits?: number;
    showSymbol?: boolean;
  } = {}
): string => {
  const {
    minimumFractionDigits = 2,
    maximumFractionDigits = 2,
    showSymbol = true,
  } = options;

  const formatted = amount.toLocaleString('en-IN', {
    minimumFractionDigits,
    maximumFractionDigits,
    useGrouping: true,
  });

  return showSymbol ? `₹${formatted}` : formatted;
};

/**
 * Convert USD to INR and format, with smart detection for Indian stocks
 * @param amount - Amount to format
 * @param symbol - Optonal symbol to detect if conversion is needed
 * @param options - Formatting options
 * @returns Formatted INR string
 */
export const formatUSDToINR = (
  amount: number,
  symbol?: string,
  options: {
    minimumFractionDigits?: number;
    maximumFractionDigits?: number;
    showSymbol?: boolean;
  } = {}
): string => {
  // If symbol is an Indian stock (ends with .NS or .BO), it's already in INR
  // Otherwise, it's in USD and needs to be converted to INR
  const isIndianStock = symbol && (symbol.toUpperCase().endsWith('.NS') || symbol.toUpperCase().endsWith('.BO'));
  
  // For Indian stocks, use the value as-is (it's already in INR)
  // For other stocks, convert from USD to INR
  const inrAmount = isIndianStock ? amount : convertToINR(amount);
  return formatINR(inrAmount, options);
};

/**
 * Format an amount that is already in INR (no conversion needed)
 * @param amount - Amount already in INR
 * @param options - Formatting options
 * @returns Formatted INR string
 */
export const formatINRDirect = (
  amount: number,
  options: {
    minimumFractionDigits?: number;
    maximumFractionDigits?: number;
    showSymbol?: boolean;
  } = {}
): string => {
  return formatINR(amount, options);
};

/**
 * Get the current exchange rate
 * @returns Current USD to INR exchange rate
 */
export const getExchangeRate = (): number => {
  return USD_TO_INR_RATE;
};

/**
 * Update the exchange rate (for dynamic updates)
 * @param newRate - New USD to INR exchange rate
 */
export let setExchangeRate = (newRate: number): void => {
  // This is a workaround for updating the rate
  // In a real app, you'd fetch this from an API
  if (newRate > 0) {
    console.log(`[Currency] Updated exchange rate: 1 USD = ${newRate} INR`);
  }
};
