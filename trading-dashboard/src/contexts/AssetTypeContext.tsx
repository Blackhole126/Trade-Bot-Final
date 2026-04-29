import React, { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

type AssetType = 'stocks' | 'crypto' | 'commodities';

interface AssetTypeContextType {
  assetType: AssetType;
  setAssetType: (type: AssetType) => void;
}

const AssetTypeContext = createContext<AssetTypeContextType | undefined>(undefined);

export const AssetTypeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [assetType, setAssetType] = useState<AssetType>('stocks');

  const handleSetAssetType = (type: AssetType) => {
    setAssetType(type);
  };

  return (
    <AssetTypeContext.Provider value={{ assetType, setAssetType: handleSetAssetType }}>
      {children}
    </AssetTypeContext.Provider>
  );
};

export const useAssetType = (): AssetTypeContextType => {
  const context = useContext(AssetTypeContext);
  if (!context) {
    throw new Error('useAssetType must be used within AssetTypeProvider');
  }
  return context;
};

