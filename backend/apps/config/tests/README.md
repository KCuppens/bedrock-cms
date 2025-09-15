# Config App Test Suite

This directory contains comprehensive tests for the Django configuration system, covering all aspects of settings management, validation, and environment handling.

## Test Structure

### Core Test Files

- **`test_settings_validation.py`** - Base settings validation and structure tests
- **`test_environment_configs.py`** - Environment-specific configuration tests (local, test, prod)
- **`test_database_config.py`** - Database configuration and connection validation
- **`test_security_settings.py`** - Security settings and validation tests
- **`test_environment_variables.py`** - Environment variable handling and parsing tests
- **`test_celery_config.py`** - Celery task queue configuration tests
- **`test_wsgi_asgi_config.py`** - WSGI/ASGI deployment configuration tests
- **`test_comprehensive_config.py`** - Integration tests that validate overall configuration

## Test Coverage Areas

### 1. Settings Validation (`test_settings_validation.py`)
- **Base Settings Structure**: Validates core Django settings are present and properly configured
- **Environment Variable Handling**: Tests environment variable parsing and type conversion
- **Security Settings**: Validates security-related configurations
- **Database Configuration**: Tests database connection settings and validation
- **Cache Configuration**: Validates cache backend configuration
- **Configuration Consistency**: Tests overall configuration integrity

### 2. Environment-Specific Tests (`test_environment_configs.py`)
- **Base Settings Import**: Tests base settings module loading
- **Test Environment**: Validates test-specific configurations (in-memory DB, fast hashers, etc.)
- **Local Development**: Tests development environment settings
- **Production Settings**: Validates production security and performance settings
- **Settings Inheritance**: Tests proper inheritance chain from base to environment
- **Module Loading**: Tests dynamic settings module loading

### 3. Database Configuration (`test_database_config.py`)
- **Database Setup**: Tests database configuration structure and validity
- **Connection Pooling**: Validates connection pooling and optimization settings
- **PostgreSQL Configuration**: Tests PostgreSQL-specific settings and SSL
- **SQLite Configuration**: Tests SQLite configuration for development/testing
- **Migration Configuration**: Tests database migration settings
- **Connection Security**: Validates database security configurations

### 4. Security Settings (`test_security_settings.py`)
- **Security Middleware**: Tests security middleware presence and ordering
- **Secret Key Validation**: Tests SECRET_KEY strength and security
- **DEBUG Settings**: Validates DEBUG mode implications
- **CORS Security**: Tests CORS configuration security
- **Session Security**: Validates session cookie security settings
- **CSRF Protection**: Tests CSRF protection configuration
- **SSL/HTTPS Settings**: Tests SSL redirect and HSTS settings
- **Authentication Security**: Tests authentication backend security

### 5. Environment Variables (`test_environment_variables.py`)
- **Type Conversion**: Tests boolean, integer, float, list, dict, JSON parsing
- **URL Parsing**: Tests DATABASE_URL, CACHE_URL, EMAIL_URL parsing
- **Default Values**: Tests fallback behavior for missing variables
- **Environment File Loading**: Tests .env file loading and precedence
- **Validation**: Tests error handling for invalid variable values
- **Security**: Tests handling of sensitive environment variables

### 6. Celery Configuration (`test_celery_config.py`)
- **Broker Configuration**: Tests Celery broker URL and connection settings
- **Task Configuration**: Tests task routing, scheduling, and execution settings
- **Worker Configuration**: Tests worker performance and optimization settings
- **Security**: Tests Celery security configurations (serializers, authentication)
- **Environment Integration**: Tests Celery configuration across environments
- **Queue Management**: Tests task queue and routing configuration

### 7. WSGI/ASGI Configuration (`test_wsgi_asgi_config.py`)
- **WSGI Setup**: Tests WSGI application configuration and loading
- **ASGI Setup**: Tests ASGI application configuration and loading
- **Deployment Readiness**: Tests production deployment configurations
- **Consistency**: Tests WSGI/ASGI configuration consistency
- **Server Compatibility**: Tests compatibility with different server types
- **Performance**: Tests performance-related middleware and settings

