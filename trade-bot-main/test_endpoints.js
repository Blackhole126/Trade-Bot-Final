#!/usr/bin/env node

/**
 * Comprehensive API Endpoint Testing
 * Tests all 13 endpoints and reports results
 */

const http = require('http');
const https = require('https');

const BASE_URL = 'http://127.0.0.1:8000';

function makeRequest(method, endpoint, data = null, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const url = new URL(endpoint, BASE_URL);
    const options = {
      method,
      timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const startTime = Date.now();
    const client = url.protocol === 'https:' ? https : http;

    const req = client.request(url, options, (res) => {
      let data = '';
      
      res.on('data', chunk => {
        data += chunk;
      });

      res.on('end', () => {
        const duration = Date.now() - startTime;
        resolve({
          status: res.statusCode,
          duration,
          data: data.slice(0, 200),
        });
      });
    });

    req.on('error', (err) => {
      const duration = Date.now() - startTime;
      reject({
        error: err.message,
        duration,
      });
    });

    req.on('timeout', () => {
      req.destroy();
      const duration = Date.now() - startTime;
      reject({
        error: 'Timeout',
        duration,
      });
    });

    if (data) {
      req.write(JSON.stringify(data));
    }
    req.end();
  });
}

async function runTests() {
  console.log('\n' + '='.repeat(70));
  console.log('COMPREHENSIVE API ENDPOINT TESTING'.padStart(50));
  console.log('='.repeat(70) + '\n');

  const tests = [
    { num: 1, method: 'GET', endpoint: '/', name: 'API Info' },
    { num: 2, method: 'GET', endpoint: '/tools/health', name: 'System Health' },
    { num: 3, method: 'GET', endpoint: '/auth/status', name: 'Auth Status' },
    { 
      num: 4, method: 'POST', endpoint: '/tools/predict', name: 'Predict (AAPL)',
      data: { symbols: ['AAPL'], timeframe: 'intraday' }
    },
    { 
      num: 5, method: 'POST', endpoint: '/tools/predict', name: 'Predict (Multi)',
      data: { symbols: ['GOOGL', 'MSFT'], timeframe: 'intraday' }
    },
    { 
      num: 6, method: 'POST', endpoint: '/tools/scan_all', name: 'Scan All',
      data: { limit: 5 }
    },
    { 
      num: 7, method: 'POST', endpoint: '/tools/analyze', name: 'Analyze',
      data: { symbol: 'AAPL', current_price: 150, predicted_price: 155, confidence: 0.85 }
    },
    { 
      num: 8, method: 'POST', endpoint: '/tools/feedback', name: 'Feedback',
      data: { symbol: 'AAPL', prediction_id: 'test', feedback_type: 'correct' }
    },
    { 
      num: 9, method: 'POST', endpoint: '/tools/fetch_data', name: 'Fetch Data',
      data: { symbols: ['AAPL'], start_date: '2026-01-01', end_date: '2026-01-21' }
    },
    { 
      num: 10, method: 'POST', endpoint: '/api/risk/assess', name: 'Risk Assess',
      data: { symbol: 'AAPL', entry_price: 150, current_price: 152, portfolio_value: 10000 }
    },
    { 
      num: 11, method: 'POST', endpoint: '/api/risk/stop-loss', name: 'Stop Loss',
      data: { symbol: 'AAPL', entry_price: 150, stop_loss_percentage: 5 }
    },
    { 
      num: 12, method: 'POST', endpoint: '/api/ai/chat', name: 'AI Chat',
      data: { message: 'What are your thoughts on AAPL?' }
    },
    { 
      num: 13, method: 'GET', endpoint: '/docs', name: 'Swagger Docs'
    },
  ];

  let passed = 0, failed = 0;
  const results = [];

  for (const test of tests) {
    process.stdout.write(`[${test.num}/13] Testing ${test.method} ${test.endpoint} (${test.name})... `);
    
    try {
      const result = await makeRequest(test.method, test.endpoint, test.data);
      
      if (result.status >= 200 && result.status < 300) {
        console.log(`✓ HTTP ${result.status} (${result.duration}ms)`);
        passed++;
        results.push({ ...test, status: result.status, duration: result.duration, success: true });
      } else {
        console.log(`✗ HTTP ${result.status} (${result.duration}ms)`);
        failed++;
        results.push({ ...test, status: result.status, duration: result.duration, success: false });
      }
    } catch (err) {
      console.log(`✗ ${err.error} (${err.duration}ms)`);
      failed++;
      results.push({ ...test, error: err.error, duration: err.duration, success: false });
    }
  }

  console.log('\n' + '='.repeat(70));
  console.log('SUMMARY'.padStart(40));
  console.log('='.repeat(70));
  console.log(`✓ PASSED: ${passed}/${tests.length}`);
  console.log(`✗ FAILED: ${failed}/${tests.length}`);
  console.log('='.repeat(70) + '\n');

  if (failed === 0) {
    console.log('🎉 ALL TESTS PASSED!');
  } else {
    console.log('⚠️  SOME TESTS FAILED - Details below:\n');
    const failedTests = results.filter(r => !r.success);
    for (const test of failedTests) {
      console.log(`  ✗ [${test.method}] ${test.endpoint}`);
      console.log(`    Error: ${test.error || `HTTP ${test.status}`}`);
    }
  }
  
  console.log('\n');
}

runTests().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
