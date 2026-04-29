/**
 * Comprehensive Endpoint Verification Utility
 * Tests all backend endpoints from the frontend
 */

import { stockAPI, authAPI, riskAPI, aiAPI, tradeAPI } from '../services/api';
import { config } from '../config';

interface TestResult {
  endpoint: string;
  method: string;
  status: 'success' | 'error' | 'warning';
  responseTime: number;
  message: string;
  data?: any;
}

export class EndpointVerifier {
  private results: TestResult[] = [];
  private startTime: number = 0;

  async runAllTests(): Promise<TestResult[]> {
    console.log('🔍 Starting comprehensive endpoint verification...\n');
    this.startTime = Date.now();
    this.results = [];

    // Test 1: Connection Check
    await this.testConnection();

    // Test 2: Health Endpoint
    await this.testHealth();

    // Test 3: Rate Limit Status
    await this.testRateLimit();

    // Test 4: Prediction Endpoint
    await this.testPredict();

    // Test 5: Scan All Endpoint
    await this.testScanAll();

    // Test 6: Analyze Endpoint
    await this.testAnalyze();

    // Test 7: Feedback Endpoint
    await this.testFeedback();

    // Test 8: Train RL Endpoint
    await this.testTrainRL();

    // Test 9: Fetch Data Endpoint
    await this.testFetchData();

    // Test 10: Execute Trade Endpoint
    await this.testExecuteTrade();

    // Test 11: Risk Assessment Endpoint
    await this.testRiskAssessment();

    // Test 12: Stop Loss Endpoint
    await this.testStopLoss();

    // Test 13: AI Chat Endpoint
    await this.testAIChat();

    const totalTime = Date.now() - this.startTime;
    console.log(`\n✅ Verification completed in ${totalTime}ms`);
    console.log(`📊 Results: ${this.results.filter(r => r.status === 'success').length}/${this.results.length} endpoints working\n`);

    return this.results;
  }

  private async testEndpoint(
    name: string,
    method: string,
    testFn: () => Promise<any>,
    expectedFields?: string[]
  ): Promise<void> {
    const start = Date.now();
    try {
      const result = await testFn();
      const responseTime = Date.now() - start;
      
      let status: 'success' | 'warning' = 'success';
      let message = 'Working correctly';
      
      // Check if expected fields are present
      if (expectedFields) {
        const missingFields = expectedFields.filter(field => !(field in result));
        if (missingFields.length > 0) {
          status = 'warning';
          message = `Missing fields: ${missingFields.join(', ')}`;
        }
      }

      this.results.push({
        endpoint: name,
        method,
        status,
        responseTime,
        message,
        data: result
      });

      console.log(`✅ ${name} (${responseTime}ms) - ${message}`);
    } catch (error: any) {
      const responseTime = Date.now() - start;
      this.results.push({
        endpoint: name,
        method,
        status: 'error',
        responseTime,
        message: error.message || 'Request failed',
        data: error
      });
      console.log(`❌ ${name} (${responseTime}ms) - ${error.message}`);
    }
  }

  private async testConnection() {
    await this.testEndpoint(
      'GET /',
      'GET',
      () => stockAPI.checkConnection(),
      ['connected', 'version']
    );
  }

  private async testHealth() {
    await this.testEndpoint(
      'GET /tools/health',
      'GET',
      () => stockAPI.health(),
      ['status', 'timestamp']
    );
  }

  private async testRateLimit() {
    await this.testEndpoint(
      'GET /auth/status',
      'GET',
      () => stockAPI.getRateLimitStatus(),
      ['requests_remaining']
    );
  }

  private async testPredict() {
    await this.testEndpoint(
      'POST /tools/predict',
      'POST',
      () => stockAPI.predict(['AAPL'], 'intraday'),
      ['predictions']
    );
  }

  private async testScanAll() {
    await this.testEndpoint(
      'POST /tools/scan_all',
      'POST',
      () => stockAPI.scanAll(['AAPL', 'GOOGL', 'MSFT'], 'intraday'),
      ['results']
    );
  }

