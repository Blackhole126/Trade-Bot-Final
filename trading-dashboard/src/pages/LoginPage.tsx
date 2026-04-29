import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { TrendingUp } from 'lucide-react';
import { useNotification } from '../contexts/NotificationContext';

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const { showNotification } = useNotification();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
      showNotification('success', 'Login Successful', 'Welcome to your trading dashboard!');
      // Navigate to dashboard after successful login
      navigate('/dashboard');
    } catch (err: any) {
      const errorMsg = err.message || 'Login failed. Please try again.';
      setError(errorMsg);
      showNotification('error', 'Login Failed', errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-950 via-slate-900 to-slate-950 flex items-center justify-center p-3 sm:p-4">
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-6 sm:p-8 w-full max-w-sm border border-white/20">
        <div className="text-center mb-6 sm:mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 sm:w-16 sm:h-16 bg-amber-500 rounded-full mb-3 sm:mb-4">
            <TrendingUp className="w-7 h-7 sm:w-8 sm:h-8 text-slate-900" />
          </div>
          <div className="flex flex-col items-center gap-2 mb-2">
            <img src="/infiverse-logo.png" alt="Infiverse" className="w-16 h-16 object-contain" />
            <h1 className="text-xl sm:text-2xl font-bold text-amber-400">Samruddhi</h1>
          </div>
          <h2 className="text-lg sm:text-xl font-semibold text-white mb-1 sm:mb-2">Welcome Back</h2>
          <p className="text-sm sm:text-base text-gray-300">Sign in to your account</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded-lg text-red-200 text-xs sm:text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
          <div>
            <label className="block text-xs sm:text-sm font-medium text-gray-300 mb-1.5 sm:mb-2">
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-3 sm:px-4 py-2.5 sm:py-3 bg-white/5 border border-white/10 rounded-lg text-sm sm:text-base text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter your username"
            />
          </div>

          <div>
            <label className="block text-xs sm:text-sm font-medium text-gray-300 mb-1.5 sm:mb-2">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 sm:px-4 py-2.5 sm:py-3 bg-white/5 border border-white/10 rounded-lg text-sm sm:text-base text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 sm:py-3 bg-blue-500 hover:bg-blue-600 text-white font-semibold text-sm sm:text-base rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px]"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-4 sm:mt-6 text-center">
          <p className="text-sm text-gray-300">
            Don't have an account?{' '}
            <Link to="/signup" className="text-blue-400 hover:text-blue-300 font-semibold">
              Sign up
            </Link>
          </p>
        </div>

        <div className="mt-4 sm:mt-6 text-center text-xs text-gray-400">
          <p>Your credentials are stored securely. Use the account you created to sign in.</p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;