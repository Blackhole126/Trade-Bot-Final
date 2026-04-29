import React from 'react';
import { type HardenedApiResult, type FailureMode } from '../services/hardenedApiClient';
import { type StrictPredictResponse } from '../validators/contractValidator';

interface IntegrationInspectorProps {
  result: HardenedApiResult<StrictPredictResponse> | null;
  guardStates: {
    trustGateActive: boolean[];
    dataSourceBlocked: boolean[];
    priceDisplayBlocked: boolean[];
  };
}

export function IntegrationInspector({ result, guardStates }: IntegrationInspectorProps) {
  // ONLY VISIBLE IN DEV MODE
  if (!import.meta.env.DEV) {
    return null;
  }

  const getFailureModeColor = (mode: FailureMode) => {
    switch (mode) {
      case 'backend_unavailable': return 'text-red-600';
      case 'backend_error_response': return 'text-orange-600';
      case 'invalid_data': return 'text-purple-600';
      case 'contract_drift': return 'text-pink-600';
      case 'trust_gate_active': return 'text-yellow-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className="fixed bottom-4 right-4 w-96 bg-black text-green-400 font-mono text-xs border border-green-600 rounded shadow-lg max-h-96 overflow-y-auto">
      <div className="bg-green-600 text-black px-3 py-1 font-bold">
        INTEGRATION INSPECTOR (DEV ONLY)
      </div>
      
      <div className="p-3 space-y-3">
        {/* API RESULT STATUS */}
        <div>
          <div className="text-green-300 font-bold">API RESULT:</div>
          {result ? (
            <div className="ml-2">
              <div>Success: {result.success ? 'TRUE' : 'FALSE'}</div>
              {result.failureMode && (
                <div className={getFailureModeColor(result.failureMode)}>
                  Failure Mode: {result.failureMode}
                </div>
              )}
              {result.error && (
                <div className="text-red-400">Error: {result.error}</div>
              )}
            </div>
          ) : (
            <div className="ml-2 text-gray-400">No API call made</div>
          )}
        </div>

        {/* CONTRACT DRIFT */}
        {result?.contractDrift && (
          <div>
            <div className="text-pink-300 font-bold">CONTRACT DRIFT DETECTED:</div>
            <div className="ml-2">
              <div>Version: {result.contractDrift.contractVersion}</div>
              <div>Errors:</div>
              <ul className="ml-4 list-disc">
                {result.contractDrift.errors.map((error, i) => (
                  <li key={i} className="text-pink-400">{error}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* UI GUARD STATES */}
        <div>
          <div className="text-green-300 font-bold">UI GUARDS:</div>
          <div className="ml-2">
            <div>Trust Gate Active: {guardStates.trustGateActive.length} predictions</div>
            <div>Data Source Blocked: {guardStates.dataSourceBlocked.length} predictions</div>
            <div>Price Display Blocked: {guardStates.priceDisplayBlocked.length} predictions</div>
          </div>
        </div>

        {/* RAW RESPONSE */}
        {result?.rawResponse && (
          <div>
            <div className="text-green-300 font-bold">RAW BACKEND RESPONSE:</div>
            <pre className="ml-2 text-xs bg-gray-900 p-2 rounded overflow-x-auto max-h-32">
              {JSON.stringify(result.rawResponse, null, 2)}
            </pre>
          </div>
        )}

        {/* VALIDATION DETAILS */}
        {result?.success && result.data && (
          <div>
            <div className="text-green-300 font-bold">VALIDATION PASSED:</div>
            <div className="ml-2">
              <div>Predictions: {result.data.predictions.length}</div>
              <div>Horizon: {result.data.metadata.horizon}</div>
              <div>Required Fields: ALL PRESENT</div>
            </div>
          </div>
        )}

        {/* RENDERING BLOCKS */}
        <div>
          <div className="text-green-300 font-bold">RENDERING STATUS:</div>
          <div className="ml-2">
            {result?.success ? (
              <div className="text-green-400">✓ Content rendering ALLOWED</div>
            ) : (
              <div className="text-red-400">✗ Content rendering BLOCKED</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}