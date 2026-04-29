import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';

type Theme = 'light' | 'dark' | 'space';

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme') as Theme;
    const initialTheme = (saved && ['light', 'dark', 'space'].includes(saved)) ? saved : 'dark';
    console.log('ThemeProvider: Initial theme loaded:', initialTheme);
    return initialTheme;
  });

  useEffect(() => {
    console.log('ThemeProvider: Theme changed to:', theme);
    localStorage.setItem('theme', theme);
    // Apply theme class to document root
    document.documentElement.classList.remove('light', 'dark', 'space');
    document.documentElement.classList.add(theme);
    
    // Also add the theme to body for additional styling
    document.body.className = document.body.className.replace(/theme-\w+/g, '').trim();
    document.body.classList.add(`theme-${theme}`);
    
    // Set a data attribute for more advanced theme targeting
    document.documentElement.setAttribute('data-theme', theme);
    
    // Force a re-render by dispatching a custom event
    window.dispatchEvent(new CustomEvent('themechange', { detail: theme }));
  }, [theme]);

  const setTheme = useCallback((newTheme: Theme) => {
    console.log('ThemeProvider: setTheme called with:', newTheme, 'current theme:', theme);
    if (!['light', 'dark', 'space'].includes(newTheme)) {
      console.error('Invalid theme:', newTheme);
      return;
    }
    if (newTheme !== theme) {
      console.log('ThemeProvider: Updating theme from', theme, 'to', newTheme);
      setThemeState(newTheme);
    } else {
      console.log('ThemeProvider: Theme already set to', newTheme);
    }
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
