import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure the backend directory is in the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import the client
from dhan_client import DhanAPIClient

class TestDhanConnection(unittest.TestCase):
    def setUp(self):
        self.client_id = "test_client"
        self.access_token = "test_token"
        self.client = DhanAPIClient(self.client_id, self.access_token)

    @patch('dhan_client.fetch_fund_limit')
    def test_validate_connection_success(self, mock_fund):
        """Test successful connection validation."""
        # Mock a successful fund limit response
        mock_fund.return_value = {"availabelBalance": 1000.0}
        
        result = self.client.validate_connection()
        
        self.assertTrue(result["connected"])
        self.assertEqual(result["code"], 200)
        self.assertIsNone(result["error"])
        print("Success: Valid connection detected correctly.")

    @patch('dhan_client.fetch_fund_limit')
    def test_validate_connection_unauthorized(self, mock_fund):
        """Test 401 Unauthorized detection."""
        # Mock a 401 failure
        mock_fund.return_value = {
            "status": "failure",
            "http_code": 401,
            "remarks": "Invalid token"
        }
        
        result = self.client.validate_connection()
        
        self.assertFalse(result["connected"])
        self.assertEqual(result["code"], 401)
        self.assertEqual(result["error"], "Unauthorized")
        self.assertIn("expired or invalid", result["message"])
        print("Success: 401 Unauthorized handled correctly.")

    @patch('dhan_client.fetch_fund_limit')
    def test_validate_connection_network_error(self, mock_fund):
        """Test network error detection."""
        # Mock a network error (returns None)
        mock_fund.return_value = None
        
        result = self.client.validate_connection()
        
        self.assertFalse(result["connected"])
        self.assertEqual(result["code"], 500)
        self.assertEqual(result["error"], "Network Error")
        print("Success: Network Error handled correctly.")

    @patch('dhan_client.fetch_fund_limit')
    def test_validate_connection_general_failure(self, mock_fund):
        """Test general API failure detection."""
        # Mock a non-401 failure
        mock_fund.return_value = {
            "status": "failure",
            "http_code": 503,
            "remarks": "Service Unavailable"
        }
        
        result = self.client.validate_connection()
        
        self.assertFalse(result["connected"])
        self.assertEqual(result["code"], 503)
        self.assertEqual(result["error"], "API Failure")
        print("Success: General API failure handled correctly.")

if __name__ == "__main__":
    print("Testing Dhan Connection Status Logic...")
    unittest.main()
