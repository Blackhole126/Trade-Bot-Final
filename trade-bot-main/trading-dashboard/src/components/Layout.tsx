import { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import Navbar from './Navbar';
import { useNavigate, useLocation } from 'react-router-dom';
import { AssetTypeProvider, useAssetType } from '../contexts/AssetTypeContext';
import { useTheme } from '../contexts/ThemeContext';
import UniGuruBackground from './UniGuruBackground';
import FloatingAIButton from './FloatingAIButton';


interface LayoutProps {
  children: React.ReactNode;
}

const LayoutContent = ({ children }: LayoutProps) => {
  const { assetType, setAssetType } = useAssetType();
  const { theme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [, forceUpdate] = useState({});
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // Determine if we're on the market scan page
  const isOnMarketScan = location.pathname === '/market-scan' || location.pathname.startsWith('/market-scan');

  // Close sidebar when route changes on mobile
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setSidebarOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  // Listen for theme changes to force re-render
  useEffect(() => {
    const handleThemeChange = () => {
      forceUpdate({});
    };
    window.addEventListener('themechange', handleThemeChange);
    return () => window.removeEventListener('themechange', handleThemeChange);
  }, []);

  const handleSearch = (query: string) => {
    // Navigate to market scan with search query and asset type
    navigate(`/market-scan?q=${encodeURIComponent(query)}&type=${assetType}`);
  };

  const handleTabChange = (tab: 'stocks' | 'crypto' | 'commodities') => {
    setAssetType(tab);
    // If on market-scan page, navigate to refresh with new asset type
    if (window.location.pathname === '/market-scan') {
      navigate(`/market-scan?type=${tab}`, { replace: true });
    }
  };

  return (
    <div 
      key={theme} // Force re-render when theme changes
      className={`flex flex-col lg:flex-row h-screen relative w-full overflow-hidden ${
        theme === 'light' ? 'bg-gray-100' : 
        theme === 'space' ? 'bg-[#1b0725]' : // Deep purple-black matching Space theme
        'bg-slate-900'
      }`}
      style={theme === 'space' ? { backgroundColor: '#1b0725' } : undefined}
    >
      {theme === 'space' && <UniGuruBackground key="uniguru-bg" />}
      <Sidebar 
        isOpen={sidebarOpen} 
        onClose={() => setSidebarOpen(false)} 
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div className={`flex-1 flex flex-col overflow-hidden relative z-10 w-full min-w-0`}>
        <Navbar 
          onSearch={handleSearch} 
          activeTab={assetType} 
          onTabChange={handleTabChange}
          onMenuClick={() => setSidebarOpen(true)}
          showAssetTabs={isOnMarketScan}
        />
        <main className="flex-1 overflow-y-auto px-2 py-2 sm:px-3 sm:py-3 md:px-4 md:py-4 lg:px-6 lg:py-6 relative z-10 w-full">
          <div className="w-full h-full min-h-0">
            {children}
          </div>
        </main>
        <FloatingAIButton />
      </div>
    </div>
  );
};

const Layout = ({ children }: LayoutProps) => {
  return (
      <AssetTypeProvider>
        <LayoutContent>{children}</LayoutContent>
      </AssetTypeProvider>
  );
};

export default Layout;