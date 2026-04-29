import { Routes, Route } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import AnalyticsPage from './pages/AnalyticsPage';
import AlertsPage from './pages/AlertsPage';
import ComparePage from './pages/ComparePage';
import MarketScanPage from './pages/MarketScanPage';
import PortfolioPage from './pages/PortfolioPage';
import ScenarioPortfolioPage from './pages/ScenarioPortfolioPage';
import SettingsPage from './pages/SettingsPage';
import TradingHistoryPage from './pages/TradingHistoryPage';
import WatchListPage from './pages/WatchListPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import WelcomePage from './pages/WelcomePage';
import UserProfilePage from './pages/UserProfilePage';
import TrainModelPage from './pages/TrainModelPage';
import EducationalDashboardPage from './pages/EducationalDashboardPage';
import SimulationToolsPage from './pages/SimulationToolsPage';
import DebugPage from './pages/DebugPage';
import HftPage from './app/hft/page';
import ProtectedRoute from './components/ProtectedRoute';

export const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<WelcomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/hft" element={<ProtectedRoute><HftPage /></ProtectedRoute>} />
      <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
      <Route path="/alerts" element={<ProtectedRoute><AlertsPage /></ProtectedRoute>} />
      <Route path="/compare" element={<ProtectedRoute><ComparePage /></ProtectedRoute>} />
      <Route path="/market-scan" element={<ProtectedRoute><MarketScanPage /></ProtectedRoute>} />
      <Route path="/portfolio" element={<ProtectedRoute><PortfolioPage /></ProtectedRoute>} />
      <Route path="/scenario-portfolio" element={<ProtectedRoute><ScenarioPortfolioPage /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      <Route path="/trading-history" element={<ProtectedRoute><TradingHistoryPage /></ProtectedRoute>} />
      <Route path="/watchlist" element={<ProtectedRoute><WatchListPage /></ProtectedRoute>} />
      <Route path="/profile" element={<ProtectedRoute><UserProfilePage /></ProtectedRoute>} />
      <Route path="/train-model" element={<ProtectedRoute><TrainModelPage /></ProtectedRoute>} />
      <Route path="/education" element={<ProtectedRoute><EducationalDashboardPage /></ProtectedRoute>} />
      <Route path="/simulation-tools" element={<ProtectedRoute><SimulationToolsPage /></ProtectedRoute>} />
      <Route path="/debug" element={<ProtectedRoute><DebugPage /></ProtectedRoute>} />
    </Routes>
  );
};