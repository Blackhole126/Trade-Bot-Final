'use client';

import React, { useState, useEffect } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import Layout from '@/components/Layout';
import { useTheme } from '@/contexts/ThemeContext';
import HftDashboard from '@/components/hft/HftDashboard';
import HftPortfolio from '@/components/hft/HftPortfolio';
import HftLoadingOverlay from '@/components/hft/HftLoadingOverlay';
import HftSettingsModal from '@/components/hft/HftSettingsModal';
import { hftApiService, formatCurrency, formatPercentage, createBotStream } from '@/services/hftApiService';
import { userAPI } from '@/services/api';
import type { HftBotData, HftChatMessage } from '@/types/hft';
import { CheckCircle2, AlertCircle, RefreshCw, Play, Square, LayoutDashboard, Briefcase, MessageCircle, Loader2 } from 'lucide-react';

export default function HftPage() {
    const { theme } = useTheme();
    const isLight = theme === 'light';
    const isSpace = theme === 'space';

    const [activeTab, setActiveTab] = useState<'dashboard' | 'portfolio' | 'activity' | 'watchlist'>('dashboard');
    const [botData, setBotData] = useState<HftBotData>({
        portfolio: {
            totalValue: 0,
            cash: 0,
            holdings: {},
            tradeLog: [],
            startingBalance: 0
        },
        config: {
            mode: 'live',
            tickers: [],
            riskLevel: 'MEDIUM',
            maxAllocation: 0.25
        },
        isRunning: false,
    });

    const [loading, setLoading] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    const [liveStatus, setLiveStatus] = useState<any>(null);
    const [connected, setConnected] = useState(false);
    /** Incremented on Start Bot so analysis panels remount and never show cached/previous output. */
    const [botRunKey, setBotRunKey] = useState(0);
    const [globalBotStatus, setGlobalBotStatus] = useState<'IDLE' | 'INITIALIZING' | 'READY' | 'ERROR' | 'STOPPED'>('IDLE');

    // Poll for bot status separately — only every 30 s while analysis is running
    // so we don't flood the busy event loop with 120 s-timeout requests.
    useEffect(() => {
        const checkStatus = async () => {
            try {
                const res = await hftApiService.getBotStatus();
                setGlobalBotStatus(res.status);
            } catch (e) {
                // Silent catch — status is non-critical
            }
        };
        checkStatus();
        const interval = setInterval(checkStatus, 30000); // 30 s
        return () => clearInterval(interval);
    }, []);

    // SSE stream: connect once and keep alive; also do an initial REST load
    useEffect(() => {
        initializeApp();

        const stopStream = createBotStream(
            (_level, _message) => { /* logs no longer shown in UI */ },
            (payload) => {
                // Live bot data snapshot from SSE — never overwrite non-zero cached values with 0
                setConnected(true);
                setBotData(prev => {
                    const prevHoldings = prev.portfolio.holdings || {};
                    const newHoldings = payload.holdings && Object.keys(payload.holdings).length > 0
                        ? payload.holdings
                        : prevHoldings;

                    // Compute totalValue from holdings + cash as a safety net when backend sends 0
                    const rawCash = (payload.cash != null && payload.cash > 0) ? payload.cash : prev.portfolio.cash;
                    const rawTotal = (payload.totalValue != null && payload.totalValue > 0) ? payload.totalValue : prev.portfolio.totalValue;
                    // If still 0 but holdings exist, derive it
                    const holdingsMarketValue = Object.values(newHoldings).reduce((sum: number, h: any) => {
                        const price = h.currentPrice || h.avgPrice || 0;
                        const qty = h.quantity || h.qty || 0;
                        return sum + price * qty;
                    }, 0);
                    const derivedTotal = rawTotal > 0 ? rawTotal : (rawCash + holdingsMarketValue) || prev.portfolio.totalValue;

                    return {
                        ...prev,
                        isRunning: payload.isRunning ?? prev.isRunning,
                        portfolio: {
                            ...prev.portfolio,
                            cash: rawCash,
                            totalValue: derivedTotal,
                            unrealizedPnL: payload.unrealizedPnL ?? prev.portfolio.unrealizedPnL,
                            realizedPnL: payload.realizedPnL ?? prev.portfolio.realizedPnL,
                            holdings: newHoldings,
                            investedValue: payload.investedValue ?? prev.portfolio.investedValue,
                            todayGain: payload.todayGain ?? prev.portfolio.todayGain,
                            portfolioHistory: (payload.portfolioHistory && payload.portfolioHistory.length > 0)
                                ? payload.portfolioHistory
                                : prev.portfolio.portfolioHistory,
                        },
                        analysis: payload.analysis ?? prev.analysis,
                    };
                });
            },
            () => setConnected(true),
            // Bot cycle started
            (data) => {
                console.log('🔄 Bot cycle started:', data);
                toast.success(data.message || 'Bot started analyzing watchlist stocks');
            },
            // Ticker analysis complete
            (data) => {
                console.log(`✅ ${data.symbol} analysis complete (${data.completed}/${data.total})`);
                // Optional: show progress toast or update UI
            },
            // Bot cycle complete - stopped automatically
            async (data) => {
                console.log('⏹ Bot cycle complete:', data);
                // Update bot status to stopped immediately
                setBotData(prev => ({ ...prev, isRunning: false }));
                setGlobalBotStatus('STOPPED');
                
                // Force refresh bot data from backend to ensure UI is in sync
                try {
                    await refreshData();
                } catch (err) {
                    console.error('Error refreshing data after cycle complete:', err);
                }
                
                // Show success notification
                toast.success(data.message || 'One cycle completed! Bot stopped.', {
                    duration: 8000,
                    icon: '✅'
                });
                
                console.log('✅ Bot cycle complete notification shown');
            },
        );

        // Fallback polling every 60 s (much less aggressive now that SSE handles live updates)
        const interval = setInterval(refreshData, 60000);
        return () => {
            stopStream();
            clearInterval(interval);
        };
    }, []);

    const initializeApp = async () => {
        try {
            setLoading(true);
            await loadDataFromBackend();
            await loadLiveStatus();
            setConnected(true);
            setConnected(true);
        } catch (error) {
            console.error('Error initializing app:', error);
            toast.error('Failed to initialize application');
            setConnected(false);
        } finally {
            setLoading(false);
        }
    };

    const loadDataFromBackend = async () => {
        try {
            const data = await hftApiService.getBotData();
            // Ensure mode is properly set from backend response
            const backendMode = data?.config?.mode || 'live';
            // Also fetch watchlist directly to ensure we have the latest
            let watchlistTickers: string[] = [];
            try {
                watchlistTickers = await hftApiService.getWatchlist();
            } catch (watchlistErr) {
                // Fallback to tickers from bot data if watchlist endpoint fails
                watchlistTickers = data?.config?.tickers || [];
            }
            setBotData(prev => ({
                ...prev,
                ...data,
                config: {
                    ...prev.config,
                    ...data.config,
                    mode: backendMode,  // Use mode from backend
                    tickers: watchlistTickers  // Use watchlist from dedicated endpoint
                }
            }));
            setConnected(true);
            // Update live status based on mode
            if (backendMode === 'live') {
                await loadLiveStatus();
            }
        } catch (error: any) {
            // A timeout means the backend is slow/busy with ML analysis — NOT offline.
            // Only mark offline for true network connection failures.
            const isTimeout = error?.message?.includes('timeout') || error?.code === 'ECONNABORTED';
            const isNetworkError = error?.message === 'Network Error' || error?.code === 'ERR_NETWORK';
            if (isNetworkError && !botData.isRunning) {
                // Only mark offline for true connection failures AND only when bot is NOT running
                // (during ML analysis, even network stack can hiccup — don't show System Offline)
                setConnected(false);
            }
            // Silently keep last known state for timeouts or when bot is running
        }
    };

    const loadLiveStatus = async () => {
        try {
            const status = await hftApiService.getLiveStatus();
            setLiveStatus(status);
        } catch (error) {
            console.error('Error loading live status:', error);
        }
    };

    const refreshData = async () => {
        try {
            await loadDataFromBackend();
            await loadLiveStatus();
            try {
                await hftApiService.syncLivePortfolio();
            } catch { /* optional */ }
        } catch (error) {
            console.error('Error refreshing data:', error);
        }
    };



    const handleStartBot = async () => {
        try {
            setLoading(true);
            // 1. Load this user's personal watchlist from MongoDB
            const userTickers = await userAPI.getWatchlist();
            // 2. If the user has tickers, sync them to the bot before starting
            if (userTickers.length > 0) {
                try {
                    await hftApiService.bulkUpdateWatchlist(userTickers, 'ADD');
                } catch {
                    // If bulk update fails, still try to start
                }
            }
            // 3. Start the bot (it now has the user's tickers)
            await hftApiService.startBot();
            // 4. New run: remount analysis panels so they never show cached/previous output
            setBotRunKey(k => k + 1);
            // 5. Mark as running so panels show "Processing" until backend finishes
            setBotData(prev => ({ ...prev, isRunning: true }));
            setGlobalBotStatus('INITIALIZING');
            toast.success('Bot started! Wait for analysis to finish before results appear.');
            // 6. Refresh after a short delay to pick up backend state
            setTimeout(() => refreshData(), 3000);
        } catch (error) {
            console.error('Error starting bot:', error);
            toast.error('Failed to start bot');
        } finally {
            setLoading(false);
        }
    };

    const handleStopBot = async () => {
        try {
            setLoading(true);
            await hftApiService.stopBot();
            setBotData(prev => ({ ...prev, isRunning: false }));
            toast.success('Bot stopped successfully!');
            await refreshData();
        } catch (error) {
            console.error('Error stopping bot:', error);
            // Always mark as stopped so UI is not stuck when backend is down or request fails
            setBotData(prev => ({ ...prev, isRunning: false }));
            toast.error('Failed to stop bot (backend may be offline)');
        } finally {
            setLoading(false);
        }
    };

    const handleAddTicker = async (ticker: string) => {
        try {
            // Normalize ticker format
            const normalizedTicker = ticker.toUpperCase().trim();
            const tickerToAdd = normalizedTicker.endsWith('.NS') || normalizedTicker.endsWith('.BO')
                ? normalizedTicker
                : normalizedTicker + '.NS';

            // Call backend API
            const response = await hftApiService.addToWatchlist(tickerToAdd);

            // Update UI immediately with response data
            setBotData(prev => ({
                ...prev,
                config: {
                    ...prev.config,
                    tickers: response.tickers || []
                }
            }));

            toast.success(response.message || `Added ${tickerToAdd} to watchlist`);
        } catch (error) {
            console.error('Error adding ticker:', error);
            toast.error('Failed to add ticker');
            // Refresh to get correct state on error
            await refreshData();
        }
    };

    const handleRemoveTicker = async (ticker: string) => {
        try {
            // Normalize ticker format
            const normalizedTicker = ticker.toUpperCase().trim();
            const tickerToRemove = normalizedTicker.endsWith('.NS') || normalizedTicker.endsWith('.BO')
                ? normalizedTicker
                : normalizedTicker + '.NS';

            // Call backend API
            const response = await hftApiService.removeFromWatchlist(tickerToRemove);

            // Update UI immediately with response data
            setBotData(prev => ({
                ...prev,
                config: {
                    ...prev.config,
                    tickers: response.tickers || []
                }
            }));

            toast.success(response.message || `Removed ${tickerToRemove} from watchlist`);
        } catch (error) {
            console.error('Error removing ticker:', error);
            toast.error('Failed to remove ticker');
            // Refresh to get correct state on error
            await refreshData();
        }
    };

    const handleSaveSettings = async (settings: any) => {
        try {
            setLoading(true);
            await hftApiService.updateSettings(settings);
            toast.success('Settings saved successfully!');
            setShowSettings(false);
            // Refresh data multiple times to ensure live mode is reflected
            await refreshData();
            await new Promise(resolve => setTimeout(resolve, 500)); // Wait 500ms
            await refreshData();
            await loadLiveStatus(); // Explicitly reload live status
        } catch (error) {
            console.error('Error saving settings:', error);
            toast.error('Failed to save settings');
        } finally {
            setLoading(false);
        }
    };

    const mode = 'live'; // Hardcoding to live mode
    const cash = botData.portfolio.cash || 0;

    // Invested value: from Dhan API (cost basis). Fall back to computing if not sent.
    const computedInvested = Object.values(botData.portfolio.holdings || {}).reduce((sum: number, h: any) => {
        const avg: number = parseFloat(h.avgPrice || h.avg_price || 0);
        const qty: number = parseInt(h.quantity || h.qty || 0);
        return sum + (avg * qty);
    }, 0) as number;

    const investedValue: number = computedInvested > 0
        ? computedInvested
        : (botData.portfolio.investedValue != null ? botData.portfolio.investedValue : 0);

    // Today's gain: from Dhan positions unrealizedProfit
    const todayGain = botData.portfolio.todayGain ?? 0;
    const todayGainPct = investedValue > 0 ? (todayGain / investedValue) * 100 : 0;
    const positionsCount = Object.keys(botData.portfolio.holdings).length;

    const cardBg = isLight ? 'bg-white' : isSpace ? 'bg-slate-800/80' : 'bg-slate-800';
    const cardBorder = isLight ? 'border-gray-200' : isSpace ? 'border-purple-900/30' : 'border-slate-700';
    const textPrimary = isLight ? 'text-gray-900' : 'text-white';
    const textMuted = isLight ? 'text-gray-600' : 'text-gray-400';

    return (
        <>
            <Toaster position="top-right" />
            <Layout>
                <div className={`space-y-3 md:space-y-4 w-full ${isLight ? '' : 'animate-fadeIn'}`}>
                    {/* Header: title + status + refresh (same structure as main dashboard) */}
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                                <h1 className={`text-xl md:text-2xl font-bold ${textPrimary}`}>Trading</h1>
                                <div className="flex items-center gap-2">
                                    {/* System Connection */}
                                    {connected ? (
                                        <div className="flex items-center gap-1.5 px-2 py-1 bg-green-500/10 border border-green-500/30 rounded-lg flex-shrink-0">
                                            <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
                                            <span className="text-green-400 text-[10px] font-bold uppercase tracking-wider">System Online</span>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-1.5 px-2 py-1 bg-red-500/20 border border-red-500/50 rounded-lg flex-shrink-0">
                                            <AlertCircle className="w-3 h-3 text-red-400" />
                                            <span className="text-red-400 text-[10px] font-bold uppercase tracking-wider">System Offline</span>
                                        </div>
                                    )}

                                    {/* Broker Connection */}
                                    {connected && (
                                        liveStatus?.connected ? (
                                            <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-500/10 border border-blue-500/30 rounded-lg flex-shrink-0" title="Broker: Dhan connection validated">
                                                <CheckCircle2 className="w-3 h-3 text-blue-400" />
                                                <span className="text-blue-400 text-[10px] font-bold uppercase tracking-wider">Broker Connected</span>
                                            </div>
                                        ) : (
                                            <div
                                                className="flex items-center gap-1.5 px-2 py-1 bg-amber-500/10 border border-amber-500/30 rounded-lg flex-shrink-0 cursor-help"
                                                title={liveStatus?.dhan_error || "Broker authentication required"}
                                            >
                                                <AlertCircle className="w-3 h-3 text-amber-500" />
                                                <span className="text-amber-500 text-[10px] font-bold uppercase tracking-wider">Broker: Action Required</span>
                                            </div>
                                        )
                                    )}
                                </div>
                            </div>
                            <p className={`text-xs md:text-sm ${textMuted}`}>
                                Updated {new Date().toLocaleTimeString()}
                            </p>
                            {connected && liveStatus?.dhan_error && (
                                <p className="text-xs mt-1 text-amber-500 dark:text-amber-400 flex items-center gap-1 animate-pulse">
                                    <AlertCircle className="w-3 h-3" />
                                    Broker Status: {liveStatus.dhan_error}
                                </p>
                            )}
                        </div>
                        <button
                            onClick={refreshData}
                            disabled={loading}
                            className="flex items-center justify-center gap-1.5 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-semibold transition-all disabled:opacity-50 w-full md:w-auto min-h-[44px] md:min-h-0"
                        >
                            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                            Refresh
                        </button>
                    </div>

                    {/* Portfolio metrics row */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className={`${cardBg} border ${cardBorder} rounded-xl p-4`}>
                            <p className={`text-xs font-medium uppercase tracking-wide ${textMuted}`}>Invested Value</p>
                            <p className={`text-lg font-bold ${textPrimary}`}>{formatCurrency(investedValue)}</p>
                        </div>
                        <div className={`${cardBg} border ${cardBorder} rounded-xl p-4`}>
                            <p className={`text-xs font-medium uppercase tracking-wide ${textMuted}`}>Cash</p>
                            <p className={`text-lg font-bold ${textPrimary}`}>{formatCurrency(cash)}</p>
                        </div>
                        <div className={`${cardBg} border ${cardBorder} rounded-xl p-4`}>
                            <p className={`text-xs font-medium uppercase tracking-wide ${textMuted}`}>Today's Gains</p>
                            <p className={`text-lg font-bold ${textPrimary}`}>{formatCurrency(todayGain)}</p>
                            <p className={`text-sm font-semibold ${todayGainPct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                {formatPercentage(todayGainPct)}
                            </p>
                        </div>
                        <div className={`${cardBg} border ${cardBorder} rounded-xl p-4`}>
                            <p className={`text-xs font-medium uppercase tracking-wide ${textMuted}`}>Positions</p>
                            <p className={`text-lg font-bold ${textPrimary}`}>{positionsCount}</p>
                        </div>
                    </div>

                    {/* Quick actions */}
                    <div className="flex flex-wrap gap-2">
                        <button
                            onClick={handleStartBot}
                            disabled={botData.isRunning || globalBotStatus === 'INITIALIZING'}
                            className="flex items-center gap-2 px-4 py-2.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-semibold transition-all"
                        >
                            {globalBotStatus === 'INITIALIZING' ? (
                                <><Loader2 className="w-4 h-4 animate-spin" /> Initializing...</>
                            ) : (
                                <><Play className="w-4 h-4" /> Start Trading</>
                            )}
                        </button>
                        <button
                            onClick={handleStopBot}
                            disabled={!botData.isRunning}
                            className="flex items-center gap-2 px-4 py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-semibold transition-all"
                        >
                            <><Square className="w-4 h-4" /> Stop Trading</>
                        </button>
                        <button
                            onClick={() => setShowSettings(true)}
                            disabled={botData.isRunning}
                            className="flex items-center gap-2 px-4 py-2.5 bg-slate-600 hover:bg-slate-700 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-all"
                        >
                            Settings
                        </button>
                    </div>

                    {/* Tabs (Dashboard / Portfolio / Chat) */}
                    <div className={`${cardBg} border ${cardBorder} rounded-xl overflow-hidden`}>
                        <div className={`flex border-b ${cardBorder} p-1 gap-1`}>
                            {[
                                { id: 'dashboard' as const, label: 'Dashboard', icon: LayoutDashboard },
                                { id: 'portfolio' as const, label: 'Portfolio', icon: Briefcase },
                                { id: 'activity' as const, label: 'Recent Trading Activity', icon: MessageCircle },
                                { id: 'watchlist' as const, label: 'Watchlist', icon: CheckCircle2 },
                            ].map(({ id, label, icon: Icon }) => (
                                <button
                                    key={id}
                                    onClick={() => setActiveTab(id)}
                                    className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-medium transition-all ${activeTab === id
                                        ? isLight ? 'bg-blue-500 text-white' : 'bg-blue-600 text-white'
                                        : isLight ? 'text-gray-600 hover:bg-gray-100' : 'text-gray-400 hover:bg-slate-700'
                                        }`}
                                >
                                    <Icon className="w-4 h-4" /> {label}
                                </button>
                            ))}
                        </div>
                        <div className="p-4 md:p-6 min-h-[400px]">
                            {/* Always show components regardless of trading mode or connection status */}
                            {activeTab === 'dashboard' && <HftDashboard botData={botData} botRunKey={botRunKey} onRefresh={refreshData} />}
                            {(activeTab === 'portfolio' || activeTab === 'activity' || activeTab === 'watchlist') && (
                                <HftPortfolio
                                    activeSection={activeTab}
                                    botData={botData}
                                    botRunKey={botRunKey}
                                    onAddTicker={handleAddTicker}
                                    onRemoveTicker={handleRemoveTicker}
                                    onRefresh={refreshData}
                                />
                            )}
                        </div>
                    </div>
                </div>

                {loading && <HftLoadingOverlay />}
                {showSettings && (
                    <HftSettingsModal
                        settings={botData.config}
                        onSave={handleSaveSettings}
                        onRefresh={refreshData}
                        onClose={() => setShowSettings(false)}
                    />
                )}
            </Layout>
        </>
    );
}
