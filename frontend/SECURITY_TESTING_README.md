# Frontend Security Testing Setup

This document explains how to set up and run the frontend security regression tests.

## Overview

Frontend security tests verify:
1. **XSS Protection**: DOMPurify sanitization in RichtextBlock component
2. **Storage Security**: No sensitive data stored in localStorage/sessionStorage

## Test Files

- `src/components/blocks/__tests__/RichtextBlock.security.test.tsx` - XSS protection tests
- `src/lib/__tests__/api.security.test.ts` - localStorage security tests

## Setup Instructions

### 1. Install Test Dependencies

```bash
cd frontend

# Install Vitest and testing utilities
npm install -D vitest @vitejs/plugin-react jsdom

# Install React Testing Library
npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event

# Install type definitions
npm install -D @types/node
```

### 2. Create Vitest Configuration

Create `frontend/vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react-swc';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: [
        'src/components/**/*.{ts,tsx}',
        'src/lib/**/*.{ts,tsx}',
      ],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/**/__tests__/**',
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

### 3. Create Test Setup File

Create `frontend/src/test/setup.ts`:

```typescript
import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

global.localStorage = localStorageMock as any;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

global.sessionStorage = sessionStorageMock as any;
```

### 4. Update package.json

Add test scripts to `frontend/package.json`:

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:security": "vitest run src/**/*.security.test.*",
    "test:coverage": "vitest run --coverage"
  }
}
```

### 5. Run Tests

```bash
# Run all tests
npm test

# Run only security tests
npm run test:security

# Run with coverage
npm run test:coverage

# Run with UI
npm run test:ui
```

## Test Coverage

### XSS Protection Tests

- ✅ Script tag sanitization
- ✅ Inline event handler removal
- ✅ JavaScript URL blocking
- ✅ Data URL with scripts blocking
- ✅ Safe HTML tag preservation
- ✅ Safe attribute preservation
- ✅ SVG script blocking
- ✅ iframe/object/embed blocking
- ✅ Complex nested HTML preservation
- ✅ Table structure preservation

### localStorage Security Tests

- ✅ No token storage in localStorage
- ✅ No token storage in sessionStorage
- ✅ No token initialization from localStorage
- ✅ No user scopes in localStorage
- ✅ No user roles in localStorage
- ✅ Logout doesn't clear sensitive keys from storage
- ✅ httpOnly cookie-based authentication
- ✅ No sensitive data exposure
- ✅ XSS protection from localStorage
- ✅ Data leakage prevention
- ✅ Storage event listener security

## Continuous Integration

Add to your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run Frontend Security Tests
  run: |
    cd frontend
    npm install
    npm run test:security
```

## Troubleshooting

### Issue: "Cannot find module '@testing-library/react'"

**Solution**: Install the testing library:
```bash
npm install -D @testing-library/react @testing-library/jest-dom
```

### Issue: "ReferenceError: vi is not defined"

**Solution**: Ensure `vitest.config.ts` has `globals: true`:
```typescript
export default defineConfig({
  test: {
    globals: true,  // This enables vi globally
  },
});
```

### Issue: Tests timeout

**Solution**: Increase timeout in `vitest.config.ts`:
```typescript
export default defineConfig({
  test: {
    testTimeout: 10000,  // 10 seconds
  },
});
```

## Security Test Maintenance

When making changes to security-sensitive code:

1. **Update tests** - Ensure tests cover new attack vectors
2. **Run full test suite** - `npm run test:security`
3. **Review coverage** - `npm run test:coverage`
4. **Document changes** - Update this README if test setup changes

## Related Documentation

- [Security Fixes Implementation](../SECURITY_FIXES_IMPLEMENTED.md)
- [Security Analysis Report](../SECURITY_ANALYSIS_REPORT.md)
- [Backend Security Tests](../backend/apps/cms/tests/test_security_regression.py)

## Contact

For questions about security testing, please refer to the security team or create an issue in the repository.
