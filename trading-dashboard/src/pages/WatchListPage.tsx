import { useState, useEffect, useRef } from 'react';
import Layout from '../components/Layout';
import { Star, Plus, X, TrendingUp, TrendingDown, Play, Square, Terminal, Wifi, WifiOff } from 'lucide-react';
import { stockAPI, POPULAR_STOCKS, userAPI } from '../services/api';
import { formatUSDToINR } from '../utils/currencyConverter';
import SymbolAutocomplete from '../components/SymbolAutocomplete';
import { hftApiService, createBotStream } from '../services/hftApiService';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';

// ─── Types ────────────────────────────────────────────────────────────────────
interface LogLine {
  level: string;
  message: string;
  ts: number;
}

// ─── Inline Bot Console ───────────────────────────────────────────────────────
const BotConsole = ({
  symbol,
  onStop,
}: {
  symbol: string;
  onStop: () => void;
}) => {
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [connected, setConnected] = useState(false);
  const [botData, setBotData] = useState<any>(null);
  const terminalRef = useRef<HTMLDivElement>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  // Connect to SSE stream
  useEffect(() => {
    const addLog = (level: string, message: string) =>
      setLogs(prev => [...prev.slice(-500), { level, message, ts: Date.now() }]);

    addLog('INFO', `▶  Connecting to bot stream for ${symbol}…`);
    const close = createBotStream(addLog, (payload: any) => setBotData(payload), () => {
      setConnected(true);
      addLog('INFO', '✅  Stream connected. Bot output will appear here.');
    });
    cleanupRef.current = close;
    return () => { close(); cleanupRef.current = null; };
  }, [symbol]);

  const handleStop = async () => {
    try {
      await hftApiService.stopBot();
      toast.success('Bot stopped.');
    } catch {
      toast.error('Could not stop bot gracefully.');
    }
    cleanupRef.current?.();
    cleanupRef.current = null;
    onStop();
  };

  const levelColor = (level: string) => {
    if (level === 'ERROR') return '#ff5f57';
    if (level === 'WARNING') return '#ffbd2e';
    return '#a8ff78';
  };

  return (
    <div style={{
      background: 'linear-gradient(135deg,#0f172a,#1e293b)',
      border: '1px solid #334155',
      borderRadius: 16,
      overflow: 'hidden',
      boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      marginTop: 24,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', background: 'rgba(255,255,255,0.04)', borderBottom: '1px solid #334155' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Terminal size={18} color="#38bdf8" />
          <span style={{ color: '#e2e8f0', fontWeight: 700, fontSize: 14 }}>
            Live Bot Console — <span style={{ color: '#38bdf8' }}>{symbol}</span>
          </span>
          {connected
            ? <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#4ade80', fontSize: 12 }}><Wifi size={12} /> Live</span>
            : <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#94a3b8', fontSize: 12 }}><WifiOff size={12} /> Connecting…</span>}
        </div>
        <button
          onClick={handleStop}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', background: 'linear-gradient(90deg,#ef4444,#b91c1c)', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 700, fontSize: 13, cursor: 'pointer', boxShadow: '0 2px 8px rgba(239,68,68,0.4)' }}
        >
          <Square size={13} /> Stop Bot
        </button>
      </div>

      {/* Quick metrics */}
      {botData && (
        <div style={{ display: 'flex', gap: 24, padding: '10px 20px', borderBottom: '1px solid #1e293b', flexWrap: 'wrap' }}>
          {[
            { label: 'Portfolio', value: `₹${(botData.totalValue || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` },
            { label: 'Cash', value: `₹${(botData.cash || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` },
            { label: 'Unrealised P&L', value: `₹${(botData.unrealizedPnL || 0).toFixed(2)}`, positive: (botData.unrealizedPnL || 0) >= 0 },
            { label: 'Positions', value: Object.keys(botData.holdings || {}).length },
          ].map(m => (
            <div key={m.label}>
              <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1 }}>{m.label}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: m.positive === false ? '#f87171' : m.positive === true ? '#4ade80' : '#e2e8f0' }}>{m.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Terminal */}
      <div ref={terminalRef} style={{ fontFamily: "'JetBrains Mono','Fira Code','Courier New',monospace", fontSize: 12, lineHeight: 1.7, padding: '14px 20px', minHeight: 260, maxHeight: 400, overflowY: 'auto', background: '#020617' }}>
        {logs.length === 0
          ? <div style={{ color: '#475569' }}>{'> Waiting for bot output…'}</div>
          : logs.map((line, i) => (
            <div key={i} style={{ color: levelColor(line.level), userSelect: 'text' }}>
              <span style={{ color: '#475569', marginRight: 8, fontSize: 10 }}>{new Date(line.ts).toLocaleTimeString()}</span>
              {line.message}
            </div>
          ))}
      </div>
    </div>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────
const WatchListPage = () => {
  const { user } = useAuth();

  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [dbLoaded, setDbLoaded] = useState(false);
  const [predictions, setPredictions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [startingBot, setStartingBot] = useState<string | null>(null);
  const [activeBot, setActiveBot] = useState<string | null>(null);
  const saveTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load from DB
  useEffect(() => {
    if (!user?.username) { setWatchlist([]); setDbLoaded(false); return; }
    setDbLoaded(false); setWatchlist([]);
    let cancelled = false;
    userAPI.getWatchlist()
      .then(symbols => { if (!cancelled) { setWatchlist(symbols); setDbLoaded(true); } })
      .catch(err => { toast.error('Watchlist load failed: ' + (err?.message || String(err))); if (!cancelled) setDbLoaded(true); });
    return () => { cancelled = true; };
  }, [user?.username]);

  const handleAddToWatchlist = (symbol: string) => {
    const normalized = symbol.trim().toUpperCase();
    if (normalized && !watchlist.includes(normalized)) { setWatchlist(prev => [...prev, normalized]); setNewSymbol(''); }
  };

  // Save to DB (debounced)
  useEffect(() => {
    if (!dbLoaded || !user?.username) return;
    if (saveTimeout.current) clearTimeout(saveTimeout.current);
    saveTimeout.current = setTimeout(() => {
      const token = sessionStorage.getItem('token') || localStorage.getItem('token');
      if (!token || token === 'no-auth-required') return;
      userAPI.saveWatchlist(watchlist).catch(err => toast.error('Watchlist save failed: ' + (err?.message || String(err))));
      if (watchlist.length > 0) loadWatchlistData();
    }, 500);
    return () => { if (saveTimeout.current) clearTimeout(saveTimeout.current); };
  }, [watchlist, dbLoaded, user?.username]);

  const loadWatchlistData = async () => {
    setLoading(true);
    try {
      const response = await stockAPI.predict(watchlist, 'intraday');
      if (response.metadata?.error) throw new Error(response.metadata.error);
      setPredictions((response.predictions || []).filter((p: any) => !p.error));
    } catch { setPredictions([]); }
    finally { setLoading(false); }
  };

  const removeFromWatchlist = (symbol: string) => {
    setWatchlist(watchlist.filter(s => s !== symbol));
    if (activeBot === symbol) setActiveBot(null);
  };

  // Start bot — no navigation away
  const handleStartBot = async (symbol: string) => {
    try {
      setStartingBot(symbol);
      toast.loading(`Starting bot for ${symbol}…`, { id: `start-bot-${symbol}` });
      await hftApiService.startBotWithSymbol(symbol);
      toast.success(`Bot started for ${symbol} — watch the console below.`, { id: `start-bot-${symbol}`, duration: 3000 });
      setActiveBot(symbol);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || error?.message || `Failed to start bot for ${symbol}`, { id: `start-bot-${symbol}`, duration: 5000 });
    } finally { setStartingBot(null); }
  };

  return (
    <Layout>
      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-bold text-white mb-1">Watch List</h1>
          <p className="text-gray-400 text-xs">Monitor your favourite stocks · Start the bot · View live output</p>
        </div>

        {/* Add ticker */}
        <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
          <div className="flex items-center gap-2 mb-3">
            <div className="flex-1">
              <SymbolAutocomplete value={newSymbol} onChange={setNewSymbol} onSelect={handleAddToWatchlist} placeholder="e.g., AAPL, TCS.NS" excludeSymbols={watchlist} className="px-3 py-1.5 text-sm" />
            </div>
            <button onClick={() => handleAddToWatchlist(newSymbol)} className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-sm font-semibold rounded transition-colors flex items-center gap-1.5">
              <Plus className="w-4 h-4" /><span>Add</span>
            </button>
          </div>
          <div className="mb-2">
            <p className="text-gray-300 mb-2 text-sm">Quick Add:</p>
            <div className="flex flex-wrap gap-2">
              {POPULAR_STOCKS.slice(0, 10).map(symbol => (
                <button key={symbol} onClick={() => { if (!watchlist.includes(symbol)) setWatchlist([...watchlist, symbol]); }} disabled={watchlist.includes(symbol)}
                  className={`px-3 py-1 rounded-lg text-sm transition-colors ${watchlist.includes(symbol) ? 'bg-slate-600 text-gray-400 cursor-not-allowed' : 'bg-slate-700 text-gray-300 hover:bg-slate-600'}`}>
                  {symbol}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Stock cards */}
        {loading ? (
          <div className="text-center py-8 text-gray-400">Loading…</div>
        ) : predictions.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {predictions.map((pred, index) => {
              const symbol = watchlist[index];
              const isActive = activeBot === symbol;
              return (
                <div key={symbol} className="bg-slate-800 rounded-lg p-5 border border-slate-700" style={isActive ? { borderColor: '#38bdf8', boxShadow: '0 0 0 1px #38bdf8' } : undefined}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <Star className="w-5 h-5 text-yellow-400 fill-yellow-400" />
                      <h3 className="text-xl font-bold text-white">{symbol}</h3>
                      {isActive && <span style={{ fontSize: 10, background: '#0ea5e9', color: '#fff', borderRadius: 4, padding: '1px 6px', fontWeight: 700 }}>LIVE</span>}
                    </div>
                    <div className="flex items-center gap-2">
                      {!isActive ? (
                        <button onClick={() => handleStartBot(symbol)} disabled={startingBot === symbol}
                          className="px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded transition-colors flex items-center gap-1.5">
                          <Play className="w-3 h-3" />
                          {startingBot === symbol ? 'Starting…' : 'Start Bot'}
                        </button>
                      ) : (
                        <button onClick={() => setActiveBot(null)}
                          className="px-3 py-1.5 bg-slate-600 hover:bg-slate-500 text-white text-sm font-semibold rounded transition-colors flex items-center gap-1.5">
                          <Square className="w-3 h-3" /> Hide Console
                        </button>
                      )}
                      <button onClick={() => removeFromWatchlist(symbol)} className="p-1 hover:bg-slate-700 rounded transition-colors">
                        <X className="w-4 h-4 text-gray-400" />
                      </button>
                    </div>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Price</span>
                      <span className="text-white font-semibold">{formatUSDToINR(pred.predicted_price || pred.current_price || 0, pred.symbol)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Action</span>
                      <div className="flex items-center space-x-2">
                        {(pred.action === 'LONG' || pred.action === 'BUY') ? <TrendingUp className="w-4 h-4 text-green-400" /> : (pred.action === 'SHORT' || pred.action === 'SELL') ? <TrendingDown className="w-4 h-4 text-red-400" /> : null}
                        <span className={`font-semibold ${pred.action === 'LONG' || pred.action === 'BUY' ? 'text-green-400' : pred.action === 'SHORT' || pred.action === 'SELL' ? 'text-red-400' : 'text-yellow-400'}`}>
                          {pred.action === 'LONG' ? 'BUY' : pred.action === 'SHORT' ? 'SELL' : pred.action || 'HOLD'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Confidence</span>
                      <span className="text-white font-semibold">{((pred.confidence || 0) * 100).toFixed(1)}%</span>
                    </div>
                    {pred.predicted_return !== undefined && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-400">Return</span>
                        <span className={`font-semibold ${pred.predicted_return > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {pred.predicted_return > 0 ? '+' : ''}{(pred.predicted_return || 0).toFixed(2)}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            {watchlist.length === 0 ? 'Add stocks to your watchlist to see predictions.' : 'No prediction data available.'}
          </div>
        )}

        {/* Inline bot console */}
        {activeBot && (
          <BotConsole symbol={activeBot} onStop={() => setActiveBot(null)} />
        )}
      </div>
    </Layout>
  );
};

export default WatchListPage;
