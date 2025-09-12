#!/usr/bin/env python3
"""
Simple test script to verify authentication and blog endpoints
"""
import requests

# Base URL for the backend API
BASE_URL = "http://localhost:8000"

def test_endpoint(url, method="GET", data=None, cookies=None):
    """Test an API endpoint and return the response details"""
    try:
        if method == "GET":
            response = requests.get(url, cookies=cookies)
        elif method == "POST":
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=data, headers=headers, cookies=cookies)

        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'content': response.text[:500] if response.text else '',
            'cookies': dict(response.cookies) if response.cookies else {}
        }
    except Exception as e:
        return {'error': str(e)}

def main():
    print("=== Testing Blog API Endpoints ===\n")

    # Test 1: Check if the blog posts list endpoint works
    print("1. Testing blog posts list endpoint:")
    result = test_endpoint(f"{BASE_URL}/api/v1/blog/posts/")
    print(f"   Status: {result.get('status_code', 'ERROR')}")
    print(f"   Content preview: {result.get('content', '')[:100]}...")
    print()

    # Test 2: Check specific blog post
    print("2. Testing specific blog post endpoint:")
    result = test_endpoint(f"{BASE_URL}/api/v1/blog/posts/1/")
    print(f"   Status: {result.get('status_code', 'ERROR')}")
    print(f"   Content preview: {result.get('content', '')[:100]}...")
    print()

    # Test 3: Check publish endpoint without auth
    print("3. Testing publish endpoint (should fail without auth):")
    result = test_endpoint(f"{BASE_URL}/api/v1/blog/posts/1/publish/", method="POST")
    print(f"   Status: {result.get('status_code', 'ERROR')}")
    print(f"   Content: {result.get('content', '')}")
    print()

    # Test 4: Check unpublish endpoint without auth
    print("4. Testing unpublish endpoint (should fail without auth):")
    result = test_endpoint(f"{BASE_URL}/api/v1/blog/posts/1/unpublish/", method="POST")
    print(f"   Status: {result.get('status_code', 'ERROR')}")
    print(f"   Content: {result.get('content', '')}")
    print()

    # Test 5: Check duplicate endpoint without auth
    print("5. Testing duplicate endpoint (should fail without auth):")
    result = test_endpoint(f"{BASE_URL}/api/v1/blog/posts/1/duplicate/", method="POST",
                          data={"title": "Test Duplicate", "locale": 1})
    print(f"   Status: {result.get('status_code', 'ERROR')}")
    print(f"   Content: {result.get('content', '')}")
    print()

    # Test 6: Check current user endpoint
    print("6. Testing current user endpoint:")
    result = test_endpoint(f"{BASE_URL}/auth/users/me/")
    print(f"   Status: {result.get('status_code', 'ERROR')}")
    print(f"   Content: {result.get('content', '')}")
    print()

    print("=== Summary ===")
    print("If you see 403 errors for publish/unpublish/duplicate, that's expected without authentication.")
    print("If you see 404 errors, there's a URL routing issue.")
    print("To use these endpoints, you need to:")
    print("1. Log in through the frontend")
    print("2. Ensure the session cookies are being passed")
    print("3. Include CSRF tokens in the requests")

if __name__ == "__main__":
    main()
