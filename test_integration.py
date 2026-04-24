"""
Integration test script for CarSwap production system
Tests complete authentication and business logic flows
"""
import requests
import json
import time
from typing import Dict, Optional

BASE_URL = "http://localhost:8000"
TIMEOUT = 10

class CarSwapTester:
    def __init__(self):
        self.token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
        
    def print_result(self, test_name: str, passed: bool, message: str = ""):
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} | {test_name}")
        if message:
            print(f"      {message}")
    
    def test_signup(self) -> bool:
        """Test user registration"""
        try:
            email = f"test_user_{int(time.time())}@test.com"
            response = self.session.post(
                f"{BASE_URL}/signup",
                json={
                    "email": email,
                    "password": "testpass123",
                    "full_name": "Test User"
                }
            )
            passed = response.status_code == 200
            if passed:
                self.print_result("SIGNUP", True, f"User created: {email}")
            else:
                self.print_result("SIGNUP", False, f"Status {response.status_code}: {response.text}")
            return passed
        except Exception as e:
            self.print_result("SIGNUP", False, str(e))
            return False
    
    def test_login(self) -> bool:
        """Test user login and JWT token retrieval"""
        try:
            response = self.session.post(
                f"{BASE_URL}/login",
                data={
                    "username": "test@example.com",
                    "password": "password123"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    self.print_result("LOGIN", True, f"Token received: {self.token[:20]}...")
                    return True
                else:
                    self.print_result("LOGIN", False, "No token in response")
                    return False
            else:
                self.print_result("LOGIN", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.print_result("LOGIN", False, str(e))
            return False
    
    def test_get_current_user(self) -> bool:
        """Test retrieving current user profile"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(
                f"{BASE_URL}/me",
                headers=headers
            )
            
            if response.status_code == 200:
                user_data = response.json()
                self.user_id = user_data.get("id")
                self.print_result("GET /me", True, f"User: {user_data.get('email')}")
                return True
            else:
                self.print_result("GET /me", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.print_result("GET /me", False, str(e))
            return False
    
    def test_get_cars(self) -> bool:
        """Test retrieving available cars"""
        try:
            response = self.session.get(f"{BASE_URL}/cars")
            
            if response.status_code == 200:
                cars = response.json()
                if cars:
                    self.print_result("GET /cars", True, f"Found {len(cars)} cars")
                    return True
                else:
                    self.print_result("GET /cars", False, "No cars in database")
                    return False
            else:
                self.print_result("GET /cars", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.print_result("GET /cars", False, str(e))
            return False
    
    def test_get_subscription_plans(self) -> bool:
        """Test retrieving subscription plans"""
        try:
            response = self.session.get(f"{BASE_URL}/subscription-plans")
            
            if response.status_code == 200:
                plans = response.json()
                if plans:
                    self.print_result("GET /subscription-plans", True, f"Found {len(plans)} plans")
                    return True
                else:
                    self.print_result("GET /subscription-plans", False, "No plans in database")
                    return False
            else:
                self.print_result("GET /subscription-plans", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.print_result("GET /subscription-plans", False, str(e))
            return False
    
    def test_protected_without_token(self) -> bool:
        """Test that protected endpoints reject requests without token"""
        try:
            response = self.session.get(f"{BASE_URL}/my-subscription")
            
            # Should get 401 or 403
            if response.status_code in [401, 403]:
                self.print_result("PROTECTED (no token)", True, "Correctly rejected")
                return True
            else:
                self.print_result("PROTECTED (no token)", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.print_result("PROTECTED (no token)", False, str(e))
            return False
    
    def test_subscribe(self, car_id: int, plan_id: int) -> bool:
        """Test subscription creation"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.post(
                f"{BASE_URL}/subscribe",
                json={"car_id": car_id, "plan_id": plan_id},
                headers=headers
            )
            
            if response.status_code == 200:
                sub_data = response.json()
                self.print_result("POST /subscribe", True, f"Subscription ID: {sub_data.get('id')}")
                return True
            else:
                self.print_result("POST /subscribe", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.print_result("POST /subscribe", False, str(e))
            return False
    
    def test_swap_car(self, subscription_id: int, new_car_id: int) -> bool:
        """Test car swapping"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.post(
                f"{BASE_URL}/swap",
                json={
                    "subscription_id": subscription_id,
                    "to_car_id": new_car_id,
                    "note": "Integration test swap"
                },
                headers=headers
            )
            
            if response.status_code == 200:
                swap_data = response.json()
                self.print_result("POST /swap", True, f"Swap ID: {swap_data.get('id')}")
                return True
            else:
                self.print_result("POST /swap", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.print_result("POST /swap", False, str(e))
            return False
    
    def test_get_subscription(self) -> bool:
        """Test retrieving user subscription"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(
                f"{BASE_URL}/my-subscription",
                headers=headers
            )
            
            if response.status_code == 200:
                sub_data = response.json()
                self.print_result("GET /my-subscription", True, f"Active subscription found")
                return True, sub_data
            else:
                self.print_result("GET /my-subscription", False, f"Status {response.status_code}")
                return False, None
        except Exception as e:
            self.print_result("GET /my-subscription", False, str(e))
            return False, None
    
    def run_all_tests(self):
        """Run complete integration test suite"""
        print("\n" + "="*60)
        print("CarSwap Production System - Integration Tests")
        print("="*60 + "\n")
        
        results = {}
        
        # Test 1: Signup
        print("TEST SUITE 1: Authentication")
        print("-" * 60)
        results['signup'] = self.test_signup()
        
        # Test 2: Login
        results['login'] = self.test_login()
        if not self.token:
            print("\nCannot proceed without token. Stopping tests.")
            return results
        
        # Test 3: Get current user
        results['get_current_user'] = self.test_get_current_user()
        
        # Test Suite 2: Data Retrieval
        print("\nTEST SUITE 2: Data Retrieval")
        print("-" * 60)
        results['get_cars'] = self.test_get_cars()
        results['get_subscription_plans'] = self.test_get_subscription_plans()
        
        # Test Suite 3: Security
        print("\nTEST SUITE 3: Security & Access Control")
        print("-" * 60)
        results['protected_without_token'] = self.test_protected_without_token()
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        print(f"\nTests Passed: {passed}/{total}")
        
        for test_name, result in results.items():
            status = "✓" if result else "✗"
            print(f"  {status} {test_name}")
        
        print("\n" + "="*60 + "\n")
        
        return results

if __name__ == "__main__":
    tester = CarSwapTester()
    tester.run_all_tests()
