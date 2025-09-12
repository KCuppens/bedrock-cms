#!/usr/bin/env python3
"""
Test blog URL routing by making actual HTTP requests
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_blog_urls():
    """Test various blog API endpoints to see which ones work"""
    print("=== Testing Blog API URL Routing ===\n")
    
    endpoints_to_test = [
        ("GET", "/api/v1/blog/", "Blog API root"),
        ("GET", "/api/v1/blog/posts/", "Blog posts list"),
        ("GET", "/api/v1/blog/posts/1/", "Single blog post"),
        ("POST", "/api/v1/blog/posts/1/publish/", "Publish blog post"),
        ("POST", "/api/v1/blog/posts/1/unpublish/", "Unpublish blog post"),
        ("POST", "/api/v1/blog/posts/1/duplicate/", "Duplicate blog post"),
        ("GET", "/api/v1/blog/categories/", "Blog categories"),
        ("GET", "/api/v1/blog/tags/", "Blog tags"),
    ]
    
    results = {}
    
    for method, endpoint, description in endpoints_to_test:
        full_url = f"{BASE_URL}{endpoint}"
        print(f"Testing: {method} {endpoint} ({description})")
        
        try:
            if method == "GET":
                response = requests.get(full_url, timeout=5)
            else:
                response = requests.post(full_url, json={}, timeout=5)
            
            status = response.status_code
            print(f"  Status: {status}")
            
            if status == 200:
                print("  ✅ SUCCESS")
            elif status == 403:
                print("  🔒 FORBIDDEN (Authentication required)")
            elif status == 404:
                print("  ❌ NOT FOUND")
            elif status == 405:
                print("  ⚠️  METHOD NOT ALLOWED")
            else:
                print(f"  ⚠️  OTHER: {status}")
                
            results[endpoint] = status
            
        except requests.RequestException as e:
            print(f"  ❌ CONNECTION ERROR: {e}")
            results[endpoint] = "ERROR"
        
        print()
    
    # Summary
    print("=== Summary ===")
    found_endpoints = [ep for ep, status in results.items() if status in [200, 403]]
    not_found_endpoints = [ep for ep, status in results.items() if status == 404]
    
    print(f"Working endpoints (200/403): {len(found_endpoints)}")
    for ep in found_endpoints:
        print(f"  ✅ {ep}")
    
    print(f"\nMissing endpoints (404): {len(not_found_endpoints)}")
    for ep in not_found_endpoints:
        print(f"  ❌ {ep}")

if __name__ == "__main__":
    test_blog_urls()