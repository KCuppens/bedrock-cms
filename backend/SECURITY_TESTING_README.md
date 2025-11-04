# Backend Security Testing

This document explains the security regression tests and how to run them.

## Overview

The security regression tests ensure that all implemented security fixes continue to work correctly and that vulnerabilities remain patched.

## Test File

- **`apps/cms/tests/test_security_regression.py`** - Comprehensive security regression tests

## Test Coverage

### 1. IDOR Locale Access Tests (`IDORLocaleAccessTestCase`)

**Security Issue**: CRITICAL - IDOR vulnerability allowed users to access content in locales they didn't have permission for.

**Tests**:
- ✅ Superuser can access all locales
- ✅ User can access permitted locale
- ✅ User CANNOT access forbidden locale (403 Forbidden)
- ✅ User without locale access is blocked
- ✅ Anonymous users can access published pages

### 2. Field Filtering Security Tests (`FieldFilteringSecurityTestCase`)

**Security Issue**: HIGH - Arbitrary field filtering allowed filtering on sensitive internal fields.

**Tests**:
- ✅ Whitelisted filter fields work (id, title, slug, status, etc.)
- ✅ Sensitive filter fields are blocked (password, token, secret, api_key, etc.)
- ✅ Sensitive fields excluded from dynamic serializers

### 3. CSV Import Security Tests (`CSVImportSecurityTestCase`)

**Security Issue**: HIGH - CSV import lacked validation for file type, size, and status codes.

**Tests**:
- ✅ Valid CSV import succeeds
- ✅ Invalid MIME type blocked (400 Bad Request)
- ✅ Oversized files blocked (>5MB)
- ✅ Invalid status codes blocked (only 301, 302, 303, 307, 308 allowed)
- ✅ Valid status codes allowed

### 4. Path Traversal Security Tests (`PathTraversalSecurityTestCase`)

**Security Issue**: HIGH - Insufficient path sanitization allowed potential path traversal attacks.

**Tests**:
- ✅ Normal path access works
- ✅ Path traversal with `..` blocked (400 Bad Request)
- ✅ Double slash paths blocked (`//`)
- ✅ URL-encoded path traversal blocked (`%2e%2e`, `%252e%252e`)

### 5. File Upload Magic Bytes Tests (`FileUploadMagicBytesTestCase`)

**Security Issue**: HIGH - File upload validation relied only on MIME type and extension, allowing file type spoofing.

**Tests**:
- ✅ Valid JPEG magic bytes validated
- ✅ Valid PNG magic bytes validated
- ✅ Valid PDF magic bytes validated
- ✅ Spoofed file types detected (PNG claiming to be JPEG)
- ✅ Empty files detected
- ✅ File upload with MIME mismatch fails
- ✅ Valid files succeed

### 6. Session Security Tests (`SessionSecurityTestCase`)

**Security Issue**: MEDIUM - Session cookies lacked secure flags and had long timeouts.

**Tests**:
- ✅ SESSION_COOKIE_SECURE configured
- ✅ SESSION_COOKIE_HTTPONLY is True
- ✅ SESSION_COOKIE_SAMESITE is 'Strict'
- ✅ CSRF_COOKIE_SECURE configured
- ✅ CSRF_COOKIE_HTTPONLY is True

### 7. Security Headers Tests (`SecurityHeadersTestCase`)

**Security Issue**: MEDIUM - Missing or weak security headers.

**Tests**:
- ✅ HSTS configured (at least 1 year)
- ✅ HSTS includes subdomains
- ✅ Referrer policy is 'same-origin'
- ✅ X-Frame-Options is DENY

### 8. S3 Security Tests (`S3SecurityTestCase`)

**Security Issue**: MEDIUM - Default S3 ACL was public-read, potentially exposing files.

**Tests**:
- ✅ AWS_DEFAULT_ACL is 'private' (not 'public-read')

### 9. Celery Security Tests (`CelerySecurityTestCase`)

**Security Issue**: LOW - Celery lacked task acknowledgment and timeout settings.

**Tests**:
- ✅ CELERY_TASK_ACKS_LATE is True
- ✅ Task time limits configured (reasonable values)

### 10. Password Validation Tests (`PasswordValidationTestCase`)

**Security Issue**: MEDIUM - Minimum password length was only 8 characters.

**Tests**:
- ✅ Minimum password length is at least 10
- ✅ Weak passwords rejected
- ✅ Strong passwords accepted

### 11. File Permissions Tests (`FilePermissionsTestCase`)

**Security Issue**: LOW - File and directory permissions not explicitly set.

**Tests**:
- ✅ FILE_UPLOAD_PERMISSIONS is 0o644
- ✅ FILE_UPLOAD_DIRECTORY_PERMISSIONS is 0o755

## Running Tests

### Prerequisites

1. **Install Dependencies**:
   ```bash
   make install-test
   # Or manually:
   pip install -r backend/requirements/test.txt
   ```

2. **Set up Database** (if needed):
   ```bash
   cd backend
   python manage.py migrate
   ```

