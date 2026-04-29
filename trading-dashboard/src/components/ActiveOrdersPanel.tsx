import { useState, useEffect } from 'react';
import { getActiveOrders } from '../services/hftApiService';
import { useNotification } from '../contexts/NotificationContext';
import { Activity, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

interface ActiveOrder {
    ticker: string;
    quantity: number;
    avg_price: number;
    current_price: number;
    stop_loss: number | null;
    take_profit: number | null;
    entry_date: string | null;
}

interface ActiveOrdersPanelProps {
    isLight?: boolean;
}

export const ActiveOrdersPanel: React.FC<ActiveOrdersPanelProps> = ({ isLight = false }) => {
    const { showNotification } = useNotification();
    const [activeOrders, setActiveOrders] = useState<ActiveOrder[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadActiveOrders = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await getActiveOrders();

            if (response.success) {
                setActiveOrders(response.active_orders || []);
            } else {
                setError('Failed to load active orders');
            }
        } catch (err: any) {
            console.error('Error loading active orders:', err);
            setError(err.message || 'Failed to load active orders');
            showNotification('error', 'Load Failed', 'Could not fetch active orders');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadActiveOrders();

        // Refresh every 60 seconds to keep data fresh
        const interval = setInterval(loadActiveOrders, 60000);

        return () => clearInterval(interval);
    }, []);

    const calculateDistance = (current: number, target: number): number => {
        return ((target - current) / current) * 100;
    };

    const getStatusIcon = (order: ActiveOrder) => {
        const slDistance = order.stop_loss ? calculateDistance(order.current_price, order.stop_loss) : null;
        const tpDistance = order.take_profit ? calculateDistance(order.current_price, order.take_profit) : null;

        // Check if near stop-loss (within 2%)
        if (slDistance !== null && slDistance < 2) {
            return <AlertTriangle className="w-4 h-4 text-red-500 animate-pulse" />;
        }

        // Check if near take-profit (within 2%)
        if (tpDistance !== null && tpDistance > -2) {
            return <TrendingUp className="w-4 h-4 text-green-500 animate-pulse" />;
        }

        return <CheckCircle className="w-4 h-4 text-blue-400" />;
    };

    const renderOrderCard = (order: ActiveOrder, index: number) => {
        const pnl = (order.current_price - order.avg_price) * order.quantity;
        const pnlPercent = ((order.current_price - order.avg_price) / order.avg_price) * 100;
        const slDistance = order.stop_loss ? calculateDistance(order.current_price, order.stop_loss) : null;
        const tpDistance = order.take_profit ? calculateDistance(order.current_price, order.take_profit) : null;

        return (
            <div
                key={index}
                className={`rounded-lg border p-4 transition-all ${isLight
                        ? 'bg-white border-gray-200 hover:shadow-md'
                        : 'bg-slate-800 border-slate-700 hover:border-slate-600'
                    }`}
            >
                {/* Header */}
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        {getStatusIcon(order)}
                        <h3 className={`text-lg font-bold ${isLight ? 'text-gray-900' : 'text-white'}`}>
                            {order.ticker}
                        </h3>
                    </div>
                    <div className={`flex items-center gap-1 text-xs ${isLight ? 'text-gray-600' : 'text-gray-400'}`}>
                        <Clock className="w-3 h-3" />
                        {order.entry_date ? new Date(order.entry_date).toLocaleDateString() : 'N/A'}
                    </div>
                </div>

                {/* Position Info */}
                <div className="grid grid-cols-2 gap-3 mb-3 text-sm">
                    <div>
                        <p className={`text-xs ${isLight ? 'text-gray-600' : 'text-gray-400'}`}>Quantity</p>
                        <p className={`font-semibold ${isLight ? 'text-gray-900' : 'text-white'}`}>{order.quantity}</p>
                    </div>
                    <div>
                        <p className={`text-xs ${isLight ? 'text-gray-600' : 'text-gray-400'}`}>Avg Price</p>
                        <p className={`font-semibold ${isLight ? 'text-gray-900' : 'text-white'}`}>
                            ₹{order.avg_price?.toFixed(2) || '0.00'}
                        </p>
                    </div>
                </div>

                {/* Current Price & P&L */}
                <div className={`rounded-lg p-3 mb-3 ${isLight ? 'bg-gray-50' : 'bg-slate-900/50'}`}>
                    <div className="flex items-center justify-between mb-2">
                        <span className={`text-xs ${isLight ? 'text-gray-600' : 'text-gray-400'}`}>Current Price</span>
                        <span className={`text-lg font-bold ${isLight ? 'text-gray-900' : 'text-white'}`}>
                            ₹{order.current_price?.toFixed(2) || '0.00'}
                        </span>
                    </div>
                    <div className="flex items-center justify-between">
                        <span className={`text-xs ${isLight ? 'text-gray-600' : 'text-gray-400'}`}>P&L</span>
                        <div className="flex items-center gap-1">
                            {pnl >= 0 ? (
                                <TrendingUp className="w-3 h-3 text-green-500" />
                            ) : (
                                <TrendingDown className="w-3 h-3 text-red-500" />
                            )}
                            <span className={`font-semibold ${pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                {pnl >= 0 ? '+' : ''}₹{pnl.toFixed(2)} ({pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%)
                            </span>
                        </div>
                    </div>
                </div>

                {/* Stop-Loss & Take-Profit */}
                <div className="space-y-2">
                    {order.stop_loss && (
                        <div className={`flex items-center justify-between text-xs p-2 rounded ${slDistance !== null && slDistance < 2
                                ? isLight ? 'bg-red-50 border border-red-200' : 'bg-red-900/20 border border-red-800'
                                : isLight ? 'bg-gray-50' : 'bg-slate-700/50'
                            }`}>
                            <div className="flex items-center gap-2">
                                <AlertTriangle className={`w-3 h-3 ${slDistance !== null && slDistance < 2 ? 'text-red-500' : 'text-gray-400'}`} />
                                <span className={isLight ? 'text-gray-700' : 'text-gray-300'}>Stop-Loss:</span>
                            </div>
                            <div className="text-right">
                                <span className={`font-semibold ${isLight ? 'text-gray-900' : 'text-white'}`}>
                                    ₹{order.stop_loss.toFixed(2)}
                                </span>
                                {slDistance !== null && (
                                    <span className={`ml-2 ${slDistance < 2 ? 'text-red-500 font-bold' : isLight ? 'text-gray-600' : 'text-gray-400'}`}>
                                        ({slDistance > 0 ? '+' : ''}{slDistance.toFixed(2)}%)
                                    </span>
                                )}
                            </div>
                        </div>
                    )}

                    {order.take_profit && (
                        <div className={`flex items-center justify-between text-xs p-2 rounded ${tpDistance !== null && tpDistance > -2
                                ? isLight ? 'bg-green-50 border border-green-200' : 'bg-green-900/20 border border-green-800'
                                : isLight ? 'bg-gray-50' : 'bg-slate-700/50'
                            }`}>
                            <div className="flex items-center gap-2">
                                <TrendingUp className={`w-3 h-3 ${tpDistance !== null && tpDistance > -2 ? 'text-green-500' : 'text-gray-400'}`} />
                                <span className={isLight ? 'text-gray-700' : 'text-gray-300'}>Target:</span>
                            </div>
                            <div className="text-right">
                                <span className={`font-semibold ${isLight ? 'text-gray-900' : 'text-white'}`}>
                                    ₹{order.take_profit.toFixed(2)}
                                </span>
                                {tpDistance !== null && (
                                    <span className={`ml-2 ${tpDistance > -2 ? 'text-green-500 font-bold' : isLight ? 'text-gray-600' : 'text-gray-400'}`}>
                                        ({tpDistance > 0 ? '+' : ''}{tpDistance.toFixed(2)}%)
                                    </span>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Warning if near trigger */}
                {(slDistance !== null && slDistance < 2) || (tpDistance !== null && tpDistance > -2) ? (
                    <div className={`mt-3 flex items-center gap-2 text-xs p-2 rounded ${isLight ? 'bg-amber-50 text-amber-800' : 'bg-amber-900/20 text-amber-300'
                        }`}>
                        <AlertTriangle className="w-3 h-3" />
                        <span>
                            {slDistance !== null && slDistance < 2
                                ? `Near stop-loss! Only ${Math.abs(slDistance).toFixed(2)}% away`
                                : `Near target! Only ${Math.abs(tpDistance).toFixed(2)}% away`
                            }
                        </span>
                    </div>
                ) : null}
            </div>
        );
    };

    return (
        <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Activity className={`w-5 h-5 ${isLight ? 'text-blue-600' : 'text-blue-400'}`} />
                    <h2 className={`text-lg font-bold ${isLight ? 'text-gray-900' : 'text-white'}`}>
                        Active Orders Monitoring
                    </h2>
                    <span className={`text-xs px-2 py-1 rounded-full ${isLight ? 'bg-blue-100 text-blue-700' : 'bg-blue-900/30 text-blue-400'
                        }`}>
                        {activeOrders.length} Active
                    </span>
                </div>
                <button
                    onClick={loadActiveOrders}
                    disabled={loading}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium transition-colors ${isLight
                            ? 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                            : 'bg-slate-700 hover:bg-slate-600 text-white'
                        } disabled:opacity-50`}
                >
                    <Activity className="w-3 h-3" />
                    {loading ? 'Refreshing...' : 'Refresh'}
                </button>
            </div>

            {/* Content */}
            {loading && activeOrders.length === 0 ? (
                <div className={`text-center py-8 ${isLight ? 'text-gray-600' : 'text-gray-400'}`}>
                    <Activity className="w-8 h-8 mx-auto mb-2 animate-spin" />
                    <p className="text-sm">Loading active orders...</p>
                </div>
            ) : error ? (
                <div className={`text-center py-8 rounded-lg border ${isLight ? 'bg-red-50 border-red-200 text-red-700' : 'bg-red-900/20 border-red-800 text-red-400'
                    }`}>
                    <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
                    <p className="text-sm">{error}</p>
                </div>
            ) : activeOrders.length === 0 ? (
                <div className={`text-center py-8 rounded-lg border ${isLight ? 'bg-gray-50 border-gray-200 text-gray-600' : 'bg-slate-800/50 border-slate-700 text-gray-400'
                    }`}>
                    <Activity className="w-8 h-8 mx-auto mb-2" />
                    <p className="text-sm">No active orders with stop-loss monitoring</p>
                    <p className="text-xs mt-1">Place buy orders to see them here</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {activeOrders.map((order, index) => renderOrderCard(order, index))}
                </div>
            )}
        </div>
    );
};
