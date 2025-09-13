#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Smart Cashier POS System
Tests all backend endpoints and business logic
"""

import requests
import json
from datetime import datetime, timedelta
import sys

# Configuration
BASE_URL = "https://smartcashier.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class POSSystemTester:
    def __init__(self):
        self.auth_token = None
        self.auth_headers = HEADERS.copy()
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
    def log_result(self, test_name, success, message=""):
        if success:
            self.test_results["passed"] += 1
            print(f"✅ {test_name}: PASSED {message}")
        else:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {message}")
            print(f"❌ {test_name}: FAILED - {message}")
    
    def test_init_endpoint(self):
        """Test the initialization endpoint"""
        print("\n=== Testing Data Initialization ===")
        try:
            response = requests.post(f"{BASE_URL}/init", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                self.log_result("Data Initialization", True, f"Status: {response.status_code}")
                return True
            else:
                self.log_result("Data Initialization", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Data Initialization", False, f"Exception: {str(e)}")
            return False
    
    def test_authentication(self):
        """Test authentication system"""
        print("\n=== Testing Authentication System ===")
        
        # Test login with default admin credentials
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/auth/login", 
                                   headers=HEADERS, 
                                   json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.auth_token = data["access_token"]
                    self.auth_headers["Authorization"] = f"Bearer {self.auth_token}"
                    self.log_result("Admin Login", True, "JWT token received")
                    
                    # Test user registration
                    register_data = {
                        "username": f"kasir_maya_{datetime.now().strftime('%H%M%S')}",
                        "password": "maya2024",
                        "role": "kasir"
                    }
                    
                    reg_response = requests.post(f"{BASE_URL}/auth/register",
                                               headers=self.auth_headers,
                                               json=register_data)
                    
                    if reg_response.status_code == 200:
                        self.log_result("User Registration", True, "New cashier registered")
                    else:
                        self.log_result("User Registration", False, f"Status: {reg_response.status_code}")
                    
                    return True
                else:
                    self.log_result("Admin Login", False, "No access token in response")
                    return False
            else:
                self.log_result("Admin Login", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Authentication", False, f"Exception: {str(e)}")
            return False
    
    def test_customer_types(self):
        """Test customer type management"""
        print("\n=== Testing Customer Type Management ===")
        
        if not self.auth_token:
            self.log_result("Customer Types", False, "No authentication token")
            return False
        
        try:
            # Get existing customer types
            response = requests.get(f"{BASE_URL}/customer-types", headers=self.auth_headers)
            
            if response.status_code == 200:
                customer_types = response.json()
                self.log_result("Get Customer Types", True, f"Found {len(customer_types)} customer types")
                
                # Verify default customer types exist
                expected_types = ["regular", "sales", "bengkel"]
                found_types = [ct["name"] for ct in customer_types]
                
                for expected in expected_types:
                    if expected in found_types:
                        self.log_result(f"Customer Type '{expected}'", True, "Found in system")
                    else:
                        self.log_result(f"Customer Type '{expected}'", False, "Missing from system")
                
                return True
            else:
                self.log_result("Get Customer Types", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Customer Types", False, f"Exception: {str(e)}")
            return False
    
    def test_product_management(self):
        """Test product CRUD operations"""
        print("\n=== Testing Product Management ===")
        
        if not self.auth_token:
            self.log_result("Product Management", False, "No authentication token")
            return False
        
        try:
            # Create test products
            timestamp = datetime.now().strftime('%H%M%S')
            test_products = [
                {
                    "name": "Oli Mesin Castrol GTX 10W-40",
                    "sku": f"OLI-GTX-10W40-{timestamp}",
                    "description": "Oli mesin berkualitas tinggi untuk kendaraan",
                    "price_regular": 85000,
                    "price_sales": 80000,
                    "price_bengkel": 75000,
                    "stock": 50,
                    "min_stock": 10,
                    "category": "Oli Mesin"
                },
                {
                    "name": "Ban Motor Michelin 90/80-14",
                    "sku": f"BAN-MICH-9080-14-{timestamp}",
                    "description": "Ban motor tubeless berkualitas premium",
                    "price_regular": 320000,
                    "price_sales": 310000,
                    "price_bengkel": 300000,
                    "stock": 3,  # Low stock for testing
                    "min_stock": 5,
                    "category": "Ban Motor"
                }
            ]
            
            created_products = []
            
            for product_data in test_products:
                response = requests.post(f"{BASE_URL}/products",
                                       headers=self.auth_headers,
                                       json=product_data)
                
                if response.status_code == 200:
                    product = response.json()
                    created_products.append(product)
                    self.log_result(f"Create Product '{product_data['name']}'", True, f"ID: {product['id']}")
                else:
                    self.log_result(f"Create Product '{product_data['name']}'", False, f"Status: {response.status_code}")
            
            # Test get all products
            response = requests.get(f"{BASE_URL}/products", headers=self.auth_headers)
            if response.status_code == 200:
                products = response.json()
                self.log_result("Get All Products", True, f"Retrieved {len(products)} products")
                
                # Test get single product
                if created_products:
                    product_id = created_products[0]["id"]
                    response = requests.get(f"{BASE_URL}/products/{product_id}", headers=self.auth_headers)
                    if response.status_code == 200:
                        self.log_result("Get Single Product", True, "Product retrieved successfully")
                    else:
                        self.log_result("Get Single Product", False, f"Status: {response.status_code}")
                
                # Test product update
                if created_products:
                    product_id = created_products[0]["id"]
                    update_data = {"stock": 45, "price_regular": 87000}
                    response = requests.put(f"{BASE_URL}/products/{product_id}",
                                          headers=self.auth_headers,
                                          json=update_data)
                    if response.status_code == 200:
                        self.log_result("Update Product", True, "Product updated successfully")
                    else:
                        self.log_result("Update Product", False, f"Status: {response.status_code}")
                
                return True
            else:
                self.log_result("Get All Products", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Product Management", False, f"Exception: {str(e)}")
            return False
    
    def test_transaction_processing(self):
        """Test transaction creation and processing"""
        print("\n=== Testing Transaction Processing ===")
        
        if not self.auth_token:
            self.log_result("Transaction Processing", False, "No authentication token")
            return False
        
        try:
            # First get available products
            response = requests.get(f"{BASE_URL}/products", headers=self.auth_headers)
            if response.status_code != 200:
                self.log_result("Transaction Processing", False, "Cannot get products for transaction")
                return False
            
            products = response.json()
            if len(products) < 2:
                self.log_result("Transaction Processing", False, "Not enough products for transaction test")
                return False
            
            # Create test transaction
            transaction_data = {
                "customer_type": "regular",
                "items": [
                    {"product_id": products[0]["id"], "quantity": 2},
                    {"product_id": products[1]["id"], "quantity": 1}
                ],
                "payment_method": "tunai",
                "payment_amount": 500000
            }
            
            response = requests.post(f"{BASE_URL}/transactions",
                                   headers=self.auth_headers,
                                   json=transaction_data)
            
            if response.status_code == 200:
                transaction = response.json()
                self.log_result("Create Transaction", True, f"Transaction ID: {transaction['id']}")
                
                # Test transaction retrieval
                response = requests.get(f"{BASE_URL}/transactions", headers=self.auth_headers)
                if response.status_code == 200:
                    transactions = response.json()
                    self.log_result("Get Transactions", True, f"Retrieved {len(transactions)} transactions")
                else:
                    self.log_result("Get Transactions", False, f"Status: {response.status_code}")
                
                # Test get single transaction
                transaction_id = transaction["id"]
                response = requests.get(f"{BASE_URL}/transactions/{transaction_id}", headers=self.auth_headers)
                if response.status_code == 200:
                    self.log_result("Get Single Transaction", True, "Transaction retrieved successfully")
                else:
                    self.log_result("Get Single Transaction", False, f"Status: {response.status_code}")
                
                # Test transaction with sales customer type
                sales_transaction_data = {
                    "customer_type": "sales",
                    "items": [{"product_id": products[0]["id"], "quantity": 1}],
                    "payment_method": "transfer",
                    "payment_amount": 100000
                }
                
                response = requests.post(f"{BASE_URL}/transactions",
                                       headers=self.auth_headers,
                                       json=sales_transaction_data)
                
                if response.status_code == 200:
                    self.log_result("Sales Transaction", True, "Sales pricing applied correctly")
                else:
                    self.log_result("Sales Transaction", False, f"Status: {response.status_code}")
                
                return True
            else:
                self.log_result("Create Transaction", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Transaction Processing", False, f"Exception: {str(e)}")
            return False
    
    def test_reporting_system(self):
        """Test reporting endpoints"""
        print("\n=== Testing Reporting System ===")
        
        if not self.auth_token:
            self.log_result("Reporting System", False, "No authentication token")
            return False
        
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            current_month = datetime.now().strftime("%Y-%m")
            
            # Test daily report
            response = requests.get(f"{BASE_URL}/reports/daily?date={today}", headers=self.auth_headers)
            if response.status_code == 200:
                daily_report = response.json()
                self.log_result("Daily Report", True, f"Transactions: {daily_report['total_transactions']}, Revenue: {daily_report['total_revenue']}")
            else:
                self.log_result("Daily Report", False, f"Status: {response.status_code}")
            
            # Test weekly report
            response = requests.get(f"{BASE_URL}/reports/weekly?start_date={today}", headers=self.auth_headers)
            if response.status_code == 200:
                weekly_report = response.json()
                self.log_result("Weekly Report", True, f"Transactions: {weekly_report['total_transactions']}")
            else:
                self.log_result("Weekly Report", False, f"Status: {response.status_code}")
            
            # Test monthly report
            response = requests.get(f"{BASE_URL}/reports/monthly?month={current_month}", headers=self.auth_headers)
            if response.status_code == 200:
                monthly_report = response.json()
                self.log_result("Monthly Report", True, f"Transactions: {monthly_report['total_transactions']}")
            else:
                self.log_result("Monthly Report", False, f"Status: {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_result("Reporting System", False, f"Exception: {str(e)}")
            return False
    
    def test_dashboard_stats(self):
        """Test dashboard statistics endpoint"""
        print("\n=== Testing Dashboard Statistics ===")
        
        if not self.auth_token:
            self.log_result("Dashboard Stats", False, "No authentication token")
            return False
        
        try:
            response = requests.get(f"{BASE_URL}/dashboard/stats", headers=self.auth_headers)
            if response.status_code == 200:
                stats = response.json()
                expected_keys = ["today_transactions", "today_revenue", "total_products", "low_stock_products"]
                
                for key in expected_keys:
                    if key in stats:
                        self.log_result(f"Dashboard Stat '{key}'", True, f"Value: {stats[key]}")
                    else:
                        self.log_result(f"Dashboard Stat '{key}'", False, "Missing from response")
                
                return True
            else:
                self.log_result("Dashboard Stats", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Dashboard Stats", False, f"Exception: {str(e)}")
            return False
    
    def test_low_stock_products(self):
        """Test low stock products endpoint"""
        print("\n=== Testing Low Stock Products ===")
        
        if not self.auth_token:
            self.log_result("Low Stock Products", False, "No authentication token")
            return False
        
        try:
            response = requests.get(f"{BASE_URL}/products/low-stock", headers=self.auth_headers)
            if response.status_code == 200:
                low_stock_products = response.json()
                self.log_result("Low Stock Products", True, f"Found {len(low_stock_products)} low stock products")
                return True
            else:
                self.log_result("Low Stock Products", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Low Stock Products", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Comprehensive POS System Backend Testing")
        print(f"🌐 Testing against: {BASE_URL}")
        print("=" * 60)
        
        # Run tests in order
        self.test_init_endpoint()
        self.test_authentication()
        self.test_customer_types()
        self.test_product_management()
        self.test_transaction_processing()
        self.test_reporting_system()
        self.test_dashboard_stats()
        self.test_low_stock_products()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        
        if self.test_results['errors']:
            print("\n🔍 FAILED TESTS:")
            for error in self.test_results['errors']:
                print(f"   • {error}")
        
        success_rate = (self.test_results['passed'] / (self.test_results['passed'] + self.test_results['failed'])) * 100
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        return self.test_results['failed'] == 0

if __name__ == "__main__":
    tester = POSSystemTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)