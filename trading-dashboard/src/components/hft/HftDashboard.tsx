import React, { useState } from 'react';
import styled from 'styled-components';
import { useTheme } from '../../contexts/ThemeContext';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
    Filler
} from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';
import type { HftBotData } from '../../types/hft';
import { formatCurrency } from '../../services/hftApiService';
import HftAnalysisPanel from './HftAnalysisPanel';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, ArcElement, Filler);

const DashboardContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 100%;
  overflow: visible;
  padding-bottom: 20px;
`;

const MetricsRow = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
`;

const MetricCard = styled.div`
  background: white;
  color: #333;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 20px;
  border-radius: 12px;
  text-align: center;
`;

const MetricLabel = styled.div`
  font-size: 0.9rem;
  color: #7f8c8d;
  margin-bottom: 8px;
`;

const MetricValue = styled.div`
  font-size: 1.8rem;
  font-weight: bold;
  color: #2c3e50;
`;

const ChartsSection = styled.div`
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const ChartContainer = styled.div`
  background: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  border: 1px solid #e9ecef;

  h3 {
    margin-bottom: 15px;
    color: #2c3e50;
    text-align: center;
  }
`;

const ChartHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;

  h3 {
    margin: 0;
    color: #2c3e50;
  }
`;

const TimePeriodButtons = styled.div`
  display: flex;
  gap: 5px;
`;

const TimePeriodButton = styled.button<{ $active: boolean }>`
  padding: 6px 12px;
  border: 1px solid #ddd;
  background: ${props => props.$active ? '#f39c12' : 'white'};
  color: ${props => props.$active ? 'white' : '#666'};
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: ${props => props.$active ? '#e67e22' : '#f8f9fa'};
    border-color: #f39c12;
  }

  &:focus {
    outline: none;
    box-shadow: 0 0 0 2px rgba(243, 156, 18, 0.2);
  }
`;

const PortfolioValueDisplay = styled.div`
  margin-bottom: 20px;
  padding: 0 5px;
`;

const PortfolioValue = styled.div`
  font-size: 28px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 5px;
`;

const PortfolioChange = styled.span<{ $positive: boolean }>`
  font-size: 16px;
  font-weight: 500;
  color: ${props => props.$positive ? '#27ae60' : '#e74c3c'};
`;

const PortfolioTimestamp = styled.div`
  font-size: 12px;
  color: #95a5a6;
  margin-top: 5px;
`;

const AnalysisPanel = styled.div`
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.08);
  border: 1px solid #e9ecef;
`;

const AnalysisPanelTitle = styled.h3`
  margin: 0 0 16px 0;
  color: #2c3e50;
  font-size: 1rem;
  font-weight: 600;
`;

const NoAnalysisMsg = styled.div`
  text-align: center;
  padding: 24px;
  color: #999;
  font-size: 0.9rem;
`;

const HoldingsTable = styled.div`
  overflow-x: auto;
  margin-top: 4px;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
`;

const Th = styled.th`
  text-align: left;
  padding: 8px 12px;
  color: #7f8c8d;
  font-weight: 600;
  border-bottom: 2px solid #e9ecef;
  white-space: nowrap;
`;

const Td = styled.td`
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
  white-space: nowrap;
`;

const PnLCell = styled.td<{ $positive: boolean }>`
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
  color: ${p => p.$positive ? '#27ae60' : '#e74c3c'};
  font-weight: 600;
  white-space: nowrap;
`;



type TimePeriod = '1D' | '1M' | '1Y' | 'All';

interface HftDashboardProps {
    botData: HftBotData;
    botRunKey?: number;

    onRefresh?: () => Promise<void>;
}

