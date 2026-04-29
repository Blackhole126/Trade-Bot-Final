#!/usr/bin/env python3
"""
API Endpoint Test Script
This script tests all backend API endpoints to ensure they are working properly
before making any changes to the codebase.
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List

class APITester:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def test_endpoint(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Test a single endpoint and return the response"""
        try:
            url = f"{self.base_url}{endpoint}"
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return {
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 300,
                "response": response.json() if response.content else {},
                "error": None
            }
        except Exception as e:
            return {
                "status_code": None,
                "success": False,
                "response": {},
                "error": str(e)
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all API endpoint tests"""
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_url": self.base_url,
            "tests": {}
        }
        
        # Test 1: Root endpoint
        print("Testing root endpoint...")
        results["tests"]["root"] = self.test_endpoint("GET", "/")
        
        # Test 2: Health endpoint
        print("Testing health endpoint...")
        results["tests"]["health"] = self.test_endpoint("GET", "/tools/health")
        
        # Test 3: Predict endpoint
        print("Testing predict endpoint...")
        results["tests"]["predict"] = self.test_endpoint("POST", "/tools/predict", {
            "symbols": ["AAPL"],
            "horizon": "intraday"
        })
        
        # Test 4: Scan All endpoint
        print("Testing scan_all endpoint...")
        results["tests"]["scan_all"] = self.test_endpoint("POST", "/tools/scan_all", {
            "symbols": ["AAPL", "GOOGL"],
            "horizon": "intraday",
            "min_confidence": 0.3
        })
        
        # Test 5: Analyze endpoint
        print("Testing analyze endpoint...")
        results["tests"]["analyze"] = self.test_endpoint("POST", "/tools/analyze", {
            "symbol": "AAPL",
            "horizons": ["intraday"],
            "stop_loss_pct": 2.0,
            "capital_risk_pct": 1.0,
            "drawdown_limit_pct": 5.0
        })
        
        # Test 6: Fetch Data endpoint
        print("Testing fetch_data endpoint...")
        results["tests"]["fetch_data"] = self.test_endpoint("POST", "/tools/fetch_data", {
            "symbols": ["AAPL"],
            "period": "1d",
            "include_features": False,
            "refresh": False
        })
        
        # Test 7: Feedback endpoint
        print("Testing feedback endpoint...")
        results["tests"]["feedback"] = self.test_endpoint("POST", "/tools/feedback", {
            "symbol": "AAPL",
            "predicted_action": "LONG",
            "user_feedback": "correct",
            "actual_return": 1.5
        })
        
        # Test 8: Train RL endpoint
        print("Testing train_rl endpoint...")
        results["tests"]["train_rl"] = self.test_endpoint("POST", "/tools/train_rl", {
            "symbol": "AAPL",
            "horizon": "intraday",
            "n_episodes": 10,
            "force_retrain": False
        })
        
        # Test 9: Auth status endpoint
        print("Testing auth status endpoint...")
        results["tests"]["auth_status"] = self.test_endpoint("GET", "/auth/status")
        
        return results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of test results"""
        print("\n" + "="*60)
        print("API ENDPOINT TEST RESULTS")
        print("="*60)
        print(f"Base URL: {results['base_url']}")
        print(f"Timestamp: {results['timestamp']}")
        print()
        
        all_passed = True
        for test_name, test_result in results['tests'].items():
            status = "✓ PASS" if test_result['success'] else "✗ FAIL"
            print(f"{test_name:15} | {status:8} | Status: {test_result['status_code']}")
            
            if not test_result['success']:
                all_passed = False
                print(f"                 | Error: {test_result.get('error', 'Unknown error')}")
        
        print()
        if all_passed:
            print("🎉 All API endpoints are working correctly!")
        else:
            print("❌ Some API endpoints are not working properly.")
        
        print("="*60)
        
        return all_passed

def main():
    """Main function to run the API tests"""
    print("Starting API endpoint tests...")
    
    # Check if backend is running first
    try:
        response = requests.get("http://127.0.0.1:8000/")
        print("✓ Backend server is running")
    except requests.exceptions.ConnectionError:
        print("✗ Backend server is not running. Please start the backend server first.")
        print("Run: cd backend && python api_server.py")
        sys.exit(1)
    
    # Run tests
    tester = APITester()
    results = tester.run_all_tests()
    success = tester.print_summary(results)
    
    # Save detailed results to file
    with open("api_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: api_test_results.json")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()