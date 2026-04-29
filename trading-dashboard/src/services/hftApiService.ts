import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
    HftBotData,
    HftLiveStatus,
    HftMcpStatus,
    HftMcpAnalysisRequest,
    HftMcpAnalysisResponse,
    HftWatchlistResponse,
    HftSettingsUpdate,
    HftTrade,
    HftPortfolio
} from '../types/hft';

// Use same backend as health check so BOT and "System Offline" use one server
import { config } from '../config';
const API_BASE_URL = config.API_BASE_URL;

// Create axios instance with default config
const api: AxiosInstance = axios.create({
    baseURL: `${API_BASE_URL}/api`,
    timeout: 120000, // 120 seconds so long analysis/bot init doesn't timeout
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor: attach auth token (so watchlist and bot start are per-user)
api.interceptors.request.use(
    (config) => {
        // Priority: sessionStorage (tab-specific) > localStorage (persistent)
        const token = typeof sessionStorage !== 'undefined'
            ? (sessionStorage.getItem('token') || localStorage.getItem('token'))
            : null;

        if (token && token !== 'no-auth-required' && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        console.log(`[HFT API] Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
    },
    (error: AxiosError) => {
        console.error('[HFT API] Request Error:', error);
        return Promise.reject(error);
    }
);

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => {
        console.log(`[HFT API] Response: ${response.status} ${response.config.url}`);
        return response;
    },
    (error: AxiosError) => {
        console.error('[HFT API] Response Error:', error.response?.data || error.message);

        // Handle specific error cases
        if (error.response?.status === 404) {
            throw new Error('API endpoint not found');
        } else if (error.response?.status === 500) {
            throw new Error('Server error occurred');
        } else if (error.code === 'ECONNABORTED') {
            throw new Error('Request timeout');
        } else if (!error.response) {
            throw new Error('Network error - please check if the backend server is running');
        }

        throw error;
    }
);

export const hftApiService = {
    async getBotStatus(): Promise<{ status: 'INITIALIZING' | 'READY' | 'ERROR' | 'STOPPED' }> {
        try {
            const response = await api.get<{ status: 'INITIALIZING' | 'READY' | 'ERROR' | 'STOPPED' }>('/bot/status');
            return response.data;
        } catch (error) {
            console.error('Error getting bot status:', error);
            throw error;
        }
    },

    // ===== Complete Bot Data =====
    async getBotData(): Promise<HftBotData> {
        try {
            const response = await api.get<HftBotData>('/bot-data', { timeout: 60000 }); // 60s for live Dhan fetch / bot init when not ready
            return response.data;
        } catch (error) {
            console.error('Error getting bot data:', error);
            throw error;
        }
    },

    // ===== Portfolio Management =====
    async getPortfolio(): Promise<HftPortfolio> {
        try {
            const response = await api.get<HftPortfolio>('/portfolio');
            return response.data;
        } catch (error) {
            console.error('Error getting portfolio:', error);
            throw error;
        }
    },

    // ===== Trading History =====
    async getTrades(limit: number = 10): Promise<HftTrade[]> {
        try {
            const response = await api.get<HftTrade[]>(`/trades?limit=${limit}`);
            return response.data;
        } catch (error) {
            console.error('Error getting trades:', error);
            throw error;
        }
    },

    // ===== Per-user Demat (broker) credentials =====
    async getDematStatus(): Promise<{ linked: boolean; broker?: string; client_id_masked?: string }> {
        const response = await api.get<{ linked: boolean; broker?: string; client_id_masked?: string }>('/user/demat');
        return response.data;
    },

    async saveDemat(broker: string, clientId: string, accessToken: string): Promise<{ success: boolean; message?: string }> {
        const response = await api.post<{ success: boolean; message?: string }>('/user/demat', {
            broker: broker || 'dhan',
            client_id: clientId,
            access_token: accessToken,
        });
        return response.data;
    },

    async refreshDematToken(accessToken: string): Promise<{ success: boolean; message?: string }> {
        const response = await api.put<{ success: boolean; message?: string }>('/user/demat/token', {
            access_token: accessToken,
        });
        return response.data;
    },

    // ===== Watchlist Management =====
    async getWatchlist(): Promise<string[]> {
        try {
            const response = await api.get<string[]>('/watchlist');
            // Backend returns array directly, not wrapped in {tickers: []}
            return Array.isArray(response.data) ? response.data : [];
        } catch (error) {
            console.error('Error getting watchlist:', error);
            throw error;
        }
    },

    async addToWatchlist(ticker: string): Promise<HftWatchlistResponse> {
        try {
            const response = await api.post<HftWatchlistResponse>(`/watchlist/add/${ticker}`);
            return response.data;
        } catch (error) {
            console.error('Error adding to watchlist:', error);
            throw error;
        }
    },

    async removeFromWatchlist(ticker: string): Promise<HftWatchlistResponse> {
        try {
            const response = await api.delete<HftWatchlistResponse>(`/watchlist/remove/${ticker}`);
            return response.data;
        } catch (error) {
            console.error('Error removing from watchlist:', error);
            throw error;
        }
    },

    async bulkUpdateWatchlist(tickers: string[], action: 'ADD' | 'REMOVE' = 'ADD'): Promise<HftWatchlistResponse> {
        try {
            const response = await api.post<HftWatchlistResponse>('/watchlist/bulk', {
                tickers,
                action,
            });
            return response.data;
        } catch (error) {
            console.error('Error bulk updating watchlist:', error);
            throw error;
        }
    },


    // ===== MCP (Model Context Protocol) API Endpoints =====
    async mcpAnalyzeMarket(analysisRequest: HftMcpAnalysisRequest): Promise<HftMcpAnalysisResponse> {
        try {
            const response = await api.post<HftMcpAnalysisResponse>('/mcp/analyze', analysisRequest);
            return response.data;
        } catch (error) {
            console.error('MCP market analysis error:', error);
            throw error;
        }
    },

    async mcpExecuteTrade(tradeRequest: any): Promise<any> {
        try {
            const response = await api.post('/mcp/execute', tradeRequest);
            return response.data;
        } catch (error) {
            console.error('MCP trade execution error:', error);
            throw error;
        }
    },


    async getMcpStatus(): Promise<HftMcpStatus> {
        try {
            const response = await api.get<HftMcpStatus>('/mcp/status');
            return response.data;
        } catch (error) {
            console.error('MCP status error:', error);
            throw error;
        }
    },

    // ===== Bot Control =====
    async startBot(): Promise<{ message: string }> {
        try {
            const response = await api.post<{ message: string }>('/bot/start');
            return response.data;
        } catch (error) {
            console.error('Error starting bot:', error);
            throw error;
        }
    },

    async startBotWithSymbol(symbol: string): Promise<any> {
        try {
            // Use longer timeout for bot initialization
            const response = await api.post('/bot/start-with-symbol', { symbol }, { timeout: 10000 }); // 10 seconds - should return quickly
            return response.data;
        } catch (error) {
            console.error('Error starting bot with symbol:', error);
            throw error;
        }
    },

    async stopBot(): Promise<{ message: string }> {
        try {
            const response = await api.post<{ message: string }>('/bot/stop');
            return response.data;
        } catch (error) {
            console.error('Error stopping bot:', error);
            throw error;
        }
    },

    // ===== Settings Management =====
    async getSettings(): Promise<any> {
        try {
            const response = await api.get('/settings');
            return response.data;
        } catch (error) {
            console.error('Error getting settings:', error);
            throw error;
        }
    },

    async updateSettings(settings: HftSettingsUpdate): Promise<{ message: string }> {
        try {
            const response = await api.post<{ message: string }>('/settings', settings);
            return response.data;
        } catch (error) {
            console.error('Error updating settings:', error);
            throw error;
        }
    },

    // ===== Live Trading Status =====
    async getLiveStatus(): Promise<HftLiveStatus> {
        try {
            const response = await api.get<HftLiveStatus>('/live-status', { timeout: 10000 }); // 10 seconds for live status
            return response.data;
        } catch (error) {
            console.error('Error getting live status:', error);
            throw error;
        }
    },

    async syncLivePortfolio(): Promise<any> {
        try {
            const response = await api.post('/live/sync');
            return response.data;
        } catch (error) {
            console.error('Error syncing live portfolio:', error);
            throw error;
        }
    },

    // ===== Vetting predictions (Market Scan backend) =====
    async getPredictions(symbols: string[] = ['RELIANCE.NS'], horizon: string = 'intraday'): Promise<any> {
        try {
            const syms = symbols.length ? symbols.join(',') : 'RELIANCE.NS';
            const response = await api.get(`/predictions?symbols=${encodeURIComponent(syms)}&horizon=${encodeURIComponent(horizon)}`);
            return response.data;
        } catch (error) {
            console.error('Error fetching predictions:', error);
            throw error;
        }
    },

    // ===== Place order (buy/sell) =====
    async placeOrder(symbol: string, side: 'BUY' | 'SELL', quantity: number, orderType: string = 'MARKET', price?: number, security_id?: string, exchange_segment?: string): Promise<any> {
        try {
            const body: Record<string, unknown> = { symbol, side, quantity, order_type: orderType, price, security_id, exchange_segment };
            const response = await api.post('/order', body);
            return response.data;
        } catch (error) {
            console.error('Error placing order:', error);
            throw error;
        }
    },

    // ===== Health Check =====
    async healthCheck(): Promise<boolean> {
        try {
            const response = await api.get('/status');
            return response.status === 200;
        } catch (error) {
            console.error('Health check failed:', error);
            return false;
        }
    },

    // ===== Production-level API calls =====
    async getSignalPerformance(): Promise<any> {
        try {
            const response = await api.get('/production/signal-performance');
            return response.data;
        } catch (error) {
            console.error('Error getting signal performance:', error);
            throw error;
        }
    },

    async getRiskMetrics(): Promise<any> {
        try {
            const response = await api.get('/production/risk-metrics');
            return response.data;
        } catch (error) {
            console.error('Error getting risk metrics:', error);
            throw error;
        }
    },

    async makeProductionDecision(symbol: string): Promise<any> {
        try {
            const response = await api.post('/production/make-decision', { symbol });
            return response.data;
        } catch (error) {
            console.error('Error making production decision:', error);
            throw error;
        }
    },

    async getLearningInsights(): Promise<any> {
        try {
            const response = await api.get('/production/learning-insights');
            return response.data;
        } catch (error) {
            console.error('Error getting learning insights:', error);
            throw error;
        }
    },

    async getDecisionHistory(days: number = 7): Promise<any> {
        try {
            const response = await api.get(`/production/decision-history?days=${days}`);
            return response.data;
        } catch (error) {
            console.error('Error getting decision history:', error);
            throw error;
        }
    },

    // ===== Analysis Result (polls stock_analysis/ folder on backend) =====
    async getAnalysisResult(symbol: string): Promise<{
        status: 'pending' | 'ready' | 'error';
        symbol?: string;
        data?: any;
        message?: string;
    }> {
        try {
            const response = await api.get(`/analysis-result?symbol=${encodeURIComponent(symbol)}`, {
                timeout: 30000,
            });
            const result = response.data;

            // --- OVERRIDE: fetch the professional signal file written by analyze_stock ---
            // This file is written immediately after RL analysis in testindia.py
            // and contains the EXACT BUY/SELL/HOLD that appears in the terminal output.
            if (result?.status === 'ready' && result?.data) {
                try {
                    const sigResp = await api.get(`/trade-signal?symbol=${encodeURIComponent(symbol)}`, {
                        timeout: 5000,
                    });
                    const sig = sigResp.data;
                    if (sig?.success && sig?.action && ['BUY', 'SELL', 'HOLD'].includes(sig.action)) {
                        // Directly override the recommendation and reasoning in the result data
                        result.data.recommendation = sig.action;
                        if (sig.confidence_score !== undefined && sig.confidence_score >= 0 && sig.confidence_score <= 1) {
                            result.data.confidence = sig.confidence_score;
                        }
                        if (sig.reasoning) {
                            result.data.reasoning = `[RL: ${sig.rl_recommendation ?? sig.action}] ${sig.reasoning}`;
                        }
                        if (sig.stop_loss && sig.stop_loss > 0) {
                            result.data.stop_loss = sig.stop_loss;
                        }
                        if (sig.take_profit && sig.take_profit > 0) {
                            result.data.target_price = sig.take_profit;
                        }
                        console.log(`[HFT API] Professional signal loaded for ${symbol}: ${sig.action} (RL: ${sig.rl_recommendation})`);
                    }
                } catch (_sigErr) {
                    // Signal file not yet available — use the base analysis result as-is
                    console.log(`[HFT API] No professional signal file for ${symbol} yet`);
                }
            }
            return result;
        } catch (error) {
            console.error('Error getting analysis result:', error);
            return { status: 'error', message: 'Request failed' };
        }
    },


    // ===== Auto-Execute Signal =====
    async executeSignal(symbol: string, username: string, force: boolean = false): Promise<{
        success: boolean;
        message?: string;
        order_id?: string;
        recommendation?: string;
    }> {
        try {
            const response = await api.post('/execute-signal', { symbol, username, force });
            return response.data;
        } catch (error: any) {
            console.error(`Error executing signal for ${symbol}:`, error);
            return {
                success: false,
                message: error.response?.data?.message || error.message || 'Execution failed'
            };
        }
    },
};

// ===== SSE Stream =====
export function createBotStream(
    onLog: (level: string, message: string) => void,
    onData: (payload: any) => void,
    onConnected?: () => void,
    onBotCycleStart?: (data: any) => void,
    onTickerComplete?: (data: any) => void,
    onBotCycleComplete?: (data: any) => void,
): () => void {
    const url = `${API_BASE_URL}/api/stream`;
    const es = new EventSource(url);

    es.onopen = () => onConnected?.();

    es.onmessage = (ev) => {
        try {
            const parsed = JSON.parse(ev.data);
            if (parsed.type === 'log') {
                onLog(parsed.level ?? 'INFO', parsed.message ?? '');
            } else if (parsed.type === 'data') {
                onData(parsed.payload);
            } else if (parsed.type === 'connected') {
                onConnected?.();
            } else if (parsed.type === 'bot_cycle_start') {
                onBotCycleStart?.(parsed);
            } else if (parsed.type === 'ticker_complete') {
                onTickerComplete?.(parsed);
            } else if (parsed.type === 'bot_cycle_complete') {
                onBotCycleComplete?.(parsed);
            }
        } catch {
            // ignore malformed events
        }
    };

    es.onerror = () => {
        // EventSource will auto-reconnect; no action needed
    };

    return () => es.close();
}

// ===== Utility Functions =====
export const formatCurrency = (amount: number | null | undefined): string => {
    // Handle NaN, undefined, null values
    if (amount === null || amount === undefined || isNaN(amount)) {
        return '₹0.00';
    }

    // For sidebar metrics, use compact notation for large numbers
    if (Math.abs(amount) >= 10000000) { // 1 crore
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            notation: 'compact',
            maximumFractionDigits: 2,
        }).format(amount);
    } else if (Math.abs(amount) >= 100000) { // 1 lakh
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0,
        }).format(amount);
    } else {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 2,
        }).format(amount);
    }
};

export const formatPercentage = (value: number | null | undefined): string => {
    // Handle NaN, undefined, null values
    if (value === null || value === undefined || isNaN(value)) {
        return '0.00%';
    }

    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
};

export const formatNumber = (value: number): string => {
    return new Intl.NumberFormat('en-IN').format(value);
};

// ===== Active Orders Monitoring =====
export const getActiveOrders = async () => {
    try {
        const response = await api.get('/active_orders');
        return response.data;
    } catch (error) {
        console.error('Error getting active orders:', error);
        throw error;
    }
};

export default hftApiService;
