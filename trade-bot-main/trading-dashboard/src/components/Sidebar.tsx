import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  Search, 
  Briefcase, 
  History, 
  Star, 
  BarChart3,
  Bell,
  Settings,
  GitCompare,
  GraduationCap,
  LogOut,
  X,
  Activity,
  Brain,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Bug,
  Newspaper
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { useHealth } from '../contexts/HealthContext';



interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
  isCollapsed?: boolean; // New prop for collapsed state
  onToggleCollapse?: () => void; // New prop for collapse toggle function

}

const Sidebar = ({ isOpen = true, onClose, isCollapsed = false, onToggleCollapse }: SidebarProps) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const { theme } = useTheme();
  const { health } = useHealth();

  
  // State for news panel


  const menuItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/market-scan', icon: Search, label: 'Market Scan' },
    { path: '/portfolio', icon: Briefcase, label: 'Portfolio' },
    { path: '/scenario-portfolio', icon: Sparkles, label: 'Scenario Portfolio' },
    { path: '/trading-history', icon: History, label: 'Trading History' },
    { path: '/watchlist', icon: Star, label: 'Watch List' },
    { path: '/analytics', icon: BarChart3, label: 'Analytics' },
    { path: '/alerts', icon: Bell, label: 'Alerts' },
    { path: '/compare', icon: GitCompare, label: 'Compare' },
    { path: '/simulation-tools', icon: Activity, label: 'Simulation Tools' },
    { path: '/education', icon: GraduationCap, label: 'Education Center' },
    { path: '/train-model', icon: Brain, label: 'Train Model' },
    { path: '/debug', icon: Bug, label: 'System Debug' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  // Toggle news panel only on market scan page
  const isMarketScanPage = location.pathname === '/market-scan' || location.pathname.includes('market-scan');

  const isLight = theme === 'light';
  const isSpace = theme === 'space';
  
  // Handle navigation click on mobile (close sidebar)
  const handleNavClick = () => {
    if (onClose && window.innerWidth < 1024) {
      onClose();
    }
  };

  // Handle logout and close sidebar on mobile
  const handleLogout = (e?: React.MouseEvent) => {
    // Prevent any default behavior
    e?.preventDefault();
    e?.stopPropagation();
    
    // Clear state first
    logout();
    
    // Close sidebar on mobile
    if (onClose && window.innerWidth < 1024) {
      onClose();
    }
    
    // Navigate immediately using React Router (replace: true prevents back button)
    navigate('/login', { replace: true });
  };

  return (
    <>
      {/* Mobile overlay */}
      {onClose && (
        <div
          className={`fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity duration-300 lg:hidden ${
            isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
          }`}
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <div className={`
        fixed lg:static top-0 left-0 h-screen flex flex-col relative z-50
        ${isCollapsed ? 'w-16' : 'w-64'} transform transition-all duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        ${isLight 
          ? 'bg-white border-r border-gray-200' 
          : isSpace
            ? 'bg-slate-900/95 backdrop-blur-md border-r border-purple-900/20'
            : 'bg-slate-900 border-r border-slate-700'
        }
      `}>
        {/* Header with toggle button */}
        <div className={`flex items-center justify-between p-3 border-b flex-shrink-0 ${
          isLight 
            ? 'border-gray-200' 
            : isSpace 
              ? 'border-purple-900/20' 
              : 'border-slate-700'
        }`}>
          {!isCollapsed && (
            <h1 className={`text-lg font-bold ${
              isLight 
                ? 'text-gray-900' 
                : isSpace 
                  ? 'text-white drop-shadow-lg' 
                  : 'text-white'
            }`}>Trading Hub</h1>
          )}
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className={`p-1.5 rounded transition-colors ${
                isLight
                  ? 'text-gray-600 hover:bg-gray-100'
                  : isSpace
                    ? 'text-white/90 hover:bg-white/10 hover:text-white drop-shadow'
                    : 'text-gray-300 hover:bg-slate-800 hover:text-white'
              }`}
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? (
                <ChevronRight className="w-5 h-5" />
              ) : (
                <ChevronLeft className="w-5 h-5" />
              )}
            </button>
          )}
        </div>
              
        {/* Mobile header with close button */}
        {onClose && (
          <div className={`flex items-center justify-between p-3 border-b lg:hidden flex-shrink-0 ${
            isLight 
              ? 'border-gray-200' 
              : isSpace 
                ? 'border-purple-900/20' 
                : 'border-slate-700'
          }`}>
            <h1 className={`text-lg font-bold ${
              isLight 
                ? 'text-gray-900' 
                : isSpace 
                  ? 'text-white drop-shadow-lg' 
                  : 'text-white'
            }`}>Menu</h1>
            <button
              onClick={onClose}
              className={`p-1.5 rounded transition-colors ${
                isLight
                  ? 'text-gray-600 hover:bg-gray-100'
                  : 'text-gray-400 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        )}
      
        {/* Scrollable navigation area */}
        <nav className={`flex-1 overflow-y-auto p-3 space-y-1 ${isCollapsed ? 'px-1' : ''}`}>
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={handleNavClick}
                className={`flex items-center gap-2 px-3 py-2.5 rounded transition-colors ${
                  isActive
                    ? 'bg-blue-500 text-white'
                    : isLight
                      ? 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                      : isSpace
                        ? 'text-white/90 hover:bg-white/10 hover:text-white drop-shadow'
                        : 'text-gray-300 hover:bg-slate-800 hover:text-white'
                } ${isCollapsed ? '!px-2 !justify-center' : ''}`}
              >
                <Icon className={`w-5 h-5 flex-shrink-0 ${isCollapsed ? 'mx-auto' : ''}`} />
                {!isCollapsed && <span className="font-medium text-sm">{item.label}</span>}
              </Link>
            );
          })}
        </nav>
      
        {/* Fixed footer */}
        {!isCollapsed && (
        <div className={`p-3 border-t flex-shrink-0 ${
          isLight 
            ? 'border-gray-200' 
            : isSpace 
              ? 'border-purple-900/20' 
              : 'border-slate-700'
        }`}>
      
                
          {/* Health Status Indicator */}
          <div className={`flex items-center gap-2 px-3 py-2.5 rounded mb-3 ${
            health.healthy
              ? isLight
                ? 'bg-green-50 border border-green-200'
                : isSpace
                  ? 'bg-green-900/20 border border-green-900/40'
                  : 'bg-green-900/20 border border-green-800/40'
              : isLight
                ? 'bg-red-50 border border-red-200'
                : isSpace
                  ? 'bg-red-900/20 border border-red-900/40'
                  : 'bg-red-900/20 border border-red-800/40'
          }`}>
            <Activity className={`w-4 h-4 flex-shrink-0 ${
              health.healthy
                ? 'text-green-600'
                : 'text-red-600'
            }`} />
            <div className="flex-1 min-w-0">
              <p className={`text-xs font-semibold ${
                health.healthy
                  ? isLight
                    ? 'text-green-700'
                    : isSpace
                      ? 'text-green-300'
                      : 'text-green-400'
                  : isLight
                    ? 'text-red-700'
                    : isSpace
                      ? 'text-red-300'
                      : 'text-red-400'
              }`}>
                System {health.healthy ? 'Online' : 'Offline'}
              </p>
              <p className={`text-xs truncate ${
                health.healthy
                  ? isLight
                    ? 'text-green-600'
                    : isSpace
                      ? 'text-green-400'
                      : 'text-green-500'
                  : isLight
                    ? 'text-red-600'
                    : isSpace
                      ? 'text-red-400'
                      : 'text-red-500'
              }`}>
                {health.status}
              </p>
            </div>
            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
              health.healthy
                ? 'bg-green-500 animate-pulse'
                : 'bg-red-500'
            }`}></div>
          </div>
      
          <button
            onClick={handleLogout}
            className={`flex items-center gap-2 px-3 py-2.5 w-full rounded transition-colors ${
              isLight
                ? 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                : isSpace
                  ? 'text-white/90 hover:bg-white/10 hover:text-white drop-shadow'
                  : 'text-gray-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            <span className="font-medium text-sm">Logout</span>
          </button>
        </div>
        )}
        

      </div>
    </>
  );
};

export default Sidebar;