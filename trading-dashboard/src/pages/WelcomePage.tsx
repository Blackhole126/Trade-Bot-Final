import { Link } from 'react-router-dom';
import { TrendingUp, LogIn, UserPlus, Sparkles } from 'lucide-react';

const WelcomePage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-950 via-slate-900 to-slate-950 flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Animated background accents */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-amber-400/5 rounded-full" />
      </div>

      <div className="relative z-10 text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/20 border border-amber-400/30 text-amber-300 text-sm font-medium mb-8">
          <Sparkles className="w-4 h-4" />
          Your trusted trading platform
        </div>

        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-4 tracking-tight">
          Welcome to
        </h1>
        <div className="flex flex-col items-center gap-4 mb-4">
          <img src="/infiverse-logo.png" alt="Infiverse" className="w-24 h-24 object-contain drop-shadow-2xl" />
          <h2 className="text-4xl sm:text-5xl md:text-6xl font-bold bg-gradient-to-r from-amber-400 via-yellow-300 to-amber-400 bg-clip-text text-transparent drop-shadow-lg">
            Samruddhi
          </h2>
        </div>
        <p className="text-slate-400 text-lg sm:text-xl mb-12 max-w-md mx-auto">
          Sign in or create an account to access your portfolio, market insights, and trading tools. All your data is saved securely.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <Link
            to="/login"
            className="flex items-center justify-center gap-2 w-full sm:w-auto px-8 py-4 bg-amber-500 hover:bg-amber-400 text-slate-900 font-semibold rounded-xl transition-all shadow-lg shadow-amber-500/25 hover:shadow-amber-400/30 hover:scale-[1.02]"
          >
            <LogIn className="w-5 h-5" />
            Sign In
          </Link>
          <Link
            to="/signup"
            className="flex items-center justify-center gap-2 w-full sm:w-auto px-8 py-4 bg-white/10 hover:bg-white/20 text-white font-semibold rounded-xl border border-white/20 transition-all hover:scale-[1.02]"
          >
            <UserPlus className="w-5 h-5" />
            Create Account
          </Link>
        </div>

        <div className="mt-16 flex items-center justify-center gap-2 text-slate-500 text-sm">
          <TrendingUp className="w-4 h-4" />
          <span>Credentials and activity are stored securely in your account.</span>
        </div>
      </div>
    </div>
  );
};

export default WelcomePage;
