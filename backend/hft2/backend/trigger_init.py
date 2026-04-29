
import requests
import sys

try:
    print("Triggering /api/init...")
    response = requests.post("http://127.0.0.1:5000/api/init", timeout=60)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
