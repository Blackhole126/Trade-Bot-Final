import { useState, useEffect, useRef, useMemo } from 'react';
import { POPULAR_STOCKS } from '../services/api';

interface SymbolAutocompleteProps {
  value: string;
  onChange: (symbol: string) => void;
  onSelect?: (symbol: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  excludeSymbols?: string[];
  maxSuggestions?: number;
}

const SymbolAutocomplete = ({
  value,
  onChange,
  onSelect,
  placeholder = 'e.g., AAPL, RELIANCE.NS',
  disabled = false,
  className = '',
  excludeSymbols = [],
  maxSuggestions = 8
}: SymbolAutocompleteProps) => {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  const memoizedExcludeSymbols = useMemo(() => excludeSymbols, [excludeSymbols.join(',')]);

  useEffect(() => {
    if (value.length > 0) {
      const query = value.toUpperCase();
      const filtered = POPULAR_STOCKS.filter(
        stock => stock.includes(query) && !memoizedExcludeSymbols.includes(stock)
      ).slice(0, maxSuggestions);
      setSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
      setSelectedIndex(-1);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  }, [value, memoizedExcludeSymbols, maxSuggestions]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const upperValue = e.target.value.toUpperCase();
    onChange(upperValue);
  };

  const handleSelectSuggestion = (symbol: string) => {
    onChange(symbol);
    setSuggestions([]);
    setShowSuggestions(false);
    setSelectedIndex(-1);
    if (onSelect) {
      onSelect(symbol);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showSuggestions || suggestions.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => 
        prev < suggestions.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (selectedIndex >= 0) {
        handleSelectSuggestion(suggestions[selectedIndex]);
      } else if (onSelect && value) {
        onSelect(value);
      }
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      setSelectedIndex(-1);
    }
  };

  const handleFocus = () => {
    if (value && suggestions.length > 0) {
      setShowSuggestions(true);
    }
  };

  const handleBlur = () => {
    setTimeout(() => {
      setShowSuggestions(false);
      setSelectedIndex(-1);
    }, 200);
  };

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={handleFocus}
        onBlur={handleBlur}
        disabled={disabled}
        placeholder={placeholder}
        className={`w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-gray-500 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500 ${className}`}
      />
      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute z-10 w-full mt-1 bg-slate-700 border border-slate-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {suggestions.map((symbol, index) => (
            <button
              key={symbol}
              onClick={() => handleSelectSuggestion(symbol)}
              className={`w-full px-3 py-2 text-left text-white hover:bg-slate-600 transition-colors text-sm ${
                index === selectedIndex ? 'bg-slate-600' : ''
              }`}
            >
              {symbol}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default SymbolAutocomplete;
