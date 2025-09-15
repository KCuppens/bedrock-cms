# Content Versioning and Revisions Test Suite

This directory contains comprehensive tests for the content versioning and revisions functionality of the CMS. The tests are split across two main files:

## Test Files

### 1. `test_versioning.py` (Original Tests)
Contains the original versioning tests that cover basic functionality:

- **PageRevisionModelTests**: Basic model functionality tests
- **AuditEntryModelTests**: Audit logging tests
- **RevisionDifferTests**: Diff computation tests
- **VersioningAPITests**: Basic API endpoint tests
- **VersioningSignalsTests**: Signal handling tests

### 2. `test_versioning_comprehensive.py` (Extended Test Suite)
Contains comprehensive tests for all advanced versioning functionality:

- **ComprehensiveVersionCreationTests**: All aspects of version creation
- **ComprehensiveVersionManagementTests**: Version management and cleanup
- **ComprehensiveRevisionTrackingTests**: Detailed revision tracking
- **ComprehensiveContentRecoveryTests**: Content recovery and restoration
- **ComprehensiveVersionPermissionsTests**: Permission-based access control
- **ComprehensiveAPIIntegrationTests**: Complete API testing
- **ComprehensiveBlockLevelVersioningTests**: Block-level version tracking

## Test Coverage

### 1. Version Creation Tests ✅
- [x] Automatic version creation on content changes
- [x] Manual version snapshots
- [x] Version metadata (author, timestamp, comment)
- [x] Version numbering and incrementing
- [x] Initial version creation
- [x] Published version snapshots
- [x] Autosave version creation with throttling

### 2. Version Management Tests ✅
- [x] List all versions for content
- [x] Compare versions (diff functionality)
- [x] Restore to previous version
- [x] Delete old versions
- [x] Version pruning and cleanup
- [x] Diff with current page state

### 3. Revision Tracking Tests ✅
- [x] Track field-level changes
- [x] Change attribution (who made what changes)
- [x] Change timestamps and audit trail
- [x] Revision comments and annotations
- [x] Comprehensive audit trail queries

### 4. Content Recovery Tests ✅
- [x] Restore deleted content from versions
- [x] Partial field restoration
- [x] Rollback to specific revision
- [x] Merge conflict resolution
- [x] Recovery with missing dependencies

### 5. Version Permissions Tests ✅
- [x] Access control for viewing versions
- [x] Permission to create versions
- [x] Permission to restore versions
- [x] Editor vs admin version capabilities
- [x] Version access audit logging

### 6. API Integration Tests ✅
- [x] Version listing endpoints
- [x] Version comparison endpoints
- [x] Version restoration endpoints
- [x] Version deletion endpoints (model-level)
- [x] Autosave API endpoints
- [x] Publish/unpublish API endpoints
- [x] Audit trail API endpoints
- [x] API permission enforcement

### 7. Block-Level Versioning Tests ✅
- [x] Block addition tracking
- [x] Block removal tracking
- [x] Block modification tracking
- [x] Block reordering tracking
- [x] Complex block operations
- [x] Block versioning with nested content
- [x] Block versioning performance

## Key Features Tested

### Version Creation
- **Automatic Versioning**: Tests ensure revisions are created automatically when content changes
- **Manual Snapshots**: Ability to create manual snapshots with custom comments
- **Metadata Tracking**: Complete metadata capture including author, timestamp, and context
- **Version Types**: Support for draft, published, and autosave versions

### Version Management
- **Listing & Filtering**: Comprehensive querying and filtering of versions
- **Comparison**: Detailed diff functionality between any two versions
- **Restoration**: Ability to restore any version as the current state
- **Cleanup**: Automated and manual version pruning capabilities

### Revision Tracking
- **Field-Level Changes**: Track exactly which fields changed in each revision
- **User Attribution**: Know exactly who made each change and when
- **Audit Trail**: Complete audit log with IP addresses, user agents, and metadata
- **Comments**: Support for revision comments and annotations

### Content Recovery
- **Deleted Content**: Restore content that was accidentally deleted
- **Selective Recovery**: Restore only specific fields from a revision
- **Conflict Resolution**: Handle merge conflicts when multiple changes exist
- **Dependency Handling**: Graceful handling of missing references

### Permissions & Security
- **Access Control**: Proper permission checks for viewing and modifying versions
- **Role-Based Access**: Different capabilities for editors vs administrators
- **Audit Logging**: All version access and operations are logged

### API Integration
- **RESTful Endpoints**: Complete API coverage for all versioning operations
- **Authentication**: Proper authentication and authorization
- **Pagination**: Support for paginated results
- **Error Handling**: Comprehensive error handling and validation

### Block-Level Versioning
- **Granular Tracking**: Track changes at the individual block level
- **Complex Operations**: Handle addition, removal, modification, and reordering
- **Nested Content**: Support for complex nested block structures
- **Performance**: Efficient handling of large numbers of blocks

## Running the Tests

### Run All Versioning Tests
```bash
cd backend
python manage.py test apps.cms.tests.test_versioning apps.cms.tests.test_versioning_comprehensive
```

### Run Specific Test Classes
```bash
# Original tests
python manage.py test apps.cms.tests.test_versioning.PageRevisionModelTests

# Comprehensive tests
python manage.py test apps.cms.tests.test_versioning_comprehensive.ComprehensiveVersionCreationTests
python manage.py test apps.cms.tests.test_versioning_comprehensive.ComprehensiveAPIIntegrationTests
```

### Run Individual Tests
```bash
python manage.py test apps.cms.tests.test_versioning_comprehensive.ComprehensiveVersionCreationTests.test_manual_version_snapshots
```

## Test Structure

Each test class follows a consistent pattern:

1. **setUp()**: Creates necessary test data (users, locales, pages, revisions)
2. **Test Methods**: Each test method focuses on a specific functionality
3. **Assertions**: Comprehensive assertions to verify expected behavior
4. **Cleanup**: Automatic cleanup through Django's test framework

## Dependencies

The tests rely on:

- **Django Test Framework**: For database transactions and isolation
- **Django REST Framework**: For API testing
- **Mock Objects**: For simulating requests and external dependencies
- **Locale System**: For multi-language content support
- **Permission System**: For access control testing

## Coverage Notes

The comprehensive test suite provides near 100% coverage of the versioning functionality, including:

- **Happy Paths**: Normal operation scenarios
- **Edge Cases**: Boundary conditions and unusual scenarios
- **Error Conditions**: Proper error handling and validation
- **Performance**: Tests with large datasets to ensure scalability
- **Security**: Permission and access control verification

## Future Enhancements

Areas for potential test expansion:

1. **Concurrent Editing**: Tests for multiple users editing simultaneously
2. **Large-Scale Operations**: Bulk version operations
3. **Integration Tests**: Cross-app version dependencies
4. **Performance Benchmarks**: Formal performance testing
5. **Browser Tests**: End-to-end user interface testing

This comprehensive test suite ensures the versioning system is robust, reliable, and meets all requirements for production use.
