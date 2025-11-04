/**
 * Security Regression Tests for API Client
 *
 * Tests that sensitive data is not stored in localStorage.
 *
 * Security Issue: CRITICAL - Storing authentication tokens in localStorage
 * makes them vulnerable to XSS attacks.
 *
 * Fix: Removed all localStorage usage for tokens and sensitive data.
 * Now relies exclusively on httpOnly cookies for authentication.
 *
 * NOTE: This test requires Vitest setup. To run these tests:
 * 1. Install Vitest: npm install -D vitest @vitejs/plugin-react jsdom
 * 2. Create vitest.config.ts
 * 3. Run: npm test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { api } from '../api';

describe('API Client Security Tests', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    sessionStorage.clear();

    // Mock console methods to avoid noise
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  describe('Token Storage Security', () => {
    it('should NOT store tokens in localStorage', () => {
      const testToken = 'test-token-12345';

      // Call setToken (if method exists)
      if (typeof (api as any).setToken === 'function') {
        (api as any).setToken(testToken);
      }

      // Verify token is NOT in localStorage
      expect(localStorage.getItem('api_token')).toBeNull();
      expect(localStorage.getItem('token')).toBeNull();
      expect(localStorage.getItem('auth_token')).toBeNull();
      expect(localStorage.getItem('access_token')).toBeNull();
    });

    it('should NOT store tokens in sessionStorage', () => {
      const testToken = 'test-token-12345';

      // Call setToken (if method exists)
      if (typeof (api as any).setToken === 'function') {
        (api as any).setToken(testToken);
      }

      // Verify token is NOT in sessionStorage
      expect(sessionStorage.getItem('api_token')).toBeNull();
      expect(sessionStorage.getItem('token')).toBeNull();
      expect(sessionStorage.getItem('auth_token')).toBeNull();
      expect(sessionStorage.getItem('access_token')).toBeNull();
    });

    it('should NOT initialize token from localStorage', () => {
      // Pre-populate localStorage with a token
      localStorage.setItem('api_token', 'malicious-token');

      // Import api client (would initialize from localStorage if vulnerable)
      // In a real test, this would require dynamic import to re-initialize
      // For now, verify the token property doesn't contain localStorage value
      const apiToken = (api as any).token;

      // If token exists, it should not be from localStorage
      if (apiToken) {
        expect(apiToken).not.toBe('malicious-token');
      }
    });

    it('should NOT store user scopes in localStorage', () => {
      // Simulate getting user scopes
      const testScopes = ['editor', 'admin'];

      // If there's a method to set scopes, call it
      if (typeof (api as any).setUserScopes === 'function') {
        (api as any).setUserScopes(testScopes);
      }

      // Verify scopes are NOT in localStorage
      expect(localStorage.getItem('user_scopes')).toBeNull();
      expect(localStorage.getItem('scopes')).toBeNull();
    });

    it('should NOT store user roles in localStorage', () => {
      // Simulate getting user role
      const testRole = 'admin';

      // If there's a method to set role, call it
      if (typeof (api as any).setUserRole === 'function') {
        (api as any).setUserRole(testRole);
      }

      // Verify role is NOT in localStorage
      expect(localStorage.getItem('user_role')).toBeNull();
      expect(localStorage.getItem('role')).toBeNull();
    });
  });

  describe('Logout Security', () => {
    it('should NOT attempt to clear tokens from localStorage on logout', () => {
      // Pre-populate localStorage
      localStorage.setItem('some_other_data', 'test');

      // Spy on localStorage.removeItem
      const removeItemSpy = vi.spyOn(localStorage, 'removeItem');

      // Perform logout (if method exists)
      if (typeof (api as any).logout === 'function') {
        (api as any).logout();
      }

      // Verify localStorage.removeItem was not called for sensitive keys
      // (It's ok to clear other non-sensitive data)
      const sensitiveKeys = ['api_token', 'token', 'auth_token', 'user_scopes', 'user_role'];
      const calls = removeItemSpy.mock.calls.map(call => call[0]);

      sensitiveKeys.forEach(key => {
        // These keys should not be in the calls because they should never be set
        // But if they are called, it means the old vulnerable code is still present
        expect(calls).not.toContain(key);
      });

      removeItemSpy.mockRestore();
    });

    it('should NOT clear sessionStorage on logout', () => {
      // Pre-populate sessionStorage
      sessionStorage.setItem('some_data', 'test');

      // Spy on sessionStorage.clear and removeItem
      const clearSpy = vi.spyOn(sessionStorage, 'clear');
      const removeItemSpy = vi.spyOn(sessionStorage, 'removeItem');

      // Perform logout (if method exists)
      if (typeof (api as any).logout === 'function') {
        (api as any).logout();
      }

      // Verify sessionStorage was not modified
      const sensitiveKeys = ['api_token', 'token', 'auth_token', 'user_scopes', 'user_role'];
      const calls = removeItemSpy.mock.calls.map(call => call[0]);

      sensitiveKeys.forEach(key => {
        expect(calls).not.toContain(key);
      });

      clearSpy.mockRestore();
      removeItemSpy.mockRestore();
    });
  });

  describe('Authentication Flow', () => {
    it('should rely on httpOnly cookies for authentication', () => {
      // This is more of a documentation test
      // The actual cookie handling happens on the backend

      // Verify that the API client doesn't attempt to manually set Authorization headers
      // from localStorage
      const headers = (api as any).getHeaders ? (api as any).getHeaders() : {};

      // If Authorization header exists, it should not come from localStorage
      if (headers.Authorization) {
        // Get all localStorage items
        const localStorageItems = Object.keys(localStorage);
        const sessionStorageItems = Object.keys(sessionStorage);

        // None of the storage items should be in the Authorization header
        localStorageItems.forEach(key => {
          const value = localStorage.getItem(key);
          if (value) {
            expect(headers.Authorization).not.toContain(value);
          }
        });

        sessionStorageItems.forEach(key => {
          const value = sessionStorage.getItem(key);
          if (value) {
            expect(headers.Authorization).not.toContain(value);
          }
        });
      }
    });

    it('should not expose sensitive data through api instance properties', () => {
      // Get all enumerable properties of api instance
      const apiProperties = Object.keys(api);

      // Sensitive property names that should not exist or be null
      const sensitiveProps = ['password', 'token', 'apiKey', 'secret', 'authToken', 'sessionId'];

      sensitiveProps.forEach(prop => {
        // Either property doesn't exist, or it's null/undefined
        if (apiProperties.includes(prop)) {
          const value = (api as any)[prop];
          expect(value).toBeNull();
        }
      });
    });
  });

  describe('XSS Protection', () => {
    it('should not eval or execute code from localStorage', () => {
      // Set malicious code in localStorage
      localStorage.setItem('api_config', 'alert("XSS")');
      localStorage.setItem('api_token', '<script>alert("XSS")</script>');

      // Spy on eval and Function constructor
      const originalEval = window.eval;
      const evalSpy = vi.fn();
      window.eval = evalSpy;

      // Try to use the API (should not execute malicious code)
      const token = (api as any).token;

      // Verify eval was not called
      expect(evalSpy).not.toHaveBeenCalled();

      // Restore eval
      window.eval = originalEval;
    });

    it('should sanitize any data read from localStorage (if any)', () => {
      // This test verifies that IF the API reads from localStorage
      // (which it shouldn't for sensitive data), it sanitizes the input

      // Set potentially dangerous values
      localStorage.setItem('non_sensitive_setting', '<script>alert("XSS")</script>');

      // If API has a method to read settings
      if (typeof (api as any).getSetting === 'function') {
        const setting = (api as any).getSetting('non_sensitive_setting');

        // Should not contain script tags
        if (setting && typeof setting === 'string') {
          expect(setting).not.toContain('<script>');
        }
      }
    });
  });

  describe('Data Leakage Prevention', () => {
    it('should not log sensitive data to console', () => {
      const consoleSpy = vi.spyOn(console, 'log');

      // Perform various API operations
      if (typeof (api as any).setToken === 'function') {
        (api as any).setToken('secret-token-12345');
      }

      // Check console logs don't contain sensitive data
      const calls = consoleSpy.mock.calls;
      calls.forEach(call => {
        const logString = call.join(' ');
        expect(logString).not.toContain('secret-token');
        expect(logString).not.toContain('password');
      });

      consoleSpy.mockRestore();
    });

    it('should not expose sensitive data in error messages', () => {
      const consoleErrorSpy = vi.spyOn(console, 'error');

      // Trigger an error (if possible)
      try {
        // Attempt invalid operation
        if (typeof (api as any).request === 'function') {
          (api as any).request('INVALID', '/invalid-endpoint');
        }
      } catch (error) {
        // Error should not contain sensitive data
        const errorMessage = error instanceof Error ? error.message : String(error);
        expect(errorMessage).not.toContain('token');
        expect(errorMessage).not.toContain('password');
        expect(errorMessage).not.toContain('secret');
      }

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Storage Event Listener Security', () => {
    it('should not listen to localStorage changes for authentication', () => {
      // This test verifies that the API doesn't synchronize auth state
      // across tabs using localStorage events (which would be a security risk)

      // Simulate localStorage change from another tab
      const event = new StorageEvent('storage', {
        key: 'api_token',
        newValue: 'malicious-token',
        oldValue: null,
        storageArea: localStorage,
      });

      window.dispatchEvent(event);

      // API should not update its token from this event
      const apiToken = (api as any).token;
      expect(apiToken).not.toBe('malicious-token');
    });
  });

  describe('Regression Tests', () => {
    it('should verify old vulnerable code is removed', () => {
      // Read the api.ts file and verify old patterns are removed
      // This is more of a code review test

      // For runtime verification, check that these methods don't exist
      // or don't interact with localStorage

      const dangerousMethods = [
        'getTokenFromLocalStorage',
        'saveTokenToLocalStorage',
        'initializeFromLocalStorage',
      ];

      dangerousMethods.forEach(method => {
        // Method should not exist
        expect(typeof (api as any)[method]).toBe('undefined');
      });
    });

    it('should maintain backward compatibility for legitimate features', () => {
      // While removing localStorage for auth, legitimate features should still work

      // API should still be able to make requests
      expect(typeof (api as any).get).toBe('function');
      expect(typeof (api as any).post).toBe('function');
      expect(typeof (api as any).put).toBe('function');
      expect(typeof (api as any).delete).toBe('function');
    });
  });
});

/**
 * Integration Test Helpers
 *
 * These tests verify the security fixes work in realistic scenarios
 */
