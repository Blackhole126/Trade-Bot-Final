import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { BackendStatusProvider } from './contexts/BackendStatusContext';
import { ConnectionProvider } from './contexts/ConnectionContext';
import { HealthProvider } from './contexts/HealthContext';
import { PortfolioProvider } from './contexts/PortfolioContext';
import { ScenarioProvider } from './contexts/ScenarioContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { GlobalOfflineIndicator } from './components/GlobalOfflineIndicator';
import { AppRoutes } from './routes';
import ErrorBoundary from './components/ErrorBoundary';
import './App.css';

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ThemeProvider>
          <BackendStatusProvider>
            <GlobalOfflineIndicator />
            <ConnectionProvider>
              <HealthProvider>
                <AuthProvider>
                  <PortfolioProvider>
                    <ScenarioProvider>
                      <NotificationProvider>
                        <AppRoutes />
                      </NotificationProvider>
                    </ScenarioProvider>
                  </PortfolioProvider>
                </AuthProvider>
              </HealthProvider>
            </ConnectionProvider>
          </BackendStatusProvider>
        </ThemeProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;