  private async testAnalyze() {
    await this.testEndpoint(
      'POST /tools/analyze',
      'POST',
      () => stockAPI.analyze('AAPL', ['intraday']),
      ['analysis']
    );
  }

  private async testFeedback() {
    await this.testEndpoint(
      'POST /tools/feedback',
      'POST',
      () => stockAPI.feedback('AAPL', 'BUY', 'correct', 0.02),
      ['success']
    );
  }

  private async testTrainRL() {
    await this.testEndpoint(
      'POST /tools/train_rl',
      'POST',
      () => stockAPI.trainRL('AAPL', 'intraday', 10),
      ['success']
    );
  }

  private async testFetchData() {
    await this.testEndpoint(
      'POST /tools/fetch_data',
      'POST',
      () => stockAPI.fetchData(['AAPL'], '1mo'),
      ['data']
    );
  }

  private async testExecuteTrade() {
    await this.testEndpoint(
      'POST /tools/execute',
      'POST',
      () => tradeAPI.execute('AAPL', 'BUY', 10, 150.00, 145.00),
      ['success']
    );
  }

  private async testRiskAssessment() {
    await this.testEndpoint(
      'POST /api/risk/assess',
      'POST',
      () => riskAPI.assess({ symbol: 'AAPL', position_size: 1000, entry_price: 150.00, stop_loss_price: 145.00 }),
      ['risk_level']
    );
  }

  private async testStopLoss() {
    await this.testEndpoint(
      'POST /api/risk/stop-loss',
      'POST',
      () => riskAPI.setStopLoss('AAPL', 145.00, 'BUY', '1D', 'manual'),
      ['success']
    );
  }

  private async testAIChat() {
    await this.testEndpoint(
      'POST /api/ai/chat',
      'POST',
      () => aiAPI.chat('What is the outlook for AAPL?', { symbol: 'AAPL' }),
      ['response']
    );
  }

  getSummary() {
    const total = this.results.length;
    const success = this.results.filter(r => r.status === 'success').length;
    const errors = this.results.filter(r => r.status === 'error').length;
    const warnings = this.results.filter(r => r.status === 'warning').length;
    
    const avgResponseTime = this.results.reduce((sum, r) => sum + r.responseTime, 0) / total;
    
    return {
      total,
      success,
      errors,
      warnings,
      successRate: ((success / total) * 100).toFixed(1),
      averageResponseTime: avgResponseTime.toFixed(0) + 'ms'
    };
  }

  printDetailedReport() {
    const summary = this.getSummary();
    
    console.log('\n' + '='.repeat(60));
    console.log('COMPREHENSIVE ENDPOINT VERIFICATION REPORT');
    console.log('='.repeat(60));
    console.log(`Total Endpoints Tested: ${summary.total}`);
    console.log(`✅ Working: ${summary.success}`);
    console.log(`❌ Errors: ${summary.errors}`);
    console.log(`⚠️  Warnings: ${summary.warnings}`);
    console.log(`📈 Success Rate: ${summary.successRate}%`);
    console.log(`⏱️  Average Response Time: ${summary.averageResponseTime}`);
    console.log('='.repeat(60));

    console.log('\n📋 DETAILED RESULTS:');
    this.results.forEach(result => {
      const statusIcon = result.status === 'success' ? '✅' : result.status === 'warning' ? '⚠️' : '❌';
      console.log(`${statusIcon} ${result.endpoint} (${result.method}) - ${result.responseTime}ms`);
      console.log(`   ${result.message}`);
      if (result.data && typeof result.data === 'object') {
        console.log(`   Response: ${JSON.stringify(result.data, null, 2).substring(0, 200)}...`);
      }
      console.log('');
    });

    console.log('='.repeat(60));
  }
}

// Export utility function for easy use
export const verifyAllEndpoints = async (): Promise<TestResult[]> => {
  const verifier = new EndpointVerifier();
  const results = await verifier.runAllTests();
  verifier.printDetailedReport();
  return results;
};

// Run verification if called directly
if (typeof window !== 'undefined') {
  // @ts-ignore
  window.verifyEndpoints = verifyAllEndpoints;
}