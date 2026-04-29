/**
 * Comprehensive endpoint testing script
 * Tests all API endpoints and reports issues
 */

const BASE_URL = 'http://127.0.0.1:8000';

interface TestResult {
  endpoint: string;
  method: string;
  status: 'PASS' | 'FAIL' | 'ERROR';
  statusCode?: number;
  errorMessage?: string;
  responseTime: number;
  response?: any;
}

const results: TestResult[] = [];

async function testEndpoint(
  method: string,
  endpoint: string,
  payload?: any,
  timeout: number = 30000
): Promise<TestResult> {
  const startTime = Date.now();
  const fullUrl = `${BASE_URL}${endpoint}`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    };

    if (payload && (method === 'POST' || method === 'PUT')) {
      options.body = JSON.stringify(payload);
    }

    const response = await fetch(fullUrl, options);
    clearTimeout(timeoutId);

    const responseTime = Date.now() - startTime;
    let responseBody;

    try {
      responseBody = await response.json();
    } catch (e) {
      responseBody = await response.text();
    }

    const result: TestResult = {
      endpoint,
      method,
      statusCode: response.status,
      responseTime,
      response: responseBody,
      status: response.ok ? 'PASS' : 'FAIL',
    };

    if (!response.ok) {
      result.errorMessage = `HTTP ${response.status}: ${JSON.stringify(responseBody)}`;
    }

    return result;
  } catch (error: any) {
    const responseTime = Date.now() - startTime;
    return {
      endpoint,
      method,
      status: 'ERROR',
      responseTime,
      errorMessage: error.message || String(error),
    };
  }
}

async function runTests() {
  console.log('========================================');
  console.log('STARTING COMPREHENSIVE ENDPOINT TESTS');
  console.log('========================================\n');

  // Test 1: GET /
  console.log('Testing GET / (API Info)...');
  results.push(await testEndpoint('GET', '/'));

  // Test 2: GET /health
  console.log('Testing GET /tools/health (System Health)...');
  results.push(await testEndpoint('GET', '/tools/health'));

  // Test 3: GET /auth/status
  console.log('Testing GET /auth/status (Rate Limit Status)...');
  results.push(await testEndpoint('GET', '/auth/status'));

  // Test 4: POST /tools/predict - with single symbol
  console.log('Testing POST /tools/predict (Single Symbol)...');
  results.push(
    await testEndpoint('POST', '/tools/predict', {
      symbols: ['AAPL'],
      timeframe: 'intraday',
    })
  );

  // Test 5: POST /tools/predict - with multiple symbols
  console.log('Testing POST /tools/predict (Multiple Symbols)...');
  results.push(
    await testEndpoint('POST', '/tools/predict', {
      symbols: ['AAPL', 'GOOGL', 'MSFT'],
      timeframe: 'intraday',
    })
  );

  // Test 6: POST /tools/scan_all
  console.log('Testing POST /tools/scan_all (Scan All Symbols)...');
  results.push(
    await testEndpoint('POST', '/tools/scan_all', {
      limit: 5,
    })
  );

  // Test 7: POST /tools/analyze
  console.log('Testing POST /tools/analyze (Analyze Symbol)...');
  results.push(
    await testEndpoint('POST', '/tools/analyze', {
      symbol: 'AAPL',
      current_price: 150.0,
      predicted_price: 155.0,
      confidence: 0.85,
      stop_loss: 145.0,
      take_profit: 165.0,
    })
  );

  // Test 8: POST /tools/feedback
  console.log('Testing POST /tools/feedback (Human Feedback)...');
  results.push(
    await testEndpoint('POST', '/tools/feedback', {
      symbol: 'AAPL',
      prediction_id: 'test-123',
      feedback_type: 'correct',
      notes: 'Test feedback',
    })
  );

  // Test 9: POST /tools/train_rl - short timeout
  console.log('Testing POST /tools/train_rl (Train RL Model)...');
  results.push(
    await testEndpoint(
      'POST',
      '/tools/train_rl',
      {
        symbol: 'AAPL',
        timeframe: 'intraday',
        periods: 2,
      },
      5000 // Short timeout to avoid waiting
    )
  );

  // Test 10: POST /tools/fetch_data
  console.log('Testing POST /tools/fetch_data (Fetch Data)...');
  results.push(
    await testEndpoint('POST', '/tools/fetch_data', {
      symbols: ['AAPL', 'GOOGL'],
      start_date: '2026-01-01',
      end_date: '2026-01-21',
    })
  );

  // Test 11: POST /api/risk/assess
  console.log('Testing POST /api/risk/assess (Risk Assessment)...');
  results.push(
    await testEndpoint('POST', '/api/risk/assess', {
      symbol: 'AAPL',
      entry_price: 150.0,
      current_price: 152.0,
      portfolio_value: 10000.0,
      position_size: 1000.0,
    })
  );

  // Test 12: POST /api/risk/stop-loss
  console.log('Testing POST /api/risk/stop-loss (Set Stop Loss)...');
  results.push(
    await testEndpoint('POST', '/api/risk/stop-loss', {
      symbol: 'AAPL',
      entry_price: 150.0,
      stop_loss_percentage: 5.0,
    })
  );

  // Test 13: POST /api/ai/chat
  console.log('Testing POST /api/ai/chat (AI Chat)...');
  results.push(
    await testEndpoint('POST', '/api/ai/chat', {
      message: 'What are your thoughts on AAPL?',
      context: 'trading',
    })
  );

  // Print results
  console.log('\n========================================');
  console.log('TEST RESULTS SUMMARY');
  console.log('========================================\n');

  const passed = results.filter((r) => r.status === 'PASS').length;
  const failed = results.filter((r) => r.status === 'FAIL').length;
  const errors = results.filter((r) => r.status === 'ERROR').length;

  console.log(`PASSED: ${passed}/${results.length}`);
  console.log(`FAILED: ${failed}/${results.length}`);
  console.log(`ERRORS: ${errors}/${results.length}\n`);

  // Print details
  results.forEach((result, index) => {
    const statusIcon =
      result.status === 'PASS'
        ? '✓'
        : result.status === 'FAIL'
          ? '✗'
          : '!';
    console.log(
      `${statusIcon} [${result.method}] ${result.endpoint} (${result.responseTime}ms)`
    );

    if (result.status !== 'PASS') {
      console.log(`   Error: ${result.errorMessage}`);
    }

    if (result.response && result.status === 'PASS') {
      console.log(`   Response: ${JSON.stringify(result.response).substring(0, 100)}...`);
    }
  });

  // Group errors
  const errorDetails = results.filter((r) => r.status !== 'PASS');
  if (errorDetails.length > 0) {
    console.log('\n========================================');
    console.log('DETAILED ERROR INFORMATION');
    console.log('========================================\n');

    errorDetails.forEach((result) => {
      console.log(`[${result.method}] ${result.endpoint}`);
      console.log(`Status: ${result.status}`);
      console.log(`Message: ${result.errorMessage}`);
      if (result.response) {
        console.log(`Response: ${JSON.stringify(result.response, null, 2)}`);
      }
      console.log('---\n');
    });
  }

  return results;
}

// Run tests and export results
export { runTests, TestResult };

// Auto-run if this is the main module
if (typeof window !== 'undefined') {
  (window as any).runApiTests = runTests;
  console.log('API test suite loaded. Run: window.runApiTests()');
}