const HftDashboard: React.FC<HftDashboardProps> = ({ botData, botRunKey = 0, onRefresh }) => {
    const { theme } = useTheme();
    const isLight = theme === 'light';
    const [timePeriod, setTimePeriod] = useState<TimePeriod>('1M');

    const getPeriodDescription = (): string => {
        switch (timePeriod) {
            case '1D': return 'Last 24 Hours';
            case '1M': return 'Last 30 Days';
            case '1Y': return 'Last 12 Months';
            case 'All': return 'Last 2 Years';
            default: return 'Last 30 Days';
        }
    };

    const calculateMetrics = () => {
        const cash = botData.portfolio.cash || 0;

        let holdingsMarketValue = 0;
        let unrealizedPnL = 0;
        Object.values(botData.portfolio.holdings || {}).forEach(holding => {
            const currentPrice = (holding as any).currentPrice || (holding as any).avgPrice || 0;
            const avgPrice = (holding as any).avgPrice || 0;
            const qty = (holding as any).quantity || (holding as any).qty || 0;
            holdingsMarketValue += currentPrice * qty;
            unrealizedPnL += (currentPrice - avgPrice) * qty;
        });

        // Derive totalValue from holdings + cash if backend sent 0
        const rawTotal = botData.portfolio.totalValue || 0;
        const totalValue = rawTotal > 0 ? rawTotal : (cash + holdingsMarketValue) || 0;

        const tradesToday = (botData.portfolio.tradeLog || []).filter(trade =>
            trade.timestamp && trade.timestamp.startsWith(new Date().toISOString().split('T')[0])
        ).length;

        return {
            totalValue,
            unrealizedPnL,
            activePositions: Object.keys(botData.portfolio.holdings || {}).length,
            tradesToday
        };
    };

    const generatePortfolioChartData = () => {
        // Use real portfolio history from backend (populated by Dhan API calls)
        const rawHistory: Array<{ time: string; value: number }> =
            (botData.portfolio as any).portfolioHistory || [];

        if (rawHistory.length >= 2) {
            // We have real data — use it directly
            const labels = rawHistory.map(p => p.time);
            const values = rawHistory.map(p => p.value);
            const first = values[0];
            const last = values[values.length - 1];
            const isPositive = last >= first;
            const color = isPositive ? '#27ae60' : '#e74c3c';
            const bgColor = isPositive ? 'rgba(39, 174, 96, 0.15)' : 'rgba(231, 76, 60, 0.15)';
            return {
                labels,
                datasets: [{
                    label: 'Portfolio Value (₹)',
                    data: values,
                    borderColor: color,
                    backgroundColor: bgColor,
                    fill: true,
                    borderWidth: 2,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointBackgroundColor: color,
                    pointBorderColor: color,
                }]
            };
        }

        // Fallback: single-point or no history yet — show a flat baseline
        const baseValue = (botData.portfolio as any).investedValue
            || botData.portfolio.totalValue
            || botData.portfolio.startingBalance
            || 0;
        const now = new Date();
        const flatLabels = Array.from({ length: 6 }, (_, i) => {
            const d = new Date(now);
            d.setMinutes(d.getMinutes() - (5 - i) * 5);
            return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });
        });
        return {
            labels: flatLabels,
            datasets: [{
                label: 'Portfolio Value (₹)',
                data: Array(6).fill(baseValue),
                borderColor: '#4A90E2',
                backgroundColor: 'rgba(74, 144, 226, 0.10)',
                fill: true,
                borderWidth: 2,
                tension: 0.3,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointBackgroundColor: '#4A90E2',
                pointBorderColor: '#4A90E2',
            }]
        };
    };

    const generateAllocationChartData = () => {
        const holdings = botData.portfolio.holdings || {};
        const cash = botData.portfolio.cash || 0;

        const labels: string[] = [];
        const data: number[] = [];
        const colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c', '#34495e', '#e67e22', '#95a5a6', '#2ecc71'];

        // Add holdings with current market values
        Object.entries(holdings).forEach(([ticker, holding]) => {
            const currentPrice = holding.currentPrice || holding.avgPrice || 0;
            const currentValue = holding.quantity * currentPrice;
            if (currentValue > 0) {
                labels.push(ticker);
                data.push(currentValue);
            }
        });

        // Add cash if significant
        if (cash > 0) {
            labels.push('Cash');
            data.push(cash);
        }

        // If no data, show placeholder
        if (labels.length === 0) {
            labels.push('No Holdings');
            data.push(1);
        }

        return {
            labels,
            datasets: [{
                data,
                backgroundColor: colors.slice(0, labels.length)
            }]
        };
    };

    const getChartOptions = () => {
        return {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index' as const
            },
            scales: {
                x: {
                    display: true,
                    ticks: {
                        maxTicksLimit: timePeriod === '1D' ? 8 : timePeriod === '1M' ? 6 : 5,
                        font: {
                            size: 10
                        }
                    },
                    grid: {
                        display: false
                    },
                    title: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    beginAtZero: false,
                    ticks: {
                        callback: function (value: any) {
                            if (value >= 100000) {
                                return '₹' + (value / 100000).toFixed(1) + 'L';
                            } else if (value >= 1000) {
                                return '₹' + (value / 1000).toFixed(1) + 'K';
                            } else {
                                return '₹' + value.toFixed(0);
                            }
                        },
                        font: {
                            size: 10
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    },
                    title: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: '#4A90E2',
                    borderWidth: 1,
                    cornerRadius: 6,
                    displayColors: false,
                    callbacks: {
                        title: function (context: any) {
                            return context[0].label;
                        },
                        label: function (context: any) {
                            return `₹${context.parsed.y.toLocaleString('en-IN')}`;
                        }
                    }
                },
                filler: {
                    propagate: true
                }
            },
            elements: {
                line: {
                    tension: 0.3
                }
            }
        };
    };

    const doughnutOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom' as const
            }
        }
    };

    const metrics = calculateMetrics();
    const portfolioChartData = generatePortfolioChartData();
    const allocationChartData = generateAllocationChartData();

    const themeWrapperClass = !isLight
        ? '[&_.hft-metric]:!bg-slate-800 [&_.hft-metric]:!text-white [&_.hft-metric]:!border-slate-700 [&_.hft-metric_.hft-label]:!text-gray-400 [&_.hft-metric_.hft-value]:!text-white [&_.hft-chart]:!bg-slate-800 [&_.hft-chart]:!text-white [&_.hft-chart]:!border-slate-700 [&_.hft-chart_h3]:!text-white [&_.hft-chart_h3]:!text-white'
        : '';

    return (
        <div className={themeWrapperClass}>
            <DashboardContainer>
                {/* Performance Metrics */}
                <MetricsRow>
                    <MetricCard className="hft-metric">
                        <MetricLabel className="hft-label">Invested Value</MetricLabel>
                        <MetricValue className="hft-value">
                            {formatCurrency(
                                (() => {
                                    // Always compute from holdings first to guarantee accuracy
                                    const computedInvested = Object.values(botData.portfolio.holdings || {}).reduce((s: number, h: any) => {
                                        const avg: number = parseFloat(h.avgPrice || h.avg_price || 0);
                                        const qty: number = parseInt(h.quantity || h.qty || 0);
                                        return s + (avg * qty);
                                    }, 0);
                                    
                                    // Use backend value only if our computed value is 0 (i.e. no holdings parsed)
                                    if (computedInvested > 0) {
                                        return computedInvested;
                                    }
                                    
                                    if ((botData.portfolio as any).investedValue != null) {
                                        return (botData.portfolio as any).investedValue;
                                    }
                                    return 0;
                                })()
                            )}
                        </MetricValue>
                    </MetricCard>

                    <MetricCard className="hft-metric">
                        <MetricLabel className="hft-label">Unrealized P&L</MetricLabel>
                        <MetricValue className="hft-value">{formatCurrency(metrics.unrealizedPnL)}</MetricValue>
                    </MetricCard>

                    <MetricCard className="hft-metric">
                        <MetricLabel className="hft-label">Active Positions</MetricLabel>
                        <MetricValue className="hft-value">{metrics.activePositions}</MetricValue>
                    </MetricCard>

                    <MetricCard className="hft-metric">
                        <MetricLabel className="hft-label">Trades Today</MetricLabel>
                        <MetricValue className="hft-value">{metrics.tradesToday}</MetricValue>
                    </MetricCard>
                </MetricsRow>

                {/* Charts Section */}
                <ChartsSection>
                    <ChartContainer className="hft-chart">
                        <ChartHeader>
                            <h3>Portfolio Performance</h3>
                            <span style={{ fontSize: '0.75rem', padding: '3px 10px', background: '#27ae60', color: 'white', borderRadius: 12, fontWeight: 600, letterSpacing: 1 }}>LIVE</span>
                        </ChartHeader>
                        <PortfolioValueDisplay>
                            <PortfolioValue>
                                {(() => {
                                    const inv = (botData.portfolio as any).investedValue;
                                    const tot = metrics.totalValue;
                                    return `₹ ${(inv ?? tot).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                                })()}
                                <PortfolioChange $positive={((botData.portfolio as any).todayGain ?? 0) >= 0}>
                                    {(() => {
                                        const gain = (botData.portfolio as any).todayGain ?? 0;
                                        const invested = (botData.portfolio as any).investedValue || metrics.totalValue || 1;
                                        const pct = (gain / invested) * 100;
                                        return ` ${gain >= 0 ? '+' : ''}₹${gain.toFixed(2)} (${pct.toFixed(2)}% today)`;
                                    })()}
                                </PortfolioChange>
                            </PortfolioValue>
                            <PortfolioTimestamp>
                                Today's real-time data from Dhan • {new Date().toLocaleDateString('en-IN', {
                                    month: 'short',
                                    day: '2-digit',
                                    year: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit',
                                    hour12: true
                                })}
                            </PortfolioTimestamp>
                        </PortfolioValueDisplay>
                        <div style={{ height: '280px' }}>
                            <Line data={portfolioChartData} options={getChartOptions()} />
                        </div>
                    </ChartContainer>

                    <ChartContainer className="hft-chart">
                        <h3>Asset Allocation</h3>
                        <div style={{ height: '300px' }}>
                            <Doughnut data={allocationChartData} options={doughnutOptions} />
                        </div>
                    </ChartContainer>
                </ChartsSection>

                {/* Live Holdings P&L Table */}
                <AnalysisPanel className="hft-chart">
                    <AnalysisPanelTitle>Live Positions & P&L</AnalysisPanelTitle>
                    {Object.keys(botData.portfolio.holdings || {}).length > 0 ? (
                        <HoldingsTable>
                            <Table>
                                <thead>
                                    <tr>
                                        <Th>Symbol</Th>
                                        <Th>Qty</Th>
                                        <Th>Buy Price</Th>
                                        <Th>Live Price</Th>
                                        <Th>Value</Th>
                                        <Th>P&L</Th>
                                        <Th>P&L %</Th>

                                    </tr>
                                </thead>
                                <tbody>
                                    {Object.entries(botData.portfolio.holdings).map(([sym, h]) => {
                                        const qty = h.quantity || 0;
                                        const buyPrice = h.avgPrice || 0;
                                        const livePrice = h.currentPrice || buyPrice;
                                        const value = qty * livePrice;
                                        const pnl = (livePrice - buyPrice) * qty;
                                        const pnlPct = buyPrice > 0 ? ((livePrice - buyPrice) / buyPrice) * 100 : 0;
                                        return (
                                            <tr key={sym}>
                                                <Td><strong>{sym.replace('.NS', '').replace('.BO', '')}</strong></Td>
                                                <Td>{qty}</Td>
                                                <Td>₹{buyPrice.toFixed(2)}</Td>
                                                <Td>₹{livePrice.toFixed(2)}</Td>
                                                <Td>₹{value.toFixed(2)}</Td>
                                                <PnLCell $positive={pnl >= 0}>
                                                    {pnl >= 0 ? '+' : ''}₹{pnl.toFixed(2)}
                                                </PnLCell>
                                                <PnLCell $positive={pnlPct >= 0}>
                                                    {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                                                </PnLCell>

                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </Table>
                        </HoldingsTable>
                    ) : (
                        <NoAnalysisMsg>No open positions. Start the bot to begin trading.</NoAnalysisMsg>
                    )}
                </AnalysisPanel>

                {/* Bot Analysis Section */}
                <div style={{ marginTop: '10px' }}>
                    <h3 style={{ marginBottom: '15px', color: isLight ? '#2c3e50' : '#e2e8f0', fontSize: '1.2rem', fontWeight: 600 }}>Live Analysis Streams</h3>
                    {!botData.isRunning && (
                        <NoAnalysisMsg>Press Start Bot to run live AI analysis for your watchlist tickers.</NoAnalysisMsg>
                    )}
                    {botData.config?.tickers?.map(ticker => (
                        <HftAnalysisPanel
                            key={`${ticker}-${botRunKey}`}
                            symbol={ticker}
                            active={botData.isRunning}
                            botRunKey={botRunKey}
                        />
                    ))}
                </div>

            </DashboardContainer>
        </div>
    );
};

export default HftDashboard;
