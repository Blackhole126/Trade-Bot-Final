import React, { useState, useEffect, useRef, useCallback } from 'react';
import { hftApiService } from '../../services/hftApiService';
import { useAuth } from '../../contexts/AuthContext';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AnalysisResult {
    symbol: string;
    recommendation: 'BUY' | 'SELL' | 'HOLD';
    confidence: number;
    reasoning: string;
    risk_score: number;
    target_price: number | null;
    current_price: number | null;
    stop_loss: number | null;
    sentiment: string;
    sentiment_score: number;
    indicators: Record<string, { value: number | string; signal: string }>;
    model_predictions: Array<{ model: string; r2: number; prediction: number }>;
    best_model: string;
    timestamp: string;
    file?: string;
}

interface AnalysisPanelProps {
    symbol: string;
    active: boolean;   // true = bot is running
    botMode?: string;
    onResult?: (result: AnalysisResult) => void;
    botRunKey?: number;
}

// ─── Style helpers ────────────────────────────────────────────────────────────

const SIGNAL_COLORS: Record<string, { bg: string; border: string; text: string }> = {
    BUY: { bg: 'rgba(39,174,96,0.12)', border: '#27ae60', text: '#27ae60' },
    SELL: { bg: 'rgba(231,76,60,0.12)', border: '#e74c3c', text: '#e74c3c' },
    HOLD: { bg: 'rgba(243,156,18,0.12)', border: '#f39c12', text: '#f39c12' },
};

const IND_COLOR: Record<string, string> = {
    bullish: '#27ae60', oversold: '#27ae60', positive: '#27ae60',
    bearish: '#e74c3c', overbought: '#e74c3c', negative: '#e74c3c',
    neutral: '#95a5a6', normal: '#95a5a6', high: '#f39c12', low: '#f39c12',
};

function indSignalColor(sig: string) { return IND_COLOR[sig.toLowerCase()] ?? '#95a5a6'; }
function indSignalLabel(sig: string) {
    const map: Record<string, string> = {
        bullish: '▲ Bullish', bearish: '▼ Bearish', neutral: '◆ Neutral',
        oversold: '▲ Oversold', overbought: '▼ Overbought',
        positive: '▲ Positive', negative: '▼ Negative',
        high: '▲ High', low: '▼ Low', normal: '◆ Normal',
    };
    return map[sig.toLowerCase()] ?? sig;
}

// ─── Component ────────────────────────────────────────────────────────────────

const POLL_INTERVAL_MS = 30000; // poll every 30 s — analysis takes many minutes, no need to hammer backend