### 8. Comprehensive Integration (`test_comprehensive_config.py`)
- **Cross-Environment Validation**: Tests settings work across all environments
- **Integration Testing**: Tests how all configuration components work together
- **Security Comprehensive**: End-to-end security configuration validation
- **Performance Comprehensive**: Overall performance configuration testing
- **Maintenance**: Tests logging, monitoring, and maintenance configurations

## Running the Tests

### Run All Config Tests
```bash
cd backend
python -m pytest apps/config/tests/ -v
```

### Run Specific Test Categories
```bash
# Settings validation tests
python -m pytest apps/config/tests/test_settings_validation.py -v

# Environment-specific tests
python -m pytest apps/config/tests/test_environment_configs.py -v

# Security tests
python -m pytest apps/config/tests/test_security_settings.py -v

# Database tests
python -m pytest apps/config/tests/test_database_config.py -v
```

### Run with Coverage
```bash
python -m pytest apps/config/tests/ --cov=apps.config --cov-report=html
```

## Test Configuration

The tests use the `test_minimal` settings module to ensure fast, isolated testing:
- In-memory SQLite database
- Local memory cache
- Disabled logging
- Fast password hashers
- Eager Celery task execution

## Environment Variables for Testing

You can override settings during testing using environment variables:

```bash
# Test with PostgreSQL
export DATABASE_URL=postgres://user:pass@localhost/testdb
python -m pytest apps/config/tests/test_database_config.py

# Test with Redis cache
export REDIS_URL=redis://localhost:6379/0
python -m pytest apps/config/tests/test_settings_validation.py
```

## Key Test Scenarios

### 1. Development Setup Validation
Tests ensure that a developer can:
- Clone the repository
- Set minimal environment variables
- Run the application with default settings
- Override settings for their environment

### 2. Production Deployment Validation
Tests ensure that production deployments:
- Have proper security configurations
- Use environment variables correctly
- Have optimized performance settings
- Handle secrets securely

### 3. CI/CD Pipeline Validation
Tests ensure that CI/CD pipelines:
- Can run with test settings
- Handle database migrations properly
- Cache configurations work correctly
- Environment variable parsing is robust

### 4. Multi-Environment Consistency
Tests ensure that:
- All environments inherit properly from base settings
- Environment-specific overrides work correctly
- No configuration drift between environments
- Settings are consistent across deployments

## Common Issues and Solutions

### Issue: Import Errors in Production Tests
**Solution**: Production tests may fail if production dependencies (Sentry, OpenTelemetry) are not installed. These tests are skipped automatically when dependencies are missing.

### Issue: Database Connection Errors
**Solution**: Database tests use SQLite in-memory by default. Set `DATABASE_URL` environment variable for testing with other databases.

### Issue: Cache Configuration Errors
**Solution**: Tests default to local memory cache. Set `REDIS_URL` for testing Redis configurations.

### Issue: Environment Variable Parsing
**Solution**: Ensure environment variables are properly quoted and formatted. Use the `environ.Env()` methods for type conversion.

## Best Practices for Configuration Testing

1. **Test All Environments**: Ensure tests cover local, test, and production configurations
2. **Use Realistic Data**: Test with realistic environment variable values
3. **Test Error Conditions**: Validate error handling for misconfigured settings
4. **Security First**: Always test security implications of configuration changes
5. **Performance Aware**: Test that configurations don't negatively impact performance
6. **Documentation**: Keep configuration documentation updated with tests

## Extending the Test Suite

When adding new configuration settings:

1. Add validation tests to the appropriate test file
2. Test environment variable handling if applicable
3. Add security tests for sensitive settings
4. Test cross-environment consistency
5. Update comprehensive integration tests
6. Document the configuration in this README

## Maintenance

These tests should be run:
- Before any configuration changes
- As part of the CI/CD pipeline
- Before production deployments
- When adding new environment variables
- When updating Django or dependencies

The test suite provides confidence that configuration changes won't break the application and that security best practices are maintained across all environments.
