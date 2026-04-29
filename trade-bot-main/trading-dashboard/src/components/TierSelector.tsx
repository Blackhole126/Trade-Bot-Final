import React, { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';

interface TierSelectorProps {
  onTierChange?: (tier: 'SEED' | 'TREE' | 'SKY') => void;
}

const TierSelector: React.FC<TierSelectorProps> = ({ onTierChange }) => {
  const [activeTier, setActiveTier] = useState<'SEED' | 'TREE' | 'SKY'>('SEED');
  const { theme } = useTheme();
  
  const isLight = theme === 'light';
  const isSpace = theme === 'space';

  const handleTierChange = (tier: 'SEED' | 'TREE' | 'SKY') => {
    setActiveTier(tier);
    if (onTierChange) {
      onTierChange(tier);
    }
  };

  return (
    <div className={`flex gap-2 p-2 rounded-lg ${
      isLight ? 'bg-gray-100' : isSpace ? 'bg-slate-800' : 'bg-gray-800'
    }`}>
      <button
        onClick={() => handleTierChange('SEED')}
        className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          activeTier === 'SEED'
            ? 'bg-blue-600 text-white'
            : isLight
              ? 'bg-gray-300 text-gray-700 hover:bg-gray-400'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        SEED
      </button>
      <button
        onClick={() => handleTierChange('TREE')}
        className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          activeTier === 'TREE'
            ? 'bg-blue-600 text-white'
            : isLight
              ? 'bg-gray-300 text-gray-700 hover:bg-gray-400'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        TREE
      </button>
      <button
        onClick={() => handleTierChange('SKY')}
        className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          activeTier === 'SKY'
            ? 'bg-blue-600 text-white'
            : isLight
              ? 'bg-gray-300 text-gray-700 hover:bg-gray-400'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        SKY
      </button>
    </div>
  );
};

export default TierSelector;