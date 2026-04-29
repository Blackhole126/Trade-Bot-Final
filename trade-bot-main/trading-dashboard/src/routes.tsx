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
import UserProfilePage from './pages/UserProfilePage';
import TrainModelPage from './pages/TrainModelPage';
import EducationalDashboardPage from './pages/EducationalDashboardPage';
import SimulationToolsPage from './pages/SimulationToolsPage';
import DebugPage from './pages/DebugPage';

export const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/analytics" element={<AnalyticsPage />} />
      <Route path="/alerts" element={<AlertsPage />} />
      <Route path="/compare" element={<ComparePage />} />
      <Route path="/market-scan" element={<MarketScanPage />} />
      <Route path="/portfolio" element={<PortfolioPage />} />
      <Route path="/scenario-portfolio" element={<ScenarioPortfolioPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/trading-history" element={<TradingHistoryPage />} />
      <Route path="/watchlist" element={<WatchListPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/profile" element={<UserProfilePage />} />
      <Route path="/train-model" element={<TrainModelPage />} />
      <Route path="/education" element={<EducationalDashboardPage />} />
      <Route path="/simulation-tools" element={<SimulationToolsPage />} />
      <Route path="/debug" element={<DebugPage />} />
      {/* Add more routes as needed */}
    </Routes>
  );
};