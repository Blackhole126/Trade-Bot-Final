import { useEffect, useRef } from 'react';
import type { ISeriesApi } from 'lightweight-charts';

interface StopLossLineProps {
  candlestickSeries: ISeriesApi<'Candlestick'> | null;
  price: number;
  side: 'BUY' | 'SELL';
  isActive: boolean;
  onPriceChange: (newPrice: number) => void;
}

const StopLossLine = ({
  candlestickSeries,
  price,
  side,
  isActive,
}: StopLossLineProps) => {
  const priceLineRef = useRef<any>(null);

  // Create price line for stop-loss on the candlestick series
  useEffect(() => {
    if (!candlestickSeries || !isActive) {
      // Remove existing price line if any
      if (priceLineRef.current && candlestickSeries) {
        try {
          candlestickSeries.removePriceLine(priceLineRef.current);
        } catch (e) {
          // Price line might already be removed
        }
        priceLineRef.current = null;
      }
      return;
    }

    // Remove existing price line before creating new one
    if (priceLineRef.current) {
      try {
        candlestickSeries.removePriceLine(priceLineRef.current);
      } catch (e) {
        // Ignore errors
      }
    }

    // Create price line on the candlestick series
    const priceLine = candlestickSeries.createPriceLine({
      price: price,
      color: '#ef4444',
      lineWidth: 2,
      lineStyle: 2, // Dashed
      axisLabelVisible: true,
      title: `Stop-Loss (${side}): ₹${price.toFixed(2)}`,
    });

    priceLineRef.current = priceLine;

    return () => {
      // Remove price line when component unmounts or price changes
      if (priceLineRef.current && candlestickSeries) {
        try {
          candlestickSeries.removePriceLine(priceLineRef.current);
        } catch (e) {
          // Price line might already be removed
        }
        priceLineRef.current = null;
      }
    };
  }, [candlestickSeries, isActive, side, price]);

  // Handle mouse events for dragging (simplified - lightweight-charts doesn't have built-in drag)
  // This is a placeholder - actual dragging would require more complex implementation
  // For now, the line is updated via the panel input

  return null; // This component doesn't render anything visible, it just manages the chart series
};

export default StopLossLine;