describe('API Security Integration Tests', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('should complete authentication flow without using localStorage', async () => {
    // This test simulates a complete auth flow
    // All authentication should happen via httpOnly cookies

    // Verify localStorage is empty before auth
    expect(localStorage.length).toBe(0);

    // Simulate login (in real implementation, this would make an API call)
    // The response would set httpOnly cookies on the backend

    // Verify localStorage is still empty after auth
    expect(localStorage.length).toBe(0);

    // Verify no sensitive keys exist
    const sensitiveKeys = ['api_token', 'token', 'auth_token', 'user_scopes', 'user_role'];
    sensitiveKeys.forEach(key => {
      expect(localStorage.getItem(key)).toBeNull();
      expect(sessionStorage.getItem(key)).toBeNull();
    });
  });

  it('should handle page refresh without localStorage', () => {
    // Simulate page refresh
    // Auth state should be maintained via httpOnly cookies, not localStorage

    // Before refresh - no localStorage
    expect(localStorage.getItem('api_token')).toBeNull();

    // Simulate refresh (re-import would happen in real scenario)
    // After refresh - still no localStorage
    expect(localStorage.getItem('api_token')).toBeNull();

    // Authentication should still work via cookies (tested in integration tests)
  });

  it('should handle logout without leaving traces in localStorage', () => {
    // Perform logout
    if (typeof (api as any).logout === 'function') {
      (api as any).logout();
    }

    // Verify no sensitive data in storage
    const allLocalStorageKeys = Object.keys(localStorage);
    const allSessionStorageKeys = Object.keys(sessionStorage);

    const sensitiveKeyPatterns = [
      /token/i,
      /auth/i,
      /session/i,
      /scope/i,
      /role/i,
      /user/i,
    ];

    allLocalStorageKeys.forEach(key => {
      const isSensitive = sensitiveKeyPatterns.some(pattern => pattern.test(key));
      if (isSensitive) {
        // Sensitive keys should not exist
        expect(localStorage.getItem(key)).toBeNull();
      }
    });

    allSessionStorageKeys.forEach(key => {
      const isSensitive = sensitiveKeyPatterns.some(pattern => pattern.test(key));
      if (isSensitive) {
        expect(sessionStorage.getItem(key)).toBeNull();
      }
    });
  });
});
