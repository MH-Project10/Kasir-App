#!/usr/bin/env python3
import requests
import json

BASE_URL = "https://smartcashier.preview.emergentagent.com/api"

# Get auth token
login_response = requests.post(f"{BASE_URL}/auth/login", 
                              headers={"Content-Type": "application/json"},
                              json={"username": "admin", "password": "admin123"})

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Test user registration
    print("=== Testing User Registration ===")
    reg_response = requests.post(f"{BASE_URL}/auth/register",
                               headers=headers,
                               json={"username": "kasir_maya", "password": "maya2024", "role": "kasir"})
    print(f"Status: {reg_response.status_code}")
    print(f"Response: {reg_response.text}")
    
    # Test product creation
    print("\n=== Testing Product Creation ===")
    product_data = {
        "name": "Test Product",
        "sku": "TEST-001",
        "description": "Test product",
        "price_regular": 10000,
        "price_sales": 9000,
        "price_bengkel": 8000,
        "stock": 3,  # Low stock to test low-stock endpoint
        "min_stock": 5,
        "category": "Test"
    }
    
    prod_response = requests.post(f"{BASE_URL}/products",
                                headers=headers,
                                json=product_data)
    print(f"Status: {prod_response.status_code}")
    print(f"Response: {prod_response.text}")
    
    # Test low stock endpoint
    print("\n=== Testing Low Stock Endpoint ===")
    low_stock_response = requests.get(f"{BASE_URL}/products/low-stock", headers=headers)
    print(f"Status: {low_stock_response.status_code}")
    print(f"Response: {low_stock_response.text}")
    
else:
    print(f"Login failed: {login_response.status_code} - {login_response.text}")