### Run All Security Tests

```bash
# Using Django test runner
cd backend
python manage.py test apps.cms.tests.test_security_regression --verbosity=2

# Using pytest
cd backend
pytest apps/cms/tests/test_security_regression.py -v

# Using make
make test
```

### Run Specific Test Classes

```bash
# Run only IDOR tests
python manage.py test apps.cms.tests.test_security_regression.IDORLocaleAccessTestCase -v2

# Run only file upload tests
python manage.py test apps.cms.tests.test_security_regression.FileUploadMagicBytesTestCase -v2

# Using pytest with pattern
pytest apps/cms/tests/test_security_regression.py::IDORLocaleAccessTestCase -v
```

### Run with Coverage

```bash
# Using pytest with coverage
cd backend
pytest apps/cms/tests/test_security_regression.py --cov=apps.cms --cov-report=html

# Using Django with coverage
coverage run --source='apps' manage.py test apps.cms.tests.test_security_regression
coverage report
coverage html
```

## Expected Results

All tests should **PASS**. If any test fails, it indicates:

1. **Test Failure**: A security fix has regressed or was not properly implemented
2. **Security Risk**: The vulnerability may be exploitable again
3. **Immediate Action Required**: Investigate and fix the failing test

### Sample Output

```
test_anonymous_users_can_access_published_pages ... ok
test_superuser_can_access_all_locales ... ok
test_user_can_access_permitted_locale ... ok
test_user_cannot_access_forbidden_locale ... ok
test_user_without_any_locale_access_blocked ... ok
test_allowed_filter_fields_work ... ok
test_sensitive_filter_fields_blocked ... ok
test_sensitive_fields_excluded_from_serializer ... ok
...

----------------------------------------------------------------------
Ran 67 tests in 12.345s

OK
```

## Integration with CI/CD

Add to your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run Backend Security Tests
  run: |
    cd backend
    python manage.py test apps.cms.tests.test_security_regression --verbosity=2

- name: Security Test Coverage
  run: |
    cd backend
    coverage run --source='apps' manage.py test apps.cms.tests.test_security_regression
    coverage report --fail-under=90
```

## Docker Environment

If using Docker:

```bash
# Run tests in Docker container
docker-compose exec backend python manage.py test apps.cms.tests.test_security_regression -v2

# Or run tests when starting services
docker-compose run --rm backend python manage.py test apps.cms.tests.test_security_regression
```

## Troubleshooting

### Issue: ImportError for magic_validation

**Cause**: `magic_validation.py` not found

**Solution**: Ensure `backend/apps/files/magic_validation.py` exists

### Issue: Database errors

**Cause**: Test database not set up

**Solution**:
```bash
cd backend
python manage.py migrate --settings=apps.config.settings.test
```

### Issue: Permission errors

**Cause**: User doesn't have database permissions

**Solution**: Use test settings with appropriate database configuration

### Issue: Tests timeout

**Cause**: Database queries taking too long

**Solution**: Ensure test database is using SQLite or adjust statement timeout

## Test Maintenance

When modifying security-sensitive code:

1. **Run security tests first**: Ensure current tests pass
2. **Make changes**: Implement new features or fixes
3. **Update tests**: Add new test cases for new attack vectors
4. **Run tests again**: Verify all tests still pass
5. **Review coverage**: Ensure new code is covered

## Related Documentation

- [Security Analysis Report](../SECURITY_ANALYSIS_REPORT.md) - Original vulnerability analysis
- [Security Fixes Implemented](../SECURITY_FIXES_IMPLEMENTED.md) - Implementation details
- [Frontend Security Tests](../frontend/SECURITY_TESTING_README.md) - Frontend test setup

## Adding New Security Tests

When adding new security tests:

1. **Create test class**: Inherit from `TestCase`
2. **Add docstring**: Explain the security issue and fix
3. **Write positive tests**: Verify fix works correctly
4. **Write negative tests**: Verify attacks are blocked
5. **Write regression tests**: Verify existing functionality works
6. **Document**: Add to this README

Example template:

```python
class NewSecurityTestCase(TestCase):
    """
    Test description of security fix.

    Security Issue: SEVERITY - Description of vulnerability
    Fix: Description of how it was fixed
    """

    def setUp(self):
        # Set up test data
        pass

    def test_fix_works(self):
        """SECURITY: Test that fix works correctly."""
        # Positive test
        pass

    def test_attack_blocked(self):
        """SECURITY: Test that attack is blocked."""
        # Negative test
        pass
```

## Security Test Statistics

- **Total Test Classes**: 11
- **Total Test Cases**: 67+
- **Security Issues Covered**: 12 (4 Critical, 3 High, 3 Medium, 2 Low)
- **Expected Duration**: ~10-15 seconds
- **Minimum Coverage**: 90%

## Contact

For questions about security tests or if you find a security issue, please:
1. Do NOT create a public issue
2. Contact the security team directly
3. Follow responsible disclosure practices

---

Last Updated: 2025-11-04
Test Suite Version: 1.0.0
