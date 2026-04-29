/**
 * Quick Endpoint Test Utility
 * Run this in browser console to test all endpoints
 */

import { verifyAllEndpoints } from './endpointVerification';

// Make it globally available
if (typeof window !== 'undefined') {
  // @ts-ignore
  window.runEndpointTests = async () => {
    console.log('🚀 Starting endpoint verification...');
    try {
      const results = await verifyAllEndpoints();
      console.log('✅ All tests completed!');
      return results;
    } catch (error) {
      console.error('❌ Test failed:', error);
      throw error;
    }
  };
  
  console.log('%c✨ Endpoint test utility loaded!', 'color: #4ade80; font-weight: bold;');
  console.log('%cRun: await window.runEndpointTests()', 'color: #60a5fa;');
}

export { verifyAllEndpoints };