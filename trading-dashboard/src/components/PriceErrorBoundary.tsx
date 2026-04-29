import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

interface PriceErrorBoundaryProps {
  children: React.ReactNode;
  symbol?: string;
  fallback?: React.ReactNode;
  onError?: (error: Error) => void;
}

interface PriceErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class PriceErrorBoundary extends React.Component<
  PriceErrorBoundaryProps,
  PriceErrorBoundaryState
> {
  constructor(props: PriceErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): PriceErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(
      `[PRICE ERROR BOUNDARY] Error with ${this.props.symbol || 'unknown symbol'}:`,
      error,
      errorInfo
    );

    if (this.props.onError) {
      this.props.onError(error);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <PriceErrorDisplay
          symbol={this.props.symbol}
          error={this.state.error}
          fallback={this.props.fallback}
        />
      );
    }

    return this.props.children;
  }
}

interface PriceErrorDisplayProps {
  symbol?: string;
  error: Error | null;
  fallback?: React.ReactNode;
}

const PriceErrorDisplay: React.FC<PriceErrorDisplayProps> = ({
  symbol,
  error,
  fallback
}) => {
  const { theme } = useTheme();
  const isLight = theme === 'light';

  const bgColor = isLight ? 'bg-red-50' : 'bg-red-900/20';
  const borderColor = isLight ? 'border-red-200' : 'border-red-800';
  const textColor = isLight ? 'text-red-700' : 'text-red-400';
  const headingColor = isLight ? 'text-red-900' : 'text-red-200';

  const displaySymbol = symbol ? ` for ${symbol}` : '';
  const errorMessage = error?.message || 'Unknown price error';

  // Check if this is a critical error (missing price) vs a non-critical one
  const isCritical = errorMessage.includes('Invalid currentPrice') ||
    errorMessage.includes('No price available') ||
    errorMessage.includes('Price validation failed');

  return (
    <div
      className={`flex gap-3 p-4 rounded-lg border ${bgColor} ${borderColor}`}
      role="alert"
    >
      <AlertTriangle className={`flex-shrink-0 h-5 w-5 ${textColor} mt-0.5`} />

      <div className="flex-1">
        <h3 className={`font-bold ${headingColor}`}>
          {isCritical ? '⚠️ Invalid Price Data' : '⚠️ Price Error'}
        </h3>

        <p className={`text-sm ${textColor} mt-1`}>
          {isCritical
            ? `Cannot render component${displaySymbol} - price data is missing or invalid.`
            : `Error loading price${displaySymbol}: ${errorMessage}`}
        </p>

        {isCritical && (
          <p className={`text-xs ${textColor} mt-2 opacity-75`}>
            This usually means the backend API did not return a valid price.
            Please check the backend logs or try refreshing.
          </p>
        )}

        {fallback && <div className="mt-3">{fallback}</div>}
      </div>
    </div>
  );
};

export default PriceErrorBoundary;
