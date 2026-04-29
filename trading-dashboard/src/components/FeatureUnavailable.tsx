import { AlertCircle, Info } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

interface FeatureUnavailableProps {
  feature: string;
  reason: string;
  suggestion?: string;
  mode?: 'error' | 'warning' | 'info';
}

export const FeatureUnavailable = ({ 
  feature, 
  reason, 
  suggestion,
  mode = 'warning' 
}: FeatureUnavailableProps) => {
  const { theme } = useTheme();
  const isLight = theme === 'light';

  const colors = {
    error: isLight ? 'bg-red-50 border-red-300 text-red-700' : 'bg-red-900/20 border-red-500/50 text-red-300',
    warning: isLight ? 'bg-yellow-50 border-yellow-300 text-yellow-800' : 'bg-yellow-900/20 border-yellow-500/50 text-yellow-300',
    info: isLight ? 'bg-blue-50 border-blue-300 text-blue-700' : 'bg-blue-900/20 border-blue-500/50 text-blue-300',
  };

  const iconColors = {
    error: isLight ? 'text-red-600' : 'text-red-400',
    warning: isLight ? 'text-yellow-600' : 'text-yellow-400',
    info: isLight ? 'text-blue-600' : 'text-blue-400',
  };

  return (
    <div className={`border-2 rounded-xl p-6 ${colors[mode]}`}>
      <div className="flex items-start gap-4">
        {mode === 'info' ? (
          <Info className={`w-6 h-6 flex-shrink-0 ${iconColors[mode]}`} />
        ) : (
          <AlertCircle className={`w-6 h-6 flex-shrink-0 ${iconColors[mode]}`} />
        )}
        <div className="flex-1">
          <h3 className="font-bold text-lg mb-2">{feature}</h3>
          <p className="text-sm mb-3">{reason}</p>
          {suggestion && (
            <p className="text-sm font-medium">{suggestion}</p>
          )}
        </div>
      </div>
    </div>
  );
};
