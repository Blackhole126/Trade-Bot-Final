import { useState, useRef, useEffect } from 'react';
import { Search, Bell, User, Sun, Moon, Sparkles, Menu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { POPULAR_STOCKS, POPULAR_CRYPTO, POPULAR_COMMODITIES } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import ServerStatusIndicator from './ServerStatusIndicator';
import NotificationCenter from './NotificationCenter';


interface NavbarProps {
  onSearch: (query: string) => void;
  activeTab: 'stocks' | 'crypto' | 'commodities';
  onTabChange: (tab: 'stocks' | 'crypto' | 'commodities') => void;
  onMenuClick?: () => void;
  showAssetTabs?: boolean;
}

const Navbar = ({ onSearch, activeTab, onTabChange, onMenuClick, showAssetTabs = false }: NavbarProps) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [filteredSymbols, setFilteredSymbols] = useState<string[]>([]);
  // Removed showThemeMenu state since we're now using a cycling button
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();
  const navigate = useNavigate();
  // Removed themeMenuRef since we're not using dropdown anymore
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Get appropriate symbol list based on active tab
  const getSymbolList = () => {
    if (activeTab === 'stocks') return POPULAR_STOCKS;
    if (activeTab === 'crypto') return POPULAR_CRYPTO;
    if (activeTab === 'commodities') return POPULAR_COMMODITIES;
    return POPULAR_STOCKS;
  };

  const handleSearchChange = (value: string) => {
    try {
      setSearchQuery(value);
      if (value.length > 0) {
        const symbols = getSymbolList();
        const filtered = symbols.filter((symbol) =>
          symbol.toLowerCase().includes(value.toLowerCase())
        ).slice(0, 10);
        setFilteredSymbols(filtered);
        setShowSuggestions(true);
      } else {
        setFilteredSymbols([]);
        setShowSuggestions(false);
      }
    } catch (error) {
      console.error('Error in search change:', error);
      setFilteredSymbols([]);
      setShowSuggestions(false);
    }
  };

  const handleSelectStock = (symbol: string) => {
    try {
      setSearchQuery(symbol);
      setShowSuggestions(false);
      if (onSearch && typeof onSearch === 'function') {
        onSearch(symbol);
      }
    } catch (error) {
      console.error('Error selecting stock:', error);
      setShowSuggestions(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    try {
      e.preventDefault();
      if (searchQuery && onSearch && typeof onSearch === 'function') {
        onSearch(searchQuery);
        setShowSuggestions(false);
      }
    } catch (error) {
      console.error('Error submitting search:', error);
      setShowSuggestions(false);
    }
  };

  // Removed the effect that handles clicks outside theme menu since we're not using dropdown

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };

    if (showSuggestions) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [showSuggestions]);

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
    <div className={`px-2 sm:px-3 md:px-4 py-2 sm:py-2.5 md:py-3 border-b relative z-30 sticky top-0 ${
      isLight 
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
            className={`lg:hidden p-2 rounded transition-colors flex-shrink-0 ${
              isLight
                ? 'text-gray-600 hover:bg-gray-100'
                : 'text-gray-300 hover:bg-slate-700 hover:text-white'
            }`}
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        
        {/* Search Container - Responsive sizing */}
        <div ref={searchContainerRef} className="flex-1 min-w-0 max-w-full md:max-w-2xl lg:max-w-3xl relative z-40">
          <form onSubmit={handleSubmit} className="relative">
            <Search className={`absolute left-2.5 top-1/2 transform -translate-y-1/2 w-3.5 h-3.5 sm:w-4 sm:h-4 pointer-events-none ${
              isLight ? 'text-gray-500' : isSpace ? 'text-gray-300' : 'text-gray-400'
            }`} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              onFocus={() => searchQuery && setShowSuggestions(true)}
              onBlur={() => {
                // Delay to allow click on suggestion
                setTimeout(() => setShowSuggestions(false), 200);
              }}
              placeholder="Search stocks, crypto, commodities..."
              className={`w-full pl-7 sm:pl-8 pr-2 sm:pr-3 py-1.5 sm:py-2 text-xs sm:text-sm md:text-base rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 ${
                isLight
                  ? 'bg-white/80 border border-gray-300 text-gray-900 placeholder-gray-500 backdrop-blur-sm'
                  : isSpace
                    ? 'bg-slate-800/70 backdrop-blur-md border border-purple-900/40 text-white placeholder-gray-300'
                    : 'bg-slate-800/70 backdrop-blur-sm border border-slate-600 text-white placeholder-gray-400'
              }`}
            />
            {/* Search Suggestions - Fixed positioning and z-index */}
            {showSuggestions && filteredSymbols.length > 0 && (
              <div 
                className={`absolute top-full left-0 right-0 mt-1 rounded-lg shadow-2xl max-h-60 overflow-y-auto z-[9999] ${
                  isLight
                    ? 'bg-white border border-gray-300'
                    : isSpace
                      ? 'bg-slate-800/95 backdrop-blur-xl border border-purple-900/50'
                      : 'bg-slate-800/95 backdrop-blur-lg border border-slate-600'
                }`}
                style={{ 
                  position: 'absolute',
                  zIndex: 9999,
                  top: '100%',
                  left: 0,
                  right: 0,
                }}
              >
                {filteredSymbols.map((symbol) => (
                  <button
                    key={symbol}
                    type="button"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      handleSelectStock(symbol);
                    }}
                    className={`w-full px-3 py-2 text-xs sm:text-sm md:text-base text-left transition-colors ${
                      isLight
                        ? 'text-gray-900 hover:bg-blue-50 hover:bg-opacity-80'
                        : 'text-white hover:bg-slate-600 hover:bg-opacity-80'
                    }`}
                  >
                    {symbol}
                  </button>
                ))}
              </div>
            )}
          </form>
        </div>

        {/* Right side controls - Responsive */}
        <div className="flex items-center gap-0.5 sm:gap-1.5 md:gap-2 flex-shrink-0">
          {/* Server Status Indicator - Hidden on very small screens */}
          <ServerStatusIndicator className="hidden lg:block" />
          
          {/* Tab Switcher - Responsive with tooltips - Only show when showAssetTabs is true */}
          {showAssetTabs && (
            <div className={`hidden sm:flex gap-0.5 sm:gap-1 rounded p-0.5 ${
              isLight ? 'bg-gray-100' : isSpace ? 'bg-slate-800/60 backdrop-blur-sm' : 'bg-slate-700'
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
                  className={`px-2 sm:px-2.5 md:px-3 py-1 rounded text-xs sm:text-xs md:text-sm font-medium transition-colors cursor-pointer relative z-10 whitespace-nowrap ${
                    activeTab === tab
                      ? 'bg-blue-500 text-white shadow-lg'
                      : isLight
                        ? 'text-gray-700 hover:text-gray-900 hover:bg-gray-200'
                        : 'text-gray-300 hover:text-white hover:bg-slate-600'
                  }`}
                  title={tab.charAt(0).toUpperCase() + tab.slice(1)}
                >
                  <span className="hidden sm:inline">{tab.charAt(0).toUpperCase() + tab.slice(1)}</span>
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
            className={`p-1.5 md:p-2 rounded transition-colors flex items-center gap-1 flex-shrink-0 ${
              isLight
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
            className={`p-1.5 md:p-2 rounded-lg transition-colors flex-shrink-0 ${
              isLight
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
