#!/usr/bin/env python3
"""
Comprehensive API Endpoint Testing Script
Tests all endpoints and detects errors
"""

import requests
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

class APITester:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.session = requests.Session()
        
    def test_endpoint(self, method: str, endpoint: str, data: Optional[Dict] = None, timeout: int = 30) -> Dict[str, Any]:
        """Test a single endpoint"""
        url = f"{BASE_URL}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data or {}, timeout=timeout)
            else:
                return {"error": f"Unsupported method: {method}"}
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            try:
                response_body = response.json()
            except:
                response_body = response.text
            
            result = {
                "endpoint": endpoint,
                "method": method,
                "status_code": response.status_code,
                "response_time_ms": round(response_time, 2),
                "success": 200 <= response.status_code < 300,
                "response": response_body if response.status_code < 400 else str(response_body)[:200]
            }
            
            if not result["success"]:
                result["error"] = f"HTTP {response.status_code}"
            
            return result
            
        except requests.Timeout:
            response_time = (time.time() - start_time) * 1000
            return {
                "endpoint": endpoint,
                "method": method,
                "success": False,
                "error": "Timeout",
                "response_time_ms": round(response_time, 2)
            }
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                "endpoint": endpoint,
                "method": method,
                "success": False,
                "error": str(e),
                "response_time_ms": round(response_time, 2)
            }
    
    def run_all_tests(self):
        """Run all endpoint tests"""
        print("\n" + "="*60)
        print("COMPREHENSIVE API ENDPOINT TESTING")
        print("="*60 + "\n")
        
        # GET Endpoints
        print("[1/13] Testing GET / (API Info)")
        self.results.append(self.test_endpoint("GET", "/"))
        
        print("[2/13] Testing GET /tools/health (System Health)")
        self.results.append(self.test_endpoint("GET", "/tools/health"))
        
        print("[3/13] Testing GET /auth/status (Rate Limit Status)")
        self.results.append(self.test_endpoint("GET", "/auth/status"))
        
        # POST Endpoints
        print("[4/13] Testing POST /tools/predict (Single Symbol)")
        self.results.append(self.test_endpoint("POST", "/tools/predict", {
            "symbols": ["AAPL"],
            "timeframe": "intraday"
        }))
        
        print("[5/13] Testing POST /tools/predict (Multiple Symbols)")
        self.results.append(self.test_endpoint("POST", "/tools/predict", {
            "symbols": ["AAPL", "GOOGL", "MSFT"],
            "timeframe": "intraday"
        }))
        
        print("[6/13] Testing POST /tools/scan_all")
        self.results.append(self.test_endpoint("POST", "/tools/scan_all", {
            "limit": 5
        }))
        
        print("[7/13] Testing POST /tools/analyze")
        self.results.append(self.test_endpoint("POST", "/tools/analyze", {
            "symbol": "AAPL",
            "current_price": 150.0,
            "predicted_price": 155.0,
            "confidence": 0.85,
            "stop_loss": 145.0,
            "take_profit": 165.0
        }))
        
        print("[8/13] Testing POST /tools/feedback")
        self.results.append(self.test_endpoint("POST", "/tools/feedback", {
            "symbol": "AAPL",
            "prediction_id": "test-123",
            "feedback_type": "correct",
            "notes": "Test feedback"
        }))
        
        print("[9/13] Testing POST /tools/train_rl (with timeout)")
        self.results.append(self.test_endpoint("POST", "/tools/train_rl", {
            "symbol": "AAPL",
            "timeframe": "intraday",
            "periods": 2
        }, timeout=5))
        
        print("[10/13] Testing POST /tools/fetch_data")
        self.results.append(self.test_endpoint("POST", "/tools/fetch_data", {
            "symbols": ["AAPL", "GOOGL"],
            "start_date": "2026-01-01",
            "end_date": "2026-01-21"
        }))
        
        print("[11/13] Testing POST /api/risk/assess")
        self.results.append(self.test_endpoint("POST", "/api/risk/assess", {
            "symbol": "AAPL",
            "entry_price": 150.0,
            "current_price": 152.0,
            "portfolio_value": 10000.0,
            "position_size": 1000.0
        }))
        
        print("[12/13] Testing POST /api/risk/stop-loss")
        self.results.append(self.test_endpoint("POST", "/api/risk/stop-loss", {
            "symbol": "AAPL",
            "entry_price": 150.0,
            "stop_loss_percentage": 5.0
        }))
        
        print("[13/13] Testing POST /api/ai/chat")
        self.results.append(self.test_endpoint("POST", "/api/ai/chat", {
            "message": "What are your thoughts on AAPL?",
            "context": "trading"
        }))
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        passed = sum(1 for r in self.results if r.get("success"))
        failed = len(self.results) - passed
        
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        print(f"✓ PASSED: {passed}/{len(self.results)}")
        print(f"✗ FAILED: {failed}/{len(self.results)}")
        print("="*60 + "\n")
        
        # Print each result
        for i, result in enumerate(self.results, 1):
            status_icon = "✓" if result.get("success") else "✗"
            method = result.get("method", "")
            endpoint = result.get("endpoint", "")
            time_ms = result.get("response_time_ms", 0)
            
            print(f"{status_icon} [{method:4}] {endpoint:35} ({time_ms:6.2f}ms)", end="")
            
            if not result.get("success"):
                error = result.get("error", "Unknown error")
                code = result.get("status_code", "")
                if code:
                    print(f" | Error: HTTP {code} - {error}")
                else:
                    print(f" | Error: {error}")
            else:
                print(" | OK")
        
        # Detailed errors
        errors = [r for r in self.results if not r.get("success")]
        if errors:
            print("\n" + "="*60)
            print("DETAILED ERROR INFORMATION")
            print("="*60 + "\n")
            
            for result in errors:
                print(f"[{result.get('method')}] {result.get('endpoint')}")
                print(f"  Status: {result.get('status_code', 'N/A')}")
                print(f"  Error: {result.get('error', 'Unknown')}")
                print(f"  Response Time: {result.get('response_time_ms', 0)}ms")
                if result.get("response"):
                    print(f"  Response: {str(result.get('response'))[:150]}...")
                print()
        
        # Save results to file
        with open("endpoint_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nResults saved to endpoint_test_results.json")

if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests()
