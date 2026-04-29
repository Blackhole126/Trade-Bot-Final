import React from 'react';
import { type StrictDataStatus, type StrictPredictionResult } from '../validators/contractValidator';

interface HardenedDataStatusGuardProps {
  dataStatus: StrictDataStatus;
  children: React.ReactNode;
}

export function HardenedDataStatusGuard({ dataStatus, children }: HardenedDataStatusGuardProps) {
  // BLOCK RENDERING ON INVALID DATA SOURCE
  if (dataStatus.data_source === 'INVALID') {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded p-3">
        <p className="text-red-400 font-medium">INVALID DATA SOURCE</p>
        <p className="text-red-300 text-sm">Rendering blocked - data source validation failed</p>
      </div>
    );
  }

  return <>{children}</>;
}

interface HardenedTrustGateGuardProps {
  prediction: StrictPredictionResult;
  children: React.ReactNode;
}

export function HardenedTrustGateGuard({ prediction, children }: HardenedTrustGateGuardProps) {
  // ENFORCE BACKEND TRUST GATE - NO FRONTEND OVERRIDE
  if (prediction.trust_gate_active) {
    return (
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
    );
  }

  return <>{children}</>;
}

interface HardenedPriceDisplayGuardProps {
  prediction: StrictPredictionResult;
  children: React.ReactNode;
}

export function HardenedPriceDisplayGuard({ prediction, children }: HardenedPriceDisplayGuardProps) {
  // BLOCK PRICE DISPLAY IF BACKEND REMOVES predicted_price OR ACTIVATES TRUST GATE
  if (prediction.trust_gate_active || prediction.predicted_price === undefined) {
    return (
      <div className="bg-gray-100 border border-gray-300 rounded p-2">
        <p className="text-gray-600 text-sm">Price targets disabled by backend</p>
      </div>
    );
  }

  return <>{children}</>;
}

interface FailureModeDisplayProps {
  mode: 'backend_unavailable' | 'backend_error_response' | 'invalid_data' | 'contract_drift';
  error?: string;
  contractDriftDetails?: any;
}

export function FailureModeDisplay({ mode, error, contractDriftDetails }: FailureModeDisplayProps) {
  switch (mode) {
    case 'backend_unavailable':
      return (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
          <h3 className="text-red-400 font-medium mb-2">Backend Unavailable</h3>
          <p className="text-red-300 text-sm">Cannot connect to backend server. Check if server is running.</p>
        </div>
      );

    case 'backend_error_response':
      return (
        <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4">
          <h3 className="text-orange-400 font-medium mb-2">Backend Error</h3>
          <p className="text-orange-300 text-sm">{error || 'Backend returned an error response'}</p>
        </div>
      );

    case 'invalid_data':
      return (
        <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4">
          <h3 className="text-purple-400 font-medium mb-2">Invalid Data Format</h3>
          <p className="text-purple-300 text-sm">{error || 'Backend response format is invalid'}</p>
        </div>
      );

    case 'contract_drift':
      return (
        <div className="bg-pink-500/10 border border-pink-500/30 rounded-lg p-4">
          <h3 className="text-pink-400 font-medium mb-2">Contract Drift Detected</h3>
          <p className="text-pink-300 text-sm">Backend response does not match expected contract.</p>
          <p className="text-pink-300 text-sm">Integration halted.</p>
          {contractDriftDetails && (
            <details className="mt-2">
              <summary className="text-pink-400 cursor-pointer">View Details</summary>
              <pre className="text-xs bg-pink-900/20 p-2 rounded mt-1 overflow-x-auto">
                {JSON.stringify(contractDriftDetails.errors, null, 2)}
              </pre>
            </details>
          )}
        </div>
      );

    default:
      return (
        <div className="bg-gray-500/10 border border-gray-500/30 rounded-lg p-4">
          <h3 className="text-gray-400 font-medium mb-2">Unknown Error</h3>
          <p className="text-gray-300 text-sm">An unexpected error occurred</p>
        </div>
      );
  }
}

interface HardenedLoadingGuardProps {
  loading: boolean;
  children: React.ReactNode;
}

export function HardenedLoadingGuard({ loading, children }: HardenedLoadingGuardProps) {
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