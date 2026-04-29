// HFT API Service Types
export type ProductType = 'CNC' | 'MIS'; // CNC = Delivery, MIS = Intraday

export interface HftBotConfig {
    mode: 'live';
    tickers: string[];
    riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
    maxAllocation: number;
    productType: ProductType; // CNC (Delivery) or MIS (Intraday)
}

export interface HftPortfolio {
    totalValue: number;
    cash: number;
    holdings: Record<string, HftHolding>;
    tradeLog: HftTrade[];
    startingBalance: number;
    /** Dhan "Investment" column: sum of avgCostPrice × qty for each holding */
    investedValue?: number;
    /** Dhan "Today's Profit": sum of unrealizedProfit from positions API */
    todayGain?: number;
    /** Rolling snapshots of totalValue over time for the performance chart */
    portfolioHistory?: Array<{ time: string; value: number }>;
}

export interface HftHolding {
    symbol: string;
    quantity: number;
    avgPrice: number;
    currentPrice?: number;
    value?: number;
    pnl?: number;
    pnlPercent?: number;
}

export interface HftTrade {
    symbol: string;
    action: 'BUY' | 'SELL';
    quantity: number;
    price: number;
    timestamp: string;
    total: number;
    portfolioValue?: number;
}

export interface HftSignal {
    symbol: string;
    recommendation: string;
    confidence: number;
    reasoning?: string;
    risk_score?: number;
    position_size?: number;
    target_price?: number | null;
    stop_loss?: number | null;
    timestamp?: string;
    prediction?: any;
}

export interface HftBotData {
    portfolio: HftPortfolio;
    config: HftBotConfig;
    isRunning: boolean;
    analysis?: HftSignal[];
    /** Set when Live mode + Dhan configured but portfolio fetch failed (e.g. token/network). */
    dhan_error?: string;
}

export interface HftLiveStatus {
    connected: boolean;
    mode?: string;
    lastUpdate?: string;
    dhan_configured?: boolean;
    /** Error from last Dhan portfolio fetch when in Live mode. */
    dhan_error?: string | null;
    broker?: string;
    account?: string;
    lastSync?: string;
    error?: string;
}

export interface HftMcpStatus {
    mcp_available: boolean;
    server_initialized: boolean;
}

export interface HftMcpAnalysisRequest {
    symbol: string;
    timeframe?: string;
    analysis_type?: string;
}

export interface HftMcpAnalysisResponse {
    recommendation: string;
    confidence: number;
    current_price: number;
    target_price: number;
    stop_loss: number;
    reasoning?: string;
}

export interface HftWatchlistResponse {
    message: string;
    tickers: string[];
}

export interface HftSettingsUpdate {
    mode?: 'live';
    riskLevel?: 'LOW' | 'MEDIUM' | 'HIGH';
    maxAllocation?: number;
    stopLoss?: number;
    productType?: ProductType; // CNC (Delivery) or MIS (Intraday)
}
