import { useEffect, useRef, useState, useCallback } from 'react';
import { formatUSDToINR } from '../utils/currencyConverter';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, CandlestickData, Time, LineData, WhitespaceData } from 'lightweight-charts';
import { stockAPI } from '../services/api';
import {
  BarChart3,
  TrendingUp,
  Settings,
  ZoomIn,
  ZoomOut,
  Type,
  X,
  Shield,
  Move,
  Minus,
  Maximize2,
  Minimize2,
  Crosshair,
  Lock,
  Unlock,
  Trash2,
  Eye,
  EyeOff
} from 'lucide-react';

interface CandlestickChartProps {
  symbol: string;
  exchange?: string;
  onClose?: () => void;
  onPriceUpdate?: (price: number) => void;
}

const CandlestickChart = ({ symbol, exchange = 'NSE', onClose, onPriceUpdate }: CandlestickChartProps) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const superTrendSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const macdSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const macdSignalSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const macdHistogramSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  const [timeframe, setTimeframe] = useState<string>('5m');
  const [chartType, setChartType] = useState<'candlestick' | 'line' | 'area'>('candlestick');
  const [ohlc, setOhlc] = useState({ open: 0, high: 0, low: 0, close: 0, change: 0, changePercent: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showIndicators, setShowIndicators] = useState(false);
  const [showOptionsChain, setShowOptionsChain] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [crosshairPrice, setCrosshairPrice] = useState<number | null>(null);
  const [crosshairTime, setCrosshairTime] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [drawingsLocked, setDrawingsLocked] = useState(false);
  const [drawingsVisible, setDrawingsVisible] = useState(true);
  const liveUpdateIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Timeframe options
  const timeframes = [
    { value: '1m', label: '1m' },
    { value: '5m', label: '5m' },
    { value: '15m', label: '15m' },
    { value: '30m', label: '30m' },
    { value: '1h', label: '1h' },
    { value: '1d', label: '1D' },
    { value: '1w', label: '1W' },
    { value: '1mo', label: '1M' },
  ];

  // Drawing tools (Groww Terminal style)
  const drawingTools = [
    { id: 'crosshair', icon: Crosshair, label: 'Crosshair' },
    { id: 'trend', icon: TrendingUp, label: 'Trend Line' },
    { id: 'fibonacci', icon: BarChart3, label: 'Fibonacci' },
    { id: 'text', icon: Type, label: 'Text' },
    { id: 'measure', icon: Move, label: 'Measure' },
  ];

  // Calculate SuperTrend indicator
  const calculateSuperTrend = (data: CandlestickData[], period: number = 10, multiplier: number = 3): LineData[] => {
    if (data.length < period) return [];

    const result: LineData[] = [];
    let prevATR = 0;
    let prevSuperTrend = 0;
    let prevUpperBand = 0;
    let prevLowerBand = 0;
    let trend = 1; // 1 for uptrend, -1 for downtrend

    for (let i = period; i < data.length; i++) {
      const high = data[i].high;
      const low = data[i].low;
      const close = data[i].close;

      // Calculate ATR (Average True Range)
      let trueRange = high - low;
      if (i > 0) {
        trueRange = Math.max(
          high - low,
          Math.abs(high - data[i - 1].close),
          Math.abs(low - data[i - 1].close)
        );
      }

      const ATR = prevATR === 0
        ? trueRange
        : (prevATR * (period - 1) + trueRange) / period;

      // Calculate basic bands
      const hl2 = (high + low) / 2;
      const upperBand = hl2 + (multiplier * ATR);
      const lowerBand = hl2 - (multiplier * ATR);

      // Adjust bands
      const finalUpperBand = upperBand < prevUpperBand || data[i - 1].close > prevUpperBand
        ? upperBand
        : prevUpperBand;
      const finalLowerBand = lowerBand > prevLowerBand || data[i - 1].close < prevLowerBand
        ? lowerBand
        : prevLowerBand;

      // Determine SuperTrend
      let superTrend = 0;
      if (close <= finalLowerBand) {
        trend = -1;
        superTrend = finalLowerBand;
      } else if (close >= finalUpperBand) {
        trend = 1;
        superTrend = finalUpperBand;
      } else {
        superTrend = trend === 1 ? finalLowerBand : finalUpperBand;
      }

      result.push({
        time: data[i].time,
        value: superTrend,
      });

      prevATR = ATR;
      prevSuperTrend = superTrend;
      prevUpperBand = finalUpperBand;
      prevLowerBand = finalLowerBand;
    }

    return result;
  };

  // Calculate MACD indicator
  const calculateMACD = (data: CandlestickData[], fastPeriod: number = 12, slowPeriod: number = 26, signalPeriod: number = 9) => {
    if (data.length < slowPeriod) return { macd: [], signal: [], histogram: [] };

    // Calculate EMAs
    const calculateEMA = (period: number) => {
      const multiplier = 2 / (period + 1);
      const ema: number[] = [];

      for (let i = 0; i < data.length; i++) {
        if (i === 0) {
          ema.push(data[i].close);
        } else {
          ema.push((data[i].close - ema[i - 1]) * multiplier + ema[i - 1]);
        }
      }
      return ema;
    };

    const fastEMA = calculateEMA(fastPeriod);
    const slowEMA = calculateEMA(slowPeriod);

    // Calculate MACD line
    const macdLine: LineData[] = [];
    for (let i = 0; i < data.length; i++) {
      macdLine.push({
        time: data[i].time,
        value: fastEMA[i] - slowEMA[i],
      });
    }

    // Calculate Signal line (EMA of MACD)
    const signalLine: LineData[] = [];
    const macdValues = macdLine.map(m => m.value);
    const signalMultiplier = 2 / (signalPeriod + 1);

    for (let i = 0; i < macdValues.length; i++) {
      if (i === 0) {
        signalLine.push({ time: data[i].time, value: macdValues[i] });
      } else {
        const prevSignal = signalLine[i - 1].value;
        const newSignal = (macdValues[i] - prevSignal) * signalMultiplier + prevSignal;
        signalLine.push({ time: data[i].time, value: newSignal });
      }
    }

    // Calculate Histogram
    const histogram = macdLine.map((macd, i) => ({
      time: macd.time,
      value: macd.value - signalLine[i].value,
      color: (macd.value - signalLine[i].value) >= 0 ? '#10b981' : '#ef4444',
    }));

    return { macd: macdLine, signal: signalLine, histogram };
  };

  // Fetch live price data
  const fetchLivePrice = useCallback(async () => {
    if (!symbol) return;

    try {
      // Use fetchData for live updates - lighter and faster than predict
      const response = await stockAPI.fetchData([symbol], '1d', false, false);

      if (response.data && response.data[symbol] && response.data[symbol].history) {
        const history = response.data[symbol].history;
        if (history.length > 0) {
          // Get the latest data point
          const latest = history[history.length - 1];
          const currentPrice = latest.close || latest.Close || 0;

          if (currentPrice > 0) {
            // Update OHLC (using current price as close)
            setOhlc(prev => ({
              ...prev,
              close: currentPrice,
              high: Math.max(prev.high, currentPrice, latest.high || latest.High || currentPrice),
              low: prev.low === 0 ? currentPrice : Math.min(prev.low, currentPrice, latest.low || latest.Low || currentPrice),
              change: currentPrice - prev.close,
              changePercent: prev.close > 0 ? ((currentPrice - prev.close) / prev.close) * 100 : 0,
            }));

            // Notify parent of price update
            if (onPriceUpdate) {
              onPriceUpdate(currentPrice);
            }

            // Update chart with latest candle if we have a series
            if (candlestickSeriesRef.current && chartRef.current) {
              const now = Math.floor(Date.now() / 1000) as Time;
              const allData = candlestickSeriesRef.current.data();
              const lastCandle = allData.length > 0 ? allData[allData.length - 1] : null;

              if (lastCandle && 'open' in lastCandle && 'high' in lastCandle && 'low' in lastCandle && 'close' in lastCandle) {
                // Update last candle with new close price
                const typedCandle = lastCandle as CandlestickData;
                candlestickSeriesRef.current.update({
                  time: typedCandle.time,
                  open: typedCandle.open,
                  high: Math.max(typedCandle.high, currentPrice, latest.high || latest.High || currentPrice),
                  low: Math.min(typedCandle.low, currentPrice, latest.low || latest.Low || currentPrice),
                  close: currentPrice,
                });
              } else if (allData.length === 0) {
                // Create new candle if no data exists
                candlestickSeriesRef.current.update({
                  time: now,
                  open: latest.open || latest.Open || currentPrice,
                  high: latest.high || latest.High || currentPrice,
                  low: latest.low || latest.Low || currentPrice,
                  close: currentPrice,
                });
              }
            }
          }
        }
      }
    } catch (err: any) {
      // Silently handle errors for live price updates - it's non-critical
      // Only log if it's not a connection error
      if (!err.message?.includes('Unable to connect')) {
        console.error('Failed to fetch live price:', err);
      }
    }
  }, [symbol, onPriceUpdate]);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Clean up existing chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      candlestickSeriesRef.current = null;
      volumeSeriesRef.current = null;
      superTrendSeriesRef.current = null;
      macdSeriesRef.current = null;
      macdSignalSeriesRef.current = null;
      macdHistogramSeriesRef.current = null;
    }

    chartContainerRef.current.innerHTML = '';

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0f172a' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#1e293b', style: 1 },
        horzLines: { color: '#1e293b', style: 1 },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: '#475569',
          width: 1,
          style: 2,
        },
        horzLine: {
          color: '#475569',
          width: 1,
          style: 2,
        },
      },
      rightPriceScale: {
        borderColor: '#334155',
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: true,
        secondsVisible: false,
      },
      width: chartContainerRef.current.clientWidth,
      height: isFullscreen ? window.innerHeight - 120 : 500,
    });

    chartRef.current = chart;

    // Create candlestick series
    try {
      if (typeof (chart as any).addCandlestickSeries === 'function') {
        const candlestickSeries = (chart as any).addCandlestickSeries({
          upColor: '#10b981',
          downColor: '#ef4444',
          borderVisible: false,
          wickUpColor: '#10b981',
          wickDownColor: '#ef4444',
          priceFormat: {
            type: 'price',
            precision: 2,
            minMove: 0.01,
          },
        }) as ISeriesApi<'Candlestick'>;
        candlestickSeriesRef.current = candlestickSeries;
      }
    } catch (error) {
      console.error('Failed to create candlestick series:', error);
    }

    // Create volume series
    try {
      if (typeof (chart as any).addHistogramSeries === 'function') {
        const volumeSeries = (chart as any).addHistogramSeries({
          color: '#3b82f6',
          priceFormat: { type: 'volume' },
          priceScaleId: 'volume',
          scaleMargins: { top: 0.8, bottom: 0 },
        }) as ISeriesApi<'Histogram'>;
        volumeSeriesRef.current = volumeSeries;
      }
    } catch (error) {
      console.error('Failed to create volume series:', error);
    }

    // Create SuperTrend line
    try {
      if (typeof (chart as any).addLineSeries === 'function') {
        const superTrendSeries = (chart as any).addLineSeries({
          color: '#f59e0b',
          lineWidth: 2,
          priceFormat: { type: 'price', precision: 2 },
        }) as ISeriesApi<'Line'>;
        superTrendSeriesRef.current = superTrendSeries;
      }
    } catch (error) {
      console.error('Failed to create SuperTrend series:', error);
    }

    // Handle crosshair move for price/time display
    chart.subscribeCrosshairMove((param) => {
      if (param.point === undefined || !param.time || param.point.x < 0 || param.point.y < 0) {
        setCrosshairPrice(null);
        setCrosshairTime(null);
        return;
      }

      if (candlestickSeriesRef.current && param.seriesData) {
        const data = param.seriesData.get(candlestickSeriesRef.current);
        if (data && 'close' in data) {
          setCrosshairPrice(data.close);
          // Format time
          const date = new Date(Number(param.time) * 1000);
          setCrosshairTime(date.toLocaleString());
        }
      }
    });

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: isFullscreen ? window.innerHeight - 120 : 500,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [isFullscreen]);

  // Fetch and update chart data
  useEffect(() => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current) return;

    const fetchChartData = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await stockAPI.fetchData([symbol], '1mo', false, false);

        if (response.data && response.data[symbol] && response.data[symbol].history) {
          const history = response.data[symbol].history;

          // Convert to candlestick format
          const candlestickData: CandlestickData[] = history.map((item: any, index: number) => ({
            time: (index + 1) as Time,
            open: item.open || item.Close || 0,
            high: item.high || item.Close || 0,
            low: item.low || item.Close || 0,
            close: item.close || item.Close || 0,
          }));

          const volumeData = history.map((item: any, index: number) => ({
            time: (index + 1) as Time,
            value: item.volume || 0,
            color: (item.close || item.Close || 0) >= (item.open || item.Close || 0) ? '#10b981' : '#ef4444',
          }));

          // Update series
          if (candlestickSeriesRef.current) {
            candlestickSeriesRef.current.setData(candlestickData);
          }
          if (volumeSeriesRef.current) {
            volumeSeriesRef.current.setData(volumeData);
          }

          // Calculate and add SuperTrend
          if (superTrendSeriesRef.current) {
            const superTrendData = calculateSuperTrend(candlestickData);
            superTrendSeriesRef.current.setData(superTrendData);
          }

          // Calculate and add MACD (for separate chart pane - we'll add this later)
          const macdData = calculateMACD(candlestickData);
          // Store for MACD chart pane

          // Calculate OHLC from latest data
          if (candlestickData.length > 0) {
            const latest = candlestickData[candlestickData.length - 1];
            const previous = candlestickData.length > 1 ? candlestickData[candlestickData.length - 2] : latest;

            setOhlc({
              open: latest.open,
              high: latest.high,
              low: latest.low,
              close: latest.close,
              change: latest.close - previous.close,
              changePercent: ((latest.close - previous.close) / previous.close) * 100,
            });
          }
        } else {
          setError('No historical data available for this symbol.');
        }
      } catch (err: any) {
        console.error('Failed to fetch chart data:', err);
        setError(err.message || 'Failed to load chart data');
      } finally {
        setLoading(false);
      }
    };

    fetchChartData();
  }, [symbol, timeframe]);

  // Start live updates (every 1 second)
  useEffect(() => {
    if (!symbol) return;

    // Initial fetch
    fetchLivePrice();

    // Set up interval for live updates
    liveUpdateIntervalRef.current = setInterval(() => {
      fetchLivePrice();
    }, 1000); // Update every 1 second

    return () => {
      if (liveUpdateIntervalRef.current) {
        clearInterval(liveUpdateIntervalRef.current);
        liveUpdateIntervalRef.current = null;
      }
    };
  }, [symbol, fetchLivePrice]);

  return (
    <div className={`bg-slate-900 rounded-lg border border-slate-700 overflow-hidden ${isFullscreen ? 'fixed inset-0 z-[9999]' : ''}`}>
      {/* Header - Groww Terminal Style */}
      <div className="bg-slate-950 border-b border-slate-800 p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <div>
              <h3 className="text-lg font-bold text-white">{symbol}</h3>
              <p className="text-xs text-gray-400">{exchange} • {timeframe}</p>
            </div>
            {/* OHLC Display - Groww Terminal Style */}
            <div className="flex items-center gap-4 px-3 py-1.5 bg-slate-800 rounded border border-slate-700">
              <div>
                <span className="text-xs text-gray-400">O</span>
                <p className="text-sm font-semibold text-white">{formatUSDToINR(ohlc.open, symbol)}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400">H</span>
                <p className="text-sm font-semibold text-white">{formatUSDToINR(ohlc.high, symbol)}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400">L</span>
                <p className="text-sm font-semibold text-white">{formatUSDToINR(ohlc.low, symbol)}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400">C</span>
                <p className="text-sm font-semibold text-white">{formatUSDToINR(ohlc.close, symbol)}</p>
              </div>
              <div className="border-l border-slate-700 pl-4">
                <span className="text-xs text-gray-400">Change</span>
                <p className={`text-sm font-semibold ${ohlc.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {ohlc.change >= 0 ? '+' : ''}{ohlc.change.toFixed(2)} ({ohlc.changePercent >= 0 ? '+' : ''}{ohlc.changePercent.toFixed(2)}%)
                </p>
              </div>
            </div>
            {/* Crosshair Price/Time Display */}
            {crosshairPrice && crosshairTime && (
              <div className="px-3 py-1.5 bg-slate-800 rounded border border-slate-700">
                <p className="text-xs text-gray-400">Price</p>
                <p className="text-sm font-semibold text-white">{formatUSDToINR(crosshairPrice, symbol)}</p>
                <p className="text-xs text-gray-500">{crosshairTime}</p>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 hover:bg-slate-800 rounded transition-colors"
              title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4 text-gray-400" /> : <Maximize2 className="w-4 h-4 text-gray-400" />}
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="p-1.5 hover:bg-slate-800 rounded transition-colors"
              >
                <X className="w-4 h-4 text-gray-400" />
              </button>
            )}
          </div>
        </div>

        {/* Toolbar - Groww Terminal Style */}
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          {/* Timeframe Selector */}
          <div className="flex items-center gap-1 bg-slate-800 rounded-lg p-1 border border-slate-700">
            {timeframes.map((tf) => (
              <button
                key={tf.value}
                onClick={() => setTimeframe(tf.value)}
                className={`px-2 py-1 rounded text-xs font-medium transition-colors ${timeframe === tf.value
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-slate-700'
                  }`}
              >
                {tf.label}
              </button>
            ))}
          </div>

          {/* Chart Type Selector */}
          <div className="flex items-center gap-1 bg-slate-800 rounded-lg p-1 border border-slate-700">
            <button
              onClick={() => setChartType('candlestick')}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors ${chartType === 'candlestick'
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-300 hover:text-white hover:bg-slate-700'
                }`}
              title="Candlestick"
            >
              <BarChart3 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setChartType('line')}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors ${chartType === 'line'
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-300 hover:text-white hover:bg-slate-700'
                }`}
              title="Line"
            >
              <TrendingUp className="w-4 h-4" />
            </button>
          </div>

          {/* Indicators Button */}
          <button
            onClick={() => setShowIndicators(!showIndicators)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1 border ${showIndicators
                ? 'bg-blue-500/20 border-blue-500/50 text-blue-400'
                : 'bg-slate-800 border-slate-700 text-gray-300 hover:text-white hover:bg-slate-700'
              }`}
          >
            <Settings className="w-4 h-4" />
            <span>Indicators</span>
          </button>

          {/* Live Indicator */}
          <div className="flex items-center gap-1.5 px-2 py-1 bg-green-500/20 border border-green-500/50 rounded">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-xs text-green-400 font-medium">LIVE</span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex">
        {/* Drawing Tools Sidebar - Groww Terminal Style */}
        <div className="w-12 bg-slate-950 border-r border-slate-800 flex flex-col items-center py-2 gap-1">
          {drawingTools.map((tool) => (
            <button
              key={tool.id}
              onClick={() => setSelectedTool(selectedTool === tool.id ? null : tool.id)}
              className={`p-2 rounded transition-colors ${selectedTool === tool.id
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50'
                  : 'text-gray-400 hover:text-white hover:bg-slate-800'
                }`}
              title={tool.label}
            >
              <tool.icon className="w-4 h-4" />
            </button>
          ))}
          <div className="border-t border-slate-800 my-1 w-full"></div>
          <button
            onClick={() => setDrawingsLocked(!drawingsLocked)}
            className={`p-2 rounded transition-colors ${drawingsLocked
                ? 'bg-yellow-500/20 text-yellow-400'
                : 'text-gray-400 hover:text-white hover:bg-slate-800'
              }`}
            title={drawingsLocked ? "Unlock Drawings" : "Lock Drawings"}
          >
            {drawingsLocked ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setDrawingsVisible(!drawingsVisible)}
            className={`p-2 rounded transition-colors ${!drawingsVisible
                ? 'bg-gray-500/20 text-gray-400'
                : 'text-gray-400 hover:text-white hover:bg-slate-800'
              }`}
            title={drawingsVisible ? "Hide Drawings" : "Show Drawings"}
          >
            {drawingsVisible ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          </button>
          <button
            className="p-2 rounded text-gray-400 hover:text-red-400 hover:bg-slate-800 transition-colors"
            title="Delete All Drawings"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        {/* Chart Container */}
        <div className="flex-1 relative">
          {loading && (
            <div className="absolute inset-0 bg-slate-900/80 flex items-center justify-center z-10">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-2"></div>
                <p className="text-gray-400 text-sm">Loading chart data...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 bg-slate-900/80 flex items-center justify-center z-10">
              <div className="text-center max-w-md p-6 bg-slate-800 rounded-lg border border-red-500/50">
                <p className="text-red-400 mb-4 font-semibold">{error}</p>
                <div className="space-y-2 text-sm text-gray-300 mb-4">
                  <p>To fix this issue:</p>
                  <ol className="list-decimal list-inside space-y-1 text-left">
                    <li>Check if backend is running (look for "Backend Server" window)</li>
                    <li>If not running, double-click <code className="bg-slate-700 px-1 rounded">RESTART_BACKEND.bat</code></li>
                    <li>Wait 5-10 seconds for backend to start</li>
                    <li>Verify: Open <a href="http://127.0.0.1:8000/docs" target="_blank" className="text-blue-400 hover:underline">http://127.0.0.1:8000/docs</a></li>
                    <li>Click Retry below once backend is running</li>
                  </ol>
                </div>
                <button
                  onClick={() => {
                    // Retry fetching data
                    if (candlestickSeriesRef.current && volumeSeriesRef.current) {
                      const fetchChartData = async () => {
                        setLoading(true);
                        setError(null);
                        try {
                          const response = await stockAPI.fetchData([symbol], '1mo', false, false);
                          if (response.data && response.data[symbol] && response.data[symbol].history) {
                            const history = response.data[symbol].history;
                            const candlestickData: CandlestickData[] = history.map((item: any, index: number) => ({
                              time: (index + 1) as Time,
                              open: item.open || item.Close || 0,
                              high: item.high || item.Close || 0,
                              low: item.low || item.Close || 0,
                              close: item.close || item.Close || 0,
                            }));
                            if (candlestickSeriesRef.current) {
                              candlestickSeriesRef.current.setData(candlestickData);
                            }
                            setError(null);
                          } else {
                            setError('No historical data available for this symbol.');
                          }
                        } catch (err: any) {
                          setError(err.message || 'Failed to load chart data. Please ensure backend is running.');
                        } finally {
                          setLoading(false);
                        }
                      };
                      fetchChartData();
                    }
                  }}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm font-semibold transition-all hover:scale-105"
                >
                  Retry Connection
                </button>
              </div>
            </div>
          )}

          <div ref={chartContainerRef} className="w-full" style={{ height: isFullscreen ? window.innerHeight - 120 : '500px' }} />
        </div>
      </div>

      {/* Indicators Panel */}
      {showIndicators && (
        <div className="bg-slate-950 border-t border-slate-800 p-3">
          <h4 className="text-sm font-semibold text-white mb-2">Technical Indicators</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {['SuperTrend', 'MACD', 'RSI', 'SMA', 'EMA', 'Bollinger Bands', 'Volume SMA', 'Stochastic'].map((indicator) => (
              <button
                key={indicator}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-gray-300 rounded text-xs font-medium transition-colors border border-slate-700"
              >
                {indicator}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default CandlestickChart;
