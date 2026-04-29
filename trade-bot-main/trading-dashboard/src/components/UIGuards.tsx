import React from 'react';
import { type DataStatus, type PredictionResult } from '../services/apiClient';

interface DataStatusGuardProps {
  dataStatus: DataStatus;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function DataStatusGuard({ dataStatus, children, fallback }: DataStatusGuardProps) {
  if (dataStatus.data_source === 'INVALID') {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded p-3">
        <p className="text-red-400 font-medium">Invalid Data Source</p>
        <p className="text-red-300 text-sm">Cannot display content - data source is invalid</p>
      </div>
    );
  }

  if (dataStatus.data_freshness_seconds > 3600) {
    return (
      <div className="bg-yellow-500/10 border border-yellow-500/30 rounded p-3">
        <p className="text-yellow-400 font-medium">Stale Data Warning</p>
        <p className="text-yellow-300 text-sm">Data is over 1 hour old - content may be unreliable</p>
        {fallback || null}
      </div>
    );
  }

  return <>{children}</>;
}

interface TrustGateGuardProps {
  prediction: PredictionResult;
  children: React.ReactNode;
  restrictedContent?: React.ReactNode;
}

export function TrustGateGuard({ prediction, children, restrictedContent }: TrustGateGuardProps) {
  if (prediction.trust_gate_active) {
    return (
      <div className="space-y-3">
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-yellow-700">
                ⚠️ Signal generated using cached or delayed data during volatile market conditions.
                Prices may differ from live market.
              </p>
            </div>
          </div>
        </div>
        {restrictedContent || (
          <div className="bg-gray-100 border border-gray-300 rounded p-3">
            <p className="text-gray-600 text-sm">Price targets and detailed analysis restricted by backend</p>
          </div>
        )}
      </div>
    );
  }

  return <>{children}</>;
}

interface PriceDisplayGuardProps {
  prediction: PredictionResult;
  children: React.ReactNode;
}

export function PriceDisplayGuard({ prediction, children }: PriceDisplayGuardProps) {
  // Backend removes predicted_price when trust gate is active
  if (prediction.trust_gate_active || !prediction.predicted_price) {
    return (
      <div className="bg-gray-100 border border-gray-300 rounded p-2">
        <p className="text-gray-600 text-sm">Price targets disabled by backend</p>
      </div>
    );
  }

  return <>{children}</>;
}

interface BackendErrorBoundaryProps {
  error: string | null;
  invalid_data: boolean;
  children: React.ReactNode;
}

export function BackendErrorBoundary({ error, invalid_data, children }: BackendErrorBoundaryProps) {
  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
        <h3 className="text-red-400 font-medium mb-2">Backend Error</h3>
        <p className="text-red-300 text-sm">{error}</p>
      </div>
    );
  }

  if (invalid_data) {
    return (
      <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4">
        <h3 className="text-orange-400 font-medium mb-2">Integration Error</h3>
        <p className="text-orange-300 text-sm">Backend response format is invalid - cannot display content</p>
      </div>
    );
  }

  return <>{children}</>;
}

interface LoadingGuardProps {
  loading: boolean;
  children: React.ReactNode;
}

export function LoadingGuard({ loading, children }: LoadingGuardProps) {
  if (loading) {
    return (
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-6 flex items-center justify-center">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-400 mr-3"></div>
        <span className="text-blue-400 font-medium">Loading from backend...</span>
      </div>
    );
  }

  return <>{children}</>;
}