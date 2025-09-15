# Integration Tests

This directory contains comprehensive cross-app integration tests for the bedrock-cms project.

## Test Suites

### 1. CMS-i18n Integration (`test_cms_i18n_workflows.py`)

Tests the complete integration workflow between the CMS and i18n (internationalization) systems:

- **Page creation with automatic translation units**: Verifies that creating a page automatically generates translation units for all configured target locales
- **Multilingual content publishing workflows**: Tests the complete workflow from draft creation to published multilingual content
- **Locale-specific page retrieval and SEO generation**: Ensures pages can be properly retrieved for specific locales with correct SEO data
- **Translation unit updates when pages are modified**: Verifies that changes to source content properly update translation units and their status

**Key Test Scenarios:**
- Page creation with complex block structures
- Translation workflow with approval processes
- Locale fallback chain integration
- Performance testing with large translation datasets
- Bulk translation operations

### 2. Analytics-Search Integration (`test_analytics_search_workflows.py`)

Tests the integration between Analytics and Search systems:

- **Search query logging and analytics collection**: Ensures all search queries are properly logged with performance metrics
- **Content indexing when CMS content is published**: Verifies that publishing CMS content automatically updates the search index
- **Search result analytics and user behavior tracking**: Tests tracking of user interactions with search results
- **Search suggestions based on query analytics**: Ensures search suggestions are generated from query analytics data

**Key Test Scenarios:**
- Real-time search analytics dashboard data
- Multi-locale search analytics
- Search performance impact on analytics
- Content metrics integration with search data
- Search analytics data retention and cleanup

### 3. Authentication-RBAC Integration (`test_auth_rbac_workflows.py`)

Tests the Role-Based Access Control (RBAC) system integration with authentication:

- **User permission workflows across different apps**: Verifies that user permissions work consistently across CMS, i18n, and other apps
- **Locale-based access control**: Tests that users can be restricted to specific locales
- **Content publishing permissions with user roles**: Ensures proper permission hierarchies for content publishing workflows

**Key Test Scenarios:**
- Multi-group user permissions
- Hierarchical permission inheritance
- Complex RBAC workflow scenarios (multi-language product launch)
- Performance testing with multiple groups and scopes
- Security edge cases and permission validation

## Running the Tests

### Run all integration tests:
```bash
pytest backend/tests/integration/
```

### Run specific test suite:
```bash
pytest backend/tests/integration/test_cms_i18n_workflows.py
pytest backend/tests/integration/test_analytics_search_workflows.py
pytest backend/tests/integration/test_auth_rbac_workflows.py
```

### Run with verbose output:
```bash
pytest backend/tests/integration/ -v
```

### Run with coverage:
```bash
pytest backend/tests/integration/ --cov=apps
```

## Test Data Factories

The integration tests use Factory Boy factories for creating consistent test data:

- **Base factories** (`tests/factories/base.py`): Core user and base model factories
- **CMS factories** (`tests/factories/cms.py`): Page, category, and locale factories
- **i18n factories** (`tests/factories/i18n.py`): Translation unit and locale factories
- **Search factories** (`tests/factories/search.py`): Search index, query, and suggestion factories
- **Analytics factories** (`tests/factories/analytics.py`): Page view and user activity factories

## Test Configuration

- **conftest.py**: Shared pytest fixtures and configuration
- **Integration settings**: Optimized Django settings for integration testing
- **Database access**: All tests have database access configured
- **Performance optimizations**: Disabled migrations and fast password hashing for test speed

## Best Practices

1. **Realistic Data**: Tests use realistic data scenarios that match production usage patterns
2. **Complete Workflows**: Each test covers end-to-end workflows from start to finish
3. **Success and Failure Paths**: Tests include both successful operations and error conditions
4. **Data Consistency**: Tests verify data consistency across apps and models
5. **Performance Considerations**: Large dataset tests ensure system performance at scale
6. **Security Testing**: Permission and access control tests include security edge cases

## Coverage Focus

The integration tests provide comprehensive coverage of:

- Cross-app data flow and consistency
- Permission and access control systems
- Multi-language content workflows
- Search and analytics integration
- User behavior tracking
- Performance at scale
- Security and authorization
- Data integrity across app boundaries

These tests complement the individual app unit tests by focusing on the integration points and ensuring the system works cohesively as a whole.