const HftAnalysisPanel: React.FC<AnalysisPanelProps> = ({ symbol, active, botMode = 'live', onResult, botRunKey = 0 }) => {
    const { user } = useAuth();
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [done, setDone] = useState(false);
    const [elapsedSec, setElapsedSec] = useState(0);
    const [showModels, setShowModels] = useState(false);

    // Auto-execution state
    const [isExecuting, setIsExecuting] = useState(false);
    const [executionMessage, setExecutionMessage] = useState<string | null>(null);

    const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const clockTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const mountedRef = useRef(true);
    const lastRunKeyRef = useRef(botRunKey);

    // Clear all intervals
    const stopPolling = useCallback(() => {
        if (pollTimerRef.current) { clearInterval(pollTimerRef.current); pollTimerRef.current = null; }
        if (clockTimerRef.current) { clearInterval(clockTimerRef.current); clockTimerRef.current = null; }
    }, []);

    // Reset state on new run
    const resetState = useCallback(() => {
        setResult(null);
        setError(null);
        setDone(false);
        setElapsedSec(0);
        setShowModels(false);
        setIsExecuting(false);
        setExecutionMessage(null);
    }, []);

    // Core poll function
    const poll = useCallback(async () => {
        if (!mountedRef.current) return;
        try {
            const resp = await hftApiService.getAnalysisResult(symbol);
            if (!mountedRef.current) return;

            if (resp.status === 'ready' && resp.data) {
                const data = resp.data as AnalysisResult;
                setResult(data);
                setDone(true);
                setError(null);
                stopPolling();
                onResult?.(data);

                // Auto-execute if it's a BUY and we are in live mode
                if (data.recommendation === 'BUY' && botMode?.toLowerCase() === 'live' && user?.username) {
                    setIsExecuting(true);
                    setExecutionMessage(`Executing BUY order for ${symbol}...`);
                    hftApiService.executeSignal(symbol, user.username)
                        .then(execRes => {
                            if (execRes.success) {
                                setExecutionMessage(`✅ Order placed: ${execRes.message}`);
                            } else {
                                setExecutionMessage(`❌ Execution failed: ${execRes.message}`);
                            }
                        })
                        .catch(err => setExecutionMessage(`❌ Error: ${err.message}`))
                        .finally(() => setIsExecuting(false));
                }
            } else if (resp.status === 'error') {
                // analysis itself errored (not a network error) — keep polling in case
                // a new analysis file appears, but surface the message
                setError(resp.message ?? 'Analysis error');
            }
            // status === 'pending' → file not ready yet, keep polling
        } catch {
            // network error — silently keep polling
        }
    }, [symbol, stopPolling, onResult, botMode, user?.username]);

    // Start polling
    const startPolling = useCallback(() => {
        stopPolling();
        resetState();
        poll(); // immediate first check
        pollTimerRef.current = setInterval(poll, POLL_INTERVAL_MS);
        clockTimerRef.current = setInterval(() => {
            if (mountedRef.current) setElapsedSec(s => s + 1);
        }, 1000);
    }, [poll, stopPolling, resetState]);

    // React to active / botRunKey changes
    useEffect(() => {
        if (active) {
            // New bot run or symbol change → restart
            if (!done || botRunKey !== lastRunKeyRef.current) {
                lastRunKeyRef.current = botRunKey;
                startPolling();
            }
        } else {
            // Bot stopped → stop polling but KEEP result displayed
            stopPolling();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [active, botRunKey]);

    // Reset when symbol changes
    useEffect(() => {
        stopPolling();
        resetState();
        if (active) startPolling();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [symbol]);

    // Cleanup on unmount
    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
            stopPolling();
        };
    }, [stopPolling]);

    const rec = result?.recommendation ?? 'HOLD';
    const colors = SIGNAL_COLORS[rec] ?? SIGNAL_COLORS.HOLD;
    const shortSym = symbol.replace('.NS', '').replace('.BO', '');

    // Progress bar: infinite pulse animation while running (no %—unknown duration)
    const isRunning = active && !done;

    return (
        <div style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 14,
            padding: 20,
            marginBottom: 16,
            fontFamily: 'Inter, system-ui, sans-serif',
        }}>
            {/* ── Header ── */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                <span style={{
                    fontSize: '1rem', fontWeight: 700, letterSpacing: '0.04em',
                    color: '#e6edf3', background: 'rgba(255,255,255,0.08)',
                    padding: '3px 10px', borderRadius: 6,
                }}>
                    {shortSym}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#8b949e' }}>{symbol}</span>

                {isRunning && (
                    <span style={{ fontSize: '0.75rem', color: '#79c0ff', marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: '#79c0ff', animation: 'hftPulse 1.4s infinite' }} />
                        Analysing… {formatElapsed(elapsedSec)}
                    </span>
                )}
                {done && (
                    <span style={{ fontSize: '0.75rem', color: '#3fb950', marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
                        ✓ Analysis Complete
                        {active && (
                            <button
                                onClick={() => { setDone(false); startPolling(); }}
                                style={{
                                    background: 'rgba(79,184,255,0.15)', border: '1px solid #4ab8ff',
                                    borderRadius: 4, color: '#79c0ff', cursor: 'pointer',
                                    fontSize: '0.7rem', padding: '2px 8px',
                                }}
                            >
                                ↻ Re-analyze
                            </button>
                        )}
                    </span>
                )}
                {!active && !done && (
                    <span style={{ fontSize: '0.75rem', color: '#484f58', marginLeft: 'auto' }}>
                        Start bot to analyze
                    </span>
                )}
            </div>

            {/* ── Progress bar / pulse strip ── */}
            {isRunning && (
                <div style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#8b949e', marginBottom: 6 }}>
                        <span>Running heavy ML pipeline — please wait…</span>
                        <span>{formatElapsed(elapsedSec)}</span>
                    </div>
                    <div style={{ height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 4, overflow: 'hidden' }}>
                        <div style={{
                            height: '100%',
                            background: 'linear-gradient(90deg, #4a90e2, #27ae60, #4a90e2)',
                            backgroundSize: '200% 100%',
                            animation: 'hftSlide 2s linear infinite',
                            borderRadius: 4,
                        }} />
                    </div>
                    <div style={{ fontSize: '0.68rem', color: '#6e7681', marginTop: 4 }}>
                        Fetching market data → training ML models → generating predictions…
                    </div>
                </div>
            )}

            {/* ── Error banner (non-fatal, keeps polling) ── */}
            {error && !done && (
                <div style={{
                    background: 'rgba(255,191,0,0.08)', border: '1px solid #f39c12',
                    borderRadius: 8, padding: '8px 14px', color: '#f39c12',
                    fontSize: '0.78rem', marginBottom: 12,
                }}>
                    ⚠️ {error} — still waiting for new analysis…
                </div>
            )}

            {/* ── Main result card ── */}
            {result && (
                <>
                    {/* Signal row */}
                    <div style={{
                        background: colors.bg,
                        border: `1.5px solid ${colors.border}`,
                        borderRadius: 10,
                        padding: 16,
                        marginBottom: 14,
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
                            <span style={{ fontSize: '1.4rem', fontWeight: 800, color: colors.text, letterSpacing: '0.06em' }}>
                                {rec}
                            </span>
                            <span style={{
                                background: colors.border, color: '#fff',
                                fontSize: '0.72rem', fontWeight: 700,
                                padding: '3px 10px', borderRadius: 30,
                            }}>
                                {(result.confidence * 100).toFixed(1)}% confidence
                            </span>
                            <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: '#8b949e' }}>
                                {new Date(result.timestamp).toLocaleTimeString('en-IN')}
                            </span>
                        </div>

                        {/* Key price metrics */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(160px,1fr))', gap: 10, marginBottom: 12 }}>
                            {result.current_price != null && result.current_price > 0 && (
                                <div style={metricBoxStyle}>
                                    <div style={metricLabelStyle}>Current Price</div>
                                    <div style={metricValueStyle('#e6edf3')}>₹{result.current_price.toFixed(2)}</div>
                                </div>
                            )}
                            {result.target_price != null && (
                                <div style={metricBoxStyle}>
                                    <div style={metricLabelStyle}>🎯 Predicted Price</div>
                                    <div style={metricValueStyle('#3fb950')}>₹{result.target_price.toFixed(2)}</div>
                                    {result.current_price != null && result.current_price > 0 && (
                                        <div style={{ fontSize: '0.7rem', color: result.target_price > result.current_price ? '#3fb950' : '#e74c3c' }}>
                                            {result.target_price > result.current_price ? '▲' : '▼'}&nbsp;
                                            {Math.abs(((result.target_price - result.current_price) / result.current_price) * 100).toFixed(2)}%
                                        </div>
                                    )}
                                </div>
                            )}
                            {result.stop_loss != null && (
                                <div style={metricBoxStyle}>
                                    <div style={metricLabelStyle}>🛡 Stop Loss</div>
                                    <div style={metricValueStyle('#ff7b72')}>₹{result.stop_loss.toFixed(2)}</div>
                                </div>
                            )}
                            <div style={metricBoxStyle}>
                                <div style={metricLabelStyle}>📰 Sentiment</div>
                                <div style={metricValueStyle(indSignalColor(result.sentiment))}>
                                    {result.sentiment.charAt(0).toUpperCase() + result.sentiment.slice(1)}
                                </div>
                            </div>
                        </div>

                        {/* Reasoning */}
                        {result.reasoning && (
                            <div style={{
                                borderTop: '1px solid rgba(255,255,255,0.08)',
                                paddingTop: 10, fontSize: '0.78rem', color: '#8b949e',
                                lineHeight: 1.6,
                            }}>
                                {result.reasoning}
                            </div>
                        )}
                    </div>

                    {/* ── Technical Indicators ── */}
                    {Object.keys(result.indicators).length > 0 && (
                        <div style={{ marginBottom: 14 }}>
                            <div style={sectionHeaderStyle}>Technical Indicators</div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(140px,1fr))', gap: 8 }}>
                                {Object.entries(result.indicators).map(([name, ind]) => (
                                    <div key={name} style={{
                                        background: 'rgba(255,255,255,0.04)',
                                        border: `1px solid ${indSignalColor(ind.signal)}30`,
                                        borderRadius: 8, padding: '10px 12px',
                                    }}>
                                        <div style={{ fontSize: '0.68rem', color: '#8b949e', marginBottom: 3 }}>{name}</div>
                                        <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#e6edf3', marginBottom: 3 }}>
                                            {typeof ind.value === 'number' ? ind.value.toLocaleString() : ind.value}
                                        </div>
                                        <div style={{ fontSize: '0.68rem', fontWeight: 600, color: indSignalColor(ind.signal) }}>
                                            {indSignalLabel(ind.signal)}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* ── Model Predictions (collapsible) ── */}
                    {result.model_predictions && result.model_predictions.length > 0 && (
                        <div style={{ marginBottom: 4 }}>
                            <button
                                onClick={() => setShowModels(v => !v)}
                                style={{
                                    background: 'none', border: 'none', cursor: 'pointer',
                                    display: 'flex', alignItems: 'center', gap: 6,
                                    color: '#8b949e', fontSize: '0.73rem', padding: '4px 0',
                                }}
                            >
                                <span style={{ transition: 'transform 0.2s', transform: showModels ? 'rotate(90deg)' : 'none' }}>▶</span>
                                {showModels ? 'Hide' : 'Show'} ML Model Predictions ({result.model_predictions.length} models)
                                {result.best_model && (
                                    <span style={{ marginLeft: 4, background: 'rgba(60,180,255,0.12)', border: '1px solid #4ab8ff', borderRadius: 4, color: '#79c0ff', padding: '1px 6px', fontSize: '0.68rem' }}>
                                        Best: {result.best_model}
                                    </span>
                                )}
                            </button>
                            {showModels && (
                                <div style={{
                                    marginTop: 8, background: '#0d1117',
                                    border: '1px solid #30363d', borderRadius: 8,
                                    overflow: 'hidden', fontSize: '0.75rem',
                                }}>
                                    {/* Table header */}
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 80px 100px', background: 'rgba(255,255,255,0.05)', padding: '6px 12px', color: '#8b949e', fontWeight: 600 }}>
                                        <div>Model</div><div>R²</div><div>Predicted ₹</div>
                                    </div>
                                    {result.model_predictions
                                        .sort((a, b) => b.r2 - a.r2)
                                        .map(m => (
                                            <div key={m.model} style={{
                                                display: 'grid', gridTemplateColumns: '1fr 80px 100px',
                                                padding: '6px 12px', borderTop: '1px solid #21262d',
                                                color: m.model === result.best_model ? '#79c0ff' : '#c9d1d9',
                                                background: m.model === result.best_model ? 'rgba(79,184,255,0.06)' : 'transparent',
                                            }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                    {m.model === result.best_model && <span style={{ color: '#f39c12' }}>★</span>}
                                                    {m.model}
                                                </div>
                                                <div style={{ color: m.r2 > 0.3 ? '#3fb950' : m.r2 > 0 ? '#f39c12' : '#e74c3c' }}>
                                                    {m.r2.toFixed(4)}
                                                </div>
                                                <div>₹{m.prediction.toFixed(2)}</div>
                                            </div>
                                        ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* File source footer */}
                    {result.file && (
                        <div style={{ fontSize: '0.65rem', color: '#484f58', marginTop: 8 }}>
                            Source: {result.file}
                        </div>
                    )}
                </>
            )}

            {/* ── Footer for analysis status and re-analyze button ── */}
            {done && result && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 16 }}>
                    {executionMessage && (
                        <span style={{
                            fontSize: '0.75rem',
                            color: executionMessage.includes('✅') ? '#27ae60' : executionMessage.includes('❌') ? '#e74c3c' : '#f39c12',
                            animation: isExecuting ? 'pulse 1.5s infinite' : 'none',
                            fontWeight: 500
                        }}>
                            {executionMessage}
                        </span>
                    )}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', color: '#27ae60', marginLeft: 'auto' }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                        <span>Analysis Complete</span>
                    </div>
                    <button
                        onClick={() => { setDone(false); startPolling(); }}
                        style={{
                            border: `1px solid rgba(88, 166, 255, 0.4)`,
                            color: '#58a6ff',
                            borderRadius: 4,
                            padding: '2px 8px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            background: 'transparent',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 6,
                            transition: 'all 0.2s'
                        }}
                        onMouseOver={(e) => e.currentTarget.style.background = 'rgba(88, 166, 255, 0.1)'}
                        onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: 4 }}>
                            <polyline points="23 4 23 10 17 10" />
                            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                        </svg>
                        Re-analyze
                    </button>
                </div>
            )}

            {/* ── Idle placeholder ── */}
            {!active && !result && !isRunning && (
                <div style={{ textAlign: 'center', padding: '24px 0', color: '#484f58', fontSize: '0.85rem' }}>
                    Start the bot to run AI analysis on {symbol}
                </div>
            )}

            <style>{`
                @keyframes hftPulse {
                    0%, 100% { opacity: 1; transform: scale(1); }
                    50%       { opacity: 0.4; transform: scale(0.85); }
                }
                @keyframes hftSlide {
                    0%   { background-position: 100% 0; }
                    100% { background-position: -100% 0; }
                }
            `}</style>
        </div>
    );
};

// ─── Style constants ──────────────────────────────────────────────────────────

const metricBoxStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 8,
    padding: '10px 12px',
};
const metricLabelStyle: React.CSSProperties = {
    fontSize: '0.68rem', color: '#8b949e', marginBottom: 4,
};
const metricValueStyle = (color: string): React.CSSProperties => ({
    fontSize: '1rem', fontWeight: 700, color,
});
const sectionHeaderStyle: React.CSSProperties = {
    fontSize: '0.72rem', color: '#8b949e', marginBottom: 8,
    fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatElapsed(sec: number): string {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export default HftAnalysisPanel;
