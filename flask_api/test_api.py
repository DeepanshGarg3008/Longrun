import requests
import json
import sys
import time

# API base URL
BASE_URL = "http://localhost:8888"

# Test user credentials
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword"

def print_response(response):
    """Print the response details in a formatted way."""
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    print("Response Body:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print("-" * 50)

def test_health_endpoint():
    """Test the health check endpoint."""
    print("\n🔍 Testing Health Check Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print_response(response)
        
        if response.status_code == 200 and response.json().get("status") == "healthy":
            print("✅ Health check successful!")
            return True
        else:
            print("❌ Health check failed!")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_register_endpoint():
    """Test the register endpoint."""
    print("\n🔍 Testing Register Endpoint...")
    try:
        # First, try to register a new user
        payload = {
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/register", json=payload)
        print_response(response)
        
        # Check if registration was successful or user already exists
        if response.status_code == 201:
            print("✅ Registration successful!")
            return True
        elif response.status_code == 400 and "already exists" in response.json().get("error", ""):
            print("⚠️ User already exists. This is expected if you've run this test before.")
            return True
        else:
            print("❌ Registration failed!")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_login_endpoint():
    """Test the login endpoint."""
    print("\n🔍 Testing Login Endpoint...")
    try:
        # Try to login with the test user
        payload = {
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/login", json=payload)
        print_response(response)
        
        if response.status_code == 200 and "user_id" in response.json():
            print("✅ Login successful!")
            return True
        else:
            print("❌ Login failed!")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_invalid_login():
    """Test login with invalid credentials."""
    print("\n🔍 Testing Invalid Login...")
    try:
        # Try to login with invalid credentials
        payload = {
            "username": TEST_USERNAME,
            "password": "wrongpassword"
        }
        response = requests.post(f"{BASE_URL}/api/login", json=payload)
        print_response(response)
        
        if response.status_code == 401:
            print("✅ Invalid login test successful (correctly rejected)!")
            return True
        else:
            print("❌ Invalid login test failed (should have been rejected)!")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_all_tests():
    """Run all API tests."""
    print("=" * 50)
    print("🚀 Starting API Tests")
    print("=" * 50)
    
    # Wait a bit to ensure the server is up
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    # Run tests
    health_result = test_health_endpoint()
    register_result = test_register_endpoint()
    login_result = test_login_endpoint()
    invalid_login_result = test_invalid_login()
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    print(f"Health Check: {'✅ PASS' if health_result else '❌ FAIL'}")
    print(f"Registration: {'✅ PASS' if register_result else '❌ FAIL'}")
    print(f"Login: {'✅ PASS' if login_result else '❌ FAIL'}")
    print(f"Invalid Login: {'✅ PASS' if invalid_login_result else '❌ FAIL'}")
    
    # Overall result
    all_passed = all([health_result, register_result, login_result, invalid_login_result])
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! The API is working correctly.")
    else:
        print("❌ Some tests failed. Please check the logs above for details.")
    print("=" * 50)
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
