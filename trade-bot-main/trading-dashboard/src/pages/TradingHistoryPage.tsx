import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';
import { formatUSDToINR } from '../utils/currencyConverter';
import { LocalStorageWarning } from '../components/LocalStorageWarning';

const TradingHistoryPage = () => {
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    loadTradingHistory();
  }, [currentPage]);

  const loadTradingHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      // Load from localStorage (backend does not support trading history)
      const stored = localStorage.getItem('tradingHistory');
      if (stored) {
        const allTransactions = JSON.parse(stored);
        const itemsPerPage = 20;
        const startIndex = (currentPage - 1) * itemsPerPage;
        const endIndex = startIndex + itemsPerPage;
        setTransactions(allTransactions.slice(startIndex, endIndex));
        setTotalPages(Math.ceil(allTransactions.length / itemsPerPage));
      } else {
        setTransactions([]);
        setTotalPages(1);
      }
    } catch (error: any) {
      setError('Failed to load trading history from local storage');
      setTransactions([]);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        <LocalStorageWarning feature="Trading History" />
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Trading History</h1>
          <p className="text-gray-400">View all your past transactions</p>
        </div>

        {loading ? (
          <div className="text-center py-8 text-gray-400">Loading...</div>
        ) : error ? (
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center gap-3 text-red-400">
              <AlertCircle className="w-5 h-5" />
              <span>{error}</span>
            </div>
            <button 
              onClick={loadTradingHistory}
              className="mt-3 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm"
            >
              Retry
            </button>
          </div>
        ) : transactions.length > 0 ? (
          <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
            <div className="p-6 border-b border-slate-700">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-white">Transactions</h2>
                <div className="flex space-x-2">
                  <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors">
                    Filter
                  </button>
                  <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors">
                    Export
                  </button>
                </div>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Symbol</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Shares</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Price</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Total</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {transactions.map((transaction) => (
                    <tr key={transaction.id} className="hover:bg-slate-700/50">
                      <td className="px-6 py-4 whitespace-nowrap text-gray-300">{transaction.date}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          {transaction.type === 'BUY' ? (
                            <TrendingUp className="w-4 h-4 text-green-400" />
                          ) : (
                            <TrendingDown className="w-4 h-4 text-red-400" />
                          )}
                          <span className={transaction.type === 'BUY' ? 'text-green-400' : 'text-red-400'}>
                            {transaction.type}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-white font-semibold">{transaction.symbol}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-gray-300">{transaction.shares}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-gray-300">{formatUSDToINR(transaction.price || 0, transaction.symbol)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-white font-semibold">
                        {formatUSDToINR(transaction.total || 0, transaction.symbol)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded">
                          {transaction.status || 'Completed'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-slate-700 px-6 py-4">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                  className={`px-4 py-2 rounded-lg ${
                    currentPage === 1
                      ? 'bg-slate-700 text-gray-500 cursor-not-allowed'
                      : 'bg-slate-700 hover:bg-slate-600 text-white'
                  }`}
                >
                  Previous
                </button>
                
                <span className="text-white">
                  Page {currentPage} of {totalPages}
                </span>
                
                <button
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className={`px-4 py-2 rounded-lg ${
                    currentPage === totalPages
                      ? 'bg-slate-700 text-gray-500 cursor-not-allowed'
                      : 'bg-slate-700 hover:bg-slate-600 text-white'
                  }`}
                >
                  Next
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-slate-800 rounded-lg p-12 border border-slate-700 text-center">
            <AlertCircle className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Trading History</h3>
            <p className="text-gray-400">Your trading history will appear here once you make transactions.</p>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default TradingHistoryPage;