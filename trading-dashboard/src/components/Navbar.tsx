import { Bell, User, Sun, Moon, Sparkles, Menu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import NotificationCenter from './NotificationCenter';


interface NavbarProps {
  activeTab: 'stocks' | 'crypto' | 'commodities';
  onTabChange: (tab: 'stocks' | 'crypto' | 'commodities') => void;
  onMenuClick?: () => void;
  showAssetTabs?: boolean;
}

const Navbar = ({ activeTab, onTabChange, onMenuClick, showAssetTabs = false }: NavbarProps) => {
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();
  const navigate = useNavigate();

  // Cycle through themes
  const cycleTheme = () => {
    try {
      const themes: Array<'light' | 'dark' | 'space'> = ['light', 'dark', 'space'];
      const currentIndex = themes.indexOf(theme);
      const nextIndex = (currentIndex + 1) % themes.length;
      const nextTheme = themes[nextIndex];

      console.log('Changing theme to:', nextTheme);
      if (setTheme && typeof setTheme === 'function') {
        setTheme(nextTheme);
      }
    } catch (error) {
      console.error('Error cycling theme:', error);
    }
  };

  const isLight = theme === 'light';
  const isSpace = theme === 'space';

  return (
    <div className={`px-2 sm:px-3 md:px-4 py-2 sm:py-2.5 md:py-3 border-b relative z-30 sticky top-0 ${isLight
      ? 'bg-white border-gray-200'
      : isSpace
        ? 'bg-transparent border-purple-900/20'
        : 'bg-slate-800 border-slate-700'
      }`}>
      <div className="flex items-center justify-between gap-1 sm:gap-2 md:gap-3">
        {/* Mobile Menu Button */}
        {onMenuClick && (
          <button
            onClick={onMenuClick}
            className={`lg:hidden p-2 rounded transition-colors flex-shrink-0 ${isLight
              ? 'text-gray-600 hover:bg-gray-100'
              : 'text-gray-300 hover:bg-slate-700 hover:text-white'
              }`}
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}


        {/* Right side controls - Responsive */}
        <div className="flex items-center gap-0.5 sm:gap-1.5 md:gap-2 flex-shrink-0">

          {/* Tab Switcher - Responsive with tooltips - Only show when showAssetTabs is true */}
          {showAssetTabs && (
            <div className={`flex gap-0.5 sm:gap-1 rounded p-0.5 ${isLight ? 'bg-gray-100' : isSpace ? 'bg-slate-800/60 backdrop-blur-sm' : 'bg-slate-700'
              }`}>
              {(['stocks', 'crypto', 'commodities'] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onTabChange(tab);
                  }}
                  className={`px-2 sm:px-2.5 md:px-3 py-1 rounded text-xs sm:text-xs md:text-sm font-medium transition-colors cursor-pointer relative z-10 whitespace-nowrap ${activeTab === tab
                    ? 'bg-blue-500 text-white shadow-lg'
                    : isLight
                      ? 'text-gray-700 hover:text-gray-900 hover:bg-gray-200'
                      : 'text-gray-300 hover:text-white hover:bg-slate-600'
                    }`}
                  title={tab.charAt(0).toUpperCase() + tab.slice(1)}
                >
                  <span className="inline">{tab.charAt(0).toUpperCase() + tab.slice(1)}</span>
                </button>
              ))}
            </div>
          )}

          {/* Notification Center - Hidden on mobile */}
          <div className="hidden md:block">
            <NotificationCenter />
          </div>

          {/* Theme Switcher - Cycling Button */}
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              cycleTheme();
            }}
            className={`p-1.5 md:p-2 rounded transition-colors flex items-center gap-1 flex-shrink-0 ${isLight
              ? 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 bg-gray-100/50'
              : isSpace
                ? 'text-white/90 hover:text-white hover:bg-white/10 drop-shadow bg-purple-900/20'
                : 'text-gray-300 hover:text-white hover:bg-slate-700 bg-slate-800/50'
              }`}
            title={`Current theme: ${theme.charAt(0).toUpperCase() + theme.slice(1)}. Click to cycle theme.`}
          >
            {theme === 'light' && <Sun className="w-4 h-4" />}
            {theme === 'dark' && <Moon className="w-4 h-4" />}
            {theme === 'space' && <Sparkles className="w-4 h-4" />}
          </button>

          {/* User Profile - Responsive */}
          <button
            onClick={() => navigate('/profile')}
            title={user?.username ? `View profile for ${user.username}` : 'View profile'}
            className={`p-1.5 md:p-2 rounded-lg transition-colors flex-shrink-0 ${isLight
              ? 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              : isSpace
                ? 'text-white/90 hover:text-white hover:bg-white/10 drop-shadow'
                : 'text-gray-300 hover:text-white hover:bg-slate-700'
              }`}>
            <User className="w-4 h-4 sm:w-4 sm:h-4 md:w-5 md:h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Navbar;
