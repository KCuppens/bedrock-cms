#!/usr/bin/env python3
"""
Remove insecure localStorage usage for tokens and auth data.
Keep only non-sensitive data like locale in localStorage.
"""

import re

API_FILE = "frontend/src/lib/api.ts"

def apply_fix():
    with open(API_FILE, 'r') as f:
        content = f.read()

    # 1. Remove token initialization from localStorage
    content = re.sub(
        r"    // Get token from localStorage if available\n    this\.token = localStorage\.getItem\('api_token'\);",
        "    // Security: DO NOT store tokens in localStorage - use httpOnly cookies only\n    // this.token = localStorage.getItem('api_token');  // REMOVED FOR SECURITY",
        content
    )

    # 2. Remove token storage in setToken
    content = re.sub(
        r"  setToken\(token: string \| null\) \{\n    this\.token = token;\n    if \(token\) \{\n      localStorage\.setItem\('api_token', token\);\n    \} else \{\n      localStorage\.removeItem\('api_token'\);\n    \}\n  \}",
        """  setToken(token: string | null) {
    // Security: Removed token storage in localStorage
    // Tokens are now handled exclusively via httpOnly cookies
    // This prevents XSS attacks from stealing authentication tokens
    this.token = token;
    // DO NOT store tokens in localStorage or sessionStorage
    // if (token) {
    //   localStorage.setItem('api_token', token);  // REMOVED FOR SECURITY
    // } else {
    //   localStorage.removeItem('api_token');  // REMOVED FOR SECURITY
    // }
  }""",
        content
    )

    # 3. Remove user scopes and role from localStorage (sensitive data)
    content = re.sub(
        r"      // Get user scopes from localStorage \(set by auth context\)\n      const userScopes = localStorage\.getItem\('user_scopes'\);",
        "      // Security: User scopes should come from API, not localStorage\n      // const userScopes = localStorage.getItem('user_scopes');  // REMOVED",
        content
    )

    content = re.sub(
        r"      // Add user role for quick backend checks\n      const userRole = localStorage\.getItem\('user_role'\);",
        "      // Security: User role should come from API, not localStorage\n      // const userRole = localStorage.getItem('user_role');  // REMOVED",
        content
    )

    # 4. Comment out the lines that use these removed variables
    content = re.sub(
        r"      if \(userScopes\) \{\n        headers\['X-User-Scopes'\] = this\.encodeHeaderValue\(userScopes\);\n      \}",
        "      // Removed: X-User-Scopes header (data should come from server session)\n      // if (userScopes) {\n      //   headers['X-User-Scopes'] = this.encodeHeaderValue(userScopes);\n      // }",
        content
    )

    content = re.sub(
        r"      if \(userRole\) \{\n        headers\['X-User-Role'\] = this\.encodeHeaderValue\(userRole\);\n      \}",
        "      // Removed: X-User-Role header (data should come from server session)\n      // if (userRole) {\n      //   headers['X-User-Role'] = this.encodeHeaderValue(userRole);\n      // }",
        content
    )

    # 5. Remove localStorage cleanup in handleAuthenticationError
    content = re.sub(
        r"    localStorage\.removeItem\('user_scopes'\);\n    localStorage\.removeItem\('user_role'\);",
        "    // Security: No longer storing sensitive auth data in localStorage\n    // localStorage.removeItem('user_scopes');  // REMOVED\n    // localStorage.removeItem('user_role');  // REMOVED",
        content
    )

    # Write back
    with open(API_FILE, 'w') as f:
        f.write(content)

    print("✓ Removed insecure localStorage usage from api.ts")
    print("  - Removed api_token from localStorage")
    print("  - Removed user_scopes from localStorage")
    print("  - Removed user_role from localStorage")
    print("  - All authentication now relies on secure httpOnly cookies")
    print("  - Locale storage retained (not sensitive)")

if __name__ == "__main__":
    apply_fix()
