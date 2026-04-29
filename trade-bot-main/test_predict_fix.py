#!/usr/bin/env python3
"""
Quick test of the predict endpoint to verify JSON fixes
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

print("\n" + "="*70)
print("TESTING PREDICT ENDPOINT (JSON SERIALIZATION FIX)".center(70))
print("="*70 + "\n")

# Test 1: Single symbol prediction
print("[1] Testing AAPL prediction...")
try:
    start = time.time()
    response = requests.post(
        f"{BASE_URL}/tools/predict",
        json={"symbols": ["AAPL"], "timeframe": "intraday"},
        timeout=120
    )
    duration = time.time() - start
    
    print(f"Status: {response.status_code}")
    print(f"Response Time: {duration:.2f}s")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ SUCCESS - Got {len(data.get('predictions', []))} predictions")
        for pred in data.get('predictions', [])[:1]:
            print(f"  Symbol: {pred.get('symbol')}")
            print(f"  Direction: {pred.get('direction')}")
            print(f"  Confidence: {pred.get('confidence', 0):.4f}")
    else:
        print(f"✗ FAILED - HTTP {response.status_code}")
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"✗ ERROR: {str(e)}")

print("\n" + "="*70)

# Test 2: Multiple symbols prediction
print("[2] Testing GOOGL & MSFT prediction...")
try:
    start = time.time()
    response = requests.post(
        f"{BASE_URL}/tools/predict",
        json={"symbols": ["GOOGL", "MSFT"], "timeframe": "intraday"},
        timeout=120
    )
    duration = time.time() - start
    
    print(f"Status: {response.status_code}")
    print(f"Response Time: {duration:.2f}s")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ SUCCESS - Got {len(data.get('predictions', []))} predictions")
        for pred in data.get('predictions', []):
            print(f"  {pred.get('symbol')}: {pred.get('direction')} (confidence: {pred.get('confidence', 0):.4f})")
    else:
        print(f"✗ FAILED - HTTP {response.status_code}")
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"✗ ERROR: {str(e)}")

print("\n" + "="*70 + "\n")
