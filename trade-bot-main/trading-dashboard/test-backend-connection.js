// Backend Connectivity Test
// Run this in browser console after frontend loads

console.log('🔍 Testing Backend Connectivity...\n');

const API_BASE_URL = 'http://127.0.0.1:5000';

async function testBackend() {
  const tests = [
    { name: 'Root Endpoint', url: '/' },
    { name: 'Health Check', url: '/tools/health' },
    { name: 'Auth Status', url: '/auth/status' }
  ];

  for (const test of tests) {
    try {
      const start = Date.now();
      const response = await fetch(`${API_BASE_URL}${test.url}`);
      const time = Date.now() - start;
      const data = await response.json();
      
      console.log(`✅ ${test.name}`);
      console.log(`   Status: ${response.status}`);
      console.log(`   Time: ${time}ms`);
      console.log(`   Response:`, data);
      console.log('');
    } catch (error) {
      console.error(`❌ ${test.name} FAILED:`, error.message);
      console.log('');
    }
  }
  
  console.log('✨ Test Complete!');
}

testBackend();
