import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(endpoint, method="GET", payload=None):
    """Test a single endpoint and return the response"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\nTesting {method} {endpoint}")
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST" and payload:
            response = requests.post(url, json=payload)
        elif method == "POST":
            response = requests.post(url)
        else:
            print(f"Unsupported method: {method}")
            return None
            
        print(f"Status Code: {response.status_code}")
        
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            return {"status_code": response.status_code, "data": data}
        except:
            print(f"Raw Response: {response.text}")
            return {"status_code": response.status_code, "raw_data": response.text}
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"error": str(e)}

def main():
    print("Verifying all API endpoints...")
    
    # Test root endpoint
    print("\n" + "="*50)
    print("TESTING ROOT ENDPOINT")
    print("="*50)
    test_endpoint("/")
    
    # Test health endpoint
    print("\n" + "="*50)
    print("TESTING HEALTH ENDPOINT")
    print("="*50)
    test_endpoint("/tools/health")
    
    # Test predict endpoint
    print("\n" + "="*50)
    print("TESTING PREDICT ENDPOINT")
    print("="*50)
    predict_payload = {
        "symbols": ["TATAMOTORS.NS"],
        "horizon": "intraday"
    }
    test_endpoint("/tools/predict", "POST", predict_payload)
    
    # Test scan_all endpoint
    print("\n" + "="*50)
    print("TESTING SCAN_ALL ENDPOINT")
    print("="*50)
    scan_payload = {
        "symbols": ["TATAMOTORS.NS", "RELIANCE.NS"],
        "horizon": "intraday"
    }
    test_endpoint("/tools/scan_all", "POST", scan_payload)
    
    # Test analyze endpoint
    print("\n" + "="*50)
    print("TESTING ANALYZE ENDPOINT")
    print("="*50)
    analyze_payload = {
        "symbol": "TATAMOTORS.NS",
        "horizon": "intraday",
        "risk_tolerance": 0.1
    }
    test_endpoint("/tools/analyze", "POST", analyze_payload)
    
    # Test feedback endpoint
    print("\n" + "="*50)
    print("TESTING FEEDBACK ENDPOINT")
    print("="*50)
    feedback_payload = {
        "prediction_id": "test_prediction_123",
        "actual_outcome": "correct",
        "accuracy_rating": 0.9
    }
    test_endpoint("/tools/feedback", "POST", feedback_payload)
    
    # Test fetch_data endpoint
    print("\n" + "="*50)
    print("TESTING FETCH_DATA ENDPOINT")
    print("="*50)
    fetch_payload = {
        "symbols": ["TATAMOTORS.NS", "RELIANCE.NS"],
        "days": 30
    }
    test_endpoint("/tools/fetch_data", "POST", fetch_payload)
    
    print("\n" + "="*50)
    print("ALL ENDPOINT TESTS COMPLETED")
    print("="*50)

if __name__ == "__main__":
    main()