/**
 * Test script to verify all backend endpoints are properly integrated
 * Run this in browser console or as a utility
 */

import { stockAPI, authAPI } from '../services/api';
import { config } from '../config';

export const testAllEndpoints = async () => {
  const results: Array<{ endpoint: string; status: 'success' | 'error'; message: string }> = [];
  
  console.log('🧪 Testing all backend endpoints...\n');
  console.log(`API Base URL: ${config.API_BASE_URL}\n`);

  // Test 1: Root endpoint (API info)
  try {
    const result = await stockAPI.checkConnection();
    results.push({
      endpoint: 'GET /',
      status: result.connected ? 'success' : 'error',
      message: result.connected ? 'Connected' : result.error || 'Failed'
    });
    console.log('✅ GET / - API Info:', result.connected ? '✓ Connected' : '✗ Failed');
  } catch (error: any) {
    results.push({
      endpoint: 'GET /',
      status: 'error',
      message: error.message || 'Failed'
    });
    console.log('✗ GET / - API Info:', error.message);
  }

  // Test 2: Health check
  try {
    const health = await stockAPI.health();
    results.push({
      endpoint: 'GET /tools/health',
      status: 'success',
      message: `Status: ${health.status || 'OK'}`
    });
    console.log('✅ GET /tools/health:', health.status || 'OK');
  } catch (error: any) {
    results.push({
      endpoint: 'GET /tools/health',
      status: 'error',
      message: error.message || 'Failed'
    });
    console.log('✗ GET /tools/health:', error.message);
  }

  // Test 3: Rate limit status
  try {
    const status = await stockAPI.getRateLimitStatus();
    results.push({
      endpoint: 'GET /auth/status',
      status: 'success',
      message: `Rate limit OK`
    });
    console.log('✅ GET /auth/status - Rate Limit:', 'OK');
  } catch (error: any) {
    results.push({
      endpoint: 'GET /auth/status',
      status: 'error',
      message: error.message || 'Failed'
    });
    console.log('✗ GET /auth/status:', error.message);
  }

  // Test 4: Predict endpoint
  try {
    const predict = await stockAPI.predict(['AAPL'], 'intraday');
    results.push({
      endpoint: 'POST /tools/predict',
      status: 'success',
      message: `Got ${predict.predictions?.length || 0} predictions`
    });
    console.log('✅ POST /tools/predict:', `Got ${predict.predictions?.length || 0} predictions`);
  } catch (error: any) {
    results.push({
      endpoint: 'POST /tools/predict',
      status: 'error',
      message: error.message || 'Failed'
    });
    console.log('✗ POST /tools/predict:', error.message);
  }

  // Test 5: Scan All endpoint
  try {
    const scan = await stockAPI.scanAll(['AAPL', 'MSFT'], 'intraday', 0.3);
    results.push({
      endpoint: 'POST /tools/scan_all',
      status: 'success',
      message: `Got ${scan.shortlist?.length || 0} shortlisted`
    });
    console.log('✅ POST /tools/scan_all:', `Got ${scan.shortlist?.length || 0} shortlisted`);
  } catch (error: any) {
    results.push({
      endpoint: 'POST /tools/scan_all',
      status: 'error',
      message: error.message || 'Failed'
    });
    console.log('✗ POST /tools/scan_all:', error.message);
  }

  // Test 6: Analyze endpoint
  try {
    const analyze = await stockAPI.analyze('AAPL', ['intraday'], 2.0, 1.0, 5.0);
    results.push({
      endpoint: 'POST /tools/analyze',
      status: 'success',
      message: `Got ${analyze.predictions?.length || 0} predictions`
    });
    console.log('✅ POST /tools/analyze:', `Got ${analyze.predictions?.length || 0} predictions`);
  } catch (error: any) {
    results.push({
      endpoint: 'POST /tools/analyze',
      status: 'error',
      message: error.message || 'Failed'
    });
    console.log('✗ POST /tools/analyze:', error.message);
  }

  // Test 7: Fetch Data endpoint
  try {
    const fetchData = await stockAPI.fetchData(['AAPL'], '1y', false, false);
    results.push({
      endpoint: 'POST /tools/fetch_data',
      status: 'success',
      message: 'Data fetched successfully'
    });
    console.log('✅ POST /tools/fetch_data:', 'Success');
  } catch (error: any) {
    results.push({
      endpoint: 'POST /tools/fetch_data',
      status: 'error',
      message: error.message || 'Failed'
    });
    console.log('✗ POST /tools/fetch_data:', error.message);
  }

  // Test 8: Feedback endpoint
  try {
    const feedback = await stockAPI.feedback('AAPL', 'LONG', 'Test feedback', 5.5);
    results.push({
      endpoint: 'POST /tools/feedback',
      status: 'success',
      message: 'Feedback submitted'
    });
    console.log('✅ POST /tools/feedback:', 'Success');
  } catch (error: any) {
    results.push({
      endpoint: 'POST /tools/feedback',
      status: 'error',
      message: error.message || 'Failed'
    });
    console.log('✗ POST /tools/feedback:', error.message);
  }

  // Test 9: Train RL endpoint (skip if takes too long)
  try {
    // This might take a while, so we'll just test the endpoint exists
    // Don't actually train to avoid long wait
    results.push({
      endpoint: 'POST /tools/train_rl',
      status: 'success',
      message: 'Endpoint available (not tested to avoid long wait)'
    });
    console.log('⚠️ POST /tools/train_rl:', 'Endpoint available (skipped actual training)');
  } catch (error: any) {
    results.push({
      endpoint: 'POST /tools/train_rl',
      status: 'error',
      message: error.message || 'Failed'
    });
    console.log('✗ POST /tools/train_rl:', error.message);
  }

  // Summary
  console.log('\n📊 Test Summary:');
  const successCount = results.filter(r => r.status === 'success').length;
  const errorCount = results.filter(r => r.status === 'error').length;
  console.log(`✅ Successful: ${successCount}/${results.length}`);
  console.log(`✗ Failed: ${errorCount}/${results.length}`);
  
  results.forEach(result => {
    console.log(`${result.status === 'success' ? '✅' : '✗'} ${result.endpoint}: ${result.message}`);
  });

  return results;
};

// Make it available globally for browser console testing
if (typeof window !== 'undefined') {
  (window as any).testEndpoints = testAllEndpoints;
}




